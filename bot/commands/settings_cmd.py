"""Settings commands — view and change bot settings from Discord.

Admin-only commands that let guild administrators customise every
tunable setting without restarting the bot.
"""

from __future__ import annotations

import discord
from discord.ext import commands

from memory.guild_settings import (
    SETTING_DEFS,
    get,
    set as gs_set,
    reset,
    get_all_overrides,
    get_default,
)


def _format_value(key: str, value) -> str:
    """Pretty-print a setting value."""
    if value is None:
        return "*not set*"
    if key.endswith("_color"):
        return f"`#{value:06X}`"
    if key == "cat_personality":
        preview = str(value)[:80]
        return f'"{preview}…"' if len(str(value)) > 80 else f'"{preview}"'
    return f"`{value}`"


def _cast_value(key: str, raw: str):
    """Cast a raw string to the correct type for a setting."""
    defn = SETTING_DEFS.get(key)
    if defn is None:
        return None
    target = defn["type"]
    if target is int:
        # Support hex colours like 0xFFD700 or #FFD700
        raw = raw.strip()
        if raw.startswith("#"):
            return int(raw[1:], 16)
        if raw.lower().startswith("0x"):
            return int(raw, 16)
        return int(raw)
    return str(raw)


class SettingsCog(commands.Cog, name="Settings"):
    """Guild-level bot settings — admin only."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Main dispatcher ──────────────────────────────────
    @commands.command(name="settings")
    @commands.has_permissions(administrator=True)
    async def settings_cmd(self, ctx: commands.Context, *, args: str = ""):
        """Manage bot settings (@cat settings <action> [key] [value])."""
        if not ctx.guild:
            await ctx.send("⚠️ Settings are per-server. Use this in a server channel.")
            return

        parts = args.strip().split(None, 2)
        action = parts[0].lower() if parts else "list"

        print(f"[CMD] @cat settings {action} by {ctx.author} in #{ctx.channel.name}")

        if action in ("list", "show", "view"):
            await self._list(ctx)
        elif action == "get" and len(parts) >= 2:
            await self._get(ctx, parts[1].lower())
        elif action == "set" and len(parts) >= 3:
            await self._set(ctx, parts[1].lower(), parts[2])
        elif action == "reset" and len(parts) >= 2:
            await self._reset(ctx, parts[1].lower())
        elif action in ("keys", "help"):
            await self._show_keys(ctx)
        elif action == "reset_all":
            await self._reset_all(ctx)
        else:
            await self._show_help(ctx)

    # ── Sub-handlers ─────────────────────────────────────

    async def _list(self, ctx: commands.Context):
        """Show all settings with their current effective values."""
        guild_id = ctx.guild.id
        overrides = get_all_overrides(guild_id)

        embed = discord.Embed(
            title="⚙️  Bot Settings",
            description="Settings with ✏️ have been customised. Others use defaults.",
            color=0x5865F2,
        )

        # Group by category
        categories = {
            "📅 Schedule":   ["morning_hour", "afternoon_hour", "evening_hour"],
            "🎨 Colours":    ["morning_color", "afternoon_color", "evening_color"],
            "🤖 AI":         ["chat_model", "extraction_model", "cat_personality"],
            "🧠 Memory":     ["memory_top_k", "max_memories_per_user",
                              "max_recent_messages", "conversation_ttl_days"],
            "🏆 Challenges": ["challenge_reminder_hours"],
            "📢 Channel":    ["cat_channel_id"],
        }

        for cat_name, keys in categories.items():
            lines = []
            for key in keys:
                val = get(guild_id, key)
                marker = "✏️" if key in overrides else "📋"
                lines.append(f"{marker} **{key}** → {_format_value(key, val)}")
            embed.add_field(name=cat_name, value="\n".join(lines), inline=False)

        embed.set_footer(text="Use '@cat settings set <key> <value>' to change | '@cat settings keys' for details")
        await ctx.send(embed=embed)

    async def _get(self, ctx: commands.Context, key: str):
        """Show a single setting's current and default values."""
        if key not in SETTING_DEFS:
            await ctx.send(f"❌ Unknown setting `{key}`. Use `@cat settings keys` to see all.")
            return
        guild_id = ctx.guild.id
        current = get(guild_id, key)
        default = get_default(key)
        overrides = get_all_overrides(guild_id)
        is_custom = key in overrides
        desc = SETTING_DEFS[key]["desc"]

        embed = discord.Embed(title=f"⚙️  {key}", description=desc, color=0x5865F2)
        embed.add_field(name="Current", value=_format_value(key, current), inline=True)
        embed.add_field(name="Default", value=_format_value(key, default), inline=True)
        embed.add_field(name="Customised?", value="✅ Yes" if is_custom else "No", inline=True)
        await ctx.send(embed=embed)

    async def _set(self, ctx: commands.Context, key: str, raw_value: str):
        """Change a setting's value."""
        if key not in SETTING_DEFS:
            await ctx.send(f"❌ Unknown setting `{key}`. Use `@cat settings keys` to see all.")
            return

        try:
            value = _cast_value(key, raw_value)
        except (ValueError, TypeError):
            expected = SETTING_DEFS[key]["type"].__name__
            await ctx.send(f"❌ Invalid value. Expected type: **{expected}**")
            return

        # Validation
        if key.endswith("_hour") and not (0 <= value <= 23):
            await ctx.send("❌ Hour must be between 0 and 23.")
            return
        if key in ("memory_top_k", "max_memories_per_user", "max_recent_messages",
                    "conversation_ttl_days", "challenge_reminder_hours") and value < 1:
            await ctx.send("❌ Value must be at least 1.")
            return

        guild_id = ctx.guild.id
        gs_set(guild_id, key, value)

        embed = discord.Embed(
            title="✅  Setting Updated",
            description=f"**{key}** → {_format_value(key, value)}",
            color=0x00CC66,
        )
        embed.set_footer(text="Changes take effect immediately.")
        await ctx.send(embed=embed)
        print(f"[SETTINGS] {ctx.author} set {key} = {value!r} in guild {guild_id}")

    async def _reset(self, ctx: commands.Context, key: str):
        """Reset a setting to its global default."""
        if key not in SETTING_DEFS:
            await ctx.send(f"❌ Unknown setting `{key}`. Use `@cat settings keys` to see all.")
            return

        guild_id = ctx.guild.id
        default = reset(guild_id, key)

        embed = discord.Embed(
            title="🔄  Setting Reset",
            description=f"**{key}** → {_format_value(key, default)} *(default)*",
            color=0xFFA500,
        )
        await ctx.send(embed=embed)

    async def _reset_all(self, ctx: commands.Context):
        """Reset all settings to defaults."""
        guild_id = ctx.guild.id
        overrides = get_all_overrides(guild_id)
        if not overrides:
            await ctx.send("ℹ️ No custom settings to reset.")
            return
        for key in list(overrides.keys()):
            reset(guild_id, key)

        embed = discord.Embed(
            title="🔄  All Settings Reset",
            description=f"Reset **{len(overrides)}** setting(s) to defaults.",
            color=0xFFA500,
        )
        await ctx.send(embed=embed)

    async def _show_keys(self, ctx: commands.Context):
        """Show all available setting keys with descriptions."""
        embed = discord.Embed(
            title="🔑  Available Settings",
            description="All keys you can customise with `@cat settings set <key> <value>`",
            color=0x5865F2,
        )
        lines = []
        for key, defn in SETTING_DEFS.items():
            type_name = defn["type"].__name__
            lines.append(f"`{key}` ({type_name}) — {defn['desc']}")

        # Split into chunks to stay under field value limit (1024 chars)
        chunk = ""
        chunk_num = 1
        for line in lines:
            if len(chunk) + len(line) + 1 > 1000:
                embed.add_field(name=f"Keys ({chunk_num})", value=chunk, inline=False)
                chunk = ""
                chunk_num += 1
            chunk += line + "\n"
        if chunk:
            embed.add_field(name=f"Keys ({chunk_num})" if chunk_num > 1 else "Keys", value=chunk, inline=False)

        embed.set_footer(text="Use '@cat settings set <key> <value>' | '@cat settings reset <key>'")
        await ctx.send(embed=embed)

    async def _show_help(self, ctx: commands.Context):
        """Show settings command help."""
        embed = discord.Embed(
            title="⚙️  Settings — Help",
            description="Manage bot settings for this server (admin only).",
            color=0x5865F2,
        )
        embed.add_field(name="View all settings", value="`@cat settings list`", inline=False)
        embed.add_field(name="View one setting", value="`@cat settings get <key>`", inline=False)
        embed.add_field(name="Change a setting", value="`@cat settings set <key> <value>`", inline=False)
        embed.add_field(name="Reset to default", value="`@cat settings reset <key>`", inline=False)
        embed.add_field(name="Reset everything", value="`@cat settings reset_all`", inline=False)
        embed.add_field(name="Show all keys", value="`@cat settings keys`", inline=False)
        embed.set_footer(text="Colours accept hex: #FFD700 or 0xFFD700")
        await ctx.send(embed=embed)

    @settings_cmd.error
    async def settings_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🔒 Only server administrators can change settings.")
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
