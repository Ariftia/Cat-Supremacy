"""
Cat Supremacy Discord Bot 🐱👑
Posts a cat GIF + cat fact every morning, afternoon, and evening.
"""

import discord
from discord.ext import commands
import re

import config
from scheduler import setup_scheduled_tasks, _build_scheduled_messages, _current_slot, TIME_OF_DAY
from memory import (
    get_user_memory,
    load_all as load_memories,
    save_all as save_memories,
    prune_old_memories,
    extract_and_update_memories,
    export_user_memory,
    export_all_memories,
    import_user_memory,
    import_all_memories,
)

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
    # Load persisted user memories from disk
    load_memories()
    prune_old_memories()

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
    print(f"[CMD] @cat now triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
    slot = _current_slot()
    async with ctx.typing():
        greeting, fact, gif_url = await _build_scheduled_messages(slot)
    await ctx.send(greeting[:2000])
    await ctx.send(gif_url[:2000])
    await ctx.send(fact)
    print(f"[CMD] @cat now completed for {ctx.author}")


@bot.command(name="fact")
async def cat_fact_cmd(ctx: commands.Context):
    """Get just a cat fact (!cat fact)."""
    print(f"[CMD] @cat fact triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
    from cat_service import fetch_cat_fact

    fact = await fetch_cat_fact()
    await ctx.send(f"🐱 **Cat Fact:** {fact}")
    print(f"[CMD] @cat fact completed for {ctx.author}")


@bot.command(name="gif")
async def cat_gif_cmd(ctx: commands.Context):
    """Get just a cat GIF (!cat gif)."""
    print(f"[CMD] @cat gif triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
    from cat_service import fetch_cat_gif

    gif = await fetch_cat_gif()
    await ctx.send(gif)
    print(f"[CMD] @cat gif completed for {ctx.author}")


@bot.command(name="schedule")
async def cat_schedule(ctx: commands.Context):
    """Show the daily posting schedule (!cat schedule)."""
    print(f"[CMD] @cat schedule triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
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
    print(f"[CMD] @cat schedule completed for {ctx.author}")


@bot.command(name="search")
async def cat_search(ctx: commands.Context, *, query: str = None):
    """Search the internet for news and journals (@cat search <query>)."""
    print(f"[CMD] @cat search triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')} | query='{query}'")
    if not query:
        print("[CMD] @cat search aborted — no query provided")
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
    print(f"[CMD] @cat search completed for {ctx.author}")


@bot.command(name="image")
async def cat_image(ctx: commands.Context, *, prompt: str = None):
    """Generate an image with AI (@cat image <prompt>)."""
    print(f"[CMD] @cat image triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')} | prompt='{prompt}'")
    if not prompt:
        print("[CMD] @cat image aborted — no prompt provided")
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
    print(f"[CMD] @cat image completed for {ctx.author}")


@bot.command(name="context")
async def cat_context(ctx: commands.Context, *, content: str = None):
    """Set, view, or clear custom context for AI responses (@cat context <text>)."""
    print(f"[CMD] @cat context triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
    guild_id = ctx.guild.id if ctx.guild else ctx.author.id

    if content is None:
        # Show current context
        current = custom_contexts.get(guild_id)
        if current:
            await ctx.send(f"*flicks tail* current custom context:\n```\n{current[:1500]}\n```")
            print(f"[CMD] @cat context — displayed current context for guild {guild_id}")
        else:
            await ctx.send("*yawns* no custom context set. use `@cat context <your text>` to add one~")
            print(f"[CMD] @cat context — no context set for guild {guild_id}")
        return

    if content.lower() in ("clear", "reset", "remove", "none"):
        custom_contexts.pop(guild_id, None)
        await ctx.send("*knocks context off the table* custom context cleared! back to being just a cat~ 🐱")
        print(f"[CMD] @cat context cleared for guild {guild_id} by {ctx.author}")
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
    print(f"[CMD] @cat context set for guild {guild_id} by {ctx.author} ({len(content[:4000])} chars)")


@bot.command(name="memory")
async def cat_memory(ctx: commands.Context, *, action: str = None):
    """View, clear, export, or import what the bot remembers about you."""
    print(f"[CMD] @cat memory triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
    user_id = ctx.author.id
    mem = get_user_memory(user_id, ctx.author.display_name)

    if action and action.lower() in ("clear", "reset", "forget", "wipe"):
        mem.recent_messages.clear()
        mem.long_term_notes = ""
        save_memories()
        await ctx.send("*bonks head on keyboard* poof! i forgot everything about you~ fresh start! 🐱")
        print(f"[CMD] @cat memory cleared for user {ctx.author} (ID: {user_id})")
        return

    # ── Export ───────────────────────────────────────────
    if action and action.lower() == "export":
        data = export_user_memory(user_id)
        if data is None:
            await ctx.send("*tilts head* nothing to export... talk to me first! 🐱")
            print(f"[CMD] @cat memory export — no data for {ctx.author}")
            return
        import io
        file = discord.File(
            io.BytesIO(data.encode("utf-8")),
            filename=f"cat_memory_{ctx.author.name}.json",
        )
        await ctx.send("*carefully packs memories into a box* here you go~ 📦🐱", file=file)
        print(f"[CMD] @cat memory export completed for {ctx.author}")
        return

    if action and action.lower() == "export_all":
        if not ctx.guild or not ctx.author.guild_permissions.administrator:
            await ctx.send("*hisses* only server admins can export all memories! 🐱")
            print(f"[CMD] @cat memory export_all denied for {ctx.author} — not admin")
            return
        data = export_all_memories()
        import io
        file = discord.File(
            io.BytesIO(data.encode("utf-8")),
            filename="cat_memories_all.json",
        )
        await ctx.send("*drops a big box of memories off the table* here's everyone's data~ 📦🐱", file=file)
        print(f"[CMD] @cat memory export_all completed by {ctx.author}")
        return

    # ── Import ───────────────────────────────────────────
    if action and action.lower() == "import":
        if not ctx.message.attachments:
            await ctx.send(
                "*looks around* attach a `.json` file to import!\n"
                "usage: `@cat memory import` with a file attached 🐱"
            )
            return
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".json"):
            await ctx.send("*hisses at file* that's not a `.json` file! 🐱")
            return
        try:
            raw = (await attachment.read()).decode("utf-8")
        except Exception:
            await ctx.send("*scratches file* couldn't read that... make sure it's a valid text file! 🐱")
            return
        result = import_user_memory(user_id, raw)
        if result == "ok":
            await ctx.send("*unpacks memories carefully* done! your memories have been restored~ 🐱")
            print(f"[CMD] @cat memory import completed for {ctx.author}")
        else:
            await ctx.send(f"*knocks file off table* import failed: {result} 🐱")
            print(f"[CMD] @cat memory import failed for {ctx.author}: {result}")
        return

    if action and action.lower() == "import_all":
        if not ctx.guild or not ctx.author.guild_permissions.administrator:
            await ctx.send("*hisses* only server admins can import all memories! 🐱")
            print(f"[CMD] @cat memory import_all denied for {ctx.author} — not admin")
            return
        if not ctx.message.attachments:
            await ctx.send(
                "*looks around* attach a `.json` file to import!\n"
                "usage: `@cat memory import_all` with a file attached 🐱"
            )
            return
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".json"):
            await ctx.send("*hisses at file* that's not a `.json` file! 🐱")
            return
        try:
            raw = (await attachment.read()).decode("utf-8")
        except Exception:
            await ctx.send("*scratches file* couldn't read that... make sure it's a valid text file! 🐱")
            return
        count, error = import_all_memories(raw)
        if error:
            await ctx.send(f"*knocks file off table* import failed: {error} 🐱")
            print(f"[CMD] @cat memory import_all failed: {error}")
        else:
            await ctx.send(f"*unpacks a big box* done! imported memories for {count} users~ 🐱")
            print(f"[CMD] @cat memory import_all completed by {ctx.author} — {count} users")
        return

    # ── View (default) ───────────────────────────────────
    if not mem.long_term_notes and not mem.recent_messages:
        await ctx.send("*tilts head* i don't remember anything about you yet... talk to me more! 🐱")
        print(f"[CMD] @cat memory — no memories found for {ctx.author}")
        return

    embed = discord.Embed(
        title=f"🧠 What I Remember About {ctx.author.display_name}",
        color=0xFFA500,
    )
    if mem.long_term_notes:
        embed.add_field(
            name="📝 Long-term Memories",
            value=mem.long_term_notes[:1024],
            inline=False,
        )
    embed.add_field(
        name="💬 Recent Conversation",
        value=f"{len(mem.recent_messages) // 2} exchanges in memory",
        inline=False,
    )
    import datetime
    if mem.last_seen > 0:
        last = datetime.datetime.fromtimestamp(mem.last_seen, tz=datetime.timezone.utc)
        embed.set_footer(text=f"Last talked: {last.strftime('%Y-%m-%d %H:%M UTC')}")
    await ctx.send(embed=embed)
    print(f"[CMD] @cat memory displayed for {ctx.author}")


@bot.command(name="help_me")
async def cat_help(ctx: commands.Context):
    """Show all available commands (@cat help_me)."""
    print(f"[CMD] @cat help_me triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
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
    embed.add_field(name="@cat memory", value="View what I remember about you", inline=False)
    embed.add_field(name="@cat memory clear", value="Make me forget everything about you", inline=False)
    embed.add_field(name="@cat memory export", value="Download your memories as a JSON file", inline=False)
    embed.add_field(name="@cat memory import", value="Restore memories from an attached JSON file", inline=False)
    embed.add_field(name="@cat memory export_all", value="Export all user memories (admin only)", inline=False)
    embed.add_field(name="@cat memory import_all", value="Import all user memories (admin only)", inline=False)
    embed.add_field(name="@cat <anything>", value="Just talk to me like a real cat!", inline=False)
    embed.add_field(name="@cat schedule", value="View the daily posting schedule", inline=False)
    embed.add_field(name="@cat help_me", value="Show this help message", inline=False)
    embed.set_footer(text="Cat Supremacy Bot • Cats rule the world!")
    await ctx.send(embed=embed)
    print(f"[CMD] @cat help_me completed for {ctx.author}")


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """If the command is not found, treat the entire message as a question for the AI."""
    if isinstance(error, commands.CommandNotFound):
        # Only respond when the bot is explicitly mentioned/tagged
        if bot.user not in ctx.message.mentions:
            return
        # Ignore messages from bots (including self)
        if ctx.author.bot:
            return

        # Extract everything after the mention as the question
        message = ctx.message.content
        for mention in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
            message = message.replace(mention, "")
        question = message.strip()

        if not question:
            print(f"[CHAT] Empty message from {ctx.author} — ignored")
            await ctx.send("*stares at you blankly* ...meow? ask me someething! human 🐱")
            return

        print(f"[CHAT] AI chat from {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}: '{question[:80]}'")

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

        # ── Memory integration ──────────────────────────────
        user_id = ctx.author.id
        username = ctx.author.display_name
        mem = get_user_memory(user_id, username)

        async with ctx.typing():
            answer = await ask_cat(
                question,
                custom_context=combined_context,
                user_memory_context=mem.build_context_block(),
                recent_messages=mem.build_recent_for_api(),
            )

        await ctx.send(answer[:2000])
        print(f"[CHAT] AI response sent to {ctx.author} ({len(answer)} chars)")

        # Save the exchange & extract important facts in the background
        mem.add_exchange(question, answer)
        save_memories()
        print(f"[CHAT] Exchange saved for {ctx.author} — launching memory extraction")
        # Fire-and-forget memory extraction (cheap nano model)
        bot.loop.create_task(
            extract_and_update_memories(
                user_id, username, question, answer, mem.long_term_notes
            )
        )
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
