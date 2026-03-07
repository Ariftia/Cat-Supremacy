"""Rolling per-user conversation history with JSON persistence.

Manages a short recent-messages window and delegates long-term memory
storage to the vector store (via ``memory.evaluator``).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import config


# ── Data structures ──────────────────────────────────────

@dataclass
class UserConversation:
    """Per-user rolling conversation state."""

    user_id: int
    username: str = ""
    recent_messages: list[dict] = field(default_factory=list)
    # Legacy field — kept for backward compat with old JSON files.
    long_term_notes: str = ""
    last_seen: float = 0.0

    def trim_recent(self):
        """Keep only the latest MAX_RECENT_MESSAGES pairs."""
        max_entries = config.MAX_RECENT_MESSAGES * 2
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
_store: dict[int, UserConversation] = {}


def get_user_memory(user_id: int, username: str = "") -> UserConversation:
    """Get or create a UserConversation for the given user."""
    if user_id not in _store:
        _store[user_id] = UserConversation(user_id=user_id, username=username)
        print(f"[MEMORY] Created new conversation record for user {username} (ID: {user_id})")
    mem = _store[user_id]
    if username:
        mem.username = username
    return mem


# ── Persistence ──────────────────────────────────────────

def _conversations_path() -> str:
    """Return the path to the conversations JSON file, creating the
    parent directory if it doesn't exist."""
    path = config.CONVERSATIONS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def save_all():
    """Persist the entire store to disk."""
    print(f"[MEMORY] Saving conversations for {len(_store)} users to disk...")
    data = {}
    for uid, mem in _store.items():
        data[str(uid)] = asdict(mem)
    try:
        with open(_conversations_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[MEMORY] Conversations saved successfully")
    except Exception as e:
        print(f"[WARNING] Failed to save conversations: {e}")


def load_all():
    """Load conversations from disk (call once at startup)."""
    print("[MEMORY] Loading conversations from disk...")
    global _store
    path = _conversations_path()
    if not os.path.exists(path):
        # Check legacy location
        legacy_path = os.path.join(config.PROJECT_ROOT, "user_memories.json")
        if os.path.exists(legacy_path):
            print(f"[MEMORY] Found legacy file at {legacy_path} — migrating to {path}")
            path = legacy_path
        else:
            return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for uid_str, blob in data.items():
            uid = int(uid_str)
            _store[uid] = UserConversation(
                user_id=uid,
                username=blob.get("username", ""),
                recent_messages=blob.get("recent_messages", []),
                long_term_notes=blob.get("long_term_notes", ""),
                last_seen=blob.get("last_seen", 0.0),
            )
        print(f"[INFO] Loaded conversations for {len(_store)} users.")
    except Exception as e:
        print(f"[WARNING] Failed to load conversations: {e}")


def prune_old_conversations():
    """Remove users who haven't interacted in CONVERSATION_TTL_DAYS days."""
    ttl_days = config.CONVERSATION_TTL_DAYS
    print(f"[MEMORY] Pruning conversations older than {ttl_days} days...")
    cutoff = time.time() - (ttl_days * 86400)
    to_remove = [uid for uid, mem in _store.items() if mem.last_seen < cutoff and mem.last_seen > 0]
    for uid in to_remove:
        del _store[uid]
    if to_remove:
        print(f"[MEMORY] Pruned conversations for {len(to_remove)} inactive users.")
        save_all()
    else:
        print("[MEMORY] No old conversations to prune")


# ── Export / Import ──────────────────────────────────────

def export_user_conversation(user_id: int) -> Optional[str]:
    """Export a single user's conversation as a JSON string."""
    mem = _store.get(user_id)
    if mem is None:
        return None
    return json.dumps(asdict(mem), ensure_ascii=False, indent=2)


def export_all_conversations() -> str:
    """Export the entire conversation store as a JSON string."""
    data = {str(uid): asdict(mem) for uid, mem in _store.items()}
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_user_conversation(user_id: int, raw_json: str) -> str:
    """Import a single user's conversation from a JSON string."""
    try:
        blob = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    if "user_id" in blob:
        _store[user_id] = UserConversation(
            user_id=user_id,
            username=blob.get("username", ""),
            recent_messages=blob.get("recent_messages", []),
            long_term_notes=blob.get("long_term_notes", ""),
            last_seen=blob.get("last_seen", time.time()),
        )
        save_all()
        print(f"[MEMORY] Imported single-user conversation for user {user_id}")
        return "ok"
    else:
        return "Unrecognized format — expected a single-user conversation JSON."


def import_all_conversations(raw_json: str) -> tuple[int, str]:
    """Import a full conversation store from a JSON string."""
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
        _store[uid] = UserConversation(
            user_id=uid,
            username=blob.get("username", ""),
            recent_messages=blob.get("recent_messages", []),
            long_term_notes=blob.get("long_term_notes", ""),
            last_seen=blob.get("last_seen", 0.0),
        )
        count += 1

    save_all()
    print(f"[MEMORY] Imported conversations for {count} users from uploaded file")
    return count, ""


# ── Memory extraction thin wrapper ───────────────────────

async def extract_and_update_memories(
    user_id: int,
    username: str,
    user_message: str,
    assistant_response: str,
    existing_notes: str = "",
    guild_id: int | None = None,
) -> None:
    """Evaluate an exchange and store any valuable memories in the vector DB."""
    from memory.evaluator import evaluate_and_store_memories

    try:
        count = await evaluate_and_store_memories(
            user_id, username, user_message, assistant_response,
            guild_id=guild_id,
        )
        if count:
            print(f"[MEMORY] {count} new vector memories extracted for {username}")
    except Exception as e:
        print(f"[WARNING] Vector memory extraction failed for {username}: {e}")


async def migrate_legacy_notes_to_vector_store() -> int:
    """Migrate old flat-text ``long_term_notes`` into ChromaDB.

    Call once at startup after ``load_all()``.
    Returns the total number of memories migrated.
    """
    from memory.vector_store import store_memory

    total = 0
    migrated_users: list[int] = []

    for uid, mem in _store.items():
        if not mem.long_term_notes or not mem.long_term_notes.strip():
            continue
        lines = [
            line.lstrip("-•* ").strip()
            for line in mem.long_term_notes.splitlines()
            if line.strip() and len(line.strip()) > 3
        ]
        for line in lines:
            try:
                ok = await store_memory(uid, line, category="legacy")
                if ok:
                    total += 1
            except Exception as e:
                print(f"[MEMORY] Failed to migrate note for user {uid}: {e}")

        migrated_users.append(uid)

    for uid in migrated_users:
        _store[uid].long_term_notes = ""
    if migrated_users:
        save_all()
        print(f"[MEMORY] Migrated {total} legacy notes from {len(migrated_users)} users to vector store")

    return total
