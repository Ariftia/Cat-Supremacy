# Context — Cat Supremacy Bot

> **Purpose**: Quick-reference document for anyone (human or AI) working on
> this project.  Read this first to understand what the bot does, how the
> code is organised, and what conventions to follow.

---

## What Is This?

Cat Supremacy is a Discord bot that:

1. **Posts cat content on a schedule** — A cat GIF + AI-generated greeting +
   random fact, three times daily (morning, afternoon, evening).
2. **Chats as a sassy cat** — When mentioned, responds in-character using
   OpenAI's chat API with a persistent cat personality.
3. **Remembers users** — Each Discord user has independent long-term memory
   stored as vector embeddings in ChromaDB.  The bot recalls relevant past
   information to personalize conversations.
4. **Supports rich input** — Handles images (vision), PDFs, text files, web
   search, and AI image generation.
5. **Daily & Weekly Challenges** — Users can create, join, and complete
   challenges.  The bot tracks participation and automatically reminds
   incomplete participants on a configurable schedule.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Discord | `discord.py` ≥ 2.3 |
| AI | OpenAI API — `gpt-4.1-mini` (chat), `gpt-4.1-nano` (memory extraction), `text-embedding-3-small` (embeddings), `gpt-image-1` (images) |
| Vector DB | ChromaDB (local, persistent, cosine similarity) |
| HTTP | `aiohttp` for external API calls |
| PDF | PyMuPDF (`fitz`) |
| Config | `python-dotenv` + environment variables |

---

## Project Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full specification.  Summary:

```
run.py                  ← entry point
config.py               ← env vars and tunables
bot/                    ← Discord layer (events, commands, helpers)
  commands/             ← Cog-based command groups
services/               ← Stateless API integrations (OpenAI, TheCatAPI, etc.)
memory/                 ← Memory subsystem (vector store, conversation history, prompt builder)
scheduler.py            ← Timed cat content posting
data/                   ← Runtime data (git-ignored)
```

---

## Key Design Decisions

### 1. Separation of Concerns
- `bot/` handles Discord I/O only — no business logic.
- `services/` calls external APIs — no Discord imports, no state.
- `memory/` owns all persistent state — vector DB and conversation JSON.

### 2. Per-User Memory Isolation
- Every ChromaDB query filters by `user_id`.
- Users cannot see each other's memories.
- Conversation history is keyed by Discord user ID.

### 3. Async-First
- All I/O is `async`.  ChromaDB (synchronous) is wrapped in
  `asyncio.to_thread()`.
- Memory extraction runs as a fire-and-forget task after responding, so
  the user sees the reply immediately.

### 4. Graceful Degradation
- If embedding generation fails → skip memory search, respond without
  context.
- If ChromaDB is unavailable → bot still responds normally.
- If OpenAI key is missing → commands that need it return a clear error
  message; scheduled cat content (TheCatAPI) still works.

### 5. Cog-Based Commands
- Commands are grouped into Cogs (`CatContentCog`, `AIChatCog`,
  `MemoryCog`, `ChallengeCog`) for clean organisation and auto-registration.
- The `on_command_error` fallback lives in `bot/events.py` and routes
  unrecognised messages to the AI chat path.

---

## Memory Pipeline (How It Works)

For every user message:

1. **Identify user** → Discord user ID = namespace.
2. **Retrieve memories** → Embed the message → cosine similarity search in
   ChromaDB (filtered by user_id) → top 5 results.
3. **Build prompt** → System prompt + `[User Memories]` block + rolling
   conversation history + current message.
4. **Generate response** → Chat model responds in cat character.
5. **Extract memories** (async, post-response) → Lightweight model
   evaluates if the message contains long-term info.  If yes, generates
   concise summaries, embeds them, and stores in ChromaDB.
6. **Prune** → If user exceeds 150 memories, oldest are deleted.

---

## Challenge System (How It Works)

1. **Create** — `@cat challenge create daily/weekly <title>` starts a new
   challenge with an auto-computed deadline (end of UTC day / end of Sunday).
2. **Join** — `@cat challenge join <id>` opts a user into the challenge.
3. **Complete** — `@cat challenge done <id>` marks the user as finished
   for the current period.
4. **Auto-Renew** — When a deadline passes, completions are cleared and a
   new deadline is set.  The challenge continues until manually ended.
5. **Reminders** — A task loop every `CHALLENGE_REMINDER_HOURS` hours pings
   participants who haven't completed yet.
6. **Persistence** — All data stored in `data/challenges.json` with
   per-guild isolation.

---

## Conventions

### Logging
All log lines use bracketed prefixes: `[INFO]`, `[CMD]`, `[CHAT]`, `[API]`,
`[EMBED]`, `[VECMEM]`, `[MEMORY]`, `[SCHED]`, `[ERROR]`, `[WARNING]`.

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/vars: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Error Handling
- Wrap all external calls in try/except.
- Return safe defaults on failure.
- Never let the bot crash.

### Type Hints
- All public functions are type-annotated.
- Use `from __future__ import annotations` for modern syntax.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | Yes | — | Discord bot token |
| `CAT_CHANNEL_ID` | Yes | — | Channel for scheduled posts |
| `OPENAI_API_KEY` | No | — | Enables AI features |
| `CAT_API_KEY` | No | — | Higher rate limits for TheCatAPI |
| `CHAT_MODEL` | No | `gpt-4.1-mini` | Chat model |
| `EXTRACTION_MODEL` | No | `gpt-4.1-nano` | Memory extraction model |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSIONS` | No | `1536` | Vector dimensions |
| `MEMORY_TOP_K` | No | `5` | Memories per query |
| `MAX_MEMORIES_PER_USER` | No | `150` | Memory cap per user |
| `CHALLENGE_REMINDER_HOURS` | No | `4` | Hours between auto-reminders |

---

## Common Tasks

### Adding a command
→ See ARCHITECTURE.md §9.

### Adding a new API integration
→ Create a new file in `services/`, keep it stateless.

### Changing the bot personality
→ Edit `CAT_SYSTEM_PROMPT` in `services/openai_chat.py`.

### Adjusting memory behavior
→ Tune `MEMORY_TOP_K`, `MAX_MEMORIES_PER_USER` in `.env` or `config.py`.
→ Edit the evaluation prompt in `memory/evaluator.py`.
