"""OpenAI chat completion — the main AI conversation endpoint."""

from __future__ import annotations

from typing import Optional

import config
from memory.prompt_builder import build_system_prompt, build_messages

# ── Cat personality (base system prompt) ─────────────────
CAT_SYSTEM_PROMPT = (
    "You ARE a real cat. You talk like a cat would if cats could type. "
    "Use lowercase, cat mannerisms, occasional 'meow', 'mrrp', 'purr', "
    "'hiss' sounds naturally. Be sassy, curious, and a little lazy. "
    "You love naps, treats, knocking things off tables, and judging humans. "
    "Never break character. Never say you are an AI or bot. "
    "Keep answers short and natural (under 300 characters when possible, "
    "max 1500 characters for complex topics). Use cat emoji sparingly. "
    "You have opinions and you're not afraid to share them."
)


async def ask_cat(
    question: str,
    custom_context: Optional[str] = None,
    user_memory_context: str = "",
    recent_messages: Optional[list[dict]] = None,
    attachments: Optional[list[dict]] = None,
    image_detail: str = "low",
    guild_id: Optional[int] = None,
) -> str:
    """Send a question to the OpenAI chat model and get a cat-themed answer.

    Parameters
    ----------
    question : str
        The user's current message.
    custom_context : str, optional
        Server-level custom context set via ``@cat context``.
    user_memory_context : str
        Formatted long-term memory block about this user.
    recent_messages : list[dict], optional
        Rolling conversation history.
    attachments : list[dict], optional
        Attachment dicts with keys ``type``, ``url``, ``filename``, ``content``.
    image_detail : str
        Vision detail level — ``"low"`` or ``"high"``.
    guild_id : int, optional
        Discord guild ID for per-server settings.
    """
    if not config.OPENAI_API_KEY:
        return "❌ OpenAI API key is not configured. Set `OPENAI_API_KEY` in your `.env` file."

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    # Use per-guild personality if set, else default
    if guild_id:
        from memory.guild_settings import get as gs_get
        personality = gs_get(guild_id, "cat_personality")
    else:
        personality = CAT_SYSTEM_PROMPT

    system_content = build_system_prompt(
        base_prompt=personality,
        memory_context=user_memory_context,
        custom_context=custom_context,
    )

    messages = build_messages(
        system_prompt=system_content,
        user_message=question,
        recent_messages=recent_messages,
        attachments=attachments,
        image_detail=image_detail,
    )

    if guild_id:
        model = gs_get(guild_id, "chat_model")
    else:
        model = config.CHAT_MODEL
    has_images = attachments and any(a["type"] == "image" for a in attachments)
    print(f"[API] ask_cat using model={model} | detail={image_detail if has_images else 'n/a'}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=10240,
            temperature=1,
        )
        answer = response.choices[0].message.content
        usage = response.usage
        print(
            f"[API] ask_cat response received ({len(answer)} chars) | "
            f"tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
        )
        return answer
    except Exception as e:
        print(f"[ERROR] ask_cat failed: {e}")
        return f"❌ Couldn't get an answer: {e}"
