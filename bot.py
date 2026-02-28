"""
Cat Supremacy Discord Bot 🐱👑
Posts a cat GIF + cat fact every morning, afternoon, and evening.
"""

import discord
from discord.ext import commands
import re

import config
from scheduler import setup_scheduled_tasks, _build_scheduled_messages, _current_slot, TIME_OF_DAY

# ── Bot setup ────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# Register the scheduled poster
cat_poster = setup_scheduled_tasks(bot)

# ── Per-server custom context store (in-memory) ─────────
# Maps guild_id -> custom context string
custom_contexts: dict[int, str] = {}


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


@bot.command(name="search")
async def cat_search(ctx: commands.Context, *, query: str = None):
    """Search the internet for news and journals (@cat search <query>)."""
    if not query:
        await ctx.send("*paws at keyboard* meow~ tell me what to search! usage: `@cat search <topic>`")
        return

    from cat_service import search_web

    async with ctx.typing():
        answer = await search_web(query)

    # Split long responses into multiple messages (Discord 2000 char limit)
    while len(answer) > 2000:
        split_at = answer.rfind("\n", 0, 2000)
        if split_at == -1:
            split_at = 2000
        await ctx.send(answer[:split_at])
        answer = answer[split_at:].lstrip()
    if answer:
        await ctx.send(answer)


@bot.command(name="image")
async def cat_image(ctx: commands.Context, *, prompt: str = None):
    """Generate an image with AI (@cat image <prompt>)."""
    if not prompt:
        await ctx.send("*knocks pencil off table* meow~ tell me what to draw! usage: `@cat image <description>`")
        return

    from cat_service import generate_image

    async with ctx.typing():
        result = await generate_image(prompt)

    if result.startswith("❌"):
        await ctx.send(result)
    else:
        embed = discord.Embed(color=0xFFA500)
        embed.set_image(url=result)
        embed.set_footer(text=f"🎨 {prompt[:100]}")
        await ctx.send(embed=embed)


@bot.command(name="context")
async def cat_context(ctx: commands.Context, *, content: str = None):
    """Set, view, or clear custom context for AI responses (@cat context <text>)."""
    guild_id = ctx.guild.id if ctx.guild else ctx.author.id

    if content is None:
        # Show current context
        current = custom_contexts.get(guild_id)
        if current:
            await ctx.send(f"*flicks tail* current custom context:\n```\n{current[:1500]}\n```")
        else:
            await ctx.send("*yawns* no custom context set. use `@cat context <your text>` to add one~")
        return

    if content.lower() in ("clear", "reset", "remove", "none"):
        custom_contexts.pop(guild_id, None)
        await ctx.send("*knocks context off the table* custom context cleared! back to being just a cat~ 🐱")
        return

    # Check if there's a text file attachment
    if ctx.message.attachments:
        try:
            file_content = (await ctx.message.attachments[0].read()).decode("utf-8")
            content = f"{content}\n\n{file_content}" if content.strip() else file_content
        except Exception:
            await ctx.send("*hisses at file* couldn't read that attachment... text files only please!")
            return

    custom_contexts[guild_id] = content[:4000]  # Limit to 4000 chars
    await ctx.send(f"*purrs* custom context set! ({len(content[:4000])} chars) i'll use this knowledge when answering~ 🐱")


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
    embed.add_field(name="@cat search <topic>", value="Search the internet for news & journals", inline=False)
    embed.add_field(name="@cat image <description>", value="Generate an AI image", inline=False)
    embed.add_field(name="@cat context <text>", value="Set custom knowledge for AI responses", inline=False)
    embed.add_field(name="@cat context clear", value="Remove custom context", inline=False)
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

        # Check for inline [context: ...] override
        inline_context = None
        context_match = re.search(r'\[context:\s*(.+?)\]', question, re.IGNORECASE | re.DOTALL)
        if context_match:
            inline_context = context_match.group(1).strip()
            question = re.sub(r'\[context:\s*.+?\]', '', question, flags=re.IGNORECASE | re.DOTALL).strip()

        # Combine inline context with server context
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        server_context = custom_contexts.get(guild_id)
        combined_context = None
        if inline_context and server_context:
            combined_context = f"{server_context}\n\nInline context: {inline_context}"
        elif inline_context:
            combined_context = inline_context
        elif server_context:
            combined_context = server_context

        from cat_service import ask_cat

        async with ctx.typing():
            answer = await ask_cat(question, custom_context=combined_context)

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
