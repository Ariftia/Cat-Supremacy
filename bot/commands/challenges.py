"""Challenge commands — create, join, complete, and manage daily/weekly challenges.

Includes an automatic reminder loop that pings participants who haven't
completed their active challenges.
"""

from __future__ import annotations

import datetime

import discord
from discord.ext import commands, tasks

import config
from memory.challenges import (
    Challenge,
    create_challenge,
    get_challenge,
    get_active_challenges,
    delete_challenge,
    save_challenges,
    load_challenges,
    check_and_renew_expired,
    get_incomplete_challenges,
    _format_deadline,
)


def _challenge_embed(c: Challenge, *, show_participants: bool = False) -> discord.Embed:
    """Build a rich embed for a challenge."""
    color = 0x00CC99 if c.mode == "daily" else 0x7289DA
    emoji = "📅" if c.mode == "daily" else "📆"
    status = "✅ Active" if c.active else "❌ Ended"

    embed = discord.Embed(
        title=f"{emoji}  Challenge #{c.id} — {c.title}",
        description=c.description or "*No description set.*",
        color=color,
    )
    embed.add_field(name="Mode", value=c.mode.capitalize(), inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Deadline", value=_format_deadline(c.deadline), inline=False)

    joined = len(c.participants)
    done = len(c.completions)
    embed.add_field(
        name="Progress",
        value=f"{done}/{joined} completed" if joined else "No participants yet",
        inline=True,
    )

    if show_participants and c.participants:
        done_list = [f"<@{uid}> ✅" for uid in c.participants if c.has_completed(uid)]
        pending_list = [f"<@{uid}> ⏳" for uid in c.participants if not c.has_completed(uid)]
        all_lines = done_list + pending_list
        text = "\n".join(all_lines[:20])
        if len(all_lines) > 20:
            text += f"\n… and {len(all_lines) - 20} more"
        embed.add_field(name="Participants", value=text, inline=False)

    embed.set_footer(text=f"Created by user {c.created_by} • ID: {c.id}")
    return embed


class ChallengeCog(commands.Cog, name="Challenges"):
    """Daily and weekly challenge system with reminders."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        load_challenges()
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    # ── Reminder task ────────────────────────────────────

    @tasks.loop(hours=config.CHALLENGE_REMINDER_HOURS)
    async def reminder_loop(self):
        """Periodically check for expired challenges (renew them) and
        remind participants who haven't completed active ones."""
        # 1. Renew expired challenges
        renewed = check_and_renew_expired()
        for c in renewed:
            channel = self.bot.get_channel(c.channel_id)
            if channel:
                embed = discord.Embed(
                    title=f"🔄 Challenge #{c.id} has reset!",
                    description=(
                        f"**{c.title}** ({c.mode}) has entered a new cycle.\n"
                        f"New deadline: **{_format_deadline(c.deadline)}**\n\n"
                        "Completions have been cleared — time to do it again!"
                    ),
                    color=0xFFA500,
                )
                await channel.send(embed=embed)

        # 2. Remind incomplete participants
        incomplete = get_incomplete_challenges()
        for c in incomplete:
            channel = self.bot.get_channel(c.channel_id)
            if not channel:
                continue
            missing = c.incomplete_participants
            if not missing:
                continue

            pings = " ".join(f"<@{uid}>" for uid in missing)
            remaining = c.deadline - datetime.datetime.now(datetime.timezone.utc).timestamp()
            hours_left = max(0, remaining / 3600)

            embed = discord.Embed(
                title=f"⏰ Challenge Reminder — #{c.id} {c.title}",
                description=(
                    f"**{c.description or c.title}**\n\n"
                    f"⏳ **{hours_left:.0f}h** remaining until deadline!\n"
                    f"Use `@cat challenge done {c.id}` when you're finished."
                ),
                color=0xFF4444,
            )
            done_count = len(c.completions)
            total = len(c.participants)
            embed.add_field(
                name="Progress",
                value=f"{done_count}/{total} completed",
                inline=True,
            )
            await channel.send(content=pings, embed=embed)
            print(f"[CHALLENGE] Reminded {len(missing)} users for #{c.id} in guild {c.guild_id}")

    @reminder_loop.before_loop
    async def before_reminder(self):
        await self.bot.wait_until_ready()

    # ── Main command ─────────────────────────────────────

    @commands.command(name="challenge")
    async def challenge_cmd(self, ctx: commands.Context, *, action: str = None):
        """Manage daily & weekly challenges."""
        if not action:
            await self._show_help(ctx)
            return

        parts = action.strip().split(None, 1)
        sub = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        handlers = {
            "create": self._create,
            "describe": self._describe,
            "list": self._list,
            "join": self._join,
            "leave": self._leave,
            "done": self._done,
            "complete": self._done,
            "status": self._status,
            "remind": self._remind,
            "delete": self._delete,
            "end": self._end,
            "help": self._show_help,
        }

        handler = handlers.get(sub)
        if handler:
            await handler(ctx, rest)
        else:
            await ctx.send(
                f"*tilts head* unknown action `{sub}`... "
                "try `@cat challenge help` for the full list 🐱"
            )

    # ── Sub-handlers ─────────────────────────────────────

    async def _create(self, ctx: commands.Context, rest: str):
        """``@cat challenge create <daily|weekly> <title>``"""
        parts = rest.strip().split(None, 1)
        if len(parts) < 2 or parts[0].lower() not in ("daily", "weekly"):
            await ctx.send(
                "*paws at keyboard* usage: `@cat challenge create <daily|weekly> <title>`\n"
                "example: `@cat challenge create weekly Do 100 pushups` 🐱"
            )
            return

        mode = parts[0].lower()
        title = parts[1].strip()
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id

        c = create_challenge(
            guild_id=guild_id,
            channel_id=ctx.channel.id,
            title=title,
            description="",
            mode=mode,
            created_by=ctx.author.id,
        )

        embed = _challenge_embed(c)
        embed.title = f"🎉 New {mode.capitalize()} Challenge Created!"
        embed.add_field(
            name="How to participate",
            value=(
                f"`@cat challenge join {c.id}` — join this challenge\n"
                f"`@cat challenge describe {c.id} <text>` — set a description\n"
                f"`@cat challenge done {c.id}` — mark as completed"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)
        print(f"[CMD] @cat challenge create by {ctx.author} — #{c.id} '{title}' ({mode})")

    async def _describe(self, ctx: commands.Context, rest: str):
        """``@cat challenge describe <id> <description>``"""
        parts = rest.strip().split(None, 1)
        if len(parts) < 2:
            await ctx.send("usage: `@cat challenge describe <id> <description text>` 🐱")
            return

        c = self._get_challenge_or_none(ctx, parts[0])
        if c is None:
            await ctx.send(f"*sniffs around* can't find challenge #{parts[0]}... 🐱")
            return

        # Only creator or admin can edit
        is_admin = ctx.guild and ctx.author.guild_permissions.administrator
        if ctx.author.id != c.created_by and not is_admin:
            await ctx.send("*hisses* only the creator or an admin can edit the description! 🐱")
            return

        c.description = parts[1].strip()[:2000]
        save_challenges()
        await ctx.send(f"*scribbles notes* description updated for challenge #{c.id}! 🐱")
        print(f"[CMD] @cat challenge describe #{c.id} by {ctx.author}")

    async def _list(self, ctx: commands.Context, rest: str):
        """``@cat challenge list [daily|weekly]``"""
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        mode_filter = rest.strip().lower() if rest.strip() in ("daily", "weekly") else None
        challenges = get_active_challenges(guild_id, mode=mode_filter)

        if not challenges:
            label = f" {mode_filter}" if mode_filter else ""
            await ctx.send(f"*yawns* no active{label} challenges right now... create one with `@cat challenge create`! 🐱")
            return

        embed = discord.Embed(
            title="🏆 Active Challenges",
            color=0x00CC99,
        )
        for c in challenges:
            emoji = "📅" if c.mode == "daily" else "📆"
            done = len(c.completions)
            total = len(c.participants)
            embed.add_field(
                name=f"{emoji} #{c.id} — {c.title}",
                value=(
                    f"{c.description[:100] or '*No description*'}\n"
                    f"Progress: **{done}/{total}** • Deadline: {_format_deadline(c.deadline)}"
                ),
                inline=False,
            )
        embed.set_footer(text="Use @cat challenge join <id> to participate!")
        await ctx.send(embed=embed)

    async def _join(self, ctx: commands.Context, rest: str):
        """``@cat challenge join <id>``"""
        c = self._get_challenge_or_none(ctx, rest.strip())
        if c is None:
            await ctx.send(f"*sniffs around* can't find that challenge... 🐱")
            return
        if not c.active:
            await ctx.send("*shakes head* that challenge has ended! 🐱")
            return

        if c.join(ctx.author.id):
            save_challenges()
            await ctx.send(
                f"*high-paws* {ctx.author.mention} joined challenge #{c.id} — **{c.title}**! "
                f"({len(c.participants)} participants now) 🐱🎯"
            )
            print(f"[CMD] @cat challenge join #{c.id} by {ctx.author}")
        else:
            await ctx.send("*pokes you* you already joined this challenge! 🐱")

    async def _leave(self, ctx: commands.Context, rest: str):
        """``@cat challenge leave <id>``"""
        c = self._get_challenge_or_none(ctx, rest.strip())
        if c is None:
            await ctx.send(f"*sniffs around* can't find that challenge... 🐱")
            return

        if c.leave(ctx.author.id):
            save_challenges()
            await ctx.send(f"*waves goodbye* you left challenge #{c.id}. come back anytime~ 🐱")
        else:
            await ctx.send("*tilts head* you're not in that challenge... 🐱")

    async def _done(self, ctx: commands.Context, rest: str):
        """``@cat challenge done <id>``"""
        c = self._get_challenge_or_none(ctx, rest.strip().split()[0] if rest.strip() else "")
        if c is None:
            await ctx.send(f"*sniffs around* can't find that challenge... use `@cat challenge list` to see active ones 🐱")
            return
        if not c.active:
            await ctx.send("*shakes head* that challenge has ended! 🐱")
            return

        if c.complete(ctx.author.id):
            save_challenges()
            done = len(c.completions)
            total = len(c.participants)
            await ctx.send(
                f"🎉 *purrs proudly* {ctx.author.mention} completed challenge #{c.id} — **{c.title}**! "
                f"({done}/{total} done) 🐱✨"
            )
            if done == total and total > 0:
                await ctx.send(f"🏆 **ALL participants completed challenge #{c.id}!** Amazing work everyone! 🐱👑")
            print(f"[CMD] @cat challenge done #{c.id} by {ctx.author}")
        elif ctx.author.id not in c.participants:
            await ctx.send(
                f"*tilts head* you need to join first! use `@cat challenge join {c.id}` 🐱"
            )
        else:
            await ctx.send("*pokes you* you already completed this challenge! 🐱")

    async def _status(self, ctx: commands.Context, rest: str):
        """``@cat challenge status [id]``"""
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id

        if rest.strip():
            c = self._get_challenge_or_none(ctx, rest.strip())
            if c is None:
                await ctx.send(f"*sniffs around* can't find that challenge... 🐱")
                return
            embed = _challenge_embed(c, show_participants=True)
            await ctx.send(embed=embed)
        else:
            # Show summary of all active challenges
            challenges = get_active_challenges(guild_id)
            if not challenges:
                await ctx.send("*yawns* no active challenges to show status for... 🐱")
                return
            for c in challenges[:5]:  # limit to 5 to avoid spam
                embed = _challenge_embed(c, show_participants=True)
                await ctx.send(embed=embed)

    async def _remind(self, ctx: commands.Context, rest: str):
        """``@cat challenge remind [id]``"""
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id

        if rest.strip():
            c = self._get_challenge_or_none(ctx, rest.strip())
            if c is None:
                await ctx.send(f"*sniffs around* can't find that challenge... 🐱")
                return
            challenges_to_remind = [c] if c.active and c.incomplete_participants else []
        else:
            challenges_to_remind = [
                c for c in get_active_challenges(guild_id)
                if c.incomplete_participants
            ]

        if not challenges_to_remind:
            await ctx.send("*purrs* everyone's up to date! no reminders needed 🐱✨")
            return

        for c in challenges_to_remind:
            missing = c.incomplete_participants
            pings = " ".join(f"<@{uid}>" for uid in missing)
            remaining = c.deadline - datetime.datetime.now(datetime.timezone.utc).timestamp()
            hours_left = max(0, remaining / 3600)

            embed = discord.Embed(
                title=f"⏰ Reminder — #{c.id} {c.title}",
                description=(
                    f"**{c.description or c.title}**\n\n"
                    f"⏳ **{hours_left:.0f}h** remaining!\n"
                    f"Use `@cat challenge done {c.id}` when you're finished."
                ),
                color=0xFF4444,
            )
            done_count = len(c.completions)
            total = len(c.participants)
            embed.add_field(name="Progress", value=f"{done_count}/{total} completed", inline=True)
            await ctx.send(content=pings, embed=embed)

        print(f"[CMD] @cat challenge remind by {ctx.author} — {len(challenges_to_remind)} challenges")

    async def _delete(self, ctx: commands.Context, rest: str):
        """``@cat challenge delete <id>`` (creator or admin only)"""
        c = self._get_challenge_or_none(ctx, rest.strip())
        if c is None:
            await ctx.send(f"*sniffs around* can't find that challenge... 🐱")
            return

        is_admin = ctx.guild and ctx.author.guild_permissions.administrator
        if ctx.author.id != c.created_by and not is_admin:
            await ctx.send("*hisses* only the creator or an admin can delete a challenge! 🐱")
            return

        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        delete_challenge(guild_id, c.id)
        await ctx.send(f"*knocks challenge #{c.id} off the table* deleted! 🐱")
        print(f"[CMD] @cat challenge delete #{c.id} by {ctx.author}")

    async def _end(self, ctx: commands.Context, rest: str):
        """``@cat challenge end <id>`` — deactivate without deleting (creator or admin)."""
        c = self._get_challenge_or_none(ctx, rest.strip())
        if c is None:
            await ctx.send(f"*sniffs around* can't find that challenge... 🐱")
            return

        is_admin = ctx.guild and ctx.author.guild_permissions.administrator
        if ctx.author.id != c.created_by and not is_admin:
            await ctx.send("*hisses* only the creator or an admin can end a challenge! 🐱")
            return

        c.active = False
        save_challenges()

        done = len(c.completions)
        total = len(c.participants)
        embed = discord.Embed(
            title=f"🏁 Challenge #{c.id} Has Ended!",
            description=f"**{c.title}**\n\nFinal score: **{done}/{total}** completed!",
            color=0x888888,
        )
        if c.participants:
            completed = [f"<@{uid}> ✅" for uid in c.participants if c.has_completed(uid)]
            missed = [f"<@{uid}> ❌" for uid in c.participants if not c.has_completed(uid)]
            if completed:
                embed.add_field(name="Completed", value="\n".join(completed[:10]), inline=True)
            if missed:
                embed.add_field(name="Missed", value="\n".join(missed[:10]), inline=True)
        await ctx.send(embed=embed)
        print(f"[CMD] @cat challenge end #{c.id} by {ctx.author}")

    async def _show_help(self, ctx: commands.Context, rest: str = ""):
        """Show challenge command help."""
        embed = discord.Embed(
            title="🏆 Challenge Commands",
            description="Daily & weekly challenges for your server!",
            color=0x00CC99,
        )
        cmds = [
            ("`@cat challenge create <daily|weekly> <title>`", "Create a new challenge"),
            ("`@cat challenge describe <id> <text>`", "Set/edit the description"),
            ("`@cat challenge list [daily|weekly]`", "View active challenges"),
            ("`@cat challenge join <id>`", "Join a challenge"),
            ("`@cat challenge leave <id>`", "Leave a challenge"),
            ("`@cat challenge done <id>`", "Mark yourself as completed"),
            ("`@cat challenge status [id]`", "See who's completed / pending"),
            ("`@cat challenge remind [id]`", "Ping participants who haven't finished"),
            ("`@cat challenge end <id>`", "End a challenge (creator/admin)"),
            ("`@cat challenge delete <id>`", "Permanently remove a challenge (creator/admin)"),
        ]
        for name, value in cmds:
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text="Reminders are sent automatically every few hours for active challenges!")
        await ctx.send(embed=embed)

    # ── Helpers ──────────────────────────────────────────

    def _get_challenge_or_none(self, ctx: commands.Context, id_str: str) -> Challenge | None:
        """Parse an ID string and look up the challenge in this guild."""
        try:
            cid = int(id_str)
        except (ValueError, TypeError):
            return None
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        return get_challenge(guild_id, cid)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChallengeCog(bot))
