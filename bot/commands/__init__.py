"""Command registration — loads all Cog modules."""

from discord.ext import commands

# Paths are relative to the bot package (dot-separated)
_COG_MODULES = [
    "bot.commands.cat_content",
    "bot.commands.ai_chat",
    "bot.commands.memory_cmd",
    "bot.commands.challenges",
    "bot.commands.settings_cmd",
]


async def register_all(bot: commands.Bot) -> None:
    """Load every command Cog onto *bot*."""
    for module in _COG_MODULES:
        try:
            await bot.load_extension(module)
            print(f"[INFO] Loaded cog: {module}")
        except Exception as e:
            print(f"[ERROR] Failed to load cog {module}: {e}")
