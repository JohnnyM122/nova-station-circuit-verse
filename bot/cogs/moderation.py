import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import re
import datetime
from collections import defaultdict

logger = logging.getLogger("CVNovaHelper.moderation")

INVITE_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com\/invite)\/([a-zA-Z0-9\-]+)", re.IGNORECASE)

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        # user_id -> list of timestamps
        self.user_message_times = defaultdict(list)

    def save_config(self):
        from main import save_config
        save_config(self.config)

    def check_mod_perm(self, member: discord.Member, cmd_name: str) -> tuple[bool, str]:
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return True, "Administrator"
        check_fn = getattr(self.bot, "check_command_permission", None)
        if check_fn:
            return check_fn(member, cmd_name)
        # Fallback tier check
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            tier = staff_cog.get_staff_tier(member)
            if tier in ("FOUNDER", "ADMIN", "MODERATOR"):
                return True, tier
        return False, "Staff permission required"

    async def log_mod_action(self, guild: discord.Guild, embed: discord.Embed):
        admin_logs_id = self.config.get("channels", {}).get("admin_logs", 1566609343678521344)
        if admin_logs_id:
            channel = guild.get_channel(admin_logs_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.debug(f"Could not send mod log: {e}")

    # -------------------------------------------------------------
    # Auto-Moderation Listener
    # -------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        automod_cfg = self.config.setdefault("automod", {
            "enabled": True,
            "block_invites": True,
            "anti_spam": True,
            "max_messages_per_5s": 5,
            "max_mentions": 5,
            "excessive_caps": True,
            "caps_threshold": 0.8,
            "min_caps_length": 15,
            "banned_words": ["nigger", "nigga", "faggot", "retard"]
        })

        if not automod_cfg.get("enabled", True):
            return

        # Bypass for staff & administrators
        is_staff = False
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog and isinstance(message.author, discord.Member):
            tier = staff_cog.get_staff_tier(message.author)
            if tier in ("FOUNDER", "ADMIN", "MODERATOR"):
                is_staff = True
        elif isinstance(message.author, discord.Member) and message.author.guild_permissions.administrator:
            is_staff = True

        if is_staff:
            return

        content = message.content or ""
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        author = message.author

        # 1. Anti-Spam (Rate Limiter)
        if automod_cfg.get("anti_spam", True):
            msg_times = self.user_message_times[author.id]
            msg_times.append(now)
            # Retain only timestamps from the last 5 seconds
            self.user_message_times[author.id] = [t for t in msg_times if now - t <= 5.0]

            max_msgs = automod_cfg.get("max_messages_per_5s", 5)
            if len(self.user_message_times[author.id]) > max_msgs:
                try:
                    await message.delete()
                except Exception:
                    pass

                # Apply 1-minute timeout
                try:
                    await author.timeout(datetime.timedelta(minutes=1), reason="Auto-Mod: Excessive message spam")
                    warn = await message.channel.send(f"⚠️ {author.mention} has been timed out for 1 minute for spamming.", delete_after=8)
                except Exception:
                    pass

                embed = discord.Embed(title="🛡️ Auto-Mod: Anti-Spam Triggered", color=discord.Color.orange())
                embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="Action", value="Message deleted & 1-minute timeout applied", inline=False)
                await self.log_mod_action(message.guild, embed)
                return

        # 2. Block Discord Invite Links
        if automod_cfg.get("block_invites", True):
            if INVITE_REGEX.search(content):
                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(f"🚫 {author.mention}, posting external Discord invite links is not permitted.", delete_after=8)

                embed = discord.Embed(title="🛡️ Auto-Mod: Invite Link Removed", color=discord.Color.red())
                embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="Filtered Content", value=f"`{content[:300]}`", inline=False)
                await self.log_mod_action(message.guild, embed)
                return

        # 3. Banned Word / Slur Filter
        banned_words = automod_cfg.get("banned_words", [])
        if banned_words:
            for word in banned_words:
                pattern = rf"\b{re.escape(word)}\b"
                if re.search(pattern, content, re.IGNORECASE):
                    try:
                        await message.delete()
                    except Exception:
                        pass

                    await message.channel.send(f"🚫 {author.mention}, your message contained prohibited language and was deleted.", delete_after=8)

                    embed = discord.Embed(title="🛡️ Auto-Mod: Prohibited Language Filtered", color=discord.Color.red())
                    embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
                    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                    embed.add_field(name="Matched Keyword", value=f"||`{word}`||", inline=False)
                    await self.log_mod_action(message.guild, embed)
                    return

        # 4. Mass Mentions Prevention
        max_mentions = automod_cfg.get("max_mentions", 5)
        if len(message.mentions) > max_mentions:
            try:
                await message.delete()
            except Exception:
                pass

            try:
                await author.timeout(datetime.timedelta(minutes=5), reason="Auto-Mod: Mass mentions")
                await message.channel.send(f"⚠️ {author.mention} has been timed out for 5 minutes for mass mentions.", delete_after=8)
            except Exception:
                pass

            embed = discord.Embed(title="🛡️ Auto-Mod: Mass Mentions Triggered", color=discord.Color.orange())
            embed.add_field(name="User", value=f"{author.mention} (`{author.name}`)", inline=True)
            embed.add_field(name="Mentions Count", value=str(len(message.mentions)), inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            await self.log_mod_action(message.guild, embed)
            return

        # 5. Excessive Caps
        if automod_cfg.get("excessive_caps", False):
            min_len = automod_cfg.get("min_caps_length", 15)
            thresh = automod_cfg.get("caps_threshold", 0.8)
            alpha_chars = [c for c in content if c.isalpha()]
            if len(alpha_chars) >= min_len:
                caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
                if caps_ratio >= thresh:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    await message.channel.send(f"⚠️ {author.mention}, please avoid typing in excessive all-caps.", delete_after=6)
                    return

    # -------------------------------------------------------------
    # Manual Moderation Commands
    # -------------------------------------------------------------

    @app_commands.command(name="clear", description="Clear/purge a specified number of messages from this channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Optionally filter messages to only delete those from a specific user"
    )
    async def cmd_clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100], user: discord.Member = None):
        allowed, rank_name = self.check_mod_perm(interaction.user, "clear")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        def check_msg(m):
            if user:
                return m.author.id == user.id
            return True

        try:
            deleted = await interaction.channel.purge(limit=amount, check=check_msg)
            user_suffix = f" from {user.mention}" if user else ""
            await interaction.followup.send(f"🧹 Purged **{len(deleted)}** messages{user_suffix}.", ephemeral=True)

            embed = discord.Embed(title="🧹 Chat Messages Purged", color=discord.Color.teal())
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
            embed.add_field(name="Messages Deleted", value=str(len(deleted)), inline=True)
            if user:
                embed.add_field(name="Target User", value=user.mention, inline=True)
            await self.log_mod_action(interaction.guild, embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error purging messages: `{e}`", ephemeral=True)

    @app_commands.command(name="timeout", description="Temporarily time out a member so they cannot send messages or join voice")
    @app_commands.describe(
        member="The member to time out",
        minutes="Duration of the timeout in minutes",
        reason="Reason for the timeout"
    )
    async def cmd_timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Moderator disciplinary action"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "timeout")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ You cannot time out a member with an equal or higher role than yourself.", ephemeral=True)
            return

        if minutes <= 0 or minutes > 40320: # Discord max is 28 days
            await interaction.response.send_message("❌ Timeout duration must be between 1 minute and 40,320 minutes (28 days).", ephemeral=True)
            return

        duration = datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(duration, reason=f"{reason} (by {interaction.user.name})")

            embed = discord.Embed(title="⏳ Member Timed Out", color=discord.Color.orange())
            embed.add_field(name="Target", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(name="Duration", value=f"{minutes} minutes", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=f"`{reason}`", inline=False)

            await interaction.response.send_message(embed=embed)
            await self.log_mod_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Failed to timeout member: Check the bot's role hierarchy.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: `{e}`", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove an active timeout from a member")
    @app_commands.describe(member="The member to remove timeout from", reason="Reason for lifting timeout")
    async def cmd_untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Timeout lifted by moderator"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "untimeout")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        try:
            await member.timeout(None, reason=f"{reason} (by {interaction.user.name})")
            embed = discord.Embed(title="⏱️ Member Timeout Removed", color=discord.Color.green())
            embed.add_field(name="Target", value=f"{member.mention} (`{member.name}`)", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=f"`{reason}`", inline=False)
            await interaction.response.send_message(embed=embed)
            await self.log_mod_action(interaction.guild, embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to lift timeout: `{e}`", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member from the Discord server")
    @app_commands.describe(member="The member to kick", reason="Reason for kicking")
    async def cmd_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Kicked by staff"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "kick")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ You cannot kick a member with an equal or higher role than yourself.", ephemeral=True)
            return

        # Attempt to DM explanation before kicking
        try:
            await member.send(f"⚠️ You have been kicked from **{interaction.guild.name}**.\n**Reason:** `{reason}`")
        except Exception:
            pass

        try:
            await member.kick(reason=f"{reason} (by {interaction.user.name})")
            embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
            embed.add_field(name="Target", value=f"`{member.name}` ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=f"`{reason}`", inline=False)
            await interaction.response.send_message(embed=embed)
            await self.log_mod_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Failed to kick member: Check the bot's role hierarchy.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error kicking member: `{e}`", ephemeral=True)

    @app_commands.command(name="discord_ban", description="Ban a member from the Discord server")
    @app_commands.describe(
        member="The member to ban",
        delete_message_days="Number of days of messages to delete (0-7)",
        reason="Reason for the ban"
    )
    async def cmd_discord_ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
        reason: str = "Banned by staff"
    ):
        allowed, rank_name = self.check_mod_perm(interaction.user, "discord_ban")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ You cannot ban a member with an equal or higher role than yourself.", ephemeral=True)
            return

        try:
            await member.send(f"🔨 You have been banned from **{interaction.guild.name}**.\n**Reason:** `{reason}`")
        except Exception:
            pass

        try:
            await member.ban(delete_message_days=delete_message_days, reason=f"{reason} (by {interaction.user.name})")
            embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
            embed.add_field(name="Target", value=f"`{member.name}` ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Purged Days", value=str(delete_message_days), inline=True)
            embed.add_field(name="Reason", value=f"`{reason}`", inline=False)
            await interaction.response.send_message(embed=embed)
            await self.log_mod_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Failed to ban member: Check the bot's role hierarchy.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error banning member: `{e}`", ephemeral=True)

    @app_commands.command(name="discord_unban", description="Unban a previously banned user by their Discord User ID")
    @app_commands.describe(user_id="The Discord user ID of the banned user", reason="Reason for lifting the ban")
    async def cmd_discord_unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Ban lifted by staff"):
        allowed, rank_name = self.check_mod_perm(interaction.user, "discord_unban")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        try:
            uid = int(user_id.strip())
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=f"{reason} (by {interaction.user.name})")
            embed = discord.Embed(title="🔓 Member Unbanned", color=discord.Color.green())
            embed.add_field(name="Target", value=f"`{user.name}` ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=f"`{reason}`", inline=False)
            await interaction.response.send_message(embed=embed)
            await self.log_mod_action(interaction.guild, embed)
        except discord.NotFound:
            await interaction.response.send_message(f"❌ No banned user found with ID `{user_id}`.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID. Please provide a numeric Discord ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error unbanning user: `{e}`", ephemeral=True)

    @app_commands.command(name="configure_automod", description="Configure Auto-Mod filters, rules, and banned words")
    @app_commands.describe(
        rule="The auto-mod rule to configure",
        enabled="Enable or disable this rule",
        banned_word="Word or slur to add/remove from blacklist",
        word_action="Add or Remove the specified banned word"
    )
    @app_commands.choices(
        rule=[
            app_commands.Choice(name="Master Auto-Mod (Turn all filters on/off)", value="enabled"),
            app_commands.Choice(name="Block Discord Invites", value="block_invites"),
            app_commands.Choice(name="Anti-Spam Rate Limiter", value="anti_spam"),
            app_commands.Choice(name="Excessive Caps Filter", value="excessive_caps"),
        ],
        word_action=[
            app_commands.Choice(name="Add word to filter", value="add"),
            app_commands.Choice(name="Remove word from filter", value="remove"),
            app_commands.Choice(name="List current banned words", value="list")
        ]
    )
    async def cmd_configure_automod(
        self,
        interaction: discord.Interaction,
        rule: app_commands.Choice[str] = None,
        enabled: bool = None,
        banned_word: str = None,
        word_action: app_commands.Choice[str] = None
    ):
        allowed, rank_name = self.check_mod_perm(interaction.user, "configure_automod")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_name}", ephemeral=True)
            return

        automod_cfg = self.config.setdefault("automod", {
            "enabled": True,
            "block_invites": True,
            "anti_spam": True,
            "max_messages_per_5s": 5,
            "max_mentions": 5,
            "excessive_caps": True,
            "caps_threshold": 0.8,
            "min_caps_length": 15,
            "banned_words": ["nigger", "nigga", "faggot", "retard"]
        })

        banned_words = automod_cfg.setdefault("banned_words", [])

        if word_action:
            if word_action.value == "list":
                words_str = ", ".join([f"`{w}`" for w in banned_words]) if banned_words else "No words filtered"
                await interaction.response.send_message(f"📋 **Current Banned Words ({len(banned_words)}):**\n{words_str}", ephemeral=True)
                return
            elif word_action.value == "add":
                if not banned_word:
                    await interaction.response.send_message("❌ Please provide a word to add.", ephemeral=True)
                    return
                clean = banned_word.strip().lower()
                if clean not in banned_words:
                    banned_words.append(clean)
                    self.save_config()
                    await interaction.response.send_message(f"✅ Added `||{clean}||` to the auto-mod word filter.", ephemeral=True)
                else:
                    await interaction.response.send_message("ℹ️ That word is already in the filter.", ephemeral=True)
                return
            elif word_action.value == "remove":
                if not banned_word:
                    await interaction.response.send_message("❌ Please provide a word to remove.", ephemeral=True)
                    return
                clean = banned_word.strip().lower()
                if clean in banned_words:
                    banned_words.remove(clean)
                    self.save_config()
                    await interaction.response.send_message(f"✅ Removed `||{clean}||` from the word filter.", ephemeral=True)
                else:
                    await interaction.response.send_message("ℹ️ Word not found in filter.", ephemeral=True)
                return

        if rule and enabled is not None:
            automod_cfg[rule.value] = enabled
            self.save_config()
            await interaction.response.send_message(f"✅ Auto-Mod rule **{rule.name}** set to **{'Enabled' if enabled else 'Disabled'}**.", ephemeral=True)
            return

        # Show overall status if no changes
        embed = discord.Embed(title="⚙️ Auto-Moderation Status", color=discord.Color.blue())
        embed.add_field(name="Auto-Mod Master", value="🟢 Enabled" if automod_cfg.get("enabled", True) else "🔴 Disabled", inline=True)
        embed.add_field(name="Block Invites", value="🟢 Enabled" if automod_cfg.get("block_invites", True) else "🔴 Disabled", inline=True)
        embed.add_field(name="Anti-Spam", value="🟢 Enabled" if automod_cfg.get("anti_spam", True) else "🔴 Disabled", inline=True)
        embed.add_field(name="Excessive Caps", value="🟢 Enabled" if automod_cfg.get("excessive_caps", True) else "🔴 Disabled", inline=True)
        embed.add_field(name="Max Mentions", value=str(automod_cfg.get("max_mentions", 5)), inline=True)
        embed.add_field(name="Filtered Words Count", value=f"{len(banned_words)} words", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
