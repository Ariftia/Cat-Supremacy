# 🐱👑 Cat Supremacy — Discord Bot

A Discord bot that posts **cat GIFs** and **cat facts** every morning, afternoon, and evening — and lets you chat with a sassy AI cat personality. Because cats deserve world domination.

---

## Features

### 🐾 Cat Content
- **Scheduled posts** — Automatically sends a cat GIF + AI-generated greeting + fact 3× daily (morning, afternoon, evening)
- **On-demand content** — Get random cat GIFs and facts anytime with simple commands

### 🤖 AI-Powered
- **Cat chat** — Mention the bot and talk to it like a real cat, powered by OpenAI (`gpt-5-mini`)
- **Web search** — Search the internet for news and journals via OpenAI's web search (`gpt-4.1-mini`)
- **Image generation** — Generate AI images with DALL-E 3
- **Per-server custom context** — Give the bot custom knowledge to shape its AI responses
- **Inline context** — Override context on a per-message basis with `[context: ...]`

### 🧠 Memory System
- **Per-user semantic memory** — Each user has independent vector-based long-term memory using ChromaDB and OpenAI embeddings
- **Semantic search** — Retrieves the most relevant past memories for every conversation using cosine similarity on `text-embedding-3-small` embeddings
- **Rolling conversation history** — Keeps the last 10 exchanges for natural conversational flow
- **Automatic extraction** — Uses a lightweight AI model (`gpt-4.1-nano`) to evaluate each message and extract important facts (preferences, hobbies, projects, goals, personality traits)
- **Memory pruning** — Automatically limits memories to 150 per user; oldest entries are removed when the limit is exceeded
- **Trivial message filtering** — Greetings and short questions are not stored
- **Per-user isolation** — All vector searches are filtered by Discord user ID so no user can access another's memories
- **Legacy migration** — Old flat-text memories are automatically migrated to the vector store on startup
- **Persistent storage** — ChromaDB data persists to `data/chroma_data/`; conversation history persists to `data/user_conversations.json`

### 🔌 Free APIs
- [TheCatAPI](https://thecatapi.com/) for cat GIFs
- [catfact.ninja](https://catfact.ninja/) for cat facts

---

## Daily Schedule

The bot posts automatically 3× per day. Times are configured in [config.py](config.py) as UTC offsets:

| Slot | UTC Time | Embed Color |
|------|----------|-------------|
| 🌅 Morning | `18:00` | Gold |
| ☀️ Afternoon | `01:00` | Dark Orange |
| 🌙 Evening | `09:00` | Purple |

> **Customizing times:** Edit `MORNING_HOUR`, `AFTERNOON_HOUR`, and `EVENING_HOUR` in [config.py](config.py).

---

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → name it **Cat Supremacy**
3. Go to **Bot** → click **Add Bot**
4. Copy the **Token** (you'll need it in step 3)
5. Under **Privileged Gateway Intents**, enable **Message Content Intent**

### 2. Invite the Bot to Your Server

1. Go to **OAuth2 → URL Generator**
2. Check scopes: `bot`
3. Check permissions: `Send Messages`, `Embed Links`, `Read Message History`
4. Copy the generated URL and open it in your browser to invite the bot

### 3. Configure Environment

Create a `.env` file in the project root with the following variables:

```env
DISCORD_TOKEN=your_discord_bot_token_here
CAT_CHANNEL_ID=your_channel_id_here
OPENAI_API_KEY=your_openai_key_here
CAT_API_KEY=your_cat_api_key_here
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | **Yes** | Your Discord bot token |
| `CAT_CHANNEL_ID` | **Yes** | The channel ID where scheduled posts are sent |
| `OPENAI_API_KEY` | No | Required for AI chat, web search, image generation, and memory extraction |
| `CAT_API_KEY` | No | Optional [TheCatAPI](https://thecatapi.com/) key for higher rate limits |

> **How to get Channel ID:** Enable Developer Mode in Discord Settings → Advanced, then right-click a channel → **Copy ID**.

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**

| Package | Purpose |
|---------|---------|
| `discord.py` ≥ 2.3.0 | Discord bot framework |
| `aiohttp` ≥ 3.9.0 | Async HTTP client for API calls |
| `python-dotenv` ≥ 1.0.0 | Load `.env` configuration |
| `openai` ≥ 1.0.0 | OpenAI API client (chat, embeddings, search, image, memory) |
| `chromadb` ≥ 0.5.0 | Local vector database for semantic memory storage |
| `pymupdf` ≥ 1.24.0 | PDF text extraction |

### 5. Run the Bot

```bash
python run.py
```

The bot validates that `DISCORD_TOKEN` and `CAT_CHANNEL_ID` are set before starting, and will print an error message if either is missing.

---

## Commands

All commands use Discord's mention prefix — mention the bot followed by the command.

| Command | Description |
|---------|-------------|
| `@cat now` | Post a cat GIF + AI greeting + fact immediately |
| `@cat gif` | Get a random cat GIF |
| `@cat fact` | Get a random cat fact |
| `@cat search <topic>` | Search the internet for news & journals |
| `@cat image <description>` | Generate an AI image with DALL-E 3 |
| `@cat context <text>` | Set custom knowledge for AI responses (per-server) |
| `@cat context clear` | Remove the custom context |
| `@cat context` | View the current custom context |
| `@cat memory` | View what the bot remembers about you |
| `@cat memory clear` | Make the bot forget everything about you |
| `@cat memory export` | Download your memories as a JSON file |
| `@cat memory import` | Restore your memories from an attached JSON file |
| `@cat memory export_all` | Export all user memories as JSON (admin only) |
| `@cat memory import_all` | Import all user memories from attached JSON (admin only) |
| `@cat schedule` | View the daily posting schedule |
| `@cat help_me` | Show all available commands |
| `@cat <anything>` | Just talk to the cat! AI-powered conversation |

### Inline Context

You can provide one-off context in any message using square brackets:

```
@cat [context: you are a pirate cat] what's the weather like?
```

This merges with any server-level context set via `@cat context`.

---

## Project Structure

```
Cat-Supremacy/
├── run.py                    # Entry point — validates env, starts the bot
├── config.py                 # All environment variables and tunables
├── requirements.txt          # Python dependencies
│
├── bot/                      # Discord bot layer
│   ├── __init__.py           # Creates and exports the Bot instance
│   ├── events.py             # on_ready, on_command_error (chat fallback)
│   ├── commands/             # One file per logical command group (Cogs)
│   │   ├── __init__.py       # Registers all cogs on the bot
│   │   ├── cat_content.py    # now, gif, fact, schedule
│   │   ├── ai_chat.py        # detail, image, search, context, help_me
│   │   └── memory_cmd.py     # memory view/clear/export/import
│   └── helpers.py            # Shared utilities (attachment parsing, response splitting)
│
├── services/                 # External API integrations (all async, stateless)
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
│   ├── models.py             # Memory dataclass
│   ├── vector_store.py       # ChromaDB CRUD: store, search, prune, delete
│   ├── evaluator.py          # AI-driven memory extraction (evaluate & store)
│   ├── conversation.py       # Rolling per-user conversation history (JSON persistence)
│   └── prompt_builder.py     # format_memories_block(), build_system_prompt(), build_messages()
│
├── scheduler.py              # discord.ext.tasks scheduled posting
│
├── data/                     # Runtime data (git-ignored)
│   ├── chroma_data/          # ChromaDB persistent storage
│   └── user_conversations.json
│
├── ARCHITECTURE.md           # Architecture specification
├── CONTEXT.md                # Project context for contributors / AI agents
├── README.md                 # This file
├── .env                      # Your secrets (not committed to git)
└── .gitignore
```

### Module Overview

| Module | Responsibility |
|--------|---------------|
| `run.py` | Entry point — validates environment and starts the bot |
| `config.py` | Loads `.env` variables, defines schedule hours, API endpoints, memory settings |
| `bot/` | Discord layer — events, command handlers (Cogs), helpers |
| `services/` | Stateless external API integrations (TheCatAPI, OpenAI chat/images/search/embeddings, PDF) |
| `memory/` | Per-user vector memory (ChromaDB), conversation history, prompt assembly |
| `scheduler.py` | `discord.ext.tasks` loop that fires at configured UTC times |

---

## Logging

The bot prints structured logs to stdout. Each log line is prefixed with a tag:

| Prefix | Scope |
|--------|-------|
| `[INFO]` | Bot startup & general status |
| `[CMD]` | Command invocations (who, where, input, completion) |
| `[CHAT]` | AI chat via mention (question, response length) |
| `[API]` | External API calls — TheCatAPI, catfact.ninja, OpenAI |
| `[MEMORY]` | Memory load, save, create, prune, and extraction |
| `[SCHED]` | Scheduled posting lifecycle |
| `[ERROR]` | Failures in API calls |
| `[WARNING]` | Non-fatal issues (save failures, extraction errors) |

OpenAI API calls also log **token usage** (prompt / completion / total) so you can monitor costs:

```
[API] ask_cat response received (142 chars) | tokens: prompt=385, completion=48, total=433
[API] search_web response received (1820 chars) | tokens: input=102, output=590, total=692
[MEMORY] Extraction API call | tokens: prompt=210, completion=35, total=245
```

---

## OpenAI Models Used

| Feature | Model | Notes |
|---------|-------|-------|
| AI Chat | `gpt-4.1-mini` | Main conversational model with cat personality |
| Web Search | `gpt-4.1-mini` | Uses `web_search_preview` tool |
| Memory Extraction | `gpt-4.1-nano` | Evaluates messages and extracts long-term facts |
| Embeddings | `text-embedding-3-small` | 1536-dim vectors for semantic memory search |
| Image Generation | `gpt-image-1` | 1024×1024 standard quality |

> Models are configurable via environment variables `CHAT_MODEL`, `EXTRACTION_MODEL`, and `EMBEDDING_MODEL`.

---

## Memory Pipeline

The vector memory system works as follows for every user message:

```
User sends message
        │
        ▼
┌─────────────────────────────┐
│ 1. Identify Discord user ID │  ← namespace for memory isolation
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ 2. Generate embedding for message   │  ← text-embedding-3-small
│    (services/embedding.py)          │
└─────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│ 3. Semantic search in ChromaDB           │  ← filtered by user_id
│    Retrieve top 5 most relevant memories │
│    (memory/vector_store.py)              │
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│ 4. Build prompt with [User Memories] section │
│    (memory/prompt_builder.py)                │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│ 5. Send to chat model, get response  │
│    (services/openai_chat.py)         │
└──────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────┐
│ 6. Evaluate if message has important long-term │
│    info (gpt-4.1-nano). If yes, generate       │
│    summary memories, embed, and store in       │
│    ChromaDB with user_id + timestamp + category│
│    (memory/evaluator.py)                       │
└────────────────────────────────────────────────┘
```

### Memory Categories

Stored memories are tagged with a category:

| Category | Example |
|----------|---------|
| `preference` | "User prefers concise technical explanations" |
| `hobby` | "User enjoys woodworking and 3D printing" |
| `project` | "User is building an ESP32 hydroponic monitoring system" |
| `fact` | "User's name is Alex and they live in Berlin" |
| `personality` | "User has a sarcastic sense of humor" |
| `goal` | "User is preparing for a Python certification exam" |

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIMENSIONS` | `1536` | Embedding vector dimensions |
| `CHROMA_PERSIST_DIR` | `./data/chroma_data` | ChromaDB storage directory |
| `MEMORY_TOP_K` | `5` | Memories retrieved per query |
| `MAX_MEMORIES_PER_USER` | `150` | Maximum memories before pruning |
| `CHAT_MODEL` | `gpt-4.1-mini` | Chat model for conversations |
| `EXTRACTION_MODEL` | `gpt-4.1-nano` | Model for memory extraction |

---

*Cats rule. Dogs drool. Long live Cat Supremacy.* 🐱👑
