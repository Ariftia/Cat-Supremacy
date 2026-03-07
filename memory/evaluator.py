"""AI-driven memory extraction and evaluation.

After the bot responds to a user, this module evaluates the exchange with
a lightweight model to decide if any long-term memories should be stored.
"""

from __future__ import annotations

import json

import config
from memory.vector_store import search_memories, store_memory

# ── Extraction prompt ────────────────────────────────────

EVALUATE_AND_EXTRACT_PROMPT = """\
You are a memory evaluation assistant.  Your job is to decide whether the
user's message contains important long-term information worth remembering,
and if so, produce a short memory summary.

Important information includes:
  • User preferences, hobbies, interests
  • Personal facts (name, location, pets, job, etc.)
  • Projects they are working on, goals, plans
  • Recurring topics or personality traits

Do NOT store:
  • Greetings, small talk, one-word messages
  • Temporary questions with no lasting value
  • Information already present in the existing memories

Existing memories for this user:
{existing_memories}

Latest exchange:
User ({username}): {user_message}
Assistant: {assistant_response}

If there is important new info, respond with a JSON array of objects:
[{{"text": "concise memory summary", "category": "preference|hobby|project|fact|personality|goal"}}]

If there is nothing worth storing, respond with exactly: NONE

Rules:
  - Each summary must be under 100 characters
  - Maximum 3 new memories per message
  - Be concise: "User is building an ESP32 hydroponic system" not "The user
    mentioned they are currently building..."
  - Use third-person ("User …")
"""


async def evaluate_and_store_memories(
    user_id: int,
    username: str,
    user_message: str,
    assistant_response: str,
    guild_id: int | None = None,
) -> int:
    """Evaluate a conversation exchange and store any important memories.

    Returns the number of new memories stored (0 if nothing noteworthy).
    """
    if not config.OPENAI_API_KEY:
        print("[VECMEM] Memory evaluation skipped — no OpenAI API key")
        return 0

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    # Fetch existing memories to prevent duplicates
    existing = await search_memories(user_id, user_message, top_k=10)
    existing_text = "\n".join(f"- {m.memory_text}" for m in existing) if existing else "(none)"

    prompt = EVALUATE_AND_EXTRACT_PROMPT.format(
        existing_memories=existing_text,
        username=username,
        user_message=user_message[:500],
        assistant_response=assistant_response[:500],
    )

    try:
        if guild_id:
            from memory.guild_settings import get as gs_get
            extraction_model = gs_get(guild_id, "extraction_model")
        else:
            extraction_model = config.EXTRACTION_MODEL
        resp = await client.chat.completions.create(
            model=extraction_model,
            messages=[
                {"role": "system", "content": "You extract user memories. Respond only with JSON or NONE."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=300,
            temperature=0.3,
        )
        usage = resp.usage
        print(
            f"[VECMEM] Evaluation API call for {username} | "
            f"tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
        )
        raw = resp.choices[0].message.content.strip()

        if not raw or raw.upper() == "NONE":
            print(f"[VECMEM] No new memories to store for {username}")
            return 0

        # Parse the JSON response
        try:
            if raw.startswith("```"):
                raw = raw.strip("`").strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            new_memories = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[VECMEM] Could not parse extraction response: {raw[:100]}")
            return 0

        if not isinstance(new_memories, list):
            new_memories = [new_memories]

        stored = 0
        for mem_item in new_memories[:3]:
            text = mem_item.get("text", "").strip() if isinstance(mem_item, dict) else str(mem_item).strip()
            category = mem_item.get("category", "general") if isinstance(mem_item, dict) else "general"
            if text and len(text) > 5:
                success = await store_memory(user_id, text, category=category)
                if success:
                    stored += 1

        if stored:
            print(f"[VECMEM] Stored {stored} new memories for {username}")
        return stored

    except Exception as e:
        print(f"[VECMEM] Memory evaluation failed for {username}: {e}")
        return 0
