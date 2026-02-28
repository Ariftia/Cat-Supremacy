# 🐱👑 Cat Supremacy — Discord Bot

A Discord bot that posts **cat GIFs** and **cat facts** every morning, afternoon, and evening. Because cats deserve world domination.

---

## Features

- **Scheduled posts** — Automatically sends a cat GIF + fact 3× daily (morning, afternoon, evening)
- **Beautiful embeds** — Color-coded by time of day with themed greetings
- **Manual commands** — Get cat content on-demand anytime
- **Free APIs** — Uses [TheCatAPI](https://thecatapi.com/) for GIFs and [catfact.ninja](https://catfact.ninja/) for facts

## Daily Schedule (UTC)

| Time | Slot |
|------|------|
| 🌅 08:00 | Morning |
| ☀️ 14:00 | Afternoon |
| 🌙 20:00 | Evening |

> You can change these times in `config.py`.

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

```bash
# Clone or navigate to the project
cd Cat-Supremacy

# Copy the example env file
copy .env.example .env     # Windows
# cp .env.example .env     # Mac/Linux

# Edit .env and fill in your values:
#   DISCORD_TOKEN=your_bot_token_here
#   CAT_CHANNEL_ID=your_channel_id_here
```

> **How to get Channel ID:** Enable Developer Mode in Discord Settings → Advanced, then right-click a channel → Copy ID.

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Bot

```bash
python bot.py
```

---

## Commands

| Command | Description |
|---------|-------------|
| `@cat now` | Post a cat GIF + fact immediately |
| `@cat gif` | Get a random cat GIF |
| `@cat fact` | Get a random cat fact |
| `@cat search <topic>` | Search the internet for news & journals |
| `@cat image <description>` | Generate an AI image with DALL-E |
| `@cat context <text>` | Set custom knowledge for AI responses |
| `@cat context clear` | Remove custom context |
| `@cat memory` | View what the bot remembers about you |
| `@cat memory clear` | Make the bot forget everything about you |
| `@cat schedule` | View the daily posting schedule |
| `@cat help_me` | Show all available commands |
| `@cat <anything>` | Just talk to the cat! |

---

## Logging

The bot prints structured logs to stdout for every action. Each log line is prefixed with a tag:

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

## Project Structure

```
Cat-Supremacy/
├── bot.py              # Main entry point — commands & startup
├── config.py           # Configuration & environment variables
├── cat_service.py      # API calls to fetch GIFs, facts, AI chat, search, image gen
├── memory.py           # Per-user memory system (rolling + long-term)
├── scheduler.py        # Scheduled daily posting logic
├── user_memories.json  # Persisted user memories (auto-generated)
├── requirements.txt    # Python dependencies
├── .env                # Your secrets (not committed)
├── .env.example        # Template for .env
└── .gitignore          # Git ignore rules
```

---

## Optional: The Cat API Key

The bot works without an API key, but you can get a free key from [TheCatAPI](https://thecatapi.com/) for higher rate limits. Add it to your `.env`:

```
CAT_API_KEY=your_key_here
```

---

*Cats rule. Dogs drool. Long live Cat Supremacy.* 🐱👑
