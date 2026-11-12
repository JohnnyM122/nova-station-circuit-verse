import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import re
import datetime
import json
import os
from collections import defaultdict

logger = logging.getLogger("CVNovaHelper.moderation")

# Channels
DISCORD_LOGS_CH_ID = 1566986370910654517
GENERAL_INCIDENTS_CH_ID = 1567656755016503396
STAFF_ADMIN_CH_ID = 1567464238153338910
COMMUNITY_INFO_CH_ID = 1567434275928809544

WARNINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "warnings.json")
VERIFIED_MEMBER_ROLE_ID = 1570004763586859011

# Preset regex filters
INVITE_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com\/invite)\/([a-zA-Z0-9\-]+)", re.IGNORECASE)
ALLOWED_INVITES = {"m7r8ey28q6", "circuitverse"}

PHISHING_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:"
    r"[a-z0-9\-]+\.discor[cl]\.com|"
    r"[a-z0-9\-]+\.dlscord\.com|"
    r"[a-z0-9\-]+\.discord-gift\.[a-z]+|"
    r"[a-z0-9\-]+\.nitro-steam\.[a-z]+|"
    r"[a-z0-9\-]+\.free-nitro\.[a-z]+|"
    r"grabify\.link|"
    r"iplogger\.(?:org|com|ru)|"
    r"2no\.co|"
    r"yip\.su|"
    r"blasze\.tk"
    r")",
    re.IGNORECASE
)

# Severe Hate Speech / Slurs (13+ Community Standard)
SEVERE_SLURS_REGEX = re.compile(
    r"\b(?:"
    r"n+[i1!|]+g+[e3a4@]+r*s*|"
    r"f+[a4@]+g+[o0]+t*s*|"
    r"k+[i1!|]+k+[e3]+s*|"
    r"c+[o0]+[o0]+n+s*|"
    r"t+r+[a4@]+n+n+[y1ie]+s*|"
    r"r+[e3]+t+[a4@]+r+d+s*"
    r")\b",
    re.IGNORECASE
)

# NSFW / Explicit Terms (Non-age-gated community channels)
NSFW_REGEX = re.compile(
    r"\b(?:"
    r"cp\s+links?|child\s*porn|"
    r"hentai|blowjob|cock|cunt|pussy|gangbang|"
    r"cumshot|deepthroat|dildo|orgasm"
    r")\b",
    re.IGNORECASE
)

# -------------------------------------------------------------
# Staff Incident Approval View (Interactive Buttons)
# -------------------------------------------------------------
class IncidentApprovalView(discord.ui.View):
    def __init__(self, bot, target_user_id: int, target_user_name: str, guild_id: int, reason: str, message_snippet: str):
        super().__init__(timeout=86400) # 24 hours
        self.bot = bot
        self.target_user_id = target_user_id
        self.target_user_name = target_user_name
        self.guild_id = guild_id
        self.reason = reason
        self.message_snippet = message_snippet

    def check_staff(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator or member.guild_permissions.ban_members:
            return True
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            tier = staff_cog.get_staff_tier(member)
            if tier in ("FOUNDER", "ADMIN", "MODERATOR"):
                return True
        return False

    async def log_resolution(self, guild: discord.Guild, moderator: discord.Member, decision: str):
        log_ch = guild.get_channel(DISCORD_LOGS_CH_ID) or self.bot.get_channel(DISCORD_LOGS_CH_ID)
        if log_ch:
            embed = discord.Embed(
                title="🛡️ Incident Decision Finalized",
                description=f"Staff member {moderator.mention} resolved the incident for <@{self.target_user_id}> (`{self.target_user_name}`).",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Target User", value=f"<@{self.target_user_id}> (`{self.target_user_id}`)", inline=True)
            embed.add_field(name="Staff Member", value=f"{moderator.mention} (`{moderator.name}`)", inline=True)
            embed.add_field(name="Decision", value=f"**{decision}**", inline=False)
            embed.add_field(name="Original Reason", value=self.reason, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception as e:
                logger.error(f"Error sending resolution log: {e}")

    @discord.ui.button(label="Confirm Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_staff(interaction.user):
            await interaction.response.send_message("❌ Only Community Staff (Moderators / Admins) can approve incident actions.", ephemeral=True)
            return

        guild = interaction.guild
        try:
            await guild.ban(discord.Object(id=self.target_user_id), reason=f"Staff Approved Auto-Mod Escalation: {self.reason} (Approved by {interaction.user})", delete_message_days=1)
            action_text = f"✅ **Member Banned** by {interaction.user.mention}."
        except Exception as e:
            action_text = f"⚠️ Could not execute ban: `{e}`"

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_red()
        embed.add_field(name="⚖️ Resolution", value=f"**BANNED** by {interaction.user.mention}\n*Messages from the past 24h purged.*", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
        await self.log_resolution(guild, interaction.user, "PERMANENT BAN")

    @discord.ui.button(label="Kick Member", style=discord.ButtonStyle.secondary, emoji="👢")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_staff(interaction.user):
            await interaction.response.send_message("❌ Only Community Staff can approve incident actions.", ephemeral=True)
            return

        guild = interaction.guild
        try:
            member = guild.get_member(self.target_user_id)
            if member:
                await member.kick(reason=f"Staff Approved Auto-Mod Kick: {self.reason} (Approved by {interaction.user})")
                action_text = f"👢 **Member Kicked** by {interaction.user.mention}."
            else:
                action_text = "ℹ️ User is no longer in the server."
        except Exception as e:
            action_text = f"⚠️ Could not execute kick: `{e}`"

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.add_field(name="⚖️ Resolution", value=f"**KICKED** by {interaction.user.mention}", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
        await self.log_resolution(guild, interaction.user, "KICK")

    @discord.ui.button(label="Keep Timeout Only", style=discord.ButtonStyle.primary, emoji="⏳")
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_staff(interaction.user):
            await interaction.response.send_message("❌ Only Community Staff can approve incident actions.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.blue()
        embed.add_field(name="⚖️ Resolution", value=f"**TIMEOUT MAINTAINED** by {interaction.user.mention}\n*User remains timed out without kick or ban.*", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
        await self.log_resolution(interaction.guild, interaction.user, "TIMEOUT MAINTAINED (No Ban)")

    @discord.ui.button(label="Dismiss / False Positive", style=discord.ButtonStyle.success, emoji="❌")
    async def dismiss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_staff(interaction.user):
            await interaction.response.send_message("❌ Only Community Staff can approve incident actions.", ephemeral=True)
            return

        # Attempt to lift timeout
        try:
            member = interaction.guild.get_member(self.target_user_id)
            if member:
                await member.timeout(None, reason=f"False positive dismissed by {interaction.user}")
        except Exception:
            pass

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.light_grey()
        embed.add_field(name="⚖️ Resolution", value=f"**DISMISSED** by {interaction.user.mention}\n*Timeout lifted and marked as false positive.*", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
        await self.log_resolution(interaction.guild, interaction.user, "DISMISSED (Timeout Lifted)")


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        # user_id -> list of timestamps
        self.user_message_times = defaultdict(list)
        # user_id -> list of recent message contents for duplicate spam detection
        self.user_recent_messages = defaultdict(list)
        self.warnings = self.load_warnings()

    def load_warnings(self) -> dict:
        if os.path.exists(WARNINGS_FILE):
            try:
                with open(WARNINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading warnings.json: {e}")
        return {}

    def save_warnings(self):
        try:
            with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.warnings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving warnings.json: {e}")

    def add_warning(self, user_id: int, reason: str, severity: str, channel_id: int) -> dict:
        uid_str = str(user_id)
        u_data = self.warnings.setdefault(uid_str, {
            "warnings": [],
            "total_warnings": 0,
            "total_timeouts": 0
        })

        warn_entry = {
            "id": f"W-{len(u_data['warnings']) + 1}",
            "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
            "reason": reason,
            "severity": severity,
            "channel_id": channel_id
        }
        u_data["warnings"].append(warn_entry)
        u_data["total_warnings"] = len(u_data["warnings"])
        self.save_warnings()
        return u_data

class PurgeAllConfirmView(discord.ui.View):
    def __init__(self, bot, target_channel: discord.TextChannel, author_id: int):
        super().__init__(timeout=45)
        self.bot = bot
        self.target_channel = target_channel
        self.author_id = author_id

    @discord.ui.button(label="Confirm Wipe Channel", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="confirm_purge_all_btn")
    async def confirm_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the staff member who initiated the purge can confirm it.", ephemeral=True)
            return

        channel = self.target_channel
        guild = interaction.guild

        await interaction.response.send_message("🧹 **Wiping channel and resetting all messages...**", ephemeral=True)

        try:
            # Clone channel to completely wipe all messages while preserving position, overwrites, category, and topic
            new_channel = await channel.clone(
                name=channel.name,
                reason=f"Channel Wipe/Purge All executed by {interaction.user.name} ({interaction.user.id})"
            )
            await new_channel.edit(position=channel.position)
            old_name = channel.name
            old_id = channel.id
            await channel.delete(reason=f"Purged all messages by {interaction.user.name}")

            # Send reset announcement in new channel
            wiped_embed = discord.Embed(
                title="🧹 Channel Wiped",
                description=f"All messages in this channel were purged and reset by {interaction.user.mention}.",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            wiped_embed.set_footer(text="Circuit Verse Safety & Moderation")
            await new_channel.send(embed=wiped_embed, delete_after=15)

            # Audit log to discord-logs
            log_embed = discord.Embed(
                title="🧹 Channel Completely Wiped (Purge All)",
                description=f"Channel **#{old_name}** was completely purged and reset.",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_author(name=f"{interaction.user} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            log_embed.add_field(name="Staff Member", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
            log_embed.add_field(name="New Channel", value=new_channel.mention, inline=True)
            log_embed.add_field(name="Original Channel ID", value=str(old_id), inline=True)
            log_embed.set_footer(text=f"Purge All Execution • Guild ID: {guild.id}")

            log_ch = guild.get_channel(1566986370910654517)
            if log_ch:
                await log_ch.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Error purging channel: {e}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️", custom_id="cancel_purge_all_btn")
    async def cancel_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You cannot interact with this confirmation.", ephemeral=True)
            return
        await interaction.response.edit_message(content="❌ **Channel wipe cancelled.**", embed=None, view=None)

    def check_mod_perm(self, member: discord.Member, cmd_name: str, channel: discord.abc.GuildChannel = None) -> tuple[bool, str]:
        """
        Validates command access with global and category-based permissions:
        1. Administrators / Guild Owner -> Global Access
        2. Global Staff (Founder, Community Staff, Directors, Admins) -> Global Access in any channel
        3. Server / Category Staff (MC, NS13, PZ, Unturned) -> Scoped strictly to their server's categories/channels
        """
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return True, "Administrator (Global)"

        member_role_ids = {r.id for r in member.roles}
        member_role_names = {r.name.lower() for r in member.roles}

        # Read permissions configuration
        cfg = getattr(self.bot, "config", {})
        staff_perms = cfg.get("staff_permissions", {})

        # 1. Check Global Staff Roles
        global_role_ids = set(staff_perms.get("global_staff_roles", []))
        default_global_role_ids = {
            1564610713216098394, # Founder
            1567482219495301191, # Community Director
            1567663377054957830, # Community Staff
            1567653691467632700, # Community Trial Staff
            1567449658639384678, # Server Administrator
            1567449610962735224, # Server Moderator
            1567474473404338216, # Comm Management
            1567475021906186270, # Dept.Director GC
        }
        effective_global = global_role_ids or default_global_role_ids
        if any(rid in effective_global for rid in member_role_ids) or any(
            any(k in rn for k in ["community staff", "founder", "community director", "executive director"]) for rn in member_role_names
        ):
            return True, "Global Staff"

        # Discord-wide bans are restricted to Global Staff & Administrators
        if cmd_name in ("discordban", "ban_discord"):
            return False, "Discord server bans are restricted to Global Community Staff & Administrators."

        # 2. Check Category-Scoped Staff (MC, NS13, PZ, Unturned)
        ch_category_id = getattr(channel, "category_id", None)
        ch_name = getattr(channel, "name", "").lower()
        cat_name = (channel.category.name.lower() if getattr(channel, "category", None) else "")

        category_scopes = staff_perms.get("category_scopes", {})
        default_scopes = {
            "mc": {
                "name": "Minecraft",
                "category_ids": [1567426382664040459, 1567464236177817620, 1568819751315185785],
                "role_ids": [1567474481180446761, 1567449697101287467, 1567475022405173320, 1567449681070399518, 1567449687080837192]
            },
            "ns13": {
                "name": "Nova Station 13",
                "category_ids": [1566607420275564638, 1566608607829692696, 1568819763059359754],
                "role_ids": [1567449653233057912, 1567475022724079637, 1567642505049018408]
            },
            "pz": {
                "name": "Project Zomboid",
                "category_ids": [1567692616202719405, 1567692617112756407, 1568819774803283988],
                "role_ids": [1567692601291702432, 1567475022724079637, 1567692551853449287]
            },
            "unturned": {
                "name": "Unturned",
                "category_ids": [1568805615164334171, 1568805616443596880, 1568819786228432978],
                "role_ids": [1568805610219372690, 1568805609158082641, 1568805607836745910, 1568805604447752263]
            }
        }

        member_depts = []
        for d_key, d_info in (category_scopes or default_scopes).items():
            allowed_rids = set(d_info.get("allowed_roles") or d_info.get("role_ids") or [])
            if any(rid in allowed_rids for rid in member_role_ids) or any(
                any(k in rn for k in [f"{d_key} ", f"{d_key}-", f"{d_info.get('name','').lower()} "]) for rn in member_role_names
            ):
                member_depts.append((d_key, d_info.get("name", d_key.upper())))

        if not member_depts:
            return False, "Staff permission required to execute this command."

        # If channel is provided, verify it falls within the staff member's category scope
        if channel:
            for d_key, d_name in member_depts:
                d_info = (category_scopes or default_scopes).get(d_key, {})
                cat_ids = d_info.get("category_ids", [])
                in_category = ch_category_id in cat_ids or any(k in ch_name or k in cat_name for k in [f"{d_key}-", f"{d_key}_", d_name.lower()])
                if in_category:
                    return True, f"{d_name} Staff (Scoped)"

            dept_names = " / ".join(name for _, name in member_depts)
            return False, f"Scoped Permission: As {dept_names} Staff, your commands are restricted to {dept_names} channels."

        return True, f"{member_depts[0][1]} Staff"

    async def log_action(self, guild: discord.Guild, embed: discord.Embed):
        """Sends moderation log to discord-logs channel."""
        ch_id = self.config.get("channels", {}).get("discord_logs", DISCORD_LOGS_CH_ID)
        channel = guild.get_channel(ch_id) or self.bot.get_channel(ch_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Could not send log to discord-logs: {e}")

    async def escalate_to_staff(self, guild: discord.Guild, member: discord.Member, reason: str, message_snippet: str, severity: str):
        """Dispatches an interactive approval card to general-incidents-chat and administration channels."""
        view = IncidentApprovalView(self.bot, member.id, str(member), guild.id, reason, message_snippet)

        embed = discord.Embed(
            title="🚨 Staff Approval Required: High-Severity Incident",
            description=(
                f"**Circuit Verse Helper Security System** detected a high-severity violation.\n"
                f"Offender: {member.mention} (`{member.name}` • `ID: {member.id}`)\n"
                f"Account Created: <t:{int(member.created_at.timestamp())}:R>\n"
                f"Violation Type: **{reason}**\n"
                f"Severity Level: **{severity.upper()}**\n\n"
                f"**Current Action:** User has been placed in protective timeout (7 Days). Staff authorization is requested for a permanent ban or kick."
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        safe_snippet = message_snippet[:800] if message_snippet else "*[No content]*"
        embed.add_field(name="📄 Flagged Message Content", value=f"||```\n{safe_snippet}\n```||", inline=False)
        embed.set_footer(text="Community Staff: Click an action below to resolve this incident.")

        # Channels to alert
        incident_ch_ids = [
            self.config.get("channels", {}).get("general_incidents", GENERAL_INCIDENTS_CH_ID),
            self.config.get("channels", {}).get("staff_administration", STAFF_ADMIN_CH_ID)
        ]

        sent_count = 0
        for cid in incident_ch_ids:
            ch = guild.get_channel(cid) or self.bot.get_channel(cid)
            if ch:
                try:
                    await ch.send(content="@here 🚨 **Security Escalation Alert**", embed=embed, view=view)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to post incident alert to channel {cid}: {e}")

    # -------------------------------------------------------------
    # Auto-Moderation Listener
    # -------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Bypass for staff & administrators
        is_staff = False
        if isinstance(message.author, discord.Member):
            if message.author.guild_permissions.administrator:
                is_staff = True
            else:
                staff_cog = self.bot.get_cog("StaffManagementCog")
                if staff_cog:
                    tier = staff_cog.get_staff_tier(message.author)
                    if tier in ("FOUNDER", "ADMIN", "MODERATOR"):
                        is_staff = True

        if is_staff:
            return

        content = message.content or ""
        author = message.author
        guild = message.guild
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()

        # ---------------------------------------------------------
        # Rule 1: Malicious Phishing, Scam & Token Grabber Links
        # ---------------------------------------------------------
        if PHISHING_REGEX.search(content):
            try:
                await message.delete()
            except Exception:
                pass

            # Immediate 7-day timeout
            try:
                await author.timeout(datetime.timedelta(days=7), reason="Security System: Malicious Phishing/Token Grabber Link")
            except Exception as e:
                logger.error(f"Could not timeout for phishing: {e}")

            w_data = self.add_warning(author.id, "Malicious Phishing / Scam Link", "critical", message.channel.id)

            # Log to discord-logs
            embed = discord.Embed(title="🛡️ Auto-Security: Malicious Link Intercepted", color=discord.Color.dark_red())
            embed.add_field(name="User", value=f"{author.mention} (`{author.name}` • `{author.id}`)", inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Action Taken", value="❌ Message Deleted\n⏳ 7-Day Safety Timeout Applied\n🚨 Escalated for Staff Ban Approval", inline=False)
            embed.add_field(name="Flagged Content", value=f"||`{content[:500]}`||", inline=False)
            embed.set_footer(text=f"Total Warnings: {w_data['total_warnings']}")
            await self.log_action(guild, embed)

            # Prompt Staff Approval in #general-incidents-chat and #administration
            await self.escalate_to_staff(guild, author, "Malicious Phishing / Scam / Token Grabber Link", content, "critical")
            return

        # ---------------------------------------------------------
        # Rule 2: Severe Hate Speech & Slurs (13+ Zero Tolerance)
        # ---------------------------------------------------------
        if SEVERE_SLURS_REGEX.search(content):
            try:
                await message.delete()
            except Exception:
                pass

            w_data = self.add_warning(author.id, "Severe Hate Speech / Explicit Slur", "high", message.channel.id)
            warn_count = w_data["total_warnings"]

            # Dynamic timeout: 1st time = 1 hour, 2nd time = 12 hours, 3rd+ = 24 hours + Staff Escalation
            timeout_dur = datetime.timedelta(hours=1) if warn_count == 1 else (datetime.timedelta(hours=12) if warn_count == 2 else datetime.timedelta(hours=24))

            try:
                await author.timeout(timeout_dur, reason=f"Auto-Mod: Severe Hate Speech / Slurs (Warning #{warn_count})")
                await message.channel.send(
                    f"⛔ {author.mention} has been timed out for **{int(timeout_dur.total_seconds() / 3600)}h** for violating Circuit Verse safety rules against hate speech. (Warning #{warn_count}/3)",
                    delete_after=10
                )
            except Exception as e:
                logger.error(f"Could not timeout for hate speech: {e}")

            embed = discord.Embed(title="🛡️ Auto-Mod: Hate Speech Detected", color=discord.Color.red())
            embed.add_field(name="User", value=f"{author.mention} (`{author.name}` • `{author.id}`)", inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Action", value=f"Message deleted & {int(timeout_dur.total_seconds() / 3600)}h timeout applied (Warning #{warn_count})", inline=False)
            embed.add_field(name="Flagged Snippet", value=f"||`{content[:400]}`||", inline=False)
            await self.log_action(guild, embed)

            if warn_count >= 3:
                await self.escalate_to_staff(guild, author, f"Accumulated {warn_count} Severe Hate Speech Warnings", content, "high")
            return

        # ---------------------------------------------------------
        # Rule 3: Verified Member Gate (Images, GIFs, Files, Links)
        # ---------------------------------------------------------
        # Restrict media, attachments, external links, and GIFs to Verified Members
        is_verified = False
        if isinstance(author, discord.Member):
            for r in author.roles:
                if r.id == VERIFIED_MEMBER_ROLE_ID or r.name.lower() == "verified member":
                    is_verified = True
                    break

        if not is_verified:
            has_attachments = len(message.attachments) > 0
            has_stickers = len(message.stickers) > 0

            MEDIA_LINK_REGEX = re.compile(
                r'(https?://[^\s]+|discord\.gg/[^\s]+|tenor\.com/[^\s]+|giphy\.com/[^\s]+|\.(?:png|jpe?g|gif|webp|mp4|mov|avi|webm|zip|rar|exe|pdf)(?:\?[^\s]*)?$)',
                re.IGNORECASE
            )
            has_media_or_link = has_attachments or has_stickers or (MEDIA_LINK_REGEX.search(content) is not None)

            if has_media_or_link:
                try:
                    await message.delete()
                except Exception:
                    pass

                try:
                    await message.channel.send(
                        f"🔒 {author.mention}, sharing images, GIFs, links, or files is restricted to **Verified Members** for community safety against phishing and malware.\n"
                        f"👉 You can get verified easily by submitting a ticket in <#1567464252674150410> selecting the **Verified Application** category!",
                        delete_after=10
                    )
                except Exception:
                    pass

                embed = discord.Embed(
                    title="🛡️ Auto-Mod: Unverified Media / Link Filtered",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_author(
                    name=f"{author} ({author.id})",
                    icon_url=author.display_avatar.url if author.display_avatar else None
                )
                embed.add_field(name="User", value=f"{author.mention} (`{author.name}` • `{author.id}`)", inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)

                details = []
                if has_attachments:
                    details.append(f"📁 **Attachments ({len(message.attachments)})**: " + ", ".join(f"`{a.filename}`" for a in message.attachments[:3]))
                matched_links = MEDIA_LINK_REGEX.findall(content)
                if matched_links:
                    details.append(f"🔗 **Links/Media**: " + ", ".join(f"`{l[:50]}`" for l in matched_links[:3]))
                if has_stickers:
                    details.append(f"🖼️ **Stickers ({len(message.stickers)})**")

                embed.add_field(name="Reason", value="User lacks `Verified Member` role (Community Media Lock)", inline=False)
                embed.add_field(name="Blocked Content", value="\n".join(details) if details else f"||`{content[:300]}`||", inline=False)
                embed.set_footer(text="Community Safety & Verification System")
                await self.log_action(guild, embed)
                return

        # ---------------------------------------------------------
        # Rule 4: Mass Mention / Raid Flood
        # ---------------------------------------------------------
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions >= 5 or (message.mention_everyone and not is_staff):
            try:
                await message.delete()
            except Exception:
                pass

            w_data = self.add_warning(author.id, "Mass Mention / Ping Spam", "high", message.channel.id)
            warn_count = w_data["total_warnings"]

            try:
                await author.timeout(datetime.timedelta(hours=1), reason="Auto-Mod: Mass Mention Spam")
                await message.channel.send(f"⚠️ {author.mention} has been timed out for 1 hour for mass mention spam. (Warning #{warn_count})", delete_after=8)
            except Exception:
                pass

            embed = discord.Embed(title="🛡️ Auto-Mod: Mass Mention Spam Intercepted", color=discord.Color.orange())
            embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Mentions Count", value=str(total_mentions), inline=True)
            embed.add_field(name="Action", value=f"Message deleted & 1h timeout applied (Warning #{warn_count})", inline=False)
            await self.log_action(guild, embed)
            return

        # ---------------------------------------------------------
        # Rule 4: Rapid Message Flood & Copy-Paste Raid Detection
        # ---------------------------------------------------------
        msg_times = self.user_message_times[author.id]
        msg_times.append(now)
        self.user_message_times[author.id] = [t for t in msg_times if now - t <= 4.0]

        # Duplicate spam tracking
        user_msgs = self.user_recent_messages[author.id]
        user_msgs.append((content, now))
        self.user_recent_messages[author.id] = [(c, t) for (c, t) in user_msgs if now - t <= 10.0]

        is_rate_spam = len(self.user_message_times[author.id]) > 5
        is_dup_spam = len(content) > 10 and len([c for (c, t) in self.user_recent_messages[author.id] if c == content]) >= 3

        if is_rate_spam or is_dup_spam:
            try:
                await message.delete()
            except Exception:
                pass

            w_data = self.add_warning(author.id, "Message Flooding / Repetitive Spam", "medium", message.channel.id)
            warn_count = w_data["total_warnings"]

            # 1st time = 5m timeout, 2nd time = 15m, 3rd time (threshold hit) = 1 hour
            dur = datetime.timedelta(minutes=5) if warn_count == 1 else (datetime.timedelta(minutes=15) if warn_count == 2 else datetime.timedelta(hours=1))

            try:
                await author.timeout(dur, reason=f"Auto-Mod: Message Flooding (Warning #{warn_count})")
                await message.channel.send(
                    f"⚠️ {author.mention} has been timed out for **{int(dur.total_seconds()/60)}m** for flooding the chat. (Warning #{warn_count}/3)",
                    delete_after=8
                )
            except Exception:
                pass

            embed = discord.Embed(title="🛡️ Auto-Mod: Chat Flood Blocked", color=discord.Color.gold())
            embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Spam Type", value="Duplicate Spam" if is_dup_spam else "Rate Limit Spam (>5 msgs/4s)", inline=True)
            embed.add_field(name="Action", value=f"Message deleted & {int(dur.total_seconds()/60)}m timeout applied (Warning #{warn_count})", inline=False)
            await self.log_action(guild, embed)
            return

        # ---------------------------------------------------------
        # Rule 5: Unapproved Discord Server Invites
        # ---------------------------------------------------------
        invite_matches = INVITE_REGEX.findall(content)
        if invite_matches:
            unapproved = [inv for inv in invite_matches if inv.lower() not in ALLOWED_INVITES]
            if unapproved:
                try:
                    await message.delete()
                except Exception:
                    pass

                w_data = self.add_warning(author.id, f"Unapproved Discord Invite ({unapproved[0]})", "low", message.channel.id)
                warn_count = w_data["total_warnings"]

                # 3 warnings = 1 hour timeout
                if warn_count >= 3:
                    try:
                        await author.timeout(datetime.timedelta(hours=1), reason="Auto-Mod: Reached 3 warnings (Discord Invites)")
                        await message.channel.send(f"⚠️ {author.mention} has reached **3 warnings** and was timed out for 1 hour.", delete_after=10)
                    except Exception:
                        pass
                else:
                    await message.channel.send(
                        f"🚫 {author.mention}, unsolicited server invites are not permitted. Please review our server guidelines. (Warning **#{warn_count}/3**)",
                        delete_after=8
                    )

                embed = discord.Embed(title="🛡️ Auto-Mod: Unapproved Invite Deleted", color=discord.Color.yellow())
                embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="Invite Code", value=f"`{unapproved[0]}`", inline=True)
                embed.add_field(name="Action", value=f"Message deleted & Warning #{warn_count} issued" + (" (Timed out for 1h)" if warn_count >= 3 else ""), inline=False)
                await self.log_action(guild, embed)
                return

        # ---------------------------------------------------------
        # Rule 6: NSFW / Explicit Content Filter
        # ---------------------------------------------------------
        if NSFW_REGEX.search(content):
            try:
                await message.delete()
            except Exception:
                pass

            w_data = self.add_warning(author.id, "Explicit / Inappropriate Language in Community Channel", "medium", message.channel.id)
            warn_count = w_data["total_warnings"]

            if warn_count >= 3:
                try:
                    await author.timeout(datetime.timedelta(hours=1), reason="Auto-Mod: Reached 3 warnings (NSFW/Explicit Language)")
                    await message.channel.send(f"⚠️ {author.mention} has reached **3 warnings** and received a 1-hour timeout.", delete_after=8)
                except Exception:
                    pass
            else:
                await message.channel.send(
                    f"🔞 {author.mention}, explicit content is not allowed in community channels (13+ community standard). (Warning **#{warn_count}/3**)",
                    delete_after=8
                )

            embed = discord.Embed(title="🛡️ Auto-Mod: Explicit Language Filtered", color=discord.Color.purple())
            embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Action", value=f"Message deleted & Warning #{warn_count} issued" + (" (1h timeout applied)" if warn_count >= 3 else ""), inline=False)
            await self.log_action(guild, embed)
            return

    # -------------------------------------------------------------
    # Staff Slash Commands
    # -------------------------------------------------------------

    @app_commands.command(name="purge_all", description="Delete ALL messages in this channel (Wipe and reset channel)")
    async def cmd_purge_all(self, interaction: discord.Interaction):
        allowed, rank_name = self.check_mod_perm(interaction.user, "purge_all", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        view = PurgeAllConfirmView(self.bot, interaction.channel, interaction.user.id)
        embed = discord.Embed(
            title="⚠️ Confirm Complete Channel Wipe (Purge All)",
            description=(
                f"Are you sure you want to delete **ALL** messages in {interaction.channel.mention}?\n\n"
                f"• All messages will be permanently erased and the channel reset.\n"
                f"• Category, topic, slowmode, and permissions will be fully preserved.\n"
                f"• Authorized by: **{rank_name}** ({interaction.user.mention})\n\n"
                f"*Click below to confirm or cancel.*"
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="purge", description="Bulk delete a specified number of recent messages in this channel")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def cmd_purge(self, interaction: discord.Interaction, amount: int):
        allowed, rank_name = self.check_mod_perm(interaction.user, "purge", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ Amount must be between 1 and 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"🧹 Successfully purged **{len(deleted)}** messages.", ephemeral=True)

            log_embed = discord.Embed(
                title="🧹 Messages Bulk Purged",
                description=f"**{len(deleted)}** messages were deleted in {interaction.channel.mention} by {interaction.user.mention}.",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Staff Member", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
            log_embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
            log_embed.add_field(name="Deleted Count", value=str(len(deleted)), inline=True)
            log_embed.add_field(name="Scope", value=rank_name, inline=True)
            await self.log_action(interaction.guild, log_embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to purge messages: `{e}`", ephemeral=True)

    @app_commands.command(name="warn", description="Issue an official safety warning to a community member")
    @app_commands.describe(member="Member to warn", reason="Reason for official warning")
    async def cmd_warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        allowed, rank_name = self.check_mod_perm(interaction.user, "warn", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        w_data = self.add_warning(member.id, reason, "manual", interaction.channel_id)
        warn_count = w_data["total_warnings"]

        action_applied = f"Warning #{warn_count} recorded."
        # Auto-timeout on 3 warnings
        if warn_count == 3:
            try:
                await member.timeout(datetime.timedelta(hours=1), reason=f"Automated Timeout: Reached 3 Warnings ({reason})")
                action_applied += "\n⏳ **Threshold Reached (3 Warnings)**: Automated 1-hour timeout applied."
            except Exception as e:
                action_applied += f"\n*(Could not apply auto-timeout: {e})*"
        elif warn_count > 3:
            try:
                await member.timeout(datetime.timedelta(hours=12), reason=f"Automated Timeout: {warn_count} Warnings ({reason})")
                action_applied += f"\n⏳ **Multiple Warnings ({warn_count})**: Automated 12-hour timeout applied."
            except Exception:
                pass

        # DM the user
        try:
            dm_embed = discord.Embed(
                title="⚠️ Official Community Warning Received",
                description=f"You received an official warning in **Circuit Verse**.\n\n**Reason:** `{reason}`\n**Total Warnings:** `{warn_count}/3`\n\n*Please ensure you review and adhere to all community safety guidelines.*",
                color=discord.Color.orange()
            )
            await member.send(embed=dm_embed)
        except Exception:
            pass

        embed = discord.Embed(
            title="⚠️ Official Member Warning Issued",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target User", value=f"{member.mention} (`{member.name}` • `{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Result", value=action_applied, inline=False)
        embed.set_footer(text=f"Total Active Warnings: {warn_count}")

        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="warnings", description="View warning and moderation history for a member")
    @app_commands.describe(member="Member to view history for")
    async def cmd_warnings(self, interaction: discord.Interaction, member: discord.Member):
        allowed, rank_name = self.check_mod_perm(interaction.user, "warnings", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        uid_str = str(member.id)
        u_data = self.warnings.get(uid_str)
        if not u_data or not u_data.get("warnings"):
            await interaction.response.send_message(f"✅ **{member.display_name}** has a clean record with **0 warnings**.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Safety & Warning History — {member.display_name}",
            description=f"Total Warnings: **{u_data.get('total_warnings', len(u_data['warnings']))}**",
            color=discord.Color.yellow(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        for w in u_data["warnings"][-8:]:
            ts = w.get("timestamp", 0)
            date_str = f"<t:{ts}:d> (<t:{ts}:R>)" if ts else "Unknown Date"
            embed.add_field(
                name=f"⚠️ {w.get('id', 'Warning')} — Severity: {w.get('severity', 'normal').upper()}",
                value=f"• **Reason**: `{w.get('reason', 'None')}`\n• **Date**: {date_str}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member (e.g. after appeal)")
    @app_commands.describe(member="Member whose warnings should be cleared")
    async def cmd_clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        allowed, rank_name = self.check_mod_perm(interaction.user, "clearwarnings", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        uid_str = str(member.id)
        if uid_str in self.warnings:
            del self.warnings[uid_str]
            self.save_warnings()

        embed = discord.Embed(
            title="🧹 Warnings Cleared",
            description=f"All warnings for {member.mention} have been reset by {interaction.user.mention}.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="timeout", description="Place a member in timeout")
    @app_commands.describe(
        member="Member to timeout",
        duration="Duration of timeout",
        reason="Reason for timeout"
    )
    @app_commands.choices(duration=[
        app_commands.Choice(name="60 Seconds", value="60"),
        app_commands.Choice(name="5 Minutes", value="300"),
        app_commands.Choice(name="15 Minutes", value="900"),
        app_commands.Choice(name="1 Hour", value="3600"),
        app_commands.Choice(name="6 Hours", value="21600"),
        app_commands.Choice(name="12 Hours", value="43200"),
        app_commands.Choice(name="24 Hours", value="86400"),
        app_commands.Choice(name="7 Days", value="604800"),
    ])
    async def cmd_timeout(self, interaction: discord.Interaction, member: discord.Member, duration: app_commands.Choice[str], reason: str = "Moderator applied timeout"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "timeout", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        seconds = int(duration.value)
        delta = datetime.timedelta(seconds=seconds)

        try:
            await member.timeout(delta, reason=f"{reason} (Applied by {interaction.user})")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to timeout member: `{e}`", ephemeral=True)
            return

        embed = discord.Embed(
            title="⏳ Member Placed in Timeout",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target User", value=f"{member.mention} (`{member.name}` • `{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="Duration", value=duration.name, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.describe(member="Member to untimeout", reason="Reason for lifting timeout")
    async def cmd_untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Moderator lifted timeout"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "untimeout", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        try:
            await member.timeout(None, reason=f"{reason} (Lifted by {interaction.user})")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to lift timeout: `{e}`", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔓 Member Timeout Removed",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target User", value=f"{member.mention} (`{member.name}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick", reason="Reason for kick")
    async def cmd_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "kick", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        try:
            await member.kick(reason=f"{reason} (Kicked by {interaction.user})")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to kick member: `{e}`", ephemeral=True)
            return

        embed = discord.Embed(
            title="👢 Member Kicked",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target User", value=f"{member.name} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="discordban", description="Ban a member from the Discord server")
    @app_commands.describe(
        member="Member to ban from Discord",
        reason="Reason for ban",
        delete_days="Number of days of message history to delete (0-7)"
    )
    async def cmd_ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: int = 1):
        allowed, rank_name = self.check_mod_perm(interaction.user, "discordban", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        try:
            await interaction.guild.ban(member, reason=f"{reason} (Banned by {interaction.user})", delete_message_days=min(max(delete_days, 0), 7))
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to ban member: `{e}`", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔨 Member Banned",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target User", value=f"{member.name} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="modstatus", description="Display current safety system & auto-moderation status")
    async def cmd_modstatus(self, interaction: discord.Interaction):
        allowed, rank_name = self.check_mod_perm(interaction.user, "modstatus", interaction.channel)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        total_users_warned = len(self.warnings)
        total_warns = sum(u.get("total_warnings", len(u.get("warnings", []))) for u in self.warnings.values())

        embed = discord.Embed(
            title="🛡️ Circuit Verse Helper Safety System Status",
            description="Active safety and auto-moderation subsystem protecting the Discord community.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Status", value="🟢 **Fully Active & Guarding**", inline=True)
        embed.add_field(name="Community Standard", value="🛡️ **13+ Verified Ruleset**", inline=True)
        embed.add_field(name="Warning Threshold", value="⚠️ **3 Warnings = Auto-Timeout**", inline=True)
        embed.add_field(name="Phishing / Token Guard", value="🟢 Active (7-Day Timeout + Approval)", inline=True)
        embed.add_field(name="Hate Speech / Slur Guard", value="🟢 Active (Auto-Delete + 1h-24h Timeout)", inline=True)
        embed.add_field(name="Mass Mention / Raid Guard", value="🟢 Active (>4 Pings / Flood Auto-Delete)", inline=True)
        embed.add_field(name="Total Users with Warnings", value=str(total_users_warned), inline=True)
        embed.add_field(name="Total Warnings Recorded", value=str(total_warns), inline=True)
        embed.add_field(name="Staff Approval Escalation", value="Active (`#general-incidents-chat` & `#administration`)", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
