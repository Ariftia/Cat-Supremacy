"""
Cat Supremacy — Discord bot entry point.

Validates configuration and launches the bot.
See ARCHITECTURE.md for the full project structure.
"""

import config
from bot import bot


def main():
    """Validate environment and start the bot."""
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "your_discord_bot_token_here":
        print("=" * 60)
        print("  ERROR: Set your DISCORD_TOKEN in the .env file!")
        print("  See .env.example for reference.")
        print("=" * 60)
        return

    if config.CAT_CHANNEL_ID == 0:
        print("=" * 60)
        print("  ERROR: Set your CAT_CHANNEL_ID in the .env file!")
        print("  Right-click a channel (Developer Mode) -> Copy ID")
        print("=" * 60)
        return

    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
