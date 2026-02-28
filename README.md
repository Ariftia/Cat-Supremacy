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
- **Per-user memory** — The bot remembers facts about you across conversations (name, preferences, interests, etc.)
- **Rolling conversation history** — Keeps the last 10 exchanges for natural conversational flow
- **Automatic extraction** — Uses a lightweight AI model (`gpt-4.1-nano`) to extract and store important facts after each conversation
- **Auto-pruning** — Memories older than 30 days are automatically cleaned up
- **Persistent storage** — Memories survive bot restarts via `user_memories.json`

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
| `openai` ≥ 1.0.0 | OpenAI API client (chat, search, image, memory) |

### 5. Run the Bot

```bash
python bot.py
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
├── bot.py              # Main entry point — commands, events & startup
├── config.py           # Environment variables & schedule configuration
├── cat_service.py      # External API calls (TheCatAPI, catfact.ninja, OpenAI)
├── memory.py           # Per-user memory system (rolling + long-term + persistence)
├── scheduler.py        # Scheduled daily posting logic (discord.ext.tasks)
├── user_memories.json  # Persisted user memories (auto-generated at runtime)
├── requirements.txt    # Python dependencies
├── .env                # Your secrets (not committed to git)
└── README.md           # This file
```

### Module Overview

| Module | Responsibility |
|--------|---------------|
| [bot.py](bot.py) | Bot initialization, command handlers, AI chat fallback via `on_command_error`, per-server custom context store |
| [config.py](config.py) | Loads `.env` variables, defines schedule hours, API endpoints, and embed colors |
| [cat_service.py](cat_service.py) | `fetch_cat_gif()`, `fetch_cat_fact()`, `ask_cat()`, `search_web()`, `generate_image()` — all async |
| [memory.py](memory.py) | `UserMemory` dataclass, rolling conversation window, long-term notes, AI-driven extraction, JSON persistence |
| [scheduler.py](scheduler.py) | `discord.ext.tasks` loop that fires at configured UTC times, builds and posts scheduled messages |

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
| AI Chat | `gpt-5-mini` | Main conversational model with cat personality |
| Web Search | `gpt-4.1-mini` | Uses `web_search_preview` tool |
| Memory Extraction | `gpt-4.1-nano` | Cheapest model — extraction is simple |
| Image Generation | `dall-e-3` | 1024×1024 standard quality |

---

*Cats rule. Dogs drool. Long live Cat Supremacy.* 🐱👑
