import discord
from discord.ext import commands
import logging
import asyncio
import datetime
import collections

logger = logging.getLogger("CVNovaHelper.discord_audit_logger")

DISCORD_LOGS_CH_ID = 1566986370910654517

class DiscordAuditLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self._msg_cache = collections.OrderedDict()

    def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        ch_id = self.config.get("channels", {}).get("discord_logs", DISCORD_LOGS_CH_ID)
        ch = guild.get_channel(ch_id)
        if not ch:
            ch = self.bot.get_channel(ch_id)
        return ch

    async def get_audit_entry(self, guild: discord.Guild, action, target_id=None, max_age_seconds=60):
        """Fetch the most recent audit log entry matching action and target with multi-action, retry, and crash-safe fallback support."""
        actions = action if isinstance(action, (list, tuple, set)) else [action]

        for attempt in range(2):
            try:
                await asyncio.sleep(0.6 if attempt == 0 else 1.5)
                now = discord.utils.utcnow()

                # 1. Search by specific actions
                for act in actions:
                    try:
                        async for entry in guild.audit_logs(limit=20, action=act):
                            age = (now - entry.created_at).total_seconds()
                            if age > max_age_seconds:
                                continue
                            if target_id is not None:
                                raw_id = getattr(entry, "_target_id", None)
                                extra_id = getattr(getattr(entry, "extra", None), "id", None) or getattr(getattr(getattr(entry, "extra", None), "channel", None), "id", None)
                                if raw_id == target_id or extra_id == target_id:
                                    return entry
                                try:
                                    t_id = getattr(entry.target, "id", None)
                                    if t_id == target_id:
                                        return entry
                                except Exception:
                                    pass
                            else:
                                return entry
                    except Exception as e:
                        logger.debug(f"Action search error for {act}: {e}")

                # 2. Fallback search across all recent audit logs for target_id
                if target_id is not None:
                    async for entry in guild.audit_logs(limit=25):
                        age = (now - entry.created_at).total_seconds()
                        if age > max_age_seconds:
                            continue
                        raw_id = getattr(entry, "_target_id", None)
                        extra_id = getattr(getattr(entry, "extra", None), "id", None) or getattr(getattr(getattr(entry, "extra", None), "channel", None), "id", None)
                        if raw_id == target_id or extra_id == target_id:
                            return entry
                        try:
                            t_id = getattr(entry.target, "id", None)
                            if t_id == target_id:
                                return entry
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Audit log fetch attempt {attempt} failed: {e}")

        return None

    # =========================================================================
    # 1. MEMBER UPDATES (Roles, Timeouts, Nicknames)
    # =========================================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        now = discord.utils.utcnow()

        # A. Role Changes
        if before.roles != after.roles:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]

            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_role_update, target_id=after.id)
            staff = entry.user if entry else None

            embed = discord.Embed(
                title="🛡️ Member Roles Updated",
                color=discord.Color.blue(),
                timestamp=now
            )
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="👤 Affected Member", value=f"{after.mention} (`{after.name}`)", inline=True)
            embed.add_field(
                name="🛠️ Responsible Staff",
                value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Self / System*",
                inline=True
            )

            if added_roles:
                embed.add_field(name="➕ Roles Added", value=", ".join(r.mention for r in added_roles), inline=False)
            if removed_roles:
                embed.add_field(name="➖ Roles Removed", value=", ".join(r.name for r in removed_roles), inline=False)

            if entry and entry.reason:
                embed.add_field(name="📝 Reason", value=entry.reason, inline=False)

            embed.set_footer(text=f"Target ID: {after.id}")
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error logging role update: {e}")

        # B. Timeout (Timing out members)
        if before.timed_out_until != after.timed_out_until:
            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_update, target_id=after.id)
            staff = entry.user if entry else None

            if after.timed_out_until and after.timed_out_until > now:
                # Timeout Applied
                duration_str = discord.utils.format_dt(after.timed_out_until, style="R")
                exact_str = discord.utils.format_dt(after.timed_out_until, style="F")

                embed = discord.Embed(
                    title="⏳ Member Timed Out",
                    description=f"{after.mention} has been placed in timeout until {duration_str} ({exact_str}).",
                    color=discord.Color.orange(),
                    timestamp=now
                )
                embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
                embed.add_field(name="👤 Affected Member", value=f"{after.mention} (`{after.name}`)", inline=True)
                embed.add_field(
                    name="👮 Moderating Staff",
                    value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / AutoMod*",
                    inline=True
                )
                if entry and entry.reason:
                    embed.add_field(name="📝 Reason", value=entry.reason, inline=False)

                embed.set_footer(text=f"Target ID: {after.id}")
                try:
                    await log_ch.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error logging timeout apply: {e}")

            elif before.timed_out_until and not after.timed_out_until:
                # Timeout Removed
                embed = discord.Embed(
                    title="⏱️ Member Timeout Removed",
                    description=f"Timeout for {after.mention} was removed early.",
                    color=discord.Color.green(),
                    timestamp=now
                )
                embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
                embed.add_field(name="👤 Affected Member", value=f"{after.mention} (`{after.name}`)", inline=True)
                embed.add_field(
                    name="👮 Moderating Staff",
                    value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Moderator*",
                    inline=True
                )
                embed.set_footer(text=f"Target ID: {after.id}")
                try:
                    await log_ch.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error logging timeout remove: {e}")

        # C. Nickname Changes
        if before.nick != after.nick:
            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_update, target_id=after.id)
            staff = entry.user if entry else after

            embed = discord.Embed(
                title="✏️ Member Nickname Changed",
                color=discord.Color.light_grey(),
                timestamp=now
            )
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="👤 Affected Member", value=f"{after.mention} (`{after.name}`)", inline=True)
            embed.add_field(name="🛠️ Changed By", value=f"{staff.mention} (`{staff.name}`)", inline=True)
            embed.add_field(name="Old Nickname", value=f"`{before.nick}`" if before.nick else "*None*", inline=True)
            embed.add_field(name="New Nickname", value=f"`{after.nick}`" if after.nick else "*Reset to username*", inline=True)
            embed.set_footer(text=f"Target ID: {after.id}")
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error logging nick change: {e}")

    # =========================================================================
    # 2. BANS & UNBANS
    # =========================================================================
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.ban, target_id=user.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**{user.name}** was banned from the server.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{user.name} ({user.id})", icon_url=user.display_avatar.url)
        embed.add_field(name="👤 Affected Member", value=f"{user.mention} (`{user.name}`)", inline=True)
        embed.add_field(
            name="👮 Moderating Staff",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / AutoMod*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"User ID: {user.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging ban: {e}")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.unban, target_id=user.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="🔓 Member Unbanned",
            description=f"**{user.name}** was unbanned from the server.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"{user.name} ({user.id})", icon_url=user.display_avatar.url)
        embed.add_field(name="👤 Affected Member", value=f"{user.mention} (`{user.name}`)", inline=True)
        embed.add_field(
            name="👮 Moderating Staff",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Staff*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"User ID: {user.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging unban: {e}")

    # =========================================================================
    # 3. KICKED / REMOVED MEMBERS
    # =========================================================================
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        # Check if this remove was caused by a kick
        entry = await self.get_audit_entry(guild, discord.AuditLogAction.kick, target_id=member.id, max_age_seconds=6)
        if entry:
            staff = entry.user
            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"**{member.name}** was kicked from the server.",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            embed.add_field(name="👤 Affected Member", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(name="👮 Moderating Staff", value=f"{staff.mention} (`{staff.name}`)", inline=True)
            if entry.reason:
                embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
            embed.set_footer(text=f"User ID: {member.id}")
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error logging kick: {e}")
        else:
            # Self-leave or other departure
            embed = discord.Embed(
                title="🚪 Member Left Server",
                description=f"**{member.name}** has left or disconnected from the server.",
                color=discord.Color.dark_grey(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            embed.add_field(name="👤 Member", value=f"`{member.name}` ({member.id})", inline=True)
            roles = [r.name for r in member.roles if r.name != "@everyone"]
            if roles:
                embed.add_field(name="Roles Held", value=", ".join(roles[:10]), inline=False)
            embed.set_footer(text=f"User ID: {member.id}")
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error logging leave: {e}")

    # =========================================================================
    # 4. VOICE STATE UPDATES (Server Mute, Server Deafen, Move, Disconnect)
    # =========================================================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        now = discord.utils.utcnow()

        # A. Server Mute
        if before.mute != after.mute:
            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_update, target_id=member.id)
            staff = entry.user if entry else None

            action_str = "Server Muted 🎙️🚫" if after.mute else "Server Unmuted 🎙️✅"
            color = discord.Color.red() if after.mute else discord.Color.green()

            embed = discord.Embed(
                title=f"🔊 Member {action_str}",
                description=f"{member.mention} was {action_str.lower()} in voice.",
                color=color,
                timestamp=now
            )
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            embed.add_field(name="👤 Affected Member", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(
                name="👮 Moderating Staff",
                value=f"{staff.mention} (`{staff.name}`)" if staff else "*Self / Unknown*",
                inline=True
            )
            if after.channel:
                embed.add_field(name="Channel", value=after.channel.name, inline=True)
            embed.set_footer(text=f"Target ID: {member.id}")
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error logging server mute: {e}")

        # B. Server Deafen
        if before.deaf != after.deaf:
            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_update, target_id=member.id)
            staff = entry.user if entry else None

            action_str = "Server Deafened 🎧🚫" if after.deaf else "Server Undeafened 🎧✅"
            color = discord.Color.dark_red() if after.deaf else discord.Color.green()

            embed = discord.Embed(
                title=f"🔊 Member {action_str}",
                description=f"{member.mention} was {action_str.lower()} in voice.",
                color=color,
                timestamp=now
            )
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            embed.add_field(name="👤 Affected Member", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(
                name="👮 Moderating Staff",
                value=f"{staff.mention} (`{staff.name}`)" if staff else "*Self / Unknown*",
                inline=True
            )
            if after.channel:
                embed.add_field(name="Channel", value=after.channel.name, inline=True)
            embed.set_footer(text=f"Target ID: {member.id}")
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error logging server deafen: {e}")

        # C. Member Moved Between Voice Channels by Staff
        if before.channel and after.channel and before.channel != after.channel:
            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_move, max_age_seconds=5)
            if entry and entry.user and entry.user != member:
                staff = entry.user
                embed = discord.Embed(
                    title="🔀 Member Moved to Voice Channel",
                    description=f"{member.mention} was moved between voice channels by staff.",
                    color=discord.Color.gold(),
                    timestamp=now
                )
                embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
                embed.add_field(name="👤 Affected Member", value=f"{member.mention} (`{member.name}`)", inline=True)
                embed.add_field(name="👮 Moderating Staff", value=f"{staff.mention} (`{staff.name}`)", inline=True)
                embed.add_field(name="From Channel", value=before.channel.name, inline=True)
                embed.add_field(name="To Channel", value=after.channel.name, inline=True)
                embed.set_footer(text=f"Target ID: {member.id}")
                try:
                    await log_ch.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error logging voice move: {e}")

        # D. Member Disconnected from Voice by Staff
        if before.channel and not after.channel:
            entry = await self.get_audit_entry(guild, discord.AuditLogAction.member_disconnect, max_age_seconds=5)
            if entry and entry.user and entry.user != member:
                staff = entry.user
                embed = discord.Embed(
                    title="🔌 Member Disconnected from Voice",
                    description=f"{member.mention} was disconnected from voice channel `{before.channel.name}` by staff.",
                    color=discord.Color.dark_orange(),
                    timestamp=now
                )
                embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
                embed.add_field(name="👤 Affected Member", value=f"{member.mention} (`{member.name}`)", inline=True)
                embed.add_field(name="👮 Moderating Staff", value=f"{staff.mention} (`{staff.name}`)", inline=True)
                embed.add_field(name="Channel", value=before.channel.name, inline=True)
                embed.set_footer(text=f"Target ID: {member.id}")
                try:
                    await log_ch.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error logging voice disconnect: {e}")

    # =========================================================================
    # 5. ROLES (Created, Updated, Deleted)
    # =========================================================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = role.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.role_create, target_id=role.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="✨ Role Created",
            description=f"A new role {role.mention} (`{role.name}`) was created.",
            color=role.color if role.color.value else discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏷️ Role Name", value=role.name, inline=True)
        embed.add_field(name="🆔 Role ID", value=str(role.id), inline=True)
        embed.add_field(
            name="🛠️ Created By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Bot*",
            inline=True
        )
        embed.add_field(name="🎨 Color", value=str(role.color), inline=True)
        embed.add_field(name="📌 Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="📢 Mentionable", value="Yes" if role.mentionable else "No", inline=True)

        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Role ID: {role.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging role create: {e}")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = after.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        changes = []
        if before.name != after.name:
            changes.append(f"• **Name**: `{before.name}` ➔ `{after.name}`")
        if before.color != after.color:
            changes.append(f"• **Color**: `{before.color}` ➔ `{after.color}`")
        if before.hoist != after.hoist:
            changes.append(f"• **Hoisted**: `{before.hoist}` ➔ `{after.hoist}`")
        if before.mentionable != after.mentionable:
            changes.append(f"• **Mentionable**: `{before.mentionable}` ➔ `{after.mentionable}`")
        if before.position != after.position:
            changes.append(f"• **Hierarchy Position**: `{before.position}` ➔ `{after.position}`")
        if before.permissions != after.permissions:
            added_p = [p[0] for p in after.permissions if p[1] and not getattr(before.permissions, p[0])]
            removed_p = [p[0] for p in before.permissions if p[1] and not getattr(after.permissions, p[0])]
            if added_p:
                changes.append(f"• **Granted Perms**: `{'`, `'.join(added_p)}`")
            if removed_p:
                changes.append(f"• **Revoked Perms**: `{'`, `'.join(removed_p)}`")

        if not changes:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.role_update, target_id=after.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="⚙️ Role Modified",
            description=f"Role {after.mention} (`{after.name}`) was updated.\n\n" + "\n".join(changes),
            color=after.color if after.color.value else discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏷️ Role", value=f"{after.mention} (`{after.name}`)", inline=True)
        embed.add_field(
            name="🛠️ Modified By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Bot*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Role ID: {after.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging role update: {e}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.role_delete, target_id=role.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="🗑️ Role Deleted",
            description=f"Role **`{role.name}`** was deleted.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏷️ Role Name", value=role.name, inline=True)
        embed.add_field(name="🆔 Role ID", value=str(role.id), inline=True)
        embed.add_field(
            name="🛠️ Deleted By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Staff*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Deleted Role ID: {role.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging role delete: {e}")

    # =========================================================================
    # 6. CHANNELS (Created, Updated, Deleted)
    # =========================================================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.channel_create, target_id=channel.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="📁 Channel Created",
            description=f"Channel {channel.mention} (`{channel.name}`) was created.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏷️ Channel Name", value=channel.name, inline=True)
        embed.add_field(name="📂 Type", value=str(channel.type).capitalize(), inline=True)
        if getattr(channel, "category", None):
            embed.add_field(name="🗂️ Category", value=channel.category.name, inline=True)
        embed.add_field(
            name="🛠️ Created By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Bot*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Channel ID: {channel.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging channel create: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        guild = after.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        changes = []
        if before.name != after.name:
            changes.append(f"• **Name**: `#{before.name}` ➔ `#{after.name}`")
        if getattr(before, "topic", None) != getattr(after, "topic", None):
            changes.append(f"• **Topic**: `{getattr(before, 'topic', '')}` ➔ `{getattr(after, 'topic', '')}`")
        if getattr(before, "category", None) != getattr(after, "category", None):
            b_cat = before.category.name if before.category else "*None*"
            a_cat = after.category.name if after.category else "*None*"
            changes.append(f"• **Category**: `{b_cat}` ➔ `{a_cat}`")
        if getattr(before, "slowmode_delay", None) != getattr(after, "slowmode_delay", None):
            changes.append(f"• **Slowmode**: `{before.slowmode_delay}s` ➔ `{after.slowmode_delay}s`")
        if getattr(before, "overwrites", None) != getattr(after, "overwrites", None):
            changes.append("• **Permission Overwrites**: Security permissions updated")

        if not changes:
            return

        channel_actions = [
            discord.AuditLogAction.channel_update,
            discord.AuditLogAction.overwrite_create,
            discord.AuditLogAction.overwrite_update,
            discord.AuditLogAction.overwrite_delete
        ]
        entry = await self.get_audit_entry(guild, channel_actions, target_id=after.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="⚙️ Channel Updated",
            description=f"Channel {after.mention} (`#{after.name}`) was modified.\n\n" + "\n".join(changes),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏷️ Channel", value=f"{after.mention} (`#{after.name}`)", inline=True)
        embed.add_field(
            name="🛠️ Modified By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Staff*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Channel ID: {after.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging channel update: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.channel_delete, target_id=channel.id)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            description=f"Channel **`#{channel.name}`** was deleted.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏷️ Channel Name", value=channel.name, inline=True)
        embed.add_field(name="📂 Type", value=str(channel.type).capitalize(), inline=True)
        embed.add_field(
            name="🛠️ Deleted By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Staff*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Channel ID: {channel.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging channel delete: {e}")

    # =========================================================================
    # 7. SERVER CONFIGURATION (Guild Updates)
    # =========================================================================
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        log_ch = self.get_log_channel(after)
        if not log_ch:
            return

        changes = []
        if before.name != after.name:
            changes.append(f"• **Server Name**: `{before.name}` ➔ `{after.name}`")
        if before.icon != after.icon:
            changes.append("• **Server Icon**: Changed")
        if before.banner != after.banner:
            changes.append("• **Server Banner**: Changed")
        if before.afk_channel != after.afk_channel:
            b_afk = before.afk_channel.name if before.afk_channel else "*None*"
            a_afk = after.afk_channel.name if after.afk_channel else "*None*"
            changes.append(f"• **AFK Channel**: `{b_afk}` ➔ `{a_afk}`")
        if before.afk_timeout != after.afk_timeout:
            changes.append(f"• **AFK Timeout**: `{before.afk_timeout}s` ➔ `{after.afk_timeout}s`")
        if before.verification_level != after.verification_level:
            changes.append(f"• **Verification Level**: `{before.verification_level}` ➔ `{after.verification_level}`")
        if before.default_notifications != after.default_notifications:
            changes.append(f"• **Default Notifications**: `{before.default_notifications}` ➔ `{after.default_notifications}`")
        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append(f"• **Content Filter**: `{before.explicit_content_filter}` ➔ `{after.explicit_content_filter}`")
        if before.system_channel != after.system_channel:
            b_sys = before.system_channel.name if before.system_channel else "*None*"
            a_sys = after.system_channel.name if after.system_channel else "*None*"
            changes.append(f"• **System Channel**: `{b_sys}` ➔ `{a_sys}`")
        if before.rules_channel != after.rules_channel:
            b_rules = before.rules_channel.name if before.rules_channel else "*None*"
            a_rules = after.rules_channel.name if after.rules_channel else "*None*"
            changes.append(f"• **Rules Channel**: `{b_rules}` ➔ `{a_rules}`")
        if before.vanity_url_code != after.vanity_url_code:
            changes.append(f"• **Vanity URL Code**: `{before.vanity_url_code}` ➔ `{after.vanity_url_code}`")

        if not changes:
            return

        entry = await self.get_audit_entry(after, discord.AuditLogAction.guild_update)
        staff = entry.user if entry else None

        embed = discord.Embed(
            title="🏛️ Discord Server Config Modified",
            description="Core server configuration was updated.\n\n" + "\n".join(changes),
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="🛠️ Modified By",
            value=f"{staff.mention} (`{staff.name}`)" if staff else "*Unknown / Staff*",
            inline=True
        )
        if entry and entry.reason:
            embed.add_field(name="📝 Reason", value=entry.reason, inline=False)
        embed.set_footer(text=f"Server ID: {after.id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging guild update: {e}")


    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """Log message edits across the entire server to discord-logs, including uncached messages."""
        guild_id = payload.guild_id
        if not guild_id:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        channel = guild.get_channel(payload.channel_id) or self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        # Check cached message if present
        before = payload.cached_message
        before_content = before.content if before and before.content else None

        # New content from payload data
        after_content = payload.data.get("content")
        author = before.author if before else None
        jump_url = before.jump_url if before else f"https://discord.com/channels/{guild_id}/{payload.channel_id}/{payload.message_id}"

        # If uncached or details missing, attempt to fetch the message
        if not author or after_content is None:
            try:
                fetched_msg = await channel.fetch_message(payload.message_id)
                author = fetched_msg.author
                jump_url = fetched_msg.jump_url
                if after_content is None:
                    after_content = fetched_msg.content
            except Exception:
                pass

        if author and author.bot:
            return
        if not author and "author" in payload.data and payload.data["author"].get("bot"):
            return

        # If text content didn't change (e.g. link preview/embed loaded), ignore
        if before_content is not None and after_content is not None and before_content == after_content:
            return

        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"Message edited in {channel.mention} by {author.mention if author else 'User'}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        if author:
            embed.set_author(
                name=f"{author} ({author.id})",
                icon_url=author.display_avatar.url if author.display_avatar else None
            )
        embed.add_field(name="📍 Channel", value=channel.mention, inline=True)
        embed.add_field(name="🔗 Jump Link", value=f"[Go to Message]({jump_url})", inline=True)

        b_text = before_content if before_content is not None else "*[Original message was sent prior to bot startup / uncached]*"
        a_text = after_content if after_content is not None else "*[Empty or Embed/Attachment]*"

        if len(b_text) > 1000:
            b_text = b_text[:997] + "..."
        if len(a_text) > 1000:
            a_text = a_text[:997] + "..."

        embed.add_field(name="📄 Original Content", value=f"```\n{b_text}\n```", inline=False)
        embed.add_field(name="📝 Edited Content", value=f"```\n{a_text}\n```", inline=False)
        embed.set_footer(text=f"User ID: {author.id if author else 'N/A'} • Message ID: {payload.message_id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging raw message edit: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Cache incoming messages across the server for rich delete & edit audit logging."""
        if not message.guild:
            return
        self._msg_cache[message.id] = {
            'author': message.author,
            'content': message.content,
            'attachments': [a.filename for a in message.attachments],
            'channel_id': message.channel.id,
            'created_at': message.created_at,
            'is_bot': message.author.bot
        }
        if len(self._msg_cache) > 15000:
            self._msg_cache.popitem(last=False)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """Log all message deletions (cached and uncached) across the entire server to discord-logs."""
        guild_id = payload.guild_id
        if not guild_id:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        channel = guild.get_channel(payload.channel_id) or self.bot.get_channel(payload.channel_id)
        ch_mention = channel.mention if channel else f"<#{payload.channel_id}>"

        # Check in-memory cache and discord.py cache
        cached = payload.cached_message
        local_cached = self._msg_cache.pop(payload.message_id, None)

        author = None
        content = None
        attachments = []

        if cached:
            author = cached.author
            content = cached.content
            attachments = [a.filename for a in cached.attachments]
        elif local_cached:
            author = local_cached.get('author')
            content = local_cached.get('content')
            attachments = local_cached.get('attachments', [])

        # Ignore automated messages sent by bots (e.g. status embed updates, bot pings)
        if author and getattr(author, 'bot', False):
            return
        if local_cached and local_cached.get('is_bot'):
            return

        # Check Discord audit log to see if a staff member deleted it
        deleter = None
        target_from_audit = None
        now = discord.utils.utcnow()
        try:
            await asyncio.sleep(0.4)
            async for entry in guild.audit_logs(limit=6, action=discord.AuditLogAction.message_delete):
                age = (now - entry.created_at).total_seconds()
                if age > 10:
                    continue
                extra_ch = getattr(getattr(entry, "extra", None), "channel", None)
                extra_ch_id = getattr(extra_ch, "id", None) or getattr(entry, "extra", None)
                if extra_ch_id == payload.channel_id:
                    deleter = entry.user
                    target_from_audit = entry.target
                    break
        except Exception as e:
            logger.debug(f"Audit log search on message_delete error: {e}")

        if not author and target_from_audit:
            author = target_from_audit

        if deleter and author and deleter.id != author.id:
            deleted_by_str = f"{deleter.mention} (`{deleter}`)"
            desc = f"Message deleted in {ch_mention} by staff {deleter.mention}"
        elif deleter and not author:
            deleted_by_str = f"{deleter.mention} (`{deleter}`)"
            desc = f"Message deleted in {ch_mention} by staff {deleter.mention}"
        elif author:
            deleted_by_str = f"{author.mention} (*Author Self-Delete*)"
            desc = f"Message deleted in {ch_mention} by {author.mention}"
        else:
            deleted_by_str = "*Author (Self-Delete or Uncached)*"
            desc = f"Message deleted in {ch_mention}"

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=desc,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        if author:
            embed.set_author(
                name=f"{author} ({author.id})",
                icon_url=author.display_avatar.url if getattr(author, 'display_avatar', None) else None
            )
        embed.add_field(name="📍 Channel", value=ch_mention, inline=True)
        embed.add_field(name="🗑️ Deleted By", value=deleted_by_str, inline=True)

        if content:
            m_text = content
            if len(m_text) > 1000:
                m_text = m_text[:997] + "..."
            embed.add_field(name="📄 Content", value=f"```\n{m_text}\n```", inline=False)
        else:
            embed.add_field(name="📄 Content", value="*[Message content not cached / sent prior to bot startup]*", inline=False)

        if attachments:
            att_list = [f"• `{a}`" for a in attachments]
            embed.add_field(name="📎 Attachments", value="\n".join(att_list[:5]), inline=False)

        embed.set_footer(text=f"Author ID: {author.id if author else 'N/A'} • Message ID: {payload.message_id}")

        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging raw message delete: {e}")

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        """Log bulk message purge events across the server to discord-logs."""
        guild_id = payload.guild_id
        if not guild_id:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        log_ch = self.get_log_channel(guild)
        if not log_ch:
            return

        channel = guild.get_channel(payload.channel_id) or self.bot.get_channel(payload.channel_id)
        ch_mention = channel.mention if channel else f"<#{payload.channel_id}>"

        count = len(payload.message_ids)

        # Remove from local cache
        for mid in payload.message_ids:
            self._msg_cache.pop(mid, None)

        # Check audit log if a staff member bulk-deleted
        deleter = None
        now = discord.utils.utcnow()
        try:
            await asyncio.sleep(0.4)
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.message_bulk_delete):
                age = (now - entry.created_at).total_seconds()
                if age < 12:
                    extra_ch = getattr(getattr(entry, "extra", None), "channel", None)
                    extra_ch_id = getattr(extra_ch, "id", None) or getattr(entry, "extra", None)
                    if extra_ch_id == payload.channel_id:
                        deleter = entry.user
                        break
        except Exception as e:
            logger.debug(f"Audit log check error on bulk delete: {e}")

        embed = discord.Embed(
            title="🗑️ Bulk Messages Purged",
            description=f"**{count}** messages purged in {ch_mention}{f' by {deleter.mention}' if deleter else ''}",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="📍 Channel", value=ch_mention, inline=True)
        embed.add_field(name="🔢 Message Count", value=f"`{count} messages`", inline=True)
        if deleter:
            embed.add_field(name="🛡️ Purged By", value=f"{deleter.mention} (`{deleter}`)", inline=True)

        embed.set_footer(text=f"Channel ID: {payload.channel_id}")
        try:
            await log_ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Error logging raw bulk message delete: {e}")

async def setup(bot):

    await bot.add_cog(DiscordAuditLogger(bot))
