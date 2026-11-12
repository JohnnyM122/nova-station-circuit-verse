import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio

logger = logging.getLogger("CVNovaHelper.voice_channels")

class VoiceChannelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        # channel_id -> {"creator_id": int, "delete_task": asyncio.Task | None}
        self.temp_channels = {}

    def save_config(self):
        from main import save_config
        save_config(self.config)

    def check_staff_perm(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        check_fn = getattr(self.bot, "check_command_permission", None)
        if check_fn:
            allowed, _ = check_fn(interaction.user, "configure_voice_system")
            return allowed
        return False

    def is_user_allowed_to_create_vc(self, member: discord.Member) -> bool:
        v_cfg = self.config.get("voice_system", {})
        allowed_roles = v_cfg.get("allowed_roles", [])
        if not allowed_roles:
            return True # No restriction, everyone can create
        user_role_ids = {r.id for r in member.roles}
        return any(rid in user_role_ids for rid in allowed_roles) or member.guild_permissions.administrator

    def get_member_temp_channel(self, member: discord.Member) -> discord.VoiceChannel | None:
        if not member.voice or not member.voice.channel:
            return None
        ch = member.voice.channel
        data = self.temp_channels.get(ch.id)
        if data and data.get("creator_id") == member.id:
            return ch
        return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        v_cfg = self.config.setdefault("voice_system", {
            "enabled": True,
            "creator_channel_id": 1564605316849733726, # #General voice channel
            "category_id": 1564605316849733724,        # #Voice Channels category
            "empty_delay_seconds": 30,
            "allowed_roles": []
        })

        if not v_cfg.get("enabled", True):
            return

        creator_ch_id = v_cfg.get("creator_channel_id")

        # 1. Member joined the "Join to Create" channel
        if after.channel and after.channel.id == creator_ch_id:
            # Check permissions
            if not self.is_user_allowed_to_create_vc(member):
                try:
                    await member.move_to(None) # Disconnect
                    await member.send("🚫 You do not have permission to create temporary voice channels in this server.")
                except Exception:
                    pass
                return

            guild = member.guild
            category_id = v_cfg.get("category_id") or (after.channel.category_id if after.channel else None)
            category = guild.get_channel(category_id) if category_id else None

            # Setup permissions for the new voice channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True, speak=True, view_channel=True),
                member: discord.PermissionOverwrite(
                    manage_channels=True,
                    move_members=True,
                    connect=True,
                    speak=True,
                    mute_members=True,
                    deafen_members=True,
                    priority_speaker=True
                )
            }

            clean_name = f"🔊 {member.display_name}'s Channel"
            try:
                if category and isinstance(category, discord.CategoryChannel):
                    new_ch = await category.create_voice_channel(name=clean_name, overwrites=overwrites)
                else:
                    new_ch = await guild.create_voice_channel(name=clean_name, overwrites=overwrites)

                # Move member to their new channel
                await member.move_to(new_ch)

                self.temp_channels[new_ch.id] = {
                    "creator_id": member.id,
                    "delete_task": None
                }
                logger.info(f"Created temporary VC '{clean_name}' for {member.name}")
            except Exception as e:
                logger.error(f"Failed to create temporary voice channel: {e}")

        # 2. Member left a voice channel - check if an empty temp channel should be cleaned up
        if before.channel and before.channel.id in self.temp_channels:
            temp_ch = before.channel
            # Check if now empty
            if len(temp_ch.members) == 0:
                empty_delay = v_cfg.get("empty_delay_seconds", 30)

                async def delete_channel_after_delay(channel_id: int, delay: int):
                    try:
                        await asyncio.sleep(delay)
                        ch = self.bot.get_channel(channel_id)
                        if ch and len(ch.members) == 0:
                            await ch.delete(reason=f"Temporary voice channel empty for {delay}s")
                            self.temp_channels.pop(channel_id, None)
                            logger.info(f"Deleted empty temporary voice channel {ch.name} ({channel_id})")
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error deleting temp voice channel: {e}")

                # Cancel any existing task and start a new delayed deletion
                existing_task = self.temp_channels[temp_ch.id].get("delete_task")
                if existing_task and not existing_task.done():
                    existing_task.cancel()

                task = asyncio.create_task(delete_channel_after_delay(temp_ch.id, empty_delay))
                self.temp_channels[temp_ch.id]["delete_task"] = task

        # 3. Someone joined an existing temp channel while timer was running -> cancel deletion!
        if after.channel and after.channel.id in self.temp_channels:
            task = self.temp_channels[after.channel.id].get("delete_task")
            if task and not task.done():
                task.cancel()
                self.temp_channels[after.channel.id]["delete_task"] = None

    # -------------------------------------------------------------
    # Voice Channel Control Slash Commands (For Channel Owners)
    # -------------------------------------------------------------

    @app_commands.command(name="vc_name", description="Rename your temporary voice channel")
    @app_commands.describe(new_name="The new name for your voice channel")
    async def cmd_vc_name(self, interaction: discord.Interaction, new_name: str):
        vc = self.get_member_temp_channel(interaction.user)
        if not vc:
            await interaction.response.send_message("❌ You are not currently in a temporary voice channel that you own.", ephemeral=True)
            return

        clean = new_name.strip()[:90]
        try:
            await vc.edit(name=f"🔊 {clean}")
            await interaction.response.send_message(f"✅ Your channel has been renamed to **`🔊 {clean}`**.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to rename channel: `{e}`", ephemeral=True)

    @app_commands.command(name="vc_limit", description="Set the user limit for your temporary voice channel")
    @app_commands.describe(limit="Maximum number of users allowed (0 for unlimited, 1-99)")
    async def cmd_vc_limit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):
        vc = self.get_member_temp_channel(interaction.user)
        if not vc:
            await interaction.response.send_message("❌ You are not currently in a temporary voice channel that you own.", ephemeral=True)
            return

        try:
            await vc.edit(user_limit=limit)
            limit_str = "unlimited" if limit == 0 else f"{limit} users"
            await interaction.response.send_message(f"✅ User limit set to **{limit_str}**.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to update limit: `{e}`", ephemeral=True)

    @app_commands.command(name="vc_lock", description="Lock your temporary voice channel so other members cannot join")
    async def cmd_vc_lock(self, interaction: discord.Interaction):
        vc = self.get_member_temp_channel(interaction.user)
        if not vc:
            await interaction.response.send_message("❌ You are not currently in a temporary voice channel that you own.", ephemeral=True)
            return

        try:
            await vc.set_permissions(interaction.guild.default_role, connect=False)
            await interaction.response.send_message("🔒 Your voice channel is now **locked**. Only members you permit or staff can join.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to lock channel: `{e}`", ephemeral=True)

    @app_commands.command(name="vc_unlock", description="Unlock your temporary voice channel so everyone can join")
    async def cmd_vc_unlock(self, interaction: discord.Interaction):
        vc = self.get_member_temp_channel(interaction.user)
        if not vc:
            await interaction.response.send_message("❌ You are not currently in a temporary voice channel that you own.", ephemeral=True)
            return

        try:
            await vc.set_permissions(interaction.guild.default_role, connect=True)
            await interaction.response.send_message("🔓 Your voice channel is now **unlocked**.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to unlock channel: `{e}`", ephemeral=True)

    @app_commands.command(name="vc_kick", description="Disconnect a member from your temporary voice channel")
    @app_commands.describe(member="The member to disconnect from your channel")
    async def cmd_vc_kick(self, interaction: discord.Interaction, member: discord.Member):
        vc = self.get_member_temp_channel(interaction.user)
        if not vc:
            await interaction.response.send_message("❌ You are not currently in a temporary voice channel that you own.", ephemeral=True)
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot kick yourself.", ephemeral=True)
            return

        if not member.voice or member.voice.channel.id != vc.id:
            await interaction.response.send_message("❌ That member is not currently in your voice channel.", ephemeral=True)
            return

        try:
            await member.move_to(None) # Disconnect
            await vc.set_permissions(member, connect=False) # Prevent them from immediately re-joining
            await interaction.response.send_message(f"👢 Disconnected {member.mention} from your voice channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error kicking member: `{e}`", ephemeral=True)

    @app_commands.command(name="vc_trust", description="Grant a friend permission to join your voice channel even if locked")
    @app_commands.describe(member="The member to permit")
    async def cmd_vc_trust(self, interaction: discord.Interaction, member: discord.Member):
        vc = self.get_member_temp_channel(interaction.user)
        if not vc:
            await interaction.response.send_message("❌ You are not currently in a temporary voice channel that you own.", ephemeral=True)
            return

        try:
            await vc.set_permissions(member, connect=True, speak=True, view_channel=True)
            await interaction.response.send_message(f"✅ Trusted {member.mention}! They can now join your channel anytime.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to trust member: `{e}`", ephemeral=True)

    # -------------------------------------------------------------
    # Voice System Configuration (Staff only)
    # -------------------------------------------------------------

    @app_commands.command(name="configure_voice_system", description="Configure temporary voice channels, allowed roles, and empty timeout")
    @app_commands.describe(
        creator_channel="The voice channel users join to trigger creating a temporary channel",
        empty_delay_seconds="How many seconds an empty temporary channel stays open before deleting",
        allowed_role="Role to add or remove from permitted creator roles",
        role_action="Add or remove the allowed role",
        enabled="Enable or disable the temporary voice system"
    )
    @app_commands.choices(role_action=[
        app_commands.Choice(name="Add role to allowed creators", value="add"),
        app_commands.Choice(name="Remove role from allowed creators", value="remove"),
        app_commands.Choice(name="Clear all role restrictions (allow everyone)", value="clear")
    ])
    async def cmd_configure_voice_system(
        self,
        interaction: discord.Interaction,
        creator_channel: discord.VoiceChannel = None,
        empty_delay_seconds: app_commands.Range[int, 5, 300] = None,
        allowed_role: discord.Role = None,
        role_action: app_commands.Choice[str] = None,
        enabled: bool = None
    ):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        v_cfg = self.config.setdefault("voice_system", {
            "enabled": True,
            "creator_channel_id": 1564605316849733726,
            "category_id": 1564605316849733724,
            "empty_delay_seconds": 30,
            "allowed_roles": []
        })

        changes = []
        if enabled is not None:
            v_cfg["enabled"] = enabled
            changes.append(f"• **Enabled**: `{'Yes' if enabled else 'No'}`")

        if creator_channel:
            v_cfg["creator_channel_id"] = creator_channel.id
            if creator_channel.category_id:
                v_cfg["category_id"] = creator_channel.category_id
            changes.append(f"• **Join-to-Create Channel**: {creator_channel.mention}")

        if empty_delay_seconds is not None:
            v_cfg["empty_delay_seconds"] = empty_delay_seconds
            changes.append(f"• **Empty Channel Deletion Delay**: `{empty_delay_seconds} seconds`")

        allowed_roles = v_cfg.setdefault("allowed_roles", [])
        if role_action:
            if role_action.value == "add" and allowed_role:
                if allowed_role.id not in allowed_roles:
                    allowed_roles.append(allowed_role.id)
                    changes.append(f"• **Added Allowed Role**: {allowed_role.mention}")
            elif role_action.value == "remove" and allowed_role:
                if allowed_role.id in allowed_roles:
                    allowed_roles.remove(allowed_role.id)
                    changes.append(f"• **Removed Allowed Role**: {allowed_role.mention}")
            elif role_action.value == "clear":
                allowed_roles.clear()
                changes.append("• **Cleared Role Restrictions**: Everyone is now permitted to create temporary VCs")

        if not changes:
            curr_creator = interaction.guild.get_channel(v_cfg.get("creator_channel_id"))
            creator_str = curr_creator.mention if curr_creator else f"`{v_cfg.get('creator_channel_id')}`"
            roles_str = ", ".join([interaction.guild.get_role(rid).mention for rid in allowed_roles if interaction.guild.get_role(rid)]) if allowed_roles else "Everyone (no role restrictions)"

            embed = discord.Embed(title="⚙️ Temporary Voice Channel Settings", color=discord.Color.blue())
            embed.add_field(name="Status", value="🟢 Enabled" if v_cfg.get("enabled", True) else "🔴 Disabled", inline=True)
            embed.add_field(name="Join-to-Create Channel", value=creator_str, inline=True)
            embed.add_field(name="Empty Deletion Delay", value=f"{v_cfg.get('empty_delay_seconds', 30)} seconds", inline=True)
            embed.add_field(name="Permitted Creator Roles", value=roles_str, inline=False)
            embed.set_footer(text="Users who join the creator channel get their own temporary VC with control commands.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.save_config()
        embed = discord.Embed(
            title="✅ Voice System Settings Updated",
            description="\n".join(changes),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceChannelsCog(bot))
