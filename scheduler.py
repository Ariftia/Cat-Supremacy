"""Scheduled tasks that post cat content at fixed times each day."""

import datetime
import discord
from discord.ext import tasks

import config
from services.cat_api import fetch_cat_gif, fetch_cat_fact
from services.openai_chat import ask_cat

# ── Default greeting templates ───────────────────────────
_SLOT_TEMPLATES = {
    "morning":   {"greeting": "Good Morning",   "emoji": "🌅",
                  "message": "Rise and shine, cat lovers! Here's your morning dose of whiskers:"},
    "afternoon": {"greeting": "Good Afternoon", "emoji": "☀️",
                  "message": "Afternoon paws! Time for a mid-day cat break:"},
    "evening":   {"greeting": "Good Evening",   "emoji": "🌙",
                  "message": "Evening vibes! Curl up with this cozy cat content:"},
}

# ── Module-level defaults (used by @cat now and @cat schedule) ──
TIME_OF_DAY = {
    config.MORNING_HOUR: {**_SLOT_TEMPLATES["morning"], "color": config.MORNING_COLOR},
    config.AFTERNOON_HOUR: {**_SLOT_TEMPLATES["afternoon"], "color": config.AFTERNOON_COLOR},
    config.EVENING_HOUR: {**_SLOT_TEMPLATES["evening"], "color": config.EVENING_COLOR},
}

# ── Schedule times (UTC) ─────────────────────────────────
SCHEDULE_TIMES = [
    datetime.time(hour=config.MORNING_HOUR, tzinfo=datetime.timezone.utc),
    datetime.time(hour=config.AFTERNOON_HOUR, tzinfo=datetime.timezone.utc),
    datetime.time(hour=config.EVENING_HOUR, tzinfo=datetime.timezone.utc),
]


def _build_time_of_day(guild_id: int | None = None) -> dict[int, dict]:
    """Build a TIME_OF_DAY map using per-guild settings if available."""
    if guild_id is None:
        return TIME_OF_DAY
    from memory.guild_settings import get as gs_get
    morning_h = gs_get(guild_id, "morning_hour")
    afternoon_h = gs_get(guild_id, "afternoon_hour")
    evening_h = gs_get(guild_id, "evening_hour")
    return {
        morning_h:   {**_SLOT_TEMPLATES["morning"],   "color": gs_get(guild_id, "morning_color")},
        afternoon_h: {**_SLOT_TEMPLATES["afternoon"], "color": gs_get(guild_id, "afternoon_color")},
        evening_h:   {**_SLOT_TEMPLATES["evening"],   "color": gs_get(guild_id, "evening_color")},
    }


def _current_slot(guild_id: int | None = None) -> dict:
    """Return the greeting slot for the current UTC hour."""
    tod = _build_time_of_day(guild_id)
    now_hour = datetime.datetime.now(datetime.timezone.utc).hour
    print(f"[SCHED] Determining slot for UTC hour {now_hour}")
    # Find the closest slot that has already started
    for hour in sorted(tod.keys(), reverse=True):
        if now_hour >= hour:
            return tod[hour]
    return list(tod.values())[0]


async def _build_embed(slot: dict) -> tuple[discord.Embed, str]:
    """Create a rich embed with a cat GIF and fact."""
    print(f"[SCHED] Building embed for slot '{slot['greeting']}'")
    gif_url = await fetch_cat_gif()
    fact = await fetch_cat_fact()

    embed = discord.Embed(
        title=f"{slot['emoji']}  {slot['greeting']}!  — Cat Supremacy",
        description=f"*{slot['message']}*",
        color=slot["color"],
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.set_image(url=gif_url)
    embed.add_field(name="🐱 Cat Fact", value=fact, inline=False)
    embed.set_footer(text="Cat Supremacy Bot • Powered by TheCatAPI & catfact.ninja")

    print(f"[SCHED] Embed built for '{slot['greeting']}'")
    return embed, gif_url


async def _build_scheduled_messages(slot: dict) -> tuple[str, str, str]:
    """Build the three separate messages for a scheduled post: greeting, fact, gif."""
    print(f"[SCHED] Building scheduled messages for slot '{slot['greeting']}'")
    greeting_prompt = (
        f"It's {slot['greeting'].lower()} time. Write a short, casual greeting "
        f"to the server as a cat. Be cute and in character."
    )
    greeting = await ask_cat(greeting_prompt)
    fact = await fetch_cat_fact()
    gif_url = await fetch_cat_gif()
    print(f"[SCHED] Scheduled messages built for '{slot['greeting']}'")
    return greeting, f"🐱 {fact}", gif_url


def setup_scheduled_tasks(bot: discord.Client):
    """Register the daily cat posting loop on the bot."""

    @tasks.loop(time=SCHEDULE_TIMES)
    async def post_cat_content():
        print("[SCHED] Scheduled post triggered")
        # Resolve channel — check guild overrides for each guild the bot is in
        from memory.guild_settings import get as gs_get
        channels_posted = set()
        for guild in bot.guilds:
            ch_id = gs_get(guild.id, "cat_channel_id")
            if ch_id in channels_posted:
                continue
            channel = bot.get_channel(ch_id)
            if channel is None:
                print(f"[WARNING] Channel {ch_id} not found for guild {guild.id}. Skipping.")
                continue
            channels_posted.add(ch_id)
            slot = _current_slot(guild_id=guild.id)
            greeting, fact, gif_url = await _build_scheduled_messages(slot)
            await channel.send(greeting[:2000])
            await channel.send(fact[:2000])
            await channel.send(gif_url)
            print(f"[SCHED] Posted {slot['greeting']} cat content to #{channel.name} (guild {guild.id})")

    @post_cat_content.before_loop
    async def before_post():
        await bot.wait_until_ready()
        print("[INFO] Scheduled cat poster is ready!")

    # Attach to bot so it can be started from on_ready
    bot.cat_poster = post_cat_content
    return post_cat_content
