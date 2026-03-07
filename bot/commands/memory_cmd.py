"""Memory management commands — view, clear, export, import."""

from __future__ import annotations

import datetime
import io

import discord
from discord.ext import commands

from memory import (
    get_user_memory,
    save_all as save_conversations,
    get_memory_count,
    get_all_memories,
    delete_user_memories,
    export_user_memories_json,
    import_user_memories_json,
    export_all_conversations,
    import_all_conversations,
)


class MemoryCog(commands.Cog, name="Memory"):
    """Commands for viewing and managing the bot's memory about you."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="memory")
    async def cat_memory(self, ctx: commands.Context, *, action: str = None):
        """View, clear, export, or import what the bot remembers about you."""
        print(f"[CMD] @cat memory triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        user_id = ctx.author.id
        mem = get_user_memory(user_id, ctx.author.display_name)

        # ── Clear ────────────────────────────────────────
        if action and action.lower() in ("clear", "reset", "forget", "wipe"):
            mem.recent_messages.clear()
            mem.long_term_notes = ""
            save_conversations()
            deleted = await delete_user_memories(user_id)
            await ctx.send(f"*bonks head on keyboard* poof! i forgot everything about you~ ({deleted} memories erased) fresh start! 🐱")
            print(f"[CMD] @cat memory cleared for {ctx.author} — {deleted} vector memories deleted")
            return

        # ── Export (single user — vector memories) ───────
        if action and action.lower() == "export":
            data = await export_user_memories_json(user_id)
            if data is None:
                await ctx.send("*tilts head* nothing to export... talk to me first! 🐱")
                return
            file = discord.File(
                io.BytesIO(data.encode("utf-8")),
                filename=f"cat_memory_{ctx.author.name}.json",
            )
            await ctx.send("*carefully packs memories into a box* here you go~ 📦🐱", file=file)
            print(f"[CMD] @cat memory export completed for {ctx.author}")
            return

        # ── Export all (admin only — conversation data) ──
        if action and action.lower() == "export_all":
            if not ctx.guild or not ctx.author.guild_permissions.administrator:
                await ctx.send("*hisses* only server admins can export all memories! 🐱")
                return
            data = export_all_conversations()
            file = discord.File(
                io.BytesIO(data.encode("utf-8")),
                filename="cat_memories_all.json",
            )
            await ctx.send("*drops a big box of memories off the table* here's everyone's data~ 📦🐱", file=file)
            print(f"[CMD] @cat memory export_all completed by {ctx.author}")
            return

        # ── Import (single user — vector memories) ───────
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
            count, error = await import_user_memories_json(user_id, raw)
            if error:
                await ctx.send(f"*knocks file off table* import failed: {error} 🐱")
            else:
                await ctx.send(f"*unpacks memories carefully* done! imported {count} memories~ 🐱")
                print(f"[CMD] @cat memory import completed for {ctx.author} — {count} memories")
            return

        # ── Import all (admin only — conversation data) ──
        if action and action.lower() == "import_all":
            if not ctx.guild or not ctx.author.guild_permissions.administrator:
                await ctx.send("*hisses* only server admins can import all memories! 🐱")
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
            count, error = import_all_conversations(raw)
            if error:
                await ctx.send(f"*knocks file off table* import failed: {error} 🐱")
            else:
                await ctx.send(f"*unpacks a big box* done! imported memories for {count} users~ 🐱")
                print(f"[CMD] @cat memory import_all completed by {ctx.author} — {count} users")
            return

        # ── View (default) ───────────────────────────────
        vec_count = await get_memory_count(user_id)
        if not vec_count and not mem.recent_messages:
            await ctx.send("*tilts head* i don't remember anything about you yet... talk to me more! 🐱")
            return

        embed = discord.Embed(
            title=f"🧠 What I Remember About {ctx.author.display_name}",
            color=0xFFA500,
        )
        if vec_count:
            all_mems = await get_all_memories(user_id)
            display = all_mems[:10]
            mem_lines = [f"• {m.memory_text}" for m in display]
            mem_text = "\n".join(mem_lines)
            if len(mem_text) > 1024:
                mem_text = mem_text[:1021] + "..."
            embed.add_field(
                name=f"📝 Long-term Memories ({vec_count} total)",
                value=mem_text,
                inline=False,
            )
        embed.add_field(
            name="💬 Recent Conversation",
            value=f"{len(mem.recent_messages) // 2} exchanges in memory",
            inline=False,
        )
        if mem.last_seen > 0:
            last = datetime.datetime.fromtimestamp(mem.last_seen, tz=datetime.timezone.utc)
            embed.set_footer(text=f"Last talked: {last.strftime('%Y-%m-%d %H:%M UTC')}")
        await ctx.send(embed=embed)
        print(f"[CMD] @cat memory displayed for {ctx.author}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryCog(bot))
