"""Cat content commands — now, gif, fact, schedule."""

from __future__ import annotations

import discord
from discord.ext import commands

import config
from scheduler import _build_scheduled_messages, _current_slot, _build_time_of_day, TIME_OF_DAY
from services.cat_api import fetch_cat_fact, fetch_cat_gif


class CatContentCog(commands.Cog, name="Cat Content"):
    """Commands for getting cat GIFs, facts, and schedule info."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="now")
    async def cat_now(self, ctx: commands.Context):
        """Immediately post a cat GIF and fact (@cat now)."""
        print(f"[CMD] @cat now triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        guild_id = ctx.guild.id if ctx.guild else None
        slot = _current_slot(guild_id=guild_id)
        async with ctx.typing():
            greeting, fact, gif_url = await _build_scheduled_messages(slot)
        await ctx.send(greeting[:2000])
        await ctx.send(gif_url[:2000])
        await ctx.send(fact)
        print(f"[CMD] @cat now completed for {ctx.author}")

    @commands.command(name="fact")
    async def cat_fact_cmd(self, ctx: commands.Context):
        """Get just a cat fact (@cat fact)."""
        print(f"[CMD] @cat fact triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        fact = await fetch_cat_fact()
        await ctx.send(f"🐱 **Cat Fact:** {fact}")
        print(f"[CMD] @cat fact completed for {ctx.author}")

    @commands.command(name="gif")
    async def cat_gif_cmd(self, ctx: commands.Context):
        """Get just a cat GIF (@cat gif)."""
        print(f"[CMD] @cat gif triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        gif = await fetch_cat_gif()
        await ctx.send(gif)
        print(f"[CMD] @cat gif completed for {ctx.author}")

    @commands.command(name="schedule")
    async def cat_schedule(self, ctx: commands.Context):
        """Show the daily posting schedule (@cat schedule)."""
        print(f"[CMD] @cat schedule triggered by {ctx.author} in #{getattr(ctx.channel, 'name', 'DM')}")
        guild_id = ctx.guild.id if ctx.guild else None
        tod = _build_time_of_day(guild_id)
        embed = discord.Embed(
            title="🗓️ Cat Supremacy Daily Schedule (UTC)",
            color=0xFFA500,
        )
        for hour, slot in sorted(tod.items()):
            embed.add_field(
                name=f"{slot['emoji']} {slot['greeting']}",
                value=f"`{hour:02d}:00 UTC`",
                inline=True,
            )
        embed.set_footer(text="All times are in UTC. Adjust for your timezone!")
        await ctx.send(embed=embed)
        print(f"[CMD] @cat schedule completed for {ctx.author}")


async def setup(bot: commands.Bot):
    await bot.add_cog(CatContentCog(bot))
