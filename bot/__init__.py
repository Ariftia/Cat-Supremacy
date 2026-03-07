"""Bot package — creates and exports the Discord Bot instance.

Usage::

    from bot import bot
    bot.run(token)
"""

import discord
from discord.ext import commands

# ── Create the Bot instance ──────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)


# ── Wire up events and commands on import ────────────────
from bot.events import register_events     # noqa: E402
from bot.commands import register_all      # noqa: E402

register_events(bot)


async def _load_cogs():
    """Called from on_ready-like hook; or we can use setup_hook."""
    await register_all(bot)


@bot.event
async def setup_hook():
    """discord.py 2.x hook — runs before on_ready."""
    await _load_cogs()
