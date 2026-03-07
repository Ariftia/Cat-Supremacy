"""Prompt assembly for the OpenAI chat model.

Constructs the system prompt and messages array, injecting retrieved
vector memories so the assistant can recall past user information.
"""

from __future__ import annotations

from typing import Optional

from memory.models import Memory


def format_memories_block(memories: list[Memory]) -> str:
    """Format a list of retrieved Memory objects into a readable block.

    Returns an empty string if the list is empty.
    """
    if not memories:
        return ""

    lines = ["[User Memories — things you remember about this user]"]
    for mem in memories:
        cat_tag = f" ({mem.category})" if mem.category and mem.category != "general" else ""
        lines.append(f"- {mem.memory_text}{cat_tag}")

    return "\n".join(lines)


def build_system_prompt(
    base_prompt: str,
    memory_context: str = "",
    custom_context: str | None = None,
) -> str:
    """Assemble the full system prompt with optional memory and custom context."""
    parts = [base_prompt]

    if memory_context:
        parts.append(
            "\n\nYou have long-term memories about this user from past "
            "conversations. Use them naturally — reference what you know when "
            "relevant, but don't list them all at once. Act as if you genuinely "
            "remember these things.\n\n" + memory_context
        )

    if custom_context:
        parts.append(f"\n\nAdditional context provided by the user:\n{custom_context}")

    return "".join(parts)


def build_messages(
    system_prompt: str,
    user_message: str,
    recent_messages: list[dict] | None = None,
    attachments: list[dict] | None = None,
    image_detail: str = "low",
) -> list[dict]:
    """Build the full messages array for the OpenAI chat API.

    Returns a ready-to-send messages list for
    ``client.chat.completions.create()``.
    """
    messages = [{"role": "system", "content": system_prompt}]

    if recent_messages:
        messages.extend(recent_messages)

    if attachments:
        user_content: list[dict] = []
        text_parts = [user_message] if user_message else []
        for att in attachments:
            if att["type"] == "text":
                text_parts.append(f"\n[Attached file: {att['filename']}]\n{att['content']}")
        if text_parts:
            user_content.append({"type": "text", "text": "\n".join(text_parts)})
        for att in attachments:
            if att["type"] == "image":
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": att["url"], "detail": image_detail},
                })
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": user_message})

    return messages
