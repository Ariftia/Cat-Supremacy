# Architecture — Cat Supremacy Bot

> **Purpose**: This document defines the project structure, module boundaries,
> data flow, and coding conventions.  Every contributor (human or AI) must
> follow it when adding or modifying code.

---

## 1. High-Level Overview

Cat Supremacy is a Discord chatbot written in Python.  It has three major
subsystems:

| Subsystem | Packages | Responsibility |
|-----------|----------|----------------|
| **Bot / Commands** | `bot/` | Discord events, command handlers, message routing |
| **AI Services** | `services/` | OpenAI chat, embeddings, web search, image gen, external APIs |
| **Memory** | `memory/` | Per-user vector memory (ChromaDB), conversation history, prompt assembly |
| **Challenges** | `memory/challenges.py`, `bot/commands/challenges.py` | Daily/weekly challenge system with participant tracking and reminders |

A thin `config.py` at the root loads environment variables and is imported
everywhere.  The entry point is `run.py`.

---

## 2. Directory Layout

```
Cat-Supremacy/
├── run.py                    # Entry point — validates env, starts the bot
├── config.py                 # All environment variables and tunables
├── requirements.txt          # Python dependencies
│
├── bot/                      # Discord bot layer
│   ├── __init__.py           # Creates and exports the Bot instance
│   ├── events.py             # on_ready, on_command_error (chat fallback)
│   ├── commands/             # One file per logical command group
│   │   ├── __init__.py       # Registers all cogs on the bot
│   │   ├── cat_content.py    # now, gif, fact, schedule
│   │   ├── ai_chat.py        # detail, image, search, context
│   │   ├── memory_cmd.py     # memory view/clear/export/import
│   │   └── challenges.py     # challenge create/join/done/status/remind
│   └── helpers.py            # Shared utilities (attachment parsing, response splitting)
│
├── services/                 # External API integrations (all async)
│   ├── __init__.py
│   ├── cat_api.py            # fetch_cat_gif(), fetch_cat_fact()
│   ├── openai_chat.py        # ask_cat() — builds prompt, calls chat model
│   ├── openai_images.py      # generate_image()
│   ├── openai_search.py      # search_web()
│   ├── embedding.py          # generate_embedding(), generate_embeddings_batch()
│   └── pdf.py                # extract_pdf_text()
│
├── memory/                   # Memory subsystem
│   ├── __init__.py           # Re-exports public API
│   ├── models.py             # Memory, UserConversation dataclasses
│   ├── vector_store.py       # ChromaDB CRUD: store, search, prune, delete
│   ├── evaluator.py          # AI-driven memory extraction (evaluate & store)
│   ├── conversation.py       # Rolling conversation history (JSON persistence)
│   ├── prompt_builder.py     # format_memories_block(), build_system_prompt(), build_messages()
│   └── challenges.py         # Challenge data model, persistence, deadline logic
│
├── scheduler.py              # discord.ext.tasks scheduled posting
│
├── data/                     # Runtime data (git-ignored)
│   ├── chroma_data/          # ChromaDB persistent storage
│   ├── user_conversations.json
│   └── challenges.json       # Challenge data (daily/weekly)
│
├── ARCHITECTURE.md           # ← This file
├── CONTEXT.md                # Project context for contributors / AI agents
├── README.md                 # User-facing documentation
├── .env                      # Secrets (git-ignored)
├── .env.example              # Template for .env
└── .gitignore
```

---

## 3. Module Boundaries & Dependency Rules

```
run.py
  └─► bot/
        ├─► services/       (bot calls services)
        ├─► memory/          (bot calls memory)
        └─► config           (bot reads config)

services/
  ├─► config                 (reads API keys, model names)
  └─► memory/prompt_builder  (openai_chat imports prompt builder)

memory/
  ├─► services/embedding     (vector_store & evaluator call embedding service)
  └─► config                 (reads memory tunables)

scheduler
  └─► services/              (uses cat_api + openai_chat)
```

### Rules

1. **`bot/` never contains business logic.**  Commands call into `services/`
   and `memory/` and format responses for Discord.
2. **`services/` modules are stateless.**  They receive parameters, call
   external APIs, and return results.  No Discord imports.
3. **`memory/` owns all state** (ChromaDB, JSON file).  Other packages
   interact through its public API.
4. **No circular imports.**  Arrows above are one-way.  If module A imports
   module B, then B must NOT import A.
5. **`config.py` is leaf-level** — it imports only `os` and `dotenv`.

---

## 4. Data Flow — Chat Message

```
Discord message
      │
      ▼
bot/events.py  ──────────────────────────── extracts user_id, question, attachments
      │
      ├─► memory/conversation.py            get rolling history
      ├─► memory/vector_store.py            search_memories(user_id, question)
      ├─► memory/prompt_builder.py          format_memories_block() → build prompt
      │
      ├─► services/openai_chat.py           ask_cat(prompt, history, memories)
      │
      ├─► bot/helpers.py                    split_response() → send to Discord
      │
      └─► memory/evaluator.py (async)       evaluate_and_store_memories()
              │
              └─► memory/vector_store.py    store_memory() → ChromaDB
```

---

## 5. Data Flow — Memory Pipeline

```
User message  ──►  services/embedding.py  ──►  1536-dim float vector
                                                   │
                                        memory/vector_store.py
                                          search(user_id, vector) → top-K
                                                   │
                                        memory/prompt_builder.py
                                          format [User Memories] block
                                                   │
                                        services/openai_chat.py
                                          inject into system prompt
                                                   │
                                        memory/evaluator.py (post-response)
                                          AI evaluates if message is important
                                          If yes → generate summary → embed → store
```

---

## 6. Data Flow — Challenge System

```
@cat challenge create weekly "Push-ups"
      │
      ▼
bot/commands/challenges.py      parse action & arguments
      │
      ├─► memory/challenges.py  create_challenge() → compute deadline
      │       │
      │       └─► data/challenges.json   persist to disk
      │
      └─► Discord embed          respond with challenge details

Reminder loop (every N hours):
      │
      ▼
bot/commands/challenges.py      ChallengeCog.reminder_loop
      │
      ├─► memory/challenges.py  check_and_renew_expired()
      │       │
      │       ├─ expired + active → renew (reset completions, new deadline)
      │       └─ return list of renewed challenges
      │
      ├─► memory/challenges.py  get_incomplete_challenges()
      │       │
      │       └─ return challenges with incomplete participants
      │
      └─► Discord channel        ping incomplete participants
```

### Challenge Data Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-incrementing per guild |
| `guild_id` | int | Discord guild |
| `channel_id` | int | Channel for reminders |
| `title` | str | Challenge name |
| `description` | str | Detailed description |
| `mode` | str | `daily` or `weekly` |
| `created_by` | int | Creator's Discord user ID |
| `deadline` | float | Unix timestamp when current period ends |
| `active` | bool | Whether challenge is running |
| `participants` | list[int] | User IDs who joined |
| `completions` | dict[int, float] | User ID → completion timestamp |

---

## 7. Memory Schema (ChromaDB)

| Field | Storage | Description |
|-------|---------|-------------|
| `id` | ChromaDB ID | UUID4 string |
| `document` | ChromaDB document | Memory summary text |
| `embedding` | ChromaDB embedding | 1536-dim float vector |
| `user_id` | metadata | Discord user ID (string) — **always filtered** |
| `timestamp` | metadata | Unix epoch float |
| `category` | metadata | `preference`, `hobby`, `project`, `fact`, `personality`, `goal`, `general`, `legacy` |

**Isolation**: Every query uses `where={"user_id": str(uid)}`.

---

## 8. Coding Conventions

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions / variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private helpers: prefixed with `_`

### Async
- All I/O functions are `async`.
- ChromaDB (sync) operations are wrapped in `asyncio.to_thread()`.
- Fire-and-forget tasks use `asyncio.get_event_loop().create_task()`.

### Logging
- Use `print()` with structured prefixes (no logging library yet).
- Prefixes: `[INFO]`, `[CMD]`, `[CHAT]`, `[API]`, `[EMBED]`, `[VECMEM]`,
  `[MEMORY]`, `[SCHED]`, `[ERROR]`, `[WARNING]`
- OpenAI calls always log token usage.

### Error Handling
- External API calls are wrapped in try/except.
- On failure, return a safe default (empty list, `None`, fallback value).
- The bot must never crash due to an API failure.

### Imports
- Standard library first, then third-party, then local.
- Lazy imports (inside functions) only for heavy packages that slow startup
  (`openai`, `fitz`) or to break potential circular imports.
- Top-of-file imports preferred everywhere else.

### Type Hints
- All public function signatures have type hints.
- Use `from __future__ import annotations` for `X | None` syntax.

---

## 9. Configuration

All settings live in `config.py` and are loaded from environment variables
with sensible defaults.  Grouped by subsystem:

| Group | Variables |
|-------|-----------|
| Discord | `DISCORD_TOKEN`, `CAT_CHANNEL_ID` |
| API Keys | `OPENAI_API_KEY`, `CAT_API_KEY` |
| Schedule | `MORNING_HOUR`, `AFTERNOON_HOUR`, `EVENING_HOUR` |
| AI Models | `CHAT_MODEL`, `EXTRACTION_MODEL`, `EMBEDDING_MODEL` |
| Memory | `EMBEDDING_DIMENSIONS`, `MEMORY_TOP_K`, `MAX_MEMORIES_PER_USER`, `CHROMA_PERSIST_DIR` |
| Challenges | `CHALLENGE_REMINDER_HOURS` |
| Endpoints | `CAT_GIF_URL`, `CAT_FACT_URL` |

---

## 10. Adding a New Command

1. Decide which command group it belongs to (cat content, AI, memory).
2. Add a method to the corresponding Cog in `bot/commands/`.
3. Business logic goes in `services/` or `memory/`.
4. Update `bot/commands/__init__.py` if you created a new Cog file.
5. Add the command to the help embed in `bot/commands/ai_chat.py`.
6. Update `README.md` command table.

## 11. Adding a New Service

1. Create a new file in `services/`.
2. Keep it stateless — receive params, return results.
3. Import `config` for any settings.
4. No Discord-specific imports.
5. Add error handling with fallback values.

## 12. Extending the Memory System

1. New memory-related logic goes in `memory/`.
2. If you add a new metadata field, update the ChromaDB schema section above.
3. Never expose raw ChromaDB objects outside `memory/vector_store.py`.
4. All searches must filter by `user_id`.
