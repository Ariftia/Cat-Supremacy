"""Challenge system — daily and weekly challenges with participation tracking.

Provides persistent storage for per-guild challenges.  Each challenge has
a mode (daily / weekly), participant list, and completion tracking.
Deadlines auto-renew: when a daily challenge expires it resets for the
next day; weekly challenges reset for the next week.

Storage: ``data/challenges.json``
"""

from __future__ import annotations

import datetime
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import config

# ── Helpers ──────────────────────────────────────────────


def _end_of_today_utc() -> float:
    """Timestamp for 23:59:59 UTC today (or tomorrow if already past)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    if now >= end:
        end += datetime.timedelta(days=1)
    return end.timestamp()


def _end_of_week_utc() -> float:
    """Timestamp for Sunday 23:59:59 UTC of the current week."""
    now = datetime.datetime.now(datetime.timezone.utc)
    days_until_sunday = 6 - now.weekday()  # Monday=0 … Sunday=6
    if days_until_sunday == 0 and now.hour >= 23 and now.minute >= 59:
        days_until_sunday = 7
    end = (now + datetime.timedelta(days=days_until_sunday)).replace(
        hour=23, minute=59, second=59, microsecond=0,
    )
    return end.timestamp()


def _next_deadline(mode: str) -> float:
    """Compute the next deadline for a given mode."""
    if mode == "daily":
        return _end_of_today_utc()
    return _end_of_week_utc()


def _format_deadline(ts: float) -> str:
    """Human-readable UTC deadline string."""
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return dt.strftime("%A %Y-%m-%d %H:%M UTC")


# ── Data model ───────────────────────────────────────────


@dataclass
class Challenge:
    """A single daily or weekly challenge in a guild."""

    id: int
    guild_id: int
    channel_id: int                # channel where reminders are sent
    title: str
    description: str
    mode: str                      # "daily" | "weekly"
    created_by: int                # Discord user ID
    created_at: float
    deadline: float
    active: bool = True
    participants: list[int] = field(default_factory=list)      # user IDs
    completions: dict[str, float] = field(default_factory=dict) # str(uid)->ts

    # ── Queries ──────────────────────────────────────────

    @property
    def incomplete_participants(self) -> list[int]:
        """Participants who have NOT completed this cycle."""
        return [uid for uid in self.participants if str(uid) not in self.completions]

    @property
    def is_expired(self) -> bool:
        return time.time() > self.deadline

    def has_completed(self, user_id: int) -> bool:
        return str(user_id) in self.completions

    # ── Mutations ────────────────────────────────────────

    def join(self, user_id: int) -> bool:
        """Add a participant.  Returns False if already joined."""
        if user_id in self.participants:
            return False
        self.participants.append(user_id)
        return True

    def leave(self, user_id: int) -> bool:
        """Remove a participant.  Returns False if not joined."""
        if user_id not in self.participants:
            return False
        self.participants.remove(user_id)
        self.completions.pop(str(user_id), None)
        return True

    def complete(self, user_id: int) -> bool:
        """Mark a participant as done.  Returns False if not a participant
        or already completed."""
        if user_id not in self.participants:
            return False
        key = str(user_id)
        if key in self.completions:
            return False
        self.completions[key] = time.time()
        return True

    def renew(self) -> None:
        """Reset completions and advance the deadline for the next cycle."""
        self.completions.clear()
        self.deadline = _next_deadline(self.mode)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Challenge":
        return cls(**data)


# ── Per-guild store ──────────────────────────────────────

_guilds: dict[int, dict] = {}
# Structure: { guild_id: { "next_id": int, "challenges": [Challenge, …] } }

_SAVE_PATH: str = ""


def _path() -> str:
    global _SAVE_PATH
    if not _SAVE_PATH:
        _SAVE_PATH = os.path.join(config.DATA_DIR, "challenges.json")
    return _SAVE_PATH


def _ensure_guild(guild_id: int) -> dict:
    if guild_id not in _guilds:
        _guilds[guild_id] = {"next_id": 1, "challenges": []}
    return _guilds[guild_id]


# ── Persistence ──────────────────────────────────────────


def load_challenges() -> None:
    """Load challenges from disk (call once at startup)."""
    global _guilds
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        print("[CHALLENGE] No challenges file found — starting fresh")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for gid_str, gdata in raw.items():
            gid = int(gid_str)
            challenges = [Challenge.from_dict(c) for c in gdata.get("challenges", [])]
            _guilds[gid] = {
                "next_id": gdata.get("next_id", 1),
                "challenges": challenges,
            }
        total = sum(len(g["challenges"]) for g in _guilds.values())
        print(f"[CHALLENGE] Loaded {total} challenges across {len(_guilds)} guilds")
    except Exception as e:
        print(f"[WARNING] Failed to load challenges: {e}")


def save_challenges() -> None:
    """Persist all challenges to disk."""
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {}
    for gid, gdata in _guilds.items():
        data[str(gid)] = {
            "next_id": gdata["next_id"],
            "challenges": [c.to_dict() for c in gdata["challenges"]],
        }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[CHALLENGE] Challenges saved")
    except Exception as e:
        print(f"[WARNING] Failed to save challenges: {e}")


# ── Public API ───────────────────────────────────────────


def create_challenge(
    guild_id: int,
    channel_id: int,
    title: str,
    description: str,
    mode: str,
    created_by: int,
) -> Challenge:
    """Create and persist a new challenge.  Returns the created object."""
    gdata = _ensure_guild(guild_id)
    cid = gdata["next_id"]
    gdata["next_id"] = cid + 1

    challenge = Challenge(
        id=cid,
        guild_id=guild_id,
        channel_id=channel_id,
        title=title,
        description=description,
        mode=mode,
        created_by=created_by,
        created_at=time.time(),
        deadline=_next_deadline(mode),
    )
    gdata["challenges"].append(challenge)
    save_challenges()
    print(f"[CHALLENGE] Created #{cid} '{title}' ({mode}) in guild {guild_id}")
    return challenge


def get_challenge(guild_id: int, challenge_id: int) -> Optional[Challenge]:
    """Retrieve a single challenge by guild + ID."""
    gdata = _guilds.get(guild_id)
    if not gdata:
        return None
    for c in gdata["challenges"]:
        if c.id == challenge_id:
            return c
    return None


def get_active_challenges(guild_id: int, mode: str = None) -> list[Challenge]:
    """Return all active challenges for a guild, optionally filtered by mode."""
    gdata = _guilds.get(guild_id)
    if not gdata:
        return []
    result = [c for c in gdata["challenges"] if c.active]
    if mode:
        result = [c for c in result if c.mode == mode]
    return result


def get_all_guild_challenges(guild_id: int) -> list[Challenge]:
    """Return every challenge (active or not) for a guild."""
    gdata = _guilds.get(guild_id)
    if not gdata:
        return []
    return list(gdata["challenges"])


def delete_challenge(guild_id: int, challenge_id: int) -> bool:
    """Remove a challenge from the store.  Returns True if found."""
    gdata = _guilds.get(guild_id)
    if not gdata:
        return False
    before = len(gdata["challenges"])
    gdata["challenges"] = [c for c in gdata["challenges"] if c.id != challenge_id]
    if len(gdata["challenges"]) < before:
        save_challenges()
        print(f"[CHALLENGE] Deleted #{challenge_id} from guild {guild_id}")
        return True
    return False


def check_and_renew_expired() -> list[Challenge]:
    """Scan all guilds for expired active challenges and renew them.

    Returns the list of challenges that were renewed (so the caller can
    send reset notifications).
    """
    renewed: list[Challenge] = []
    for gdata in _guilds.values():
        for c in gdata["challenges"]:
            if c.active and c.is_expired:
                c.renew()
                renewed.append(c)
    if renewed:
        save_challenges()
        print(f"[CHALLENGE] Renewed {len(renewed)} expired challenges")
    return renewed


def get_incomplete_challenges() -> list[Challenge]:
    """Return all active challenges that have participants who haven't completed."""
    result: list[Challenge] = []
    for gdata in _guilds.values():
        for c in gdata["challenges"]:
            if c.active and c.incomplete_participants:
                result.append(c)
    return result
