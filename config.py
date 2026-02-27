import os
from dotenv import load_dotenv

load_dotenv()

# ── Discord ──────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CAT_CHANNEL_ID: int = int(os.getenv("CAT_CHANNEL_ID", "0"))

# ── The Cat API (optional key for higher rate limits) ────
CAT_API_KEY: str = os.getenv("CAT_API_KEY", "")

# ── Schedule times (24-hour format, UTC) ─────────────────
MORNING_HOUR = 8    # 08:00 UTC
AFTERNOON_HOUR = 14 # 14:00 UTC
EVENING_HOUR = 20   # 20:00 UTC

# ── API endpoints ────────────────────────────────────────
CAT_GIF_URL = "https://api.thecatapi.com/v1/images/search"
CAT_FACT_URL = "https://catfact.ninja/fact"

# ── Embed colors ─────────────────────────────────────────
MORNING_COLOR = 0xFFD700   # Gold
AFTERNOON_COLOR = 0xFF8C00 # Dark Orange
EVENING_COLOR = 0x6A0DAD   # Purple
