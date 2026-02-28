"""Scheduled tasks that post cat content at fixed times each day."""

import datetime
import discord
from discord.ext import tasks

import config
from cat_service import fetch_cat_gif, fetch_cat_fact, ask_cat

# ── Greeting map ─────────────────────────────────────────
TIME_OF_DAY = {
    config.MORNING_HOUR: {
        "greeting": "Good Morning",
        "emoji": "🌅",
        "color": config.MORNING_COLOR,
        "message": "Rise and shine, cat lovers! Here's your morning dose of whiskers:",
    },
    config.AFTERNOON_HOUR: {
        "greeting": "Good Afternoon",
        "emoji": "☀️",
        "color": config.AFTERNOON_COLOR,
        "message": "Afternoon paws! Time for a mid-day cat break:",
    },
    config.EVENING_HOUR: {
        "greeting": "Good Evening",
        "emoji": "🌙",
        "color": config.EVENING_COLOR,
        "message": "Evening vibes! Curl up with this cozy cat content:",
    },
}

# ── Schedule times (UTC) ─────────────────────────────────
SCHEDULE_TIMES = [
    datetime.time(hour=config.MORNING_HOUR, tzinfo=datetime.timezone.utc),
    datetime.time(hour=config.AFTERNOON_HOUR, tzinfo=datetime.timezone.utc),
    datetime.time(hour=config.EVENING_HOUR, tzinfo=datetime.timezone.utc),
]


def _current_slot() -> dict:
    """Return the greeting slot for the current UTC hour."""
    now_hour = datetime.datetime.now(datetime.timezone.utc).hour
    print(f"[SCHED] Determining slot for UTC hour {now_hour}")
    # Find the closest slot that has already started
    for hour in sorted(TIME_OF_DAY.keys(), reverse=True):
        if now_hour >= hour:
            return TIME_OF_DAY[hour]
    return TIME_OF_DAY[config.MORNING_HOUR]


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
        channel = bot.get_channel(config.CAT_CHANNEL_ID)
        if channel is None:
            print(f"[WARNING] Channel {config.CAT_CHANNEL_ID} not found. Skipping post.")
            return

        slot = _current_slot()
        greeting, fact, gif_url = await _build_scheduled_messages(slot)
        await channel.send(greeting[:2000])
        await channel.send(fact[:2000])
        await channel.send(gif_url)
        print(f"[SCHED] Posted {slot['greeting']} cat content to #{channel.name}!")

    @post_cat_content.before_loop
    async def before_post():
        await bot.wait_until_ready()
        print("[INFO] Scheduled cat poster is ready!")

    # Attach to bot so it can be started from on_ready
    bot.cat_poster = post_cat_content
    return post_cat_content
