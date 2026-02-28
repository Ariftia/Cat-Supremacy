"""
Per-user memory system for Cat Supremacy Bot.

Stores two things per user (token-efficient):
1. **Recent messages** – a short rolling window (last 8 turns) so the AI has
   conversational context without burning tokens on ancient history.
2. **Long-term memories** – compact bullet-point facts the AI extracts after
   each conversation (name, preferences, topics discussed, etc.).  These are
   tiny strings that survive across sessions and get pruned after 30 days.

Persistence: a single JSON file (`user_memories.json`) saved on every write.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Tunables ─────────────────────────────────────────────
MAX_RECENT_MESSAGES = 10          # per-user rolling window (user+assistant pairs)
MAX_MEMORY_CHARS = 1000          # hard cap on the long-term summary text
MEMORY_TTL_DAYS = 30             # auto-prune memories older than this
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "user_memories.json")


# ── Data structures ──────────────────────────────────────
@dataclass
class UserMemory:
    user_id: int
    username: str = ""
    # Rolling recent conversation (list of {"role": ..., "content": ...})
    recent_messages: list[dict] = field(default_factory=list)
    # Compact long-term facts extracted by the AI (bullet points)
    long_term_notes: str = ""
    # Epoch timestamp of last interaction
    last_seen: float = 0.0

    def trim_recent(self):
        """Keep only the latest MAX_RECENT_MESSAGES pairs."""
        # Each "pair" is 2 entries (user + assistant), keep last N*2 entries
        max_entries = MAX_RECENT_MESSAGES * 2
        if len(self.recent_messages) > max_entries:
            self.recent_messages = self.recent_messages[-max_entries:]

    def add_exchange(self, user_msg: str, assistant_msg: str):
        """Append a user/assistant turn and trim."""
        self.recent_messages.append({"role": "user", "content": user_msg})
        self.recent_messages.append({"role": "assistant", "content": assistant_msg})
        self.last_seen = time.time()
        self.trim_recent()

    def build_context_block(self) -> str:
        """Return a compact string for injection into the system prompt."""
        parts: list[str] = []
        if self.long_term_notes:
            parts.append(f"[Memory about this user]\n{self.long_term_notes}")
        return "\n".join(parts)

    def build_recent_for_api(self) -> list[dict]:
        """Return the recent messages formatted for the OpenAI messages array."""
        return list(self.recent_messages)


# ── In-memory store ──────────────────────────────────────
_store: dict[int, UserMemory] = {}


def get_user_memory(user_id: int, username: str = "") -> UserMemory:
    """Get or create a UserMemory for the given user."""
    if user_id not in _store:
        _store[user_id] = UserMemory(user_id=user_id, username=username)
        print(f"[MEMORY] Created new memory for user {username} (ID: {user_id})")
    mem = _store[user_id]
    if username:
        mem.username = username
    return mem


# ── Persistence ──────────────────────────────────────────
def save_all():
    """Persist the entire store to disk."""
    print(f"[MEMORY] Saving memories for {len(_store)} users to disk...")
    data = {}
    for uid, mem in _store.items():
        data[str(uid)] = asdict(mem)
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[MEMORY] Memories saved successfully")
    except Exception as e:
        print(f"[WARNING] Failed to save memories: {e}")


def load_all():
    """Load memories from disk (call once at startup)."""
    print("[MEMORY] Loading memories from disk...")
    global _store
    if not os.path.exists(MEMORY_FILE):
        return
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for uid_str, blob in data.items():
            uid = int(uid_str)
            _store[uid] = UserMemory(
                user_id=uid,
                username=blob.get("username", ""),
                recent_messages=blob.get("recent_messages", []),
                long_term_notes=blob.get("long_term_notes", ""),
                last_seen=blob.get("last_seen", 0.0),
            )
        print(f"[INFO] Loaded memories for {len(_store)} users.")
    except Exception as e:
        print(f"[WARNING] Failed to load memories: {e}")


def prune_old_memories():
    """Remove users who haven't interacted in MEMORY_TTL_DAYS days."""
    print(f"[MEMORY] Pruning memories older than {MEMORY_TTL_DAYS} days...")
    cutoff = time.time() - (MEMORY_TTL_DAYS * 86400)
    to_remove = [uid for uid, mem in _store.items() if mem.last_seen < cutoff and mem.last_seen > 0]
    for uid in to_remove:
        del _store[uid]
    if to_remove:
        print(f"[MEMORY] Pruned memories for {len(to_remove)} inactive users.")
        save_all()
    else:
        print("[MEMORY] No old memories to prune")


# ── Export / Import ──────────────────────────────────────
def export_user_memory(user_id: int) -> Optional[str]:
    """Export a single user's memory as a JSON string. Returns None if no data."""
    mem = _store.get(user_id)
    if mem is None:
        return None
    return json.dumps(asdict(mem), ensure_ascii=False, indent=2)


def export_all_memories() -> str:
    """Export the entire memory store as a JSON string."""
    data = {str(uid): asdict(mem) for uid, mem in _store.items()}
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_user_memory(user_id: int, raw_json: str) -> str:
    """Import a single user's memory from a JSON string.

    Returns a status message (success or error description).
    """
    try:
        blob = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    # Accept both single-user and full-store formats
    if "user_id" in blob:
        # Single-user export
        _store[user_id] = UserMemory(
            user_id=user_id,
            username=blob.get("username", ""),
            recent_messages=blob.get("recent_messages", []),
            long_term_notes=blob.get("long_term_notes", ""),
            last_seen=blob.get("last_seen", time.time()),
        )
        save_all()
        print(f"[MEMORY] Imported single-user memory for user {user_id}")
        return "ok"
    else:
        return "Unrecognized format — expected a single-user memory JSON."


def import_all_memories(raw_json: str) -> tuple[int, str]:
    """Import a full memory store from a JSON string.

    Returns ``(count_imported, error_or_empty)``.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return 0, f"Invalid JSON: {e}"

    if not isinstance(data, dict):
        return 0, "Expected a JSON object with user IDs as keys."

    count = 0
    for uid_str, blob in data.items():
        try:
            uid = int(uid_str)
        except ValueError:
            continue
        _store[uid] = UserMemory(
            user_id=uid,
            username=blob.get("username", ""),
            recent_messages=blob.get("recent_messages", []),
            long_term_notes=blob.get("long_term_notes", ""),
            last_seen=blob.get("last_seen", 0.0),
        )
        count += 1

    save_all()
    print(f"[MEMORY] Imported memories for {count} users from uploaded file")
    return count, ""


# ── Memory extraction prompt (run after each exchange) ───
EXTRACT_PROMPT = (
    "You are a memory manager. Given the conversation below, extract ONLY new "
    "important facts about the user that would be useful to remember in future "
    "conversations. Output ONLY a short bullet-point list of new facts "
    "(name, preferences, interests, location, pets, important events, etc.). "
    "If there are no new facts worth remembering, output exactly: NONE\n"
    "Keep it very concise — max 3 bullet points, each under 80 characters.\n"
    "Do NOT repeat facts already in the existing memory."
)


async def extract_and_update_memories(
    user_id: int,
    username: str,
    user_message: str,
    assistant_response: str,
    existing_notes: str,
) -> None:
    """Use the AI to extract important facts and merge into long-term memory."""
    import config

    if not config.OPENAI_API_KEY:
        print("[MEMORY] Extraction skipped — no OpenAI API key")
        return

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    print(f"[MEMORY] Extracting memories for user {username} (ID: {user_id})...")

    # Build a tiny extraction request
    extraction_input = (
        f"Existing memory:\n{existing_notes or '(none)'}\n\n"
        f"Latest exchange:\nUser ({username}): {user_message[:500]}\n"
        f"Assistant: {assistant_response[:500]}"
    )

    try:
        resp = await client.chat.completions.create(
            model="gpt-4.1-nano",  # cheapest model — extraction is simple
            messages=[
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": extraction_input},
            ],
            max_completion_tokens=200,
            temperature=0.3,
        )
        usage = resp.usage
        print(
            f"[MEMORY] Extraction API call | "
            f"tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
        )
        new_facts = resp.choices[0].message.content.strip()

        if new_facts and new_facts.upper() != "NONE":
            mem = get_user_memory(user_id, username)
            if mem.long_term_notes:
                merged = f"{mem.long_term_notes}\n{new_facts}"
            else:
                merged = new_facts
            # Cap total length
            mem.long_term_notes = merged[:MAX_MEMORY_CHARS]
            save_all()
            print(f"[MEMORY] New facts extracted and saved for {username}: {new_facts[:80]}")
        else:
            print(f"[MEMORY] No new facts to extract for {username}")
    except Exception as e:
        print(f"[WARNING] Memory extraction failed for {username}: {e}")
