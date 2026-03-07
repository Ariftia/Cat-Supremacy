"""AI-powered commands — detail, image, search, context, help_me."""

from __future__ import annotations

import base64
import io
import re

import discord
from discord.ext import commands

from bot.helpers import parse_attachments, send_long_response, IMAGE_EXTS
from memory import (
    get_user_memory,
    save_all as save_conversations,
    search_memories,
    format_memories_block,
    extract_and_update_memories,
)
from services.openai_chat import ask_cat
from services.openai_images import generate_image
from services.openai_search import search_web

# ── Per-server custom context store (in-memory) ─────────
custom_contexts: dict[int, str] = {}


class AIChatCog(commands.Cog, name="AI Chat"):
    """Commands that use OpenAI for chat, vision, image gen, and search."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── detail ───────────────────────────────────────────

    @commands.command(name="detail")
    async def cat_detail(self, ctx: commands.Context, *, question: str = None):
        """Analyze an attached image in high detail (@cat detail <question> + image)."""
        print(f"[CMD] @cat detail triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")

        if not ctx.message.attachments:
            await ctx.send("*squints* meow~ attach an image and i'll look at it closely! usage: `@cat detail <question>` with an image attached 🐱")
            return

        if not question:
            question = "Describe this image in detail. If there is any text, read and transcribe all of it."

        attachments_for_ai = await parse_attachments(ctx.message.attachments)

        if not any(a["type"] == "image" for a in attachments_for_ai):
            await ctx.send("*tilts head* that doesn't look like an image... attach a png, jpg, gif, or webp! 🐱")
            return

        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        user_id = ctx.author.id
        username = ctx.author.display_name
        mem = get_user_memory(user_id, username)

        retrieved_memories = await search_memories(user_id, question)
        memory_context = format_memories_block(retrieved_memories)

        async with ctx.typing():
            answer = await ask_cat(
                question,
                custom_context=custom_contexts.get(guild_id),
                user_memory_context=memory_context,
                recent_messages=mem.build_recent_for_api(),
                attachments=attachments_for_ai,
                image_detail="high",
            )

        await send_long_response(ctx, answer)
        mem.add_exchange(question, answer)
        save_conversations()
        print(f"[CMD] @cat detail completed for {ctx.author}")
        self.bot.loop.create_task(
            extract_and_update_memories(user_id, username, question, answer)
        )

    # ── image ────────────────────────────────────────────

    @commands.command(name="image")
    async def cat_image(self, ctx: commands.Context, *, prompt: str = None):
        """Generate an image with AI (@cat image <prompt>)."""
        print(f"[CMD] @cat image triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')} | prompt='{prompt}'")
        if not prompt and not ctx.message.attachments:
            await ctx.send("*knocks pencil off table* meow~ tell me what to draw! usage: `@cat image <description>` (attach an image to edit it!)")
            return

        if not prompt:
            prompt = "Modify this image creatively."

        image_urls: list[str] = []
        for att in ctx.message.attachments:
            fname = att.filename.lower()
            if any(fname.endswith(ext) for ext in IMAGE_EXTS) or (
                att.content_type and att.content_type.startswith("image/")
            ):
                image_urls.append(att.url)
                print(f"[CMD] @cat image — reference image: {att.filename}")

        async with ctx.typing():
            result = await generate_image(prompt, image_urls=image_urls if image_urls else None)

        if result.startswith("❌"):
            await ctx.send(result)
        elif result.startswith("data:image/"):
            b64_data = result.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
            file = discord.File(io.BytesIO(img_bytes), filename="cat_creation.png")
            embed = discord.Embed(color=0xFFA500)
            embed.set_image(url="attachment://cat_creation.png")
            embed.set_footer(text=f"🎨 {prompt[:100]}")
            await ctx.send(embed=embed, file=file)
        else:
            embed = discord.Embed(color=0xFFA500)
            embed.set_image(url=result)
            embed.set_footer(text=f"🎨 {prompt[:100]}")
            await ctx.send(embed=embed)
        print(f"[CMD] @cat image completed for {ctx.author}")

    # ── search ───────────────────────────────────────────

    @commands.command(name="search")
    async def cat_search(self, ctx: commands.Context, *, query: str = None):
        """Search the internet for news and journals (@cat search <query>)."""
        print(f"[CMD] @cat search triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')} | query='{query}'")
        if not query:
            await ctx.send("*paws at keyboard* meow~ tell me what to search! usage: `@cat search <topic>`")
            return

        async with ctx.typing():
            answer = await search_web(query)

        await send_long_response(ctx, answer)
        print(f"[CMD] @cat search completed for {ctx.author}")

    # ── context ──────────────────────────────────────────

    @commands.command(name="context")
    async def cat_context(self, ctx: commands.Context, *, content: str = None):
        """Set, view, or clear custom context for AI responses (@cat context <text>)."""
        print(f"[CMD] @cat context triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id

        if content is None:
            current = custom_contexts.get(guild_id)
            if current:
                await ctx.send(f"*flicks tail* current custom context:\n```\n{current[:1500]}\n```")
            else:
                await ctx.send("*yawns* no custom context set. use `@cat context <your text>` to add one~")
            return

        if content.lower() in ("clear", "reset", "remove", "none"):
            custom_contexts.pop(guild_id, None)
            await ctx.send("*knocks context off the table* custom context cleared! back to being just a cat~ 🐱")
            print(f"[CMD] @cat context cleared for guild {guild_id} by {ctx.author}")
            return

        if ctx.message.attachments:
            try:
                file_content = (await ctx.message.attachments[0].read()).decode("utf-8")
                content = f"{content}\n\n{file_content}" if content.strip() else file_content
            except Exception:
                await ctx.send("*hisses at file* couldn't read that attachment... text files only please!")
                return

        custom_contexts[guild_id] = content[:4000]
        await ctx.send(f"*purrs* custom context set! ({len(content[:4000])} chars) i'll use this knowledge when answering~ 🐱")
        print(f"[CMD] @cat context set for guild {guild_id} by {ctx.author} ({len(content[:4000])} chars)")

    # ── help ─────────────────────────────────────────────

    @commands.command(name="help_me")
    async def cat_help(self, ctx: commands.Context):
        """Show all available commands (@cat help_me)."""
        print(f"[CMD] @cat help_me triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        embed = discord.Embed(
            title="🐱👑 Cat Supremacy — Commands",
            description="Here's everything I can do!",
            color=0xFFA500,
        )
        embed.add_field(name="🐾 Cat Content", value=(
            "`@cat now` — Post a cat GIF + fact right now\n"
            "`@cat gif` — Get a random cat GIF\n"
            "`@cat fact` — Get a random cat fact\n"
            "`@cat schedule` — View the daily posting schedule"
        ), inline=False)
        embed.add_field(name="🤖 AI Features", value=(
            "`@cat search <topic>` — Search the internet\n"
            "`@cat image <desc>` — Generate an AI image\n"
            "`@cat detail <question>` — Analyze an attached image in detail\n"
            "`@cat context <text>` — Set custom knowledge for AI\n"
            "`@cat context clear` — Remove custom context"
        ), inline=False)
        embed.add_field(name="🧠 Memory", value=(
            "`@cat memory` — View what I remember about you\n"
            "`@cat memory clear` — Forget everything about you\n"
            "`@cat memory export` — Download your memories as JSON\n"
            "`@cat memory import` — Restore memories from JSON\n"
            "`@cat memory export_all` — Export all (admin)\n"
            "`@cat memory import_all` — Import all (admin)"
        ), inline=False)
        embed.add_field(name="🏆 Challenges", value=(
            "`@cat challenge create daily/weekly <title>` — New challenge\n"
            "`@cat challenge describe <id> <text>` — Set description\n"
            "`@cat challenge list [daily|weekly]` — List active\n"
            "`@cat challenge join <id>` — Join a challenge\n"
            "`@cat challenge leave <id>` — Leave a challenge\n"
            "`@cat challenge done <id>` — Mark as completed\n"
            "`@cat challenge status <id>` — View progress\n"
            "`@cat challenge remind [id]` — Ping incomplete participants\n"
            "`@cat challenge end <id>` — End challenge (creator/admin)\n"
            "`@cat challenge delete <id>` — Delete (creator/admin)"
        ), inline=False)
        embed.add_field(name="⚙️ Settings (admin)", value=(
            "`@cat settings list` — View all settings\n"
            "`@cat settings set <key> <value>` — Change a setting\n"
            "`@cat settings reset <key>` — Reset to default\n"
            "`@cat settings keys` — Show all available keys"
        ), inline=False)
        embed.add_field(name="💬 Chat", value=(
            "`@cat <anything>` — Talk to me! Attach images, PDFs, "
            "or text files and I'll read them too~\n"
            "`@cat help_me` — Show this message"
        ), inline=False)
        embed.set_footer(text="Cat Supremacy Bot • Cats rule the world!")
        await ctx.send(embed=embed)
        print(f"[CMD] @cat help_me completed for {ctx.author}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChatCog(bot))
