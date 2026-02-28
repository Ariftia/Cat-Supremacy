"""
Cat Supremacy Discord Bot 🐱👑
Posts a cat GIF + cat fact every morning, afternoon, and evening.
"""

import discord
from discord.ext import commands

import config
from scheduler import setup_scheduled_tasks, _build_scheduled_messages, _current_slot, TIME_OF_DAY

# ── Bot setup ────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# Register the scheduled poster
cat_poster = setup_scheduled_tasks(bot)


# ── Events ───────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[INFO] Target channel: {config.CAT_CHANNEL_ID}")
    print("[INFO] Starting scheduled cat poster...")

    if not cat_poster.is_running():
        cat_poster.start()

    # Set a fun status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="cats take over the world 🐱👑",
        )
    )
    print("[INFO] Cat Supremacy Bot is live! 🐱👑")


# ── Manual commands ──────────────────────────────────────
@bot.command(name="now")
async def cat_now(ctx: commands.Context):
    """Immediately post a cat GIF and fact (@cat now)."""
    slot = _current_slot()
    async with ctx.typing():
        greeting, fact, gif_url = await _build_scheduled_messages(slot)
    await ctx.send(greeting[:2000])
    await ctx.send(gif_url[:2000])
    await ctx.send(fact)


@bot.command(name="fact")
async def cat_fact_cmd(ctx: commands.Context):
    """Get just a cat fact (!cat fact)."""
    from cat_service import fetch_cat_fact

    fact = await fetch_cat_fact()
    await ctx.send(f"🐱 **Cat Fact:** {fact}")


@bot.command(name="gif")
async def cat_gif_cmd(ctx: commands.Context):
    """Get just a cat GIF (!cat gif)."""
    from cat_service import fetch_cat_gif

    gif = await fetch_cat_gif()
    await ctx.send(gif)


@bot.command(name="schedule")
async def cat_schedule(ctx: commands.Context):
    """Show the daily posting schedule (!cat schedule)."""
    embed = discord.Embed(
        title="🗓️ Cat Supremacy Daily Schedule (UTC)",
        color=0xFFA500,
    )
    for hour, slot in sorted(TIME_OF_DAY.items()):
        embed.add_field(
            name=f"{slot['emoji']} {slot['greeting']}",
            value=f"`{hour:02d}:00 UTC`",
            inline=True,
        )
    embed.set_footer(text="All times are in UTC. Adjust for your timezone!")
    await ctx.send(embed=embed)


@bot.command(name="help_me")
async def cat_help(ctx: commands.Context):
    """Show all available commands (@cat help_me)."""
    embed = discord.Embed(
        title="🐱👑 Cat Supremacy — Commands",
        description="Here's everything I can do!",
        color=0xFFA500,
    )
    embed.add_field(name="@cat now", value="Post a cat GIF + fact right now", inline=False)
    embed.add_field(name="@cat gif", value="Get a random cat GIF", inline=False)
    embed.add_field(name="@cat fact", value="Get a random cat fact", inline=False)
    embed.add_field(name="@cat <anything>", value="Just talk to me like a real cat!", inline=False)
    embed.add_field(name="@cat schedule", value="View the daily posting schedule", inline=False)
    embed.add_field(name="@cat help_me", value="Show this help message", inline=False)
    embed.set_footer(text="Cat Supremacy Bot • Cats rule the world!")
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """If the command is not found, treat the entire message as a question for the AI."""
    if isinstance(error, commands.CommandNotFound):
        # Extract everything after the mention as the question
        message = ctx.message.content
        for mention in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
            message = message.replace(mention, "")
        question = message.strip()

        if not question:
            await ctx.send("*stares at you blankly* ...meow? ask me someething! human 🐱")
            return

        from cat_service import ask_cat

        async with ctx.typing():
            answer = await ask_cat(question)

        await ctx.send(answer[:2000])
    else:
        raise error


# ── Run ──────────────────────────────────────────────────
if __name__ == "__main__":
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "your_discord_bot_token_here":
        print("=" * 60)
        print("  ERROR: Set your DISCORD_TOKEN in the .env file!")
        print("  See .env.example for reference.")
        print("=" * 60)
    elif config.CAT_CHANNEL_ID == 0:
        print("=" * 60)
        print("  ERROR: Set your CAT_CHANNEL_ID in the .env file!")
        print("  Right-click a channel (Developer Mode) -> Copy ID")
        print("=" * 60)
    else:
        bot.run(config.DISCORD_TOKEN)
