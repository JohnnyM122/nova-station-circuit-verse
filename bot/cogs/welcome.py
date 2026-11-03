import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import mysql.connector

logger = logging.getLogger("CVNovaHelper.welcome")

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    def get_db_connection(self):
        db_conf = self.config.get("database", {})
        return mysql.connector.connect(
            host=db_conf.get("host", "127.0.0.1"),
            user=db_conf.get("user", "nova_station_app"),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", "paradise_gamedb")
        )

    def save_config(self):
        from main import save_config
        save_config(self.config)

    def check_staff_perm(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        check_fn = getattr(self.bot, "check_command_permission", None)
        if check_fn:
            allowed, _ = check_fn(interaction.user, "configure_welcome")
            return allowed
        return False

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild
        welcome_cfg = self.config.get("welcome", {})
        autorole_cfg = self.config.get("autorole", {})

        # 1. Auto-assign General Roles & Staff Database Roles
        if autorole_cfg.get("enabled", True):
            roles_to_add = []

            # Default general roles (e.g. Circuit Member)
            default_role_ids = autorole_cfg.get("default_roles", [1564609709418221668])
            for rid in default_role_ids:
                role = guild.get_role(int(rid))
                if role and role not in member.roles:
                    roles_to_add.append(role)

            # Check if this member is linked in the MariaDB staff database
            if autorole_cfg.get("sync_staff_db_on_join", True):
                try:
                    def query_staff():
                        conn = self.get_db_connection()
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("SELECT ckey FROM discord_links WHERE discord_id = %s", (str(member.id),))
                        link = cursor.fetchone()
                        if not link:
                            cursor.close()
                            conn.close()
                            return None
                        ckey = link["ckey"]
                        cursor.execute("""
                            SELECT a.display_rank, r.name AS rank_name
                            FROM admin a
                            LEFT JOIN admin_ranks r ON a.permissions_rank = r.id
                            WHERE LOWER(a.ckey) = LOWER(%s)
                        """, (ckey,))
                        admin_info = cursor.fetchone()
                        cursor.close()
                        conn.close()
                        return admin_info

                    admin_info = await asyncio.to_thread(query_staff)
                    if admin_info:
                        db_rank = admin_info.get("display_rank") or admin_info.get("rank_name")
                        if db_rank:
                            sync_cfg = self.config.get("auto_role_sync", {})
                            rank_to_role = sync_cfg.get("rank_to_role", {})
                            target_role_id = rank_to_role.get(db_rank)
                            target_role = guild.get_role(target_role_id) if target_role_id else None
                            if not target_role:
                                target_role = discord.utils.get(guild.roles, name=db_rank)
                            if target_role and target_role not in roles_to_add:
                                roles_to_add.append(target_role)

                            # Also add the general NS13 Server Staff badge if mapped
                            staff_badge_id = 1566480612121124874 # NS13 Server Staff
                            staff_badge = guild.get_role(staff_badge_id)
                            if staff_badge and staff_badge not in roles_to_add:
                                roles_to_add.append(staff_badge)

                except Exception as e:
                    logger.error(f"Error querying staff database on member join: {e}")

            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Auto-role assignment on member join")
                    logger.info(f"Auto-assigned {len(roles_to_add)} roles to new member {member.name} ({member.id})")
                except discord.Forbidden:
                    logger.warning(f"Failed to auto-assign roles to {member.name}: Missing Permissions or role hierarchy block.")
                except Exception as e:
                    logger.error(f"Unexpected error assigning auto-roles to {member.name}: {e}")

        # 2. Welcome Channel Message
        if welcome_cfg.get("enabled", True):
            ch_id = welcome_cfg.get("channel_id", 1564605316849733725)
            channel = guild.get_channel(ch_id)
            if channel:
                raw_template = welcome_cfg.get(
                    "message",
                    "Welcome to **{server}**, {mention}! We're thrilled to have you aboard Nova Station 13. Please make sure to check out <#1566600269649678467> and enjoy your stay!"
                )
                formatted_msg = raw_template.format(
                    mention=member.mention,
                    user=member.name,
                    server=guild.name,
                    member_count=guild.member_count
                )

                embed = discord.Embed(
                    title=f"🚀 Welcome to {guild.name}!",
                    description=formatted_msg,
                    color=discord.Color.from_rgb(0, 225, 255)
                )
                if member.display_avatar:
                    embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="👤 Passenger Name", value=f"{member.mention} (`{member.name}`)", inline=True)
                embed.add_field(name="👥 Station Population", value=f"#{guild.member_count}", inline=True)
                embed.set_footer(text="Nova Station 13 • Circuit Verse Automated Terminal", icon_url=guild.icon.url if guild.icon else None)

                try:
                    await channel.send(content=member.mention, embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send welcome message to #{channel.name}: {e}")

        # 3. Optional Direct Message Welcome
        if welcome_cfg.get("dm_welcome", False):
            dm_raw = welcome_cfg.get(
                "dm_message",
                "Hello {user}! Welcome aboard **{server}**. If you ever have any questions about the station or BYOND game server, check out our discord guides or ask staff!"
            )
            dm_formatted = dm_raw.format(
                user=member.name,
                server=guild.name,
                member_count=guild.member_count
            )
            try:
                await member.send(dm_formatted)
            except discord.Forbidden:
                pass # User has DMs closed
            except Exception as e:
                logger.debug(f"Could not DM new user {member.name}: {e}")

    # -------------------------------------------------------------
    # Slash Commands: Welcome & Auto-Role Configuration
    # -------------------------------------------------------------

    @app_commands.command(name="configure_welcome", description="Configure welcome message greeting, channel, and options")
    @app_commands.describe(
        channel="The text channel where welcome greetings should be posted",
        enabled="Enable or disable the welcome greetings",
        message="Custom greeting template ({mention}, {user}, {server}, {member_count})",
        dm_welcome="Whether to send a private welcome DM to joining members",
        dm_message="Custom DM message template"
    )
    async def cmd_configure_welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        enabled: bool = None,
        message: str = None,
        dm_welcome: bool = None,
        dm_message: str = None
    ):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**: You do not have permission to configure welcome settings.", ephemeral=True)
            return

        w_cfg = self.config.setdefault("welcome", {})

        changes = []
        if channel is not None:
            w_cfg["channel_id"] = channel.id
            changes.append(f"• **Channel**: {channel.mention}")
        if enabled is not None:
            w_cfg["enabled"] = enabled
            changes.append(f"• **Enabled**: `{'Yes' if enabled else 'No'}`")
        if message is not None:
            w_cfg["message"] = message
            changes.append(f"• **Greeting Template**: Updated")
        if dm_welcome is not None:
            w_cfg["dm_welcome"] = dm_welcome
            changes.append(f"• **DM Welcome**: `{'Enabled' if dm_welcome else 'Disabled'}`")
        if dm_message is not None:
            w_cfg["dm_message"] = dm_message
            changes.append(f"• **DM Message**: Updated")

        if not changes:
            curr_ch_id = w_cfg.get("channel_id", 1564605316849733725)
            curr_ch = interaction.guild.get_channel(curr_ch_id)
            ch_str = curr_ch.mention if curr_ch else f"`{curr_ch_id}`"
            status_desc = (
                f"**Current Welcome Configuration:**\n"
                f"• **Enabled**: `{'Yes' if w_cfg.get('enabled', True) else 'No'}`\n"
                f"• **Channel**: {ch_str}\n"
                f"• **DM Welcome**: `{'Yes' if w_cfg.get('dm_welcome', False) else 'No'}`\n\n"
                f"**Current Channel Greeting Message:**\n>>> {w_cfg.get('message', 'Default')}\n\n"
                f"*Provide parameters to update these settings. Supported placeholders:* `{{mention}}`, `{{user}}`, `{{server}}`, `{{member_count}}`."
            )
            embed = discord.Embed(title="⚙️ Welcome Greeting Settings", description=status_desc, color=discord.Color.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.save_config()
        embed = discord.Embed(
            title="✅ Welcome Configuration Updated",
            description="\n".join(changes),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="test_welcome", description="Preview what the welcome message looks like in the welcome channel")
    async def cmd_test_welcome(self, interaction: discord.Interaction):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        w_cfg = self.config.get("welcome", {})
        ch_id = w_cfg.get("channel_id", 1564605316849733725)
        channel = interaction.guild.get_channel(ch_id)
        if not channel:
            await interaction.response.send_message(f"❌ Welcome channel with ID `{ch_id}` could not be found.", ephemeral=True)
            return

        member = interaction.user
        guild = interaction.guild
        raw_template = w_cfg.get(
            "message",
            "Welcome to **{server}**, {mention}! We're thrilled to have you aboard Nova Station 13. Please make sure to check out <#1566600269649678467> and enjoy your stay!"
        )
        formatted_msg = raw_template.format(
            mention=member.mention,
            user=member.name,
            server=guild.name,
            member_count=guild.member_count
        )

        embed = discord.Embed(
            title=f"🚀 Welcome to {guild.name}! [TEST PREVIEW]",
            description=formatted_msg,
            color=discord.Color.from_rgb(0, 225, 255)
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Passenger Name", value=f"{member.mention} (`{member.name}`)", inline=True)
        embed.add_field(name="👥 Station Population", value=f"#{guild.member_count}", inline=True)
        embed.set_footer(text="Nova Station 13 • Circuit Verse Automated Terminal", icon_url=guild.icon.url if guild.icon else None)

        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Test welcome card successfully dispatched to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="configure_autorole", description="Configure default roles given to new members on join and staff DB sync")
    @app_commands.describe(
        action="What action to perform",
        role="The Discord role to add or remove as a default join role",
        sync_staff_db="Whether to automatically check staff database and grant staff rank on join"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="List current auto-roles", value="list"),
        app_commands.Choice(name="Add default role for all new members", value="add"),
        app_commands.Choice(name="Remove default role", value="remove"),
        app_commands.Choice(name="Toggle Staff Database Sync on join", value="toggle_db_sync")
    ])
    async def cmd_configure_autorole(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        role: discord.Role = None,
        sync_staff_db: bool = None
    ):
        if not self.check_staff_perm(interaction):
            await interaction.response.send_message("🚫 **Access Denied**", ephemeral=True)
            return

        ar_cfg = self.config.setdefault("autorole", {})
        default_roles = ar_cfg.setdefault("default_roles", [1564609709418221668])

        if action.value == "list":
            role_mentions = []
            for rid in default_roles:
                r = interaction.guild.get_role(int(rid))
                role_mentions.append(r.mention if r else f"`{rid}` (deleted)")
            roles_str = ", ".join(role_mentions) if role_mentions else "None configured"
            db_sync = ar_cfg.get("sync_staff_db_on_join", True)

            embed = discord.Embed(
                title="🛡️ Auto-Role Configuration",
                color=discord.Color.blue()
            )
            embed.add_field(name="Auto-Role Status", value="🟢 Enabled" if ar_cfg.get("enabled", True) else "🔴 Disabled", inline=True)
            embed.add_field(name="Staff DB Auto-Sync", value="🟢 Enabled" if db_sync else "🔴 Disabled", inline=True)
            embed.add_field(name="Default Join Roles", value=roles_str, inline=False)
            embed.set_footer(text="New members receive default roles immediately upon joining the server.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        elif action.value == "add":
            if not role:
                await interaction.response.send_message("❌ Please specify a role to add.", ephemeral=True)
                return
            if role.id not in default_roles:
                default_roles.append(role.id)
                self.save_config()
                await interaction.response.send_message(f"✅ Added {role.mention} to default join auto-roles.")
            else:
                await interaction.response.send_message(f"ℹ️ {role.mention} is already in the default auto-roles list.", ephemeral=True)

        elif action.value == "remove":
            if not role:
                await interaction.response.send_message("❌ Please specify a role to remove.", ephemeral=True)
                return
            if role.id in default_roles:
                default_roles.remove(role.id)
                self.save_config()
                await interaction.response.send_message(f"✅ Removed {role.mention} from default join auto-roles.")
            else:
                await interaction.response.send_message(f"ℹ️ {role.mention} is not in the default auto-roles list.", ephemeral=True)

        elif action.value == "toggle_db_sync":
            new_val = sync_staff_db if (sync_staff_db is not None) else not ar_cfg.get("sync_staff_db_on_join", True)
            ar_cfg["sync_staff_db_on_join"] = new_val
            self.save_config()
            state_str = "Enabled" if new_val else "Disabled"
            await interaction.response.send_message(f"✅ Staff database auto-sync on join is now **{state_str}**.")

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
