"""Bot event handlers — on_ready and on_command_error (chat fallback)."""

from __future__ import annotations

import re

import discord
from discord.ext import commands

import config
from bot.helpers import parse_attachments, send_long_response
from bot.commands.ai_chat import custom_contexts
from memory.guild_settings import load_all_settings as load_guild_settings, get as gs_get
from memory import (
    get_user_memory,
    load_all as load_conversations,
    save_all as save_conversations,
    prune_old_conversations,
    search_memories,
    format_memories_block,
    extract_and_update_memories,
    migrate_legacy_notes_to_vector_store,
)
from services.openai_chat import ask_cat
from scheduler import setup_scheduled_tasks


def register_events(bot: commands.Bot) -> None:
    """Attach event handlers to *bot*."""

    # Set up the scheduled poster (returns the task; stored on bot)
    cat_poster = setup_scheduled_tasks(bot)

    @bot.event
    async def on_ready():
        load_guild_settings()
        load_conversations()
        prune_old_conversations()

        # Migrate legacy flat-text notes into ChromaDB (one-time)
        try:
            migrated = await migrate_legacy_notes_to_vector_store()
            if migrated:
                print(f"[INFO] Migrated {migrated} legacy memories to vector store")
        except Exception as e:
            print(f"[WARNING] Legacy migration failed (non-fatal): {e}")

        print(f"[INFO] Logged in as {bot.user} (ID: {bot.user.id})")
        print(f"[INFO] Target channel: {config.CAT_CHANNEL_ID}")
        print("[INFO] Starting scheduled cat poster...")

        if not cat_poster.is_running():
            cat_poster.start()

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="cats take over the world 🐱👑",
            )
        )

        channel = bot.get_channel(config.CAT_CHANNEL_ID)
        if channel:
            await channel.send(
                "*stretches and yawns* mrrp~ i'm awake! "
                "Cat Supremacy Bot is online and ready to serve the feline overlords 🐱👑"
            )
            print(f"[INFO] Hello message sent to #{channel.name}")
        else:
            print(f"[WARNING] Could not find channel {config.CAT_CHANNEL_ID} to send hello message")

        print("[INFO] Cat Supremacy Bot is live! 🐱👑")

    @bot.event
    async def on_command_error(ctx: commands.Context, error):
        """If the command is not found, treat the message as a chat question."""
        if not isinstance(error, commands.CommandNotFound):
            raise error

        if bot.user not in ctx.message.mentions:
            return
        if ctx.author.bot:
            return

        message = ctx.message.content
        for mention in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
            message = message.replace(mention, "")
        question = message.strip()

        if not question:
            await ctx.send("*stares at you blankly* ...meow? ask me someething! human 🐱")
            return

        print(f"[CHAT] AI chat from {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}: '{question[:80]}'")

        # Parse attachments
        question_ref = [question]
        attachments_for_ai = await parse_attachments(
            ctx.message.attachments, question_ref=question_ref,
        )
        question = question_ref[0]

        # Inline [context: ...] override
        inline_context = None
        context_match = re.search(r'\[context:\s*(.+?)\]', question, re.IGNORECASE | re.DOTALL)
        if context_match:
            inline_context = context_match.group(1).strip()
            question = re.sub(r'\[context:\s*.+?\]', '', question, flags=re.IGNORECASE | re.DOTALL).strip()

        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        server_context = custom_contexts.get(guild_id)
        combined_context = None
        if inline_context and server_context:
            combined_context = f"{server_context}\n\nInline context: {inline_context}"
        elif inline_context:
            combined_context = inline_context
        elif server_context:
            combined_context = server_context

        user_id = ctx.author.id
        username = ctx.author.display_name
        mem = get_user_memory(user_id, username)

        retrieved_memories = await search_memories(user_id, question)
        memory_context = format_memories_block(retrieved_memories)

        async with ctx.typing():
            answer = await ask_cat(
                question,
                custom_context=combined_context,
                user_memory_context=memory_context,
                recent_messages=mem.build_recent_for_api(),
                attachments=attachments_for_ai if attachments_for_ai else None,
                guild_id=guild_id,
            )

        await ctx.send(answer[:2000])
        print(f"[CHAT] AI response sent to {ctx.author} ({len(answer)} chars)")

        mem.add_exchange(question, answer)
        save_conversations()
        print(f"[CHAT] Exchange saved for {ctx.author} — launching vector memory extraction")
        bot.loop.create_task(
            extract_and_update_memories(user_id, username, question, answer, guild_id=guild_id)
        )
