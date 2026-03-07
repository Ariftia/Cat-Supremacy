"""Per-guild runtime settings — persisted to JSON, editable from Discord.

Every setting falls back to the value in ``config.py`` if not overridden.
Guild admins can change values via the ``@cat settings`` command and they
take effect immediately without a bot restart.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any

import config

# ── File path ────────────────────────────────────────────
_SETTINGS_FILE = os.path.join(config.DATA_DIR, "guild_settings.json")

# ── Registry of all customisable keys ────────────────────
# Maps setting name → (description, type, config-default attr)
SETTING_DEFS: dict[str, dict[str, Any]] = {
    # Schedule
    "morning_hour":           {"desc": "Morning post hour (0-23 UTC)",       "type": int,   "default_attr": "MORNING_HOUR"},
    "afternoon_hour":         {"desc": "Afternoon post hour (0-23 UTC)",     "type": int,   "default_attr": "AFTERNOON_HOUR"},
    "evening_hour":           {"desc": "Evening post hour (0-23 UTC)",       "type": int,   "default_attr": "EVENING_HOUR"},
    # Embed colours (stored as int, shown as hex)
    "morning_color":          {"desc": "Morning embed colour (hex)",         "type": int,   "default_attr": "MORNING_COLOR"},
    "afternoon_color":        {"desc": "Afternoon embed colour (hex)",       "type": int,   "default_attr": "AFTERNOON_COLOR"},
    "evening_color":          {"desc": "Evening embed colour (hex)",         "type": int,   "default_attr": "EVENING_COLOR"},
    # AI
    "chat_model":             {"desc": "OpenAI chat model",                  "type": str,   "default_attr": "CHAT_MODEL"},
    "extraction_model":       {"desc": "Memory extraction model",            "type": str,   "default_attr": "EXTRACTION_MODEL"},
    "cat_personality":        {"desc": "Cat personality system prompt",       "type": str,   "default_attr": None},
    # Memory
    "memory_top_k":           {"desc": "Memories retrieved per query",       "type": int,   "default_attr": "MEMORY_TOP_K"},
    "max_memories_per_user":  {"desc": "Max memories stored per user",       "type": int,   "default_attr": "MAX_MEMORIES_PER_USER"},
    "max_recent_messages":    {"desc": "Conversation history window size",   "type": int,   "default_attr": "MAX_RECENT_MESSAGES"},
    "conversation_ttl_days":  {"desc": "Days before inactive conversations are pruned", "type": int, "default_attr": "CONVERSATION_TTL_DAYS"},
    # Challenges
    "challenge_reminder_hours": {"desc": "Hours between challenge reminders", "type": int,  "default_attr": "CHALLENGE_REMINDER_HOURS"},
    # Channel
    "cat_channel_id":         {"desc": "Channel ID for scheduled cat posts", "type": int,   "default_attr": "CAT_CHANNEL_ID"},
}

# Default cat personality (matches services/openai_chat.py)
_DEFAULT_PERSONALITY = (
    "You ARE a real cat. You talk like a cat would if cats could type. "
    "Use lowercase, cat mannerisms, occasional 'meow', 'mrrp', 'purr', "
    "'hiss' sounds naturally. Be sassy, curious, and a little lazy. "
    "You love naps, treats, knocking things off tables, and judging humans. "
    "Never break character. Never say you are an AI or bot. "
    "Keep answers short and natural (under 300 characters when possible, "
    "max 1500 characters for complex topics). Use cat emoji sparingly. "
    "You have opinions and you're not afraid to share them."
)


# ── In-memory cache ──────────────────────────────────────
_cache: dict[str, dict[str, Any]] = {}


def _ensure_data_dir() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)


def load_all_settings() -> dict[str, dict[str, Any]]:
    """Load settings for every guild from disk into the cache."""
    global _cache
    _ensure_data_dir()
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
            print(f"[SETTINGS] Loaded settings for {len(_cache)} guild(s)")
        except Exception as e:
            print(f"[ERROR] Failed to load guild settings: {e}")
            _cache = {}
    else:
        _cache = {}
    return _cache


def save_all_settings() -> None:
    """Persist the current cache to disk."""
    _ensure_data_dir()
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save guild settings: {e}")


def _guild_key(guild_id: int) -> str:
    return str(guild_id)


def get_default(key: str) -> Any:
    """Return the global default for a setting key."""
    defn = SETTING_DEFS.get(key)
    if defn is None:
        return None
    if key == "cat_personality":
        return _DEFAULT_PERSONALITY
    attr = defn.get("default_attr")
    if attr and hasattr(config, attr):
        return getattr(config, attr)
    return None


def get(guild_id: int, key: str) -> Any:
    """Get a setting value for a guild, falling back to the global default."""
    gk = _guild_key(guild_id)
    guild_data = _cache.get(gk, {})
    if key in guild_data:
        return guild_data[key]
    return get_default(key)


def set(guild_id: int, key: str, value: Any) -> None:
    """Set a setting value for a guild and persist."""
    gk = _guild_key(guild_id)
    if gk not in _cache:
        _cache[gk] = {}
    _cache[gk][key] = value
    save_all_settings()
    print(f"[SETTINGS] {key} = {value!r} for guild {guild_id}")


def reset(guild_id: int, key: str) -> Any:
    """Reset a setting to its global default and return the default value."""
    gk = _guild_key(guild_id)
    if gk in _cache and key in _cache[gk]:
        del _cache[gk][key]
        if not _cache[gk]:
            del _cache[gk]
        save_all_settings()
    return get_default(key)


def get_all_overrides(guild_id: int) -> dict[str, Any]:
    """Return all settings that have been explicitly overridden for a guild."""
    gk = _guild_key(guild_id)
    return dict(_cache.get(gk, {}))


def get_full_settings(guild_id: int) -> dict[str, Any]:
    """Return a dict of every setting with its effective value for a guild."""
    result: dict[str, Any] = {}
    for key in SETTING_DEFS:
        result[key] = get(guild_id, key)
    return result
