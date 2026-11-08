import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger("CVNovaHelper.reaction_roles")

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    def save_config(self):
        from main import save_config
        save_config(self.config)

    def check_staff_perm(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        check_fn = getattr(self.bot, "check_command_permission", None)
        if check_fn:
            allowed, _ = check_fn(interaction.user, "reaction_roles")
            return allowed
        return False

    def get_emoji_key(self, emoji: discord.PartialEmoji) -> str:
        if emoji.id:
            return f"<:{emoji.name}:{emoji.id}>"
        return str(emoji.name)


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component or not interaction.data:
            return
        cid = str(interaction.data.get("custom_id", ""))
        if not cid.startswith("autorole:"):
            return
        role_id_str = cid.split(":", 1)[1]
        if not role_id_str.isdigit() or not interaction.guild:
            return
        role = interaction.guild.get_role(int(role_id_str))
        if not role:
            await interaction.response.send_message("❌ That role could not be found.", ephemeral=True)
            return
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Self-assignable role button toggle")
                await interaction.response.send_message(f"🗑️ Removed role {role.mention}!", ephemeral=True)
            else:
                await member.add_roles(role, reason="Self-assignable role button toggle")
                await interaction.response.send_message(f"✅ Granted role {role.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Could not update role: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        rr_cfg = self.config.get("reaction_roles", {})
        if not rr_cfg.get("enabled", True):
            return

        panels = rr_cfg.get("panels", {})
        panel_data = panels.get(str(payload.message_id))
        if not panel_data:
            return

        mappings = panel_data.get("mappings", {})
        emoji_key = self.get_emoji_key(payload.emoji)
        role_id = mappings.get(emoji_key) or mappings.get(str(payload.emoji.name))
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        role = guild.get_role(int(role_id))
        if role and role not in member.roles:
            try:
                await member.add_roles(role, reason=f"Reaction role panel ({panel_data.get('title', 'Role Menu')})")
                logger.info(f"Granted reaction role @{role.name} to {member.name}")
            except discord.Forbidden:
                logger.warning(f"Failed to assign reaction role @{role.name} to {member.name}: Check role hierarchy.")
            except Exception as e:
                logger.error(f"Error adding reaction role: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id or not payload.guild_id:
            return

        rr_cfg = self.config.get("reaction_roles", {})
        if not rr_cfg.get("enabled", True):
            return

        panels = rr_cfg.get("panels", {})
        panel_data = panels.get(str(payload.message_id))
        if not panel_data:
            return

        mappings = panel_data.get("mappings", {})
        emoji_key = self.get_emoji_key(payload.emoji)
        role_id = mappings.get(emoji_key) or mappings.get(str(payload.emoji.name))
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        role = guild.get_role(int(role_id))
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=f"Reaction role removed ({panel_data.get('title', 'Role Menu')})")
                logger.info(f"Removed reaction role @{role.name} from {member.name}")
            except discord.Forbidden:
                logger.warning(f"Failed to remove reaction role @{role.name} from {member.name}: Check role hierarchy.")
            except Exception as e:
                logger.error(f"Error removing reaction role: {e}")

    # -------------------------------------------------------------
    # Slash Commands: Reaction Roles
    # -------------------------------------------------------------

    @app_commands.command(name="reaction_role_create", description="Create a new reaction role embed panel in a channel")
    @app_commands.describe(
        channel="The text channel where the reaction role embed should be posted",
        title="Title of the role menu (e.g. 'Station Role Selection')",
        description="Introductory instructions or description"
    )
    async def cmd_reaction_role_create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str = "🛡️ Server Role Selection",
        description: str = "React with the corresponding icons below to gain or remove roles."
    ):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description=f"{description}\n\n*No roles configured yet. Use `/reaction_role_add` to add roles to this panel.*",
            color=discord.Color.from_rgb(0, 225, 255)
        )
        embed.set_footer(text="Nova Station 13 • Circuit Verse Automated Terminal", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        try:
            panel_msg = await channel.send(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send embed to {channel.mention}: `{e}`", ephemeral=True)
            return

        rr_cfg = self.config.setdefault("reaction_roles", {"enabled": True, "panels": {}})
        rr_cfg.setdefault("panels", {})[str(panel_msg.id)] = {
            "channel_id": channel.id,
            "title": title,
            "description": description,
            "mappings": {}
        }
        self.save_config()

        await interaction.response.send_message(
            f"✅ **Reaction role panel created!**\n"
            f"• **Channel**: {channel.mention}\n"
            f"• **Message ID**: `{panel_msg.id}`\n\n"
            f"Now use `/reaction_role_add message_id:{panel_msg.id} emoji:<emoji> role:@Role` to attach roles!",
            ephemeral=True
        )

    @app_commands.command(name="reaction_role_add", description="Add an emoji-to-role binding to a reaction role panel")
    @app_commands.describe(
        message_id="The message ID of the reaction role panel",
        emoji="The emoji to react with (e.g. 🎮, 🔔, or custom emoji)",
        role="The Discord role to grant on reaction"
    )
    async def cmd_reaction_role_add(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str,
        role: discord.Role
    ):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        clean_id = message_id.strip()
        rr_cfg = self.config.setdefault("reaction_roles", {"enabled": True, "panels": {}})
        panels = rr_cfg.setdefault("panels", {})

        panel_data = panels.get(clean_id)
        if not panel_data:
            await interaction.response.send_message(f"❌ No registered reaction role panel found with message ID `{clean_id}`.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(panel_data["channel_id"])
        if not channel:
            await interaction.response.send_message("❌ Panel channel could not be found.", ephemeral=True)
            return

        try:
            msg = await channel.fetch_message(int(clean_id))
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not fetch message `{clean_id}` in {channel.mention}: `{e}`", ephemeral=True)
            return

        clean_emoji = emoji.strip()
        # Add reaction to message
        try:
            await msg.add_reaction(clean_emoji)
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not react with `{clean_emoji}`: `{e}`. Ensure the bot has access to this emoji.", ephemeral=True)
            return

        # Update mappings
        panel_data.setdefault("mappings", {})[clean_emoji] = role.id
        self.save_config()

        # Update the embed message with the current mappings list
        try:
            lines = [f"{em} ➔ {interaction.guild.get_role(rid).mention if interaction.guild.get_role(rid) else f'<@&{rid}>'}" for em, rid in panel_data["mappings"].items()]
            desc = panel_data.get("description", "React to gain roles.") + "\n\n" + "\n".join(lines)
            new_embed = discord.Embed(
                title=panel_data.get("title", "Server Roles"),
                description=desc,
                color=discord.Color.from_rgb(0, 225, 255)
            )
            new_embed.set_footer(text="Nova Station 13 • Circuit Verse Automated Terminal", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            await msg.edit(embed=new_embed)
        except Exception as e:
            logger.warning(f"Could not edit panel embed: {e}")

        await interaction.response.send_message(f"✅ Bound {clean_emoji} to {role.mention} on panel `{clean_id}`!", ephemeral=True)

    @app_commands.command(name="reaction_role_remove", description="Remove an emoji binding from a reaction role panel")
    @app_commands.describe(
        message_id="The message ID of the reaction role panel",
        emoji="The emoji to remove"
    )
    async def cmd_reaction_role_remove(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str
    ):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        clean_id = message_id.strip()
        rr_cfg = self.config.get("reaction_roles", {})
        panels = rr_cfg.get("panels", {})
        panel_data = panels.get(clean_id)
        if not panel_data:
            await interaction.response.send_message(f"❌ Panel `{clean_id}` not found.", ephemeral=True)
            return

        clean_emoji = emoji.strip()
        mappings = panel_data.get("mappings", {})
        if clean_emoji in mappings:
            del mappings[clean_emoji]
            self.save_config()

            # Refresh embed
            channel = interaction.guild.get_channel(panel_data["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(int(clean_id))
                    lines = [f"{em} ➔ {interaction.guild.get_role(rid).mention if interaction.guild.get_role(rid) else f'<@&{rid}>'}" for em, rid in mappings.items()]
                    desc = panel_data.get("description", "React to gain roles.") + ("\n\n" + "\n".join(lines) if lines else "\n\n*No roles configured.*")
                    new_embed = discord.Embed(
                        title=panel_data.get("title", "Server Roles"),
                        description=desc,
                        color=discord.Color.from_rgb(0, 225, 255)
                    )
                    new_embed.set_footer(text="Nova Station 13 • Circuit Verse Automated Terminal", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                    await msg.edit(embed=new_embed)
                    await msg.clear_reaction(clean_emoji)
                except Exception:
                    pass

            await interaction.response.send_message(f"✅ Removed `{clean_emoji}` from panel `{clean_id}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ `{clean_emoji}` was not mapped on panel `{clean_id}`.", ephemeral=True)

    @app_commands.command(name="reaction_roles_list", description="List all active reaction role panels")
    async def cmd_reaction_roles_list(self, interaction: discord.Interaction):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        rr_cfg = self.config.get("reaction_roles", {})
        panels = rr_cfg.get("panels", {})
        if not panels:
            await interaction.response.send_message("ℹ️ No reaction role panels are currently registered.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 Active Reaction Role Panels", color=discord.Color.blue())
        for mid, data in panels.items():
            ch = interaction.guild.get_channel(data.get("channel_id"))
            ch_str = ch.mention if ch else f"`{data.get('channel_id')}`"
            mappings = data.get("mappings", {})
            mappings_str = "\n".join([f"• {em} ➔ <@&{rid}>" for em, rid in mappings.items()]) if mappings else "*None*"
            embed.add_field(
                name=f"Panel: {data.get('title', 'Role Menu')} (ID: `{mid}`)",
                value=f"Channel: {ch_str}\n{mappings_str}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))
