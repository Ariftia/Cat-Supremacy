import os
from dotenv import load_dotenv

load_dotenv()

# ── Project Paths ────────────────────────────────────────
PROJECT_ROOT: str = os.path.dirname(__file__)
DATA_DIR: str = os.path.join(PROJECT_ROOT, "data")

# ── Discord ──────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CAT_CHANNEL_ID: int = int(os.getenv("CAT_CHANNEL_ID", "0"))

# ── The Cat API (optional key for higher rate limits) ────
CAT_API_KEY: str = os.getenv("CAT_API_KEY", "")

# ── OpenAI ───────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ── Schedule times (24-hour format, UTC) ─────────────────
MORNING_HOUR = 5 - 11 + 24
AFTERNOON_HOUR = 12 - 11
EVENING_HOUR = 20 - 11

# ── API endpoints ────────────────────────────────────────
CAT_GIF_URL = "https://api.thecatapi.com/v1/images/search"
CAT_FACT_URL = "https://catfact.ninja/fact"

# ── Embed colors ─────────────────────────────────────────
MORNING_COLOR = 0xFFD700   # Gold
AFTERNOON_COLOR = 0xFF8C00 # Dark Orange
EVENING_COLOR = 0x6A0DAD   # Purple

# ── AI Models ────────────────────────────────────────────
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4.1-mini")
EXTRACTION_MODEL: str = os.getenv("EXTRACTION_MODEL", "gpt-4.1-nano")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

# ── Vector Memory (ChromaDB) ────────────────────────────
CHROMA_PERSIST_DIR: str = os.getenv(
    "CHROMA_PERSIST_DIR",
    os.path.join(DATA_DIR, "chroma_data"),
)
CHROMA_COLLECTION_NAME: str = "user_memories"
MEMORY_TOP_K: int = int(os.getenv("MEMORY_TOP_K", "5"))
MAX_MEMORIES_PER_USER: int = int(os.getenv("MAX_MEMORIES_PER_USER", "150"))

# ── Conversation History ────────────────────────────────
CONVERSATIONS_FILE: str = os.path.join(DATA_DIR, "user_conversations.json")
MAX_RECENT_MESSAGES: int = 10       # per-user rolling window (pairs)
CONVERSATION_TTL_DAYS: int = 30     # auto-prune inactive users

# ── Challenges ──────────────────────────────────────────
CHALLENGE_REMINDER_HOURS: int = int(os.getenv("CHALLENGE_REMINDER_HOURS", "4"))
