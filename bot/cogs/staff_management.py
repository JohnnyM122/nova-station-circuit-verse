import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
import subprocess
import mysql.connector
import re

logger = logging.getLogger("CVNovaHelper.staff_mgmt")

PERMISSION_FLAGS = {
    "BUILDMODE": 1 << 0,
    "ADMIN": 1 << 1,
    "BAN": 1 << 2,
    "EVENT": 1 << 3,
    "SERVER": 1 << 4,
    "DEBUG": 1 << 5,
    "POSSESS": 1 << 6,
    "PERMISSIONS": 1 << 7,
    "STEALTH": 1 << 8,
    "REJUVINATE": 1 << 9,
    "VAREDIT": 1 << 10,
    "SOUNDS": 1 << 11,
    "SPAWN": 1 << 12,
    "MOD": 1 << 13,
    "MENTOR": 1 << 14,
    "PROCCALL": 1 << 15,
    "VIEWRUNTIMES": 1 << 16,
    "MAINTAINER": 1 << 17,
    "DEV_TEAM": 1 << 18,
    "VIEWLOGS": 1 << 19,
    "STAFF_OBSERVER": 1 << 20,
    "MANAGEMENT": 1 << 21,
    "CHIEF_MENTOR": 1 << 22,
    "ALL": -1
}

def get_rank_color(rank_name: str) -> discord.Color:
    r = rank_name.lower()
    # Founder / Host
    if "founder" in r or "host" in r:
        return discord.Color.from_rgb(231, 76, 60) # Crimson Red
    # Game Master / Management
    if "game master" in r or "gm" in r or "management" in r:
        if "chief" in r:
            return discord.Color.from_rgb(180, 0, 255) # Electric Purple
        elif "trainee" in r:
            return discord.Color.from_rgb(130, 80, 180) # Light Purple
        return discord.Color.from_rgb(150, 50, 220) # Medium Purple
    # Administration
    if "admin" in r or "head" in r:
        if "head" in r:
            return discord.Color.from_rgb(220, 20, 60) # Deep Crimson
        elif "senior" in r:
            return discord.Color.from_rgb(255, 69, 0) # Red Orange
        elif "trial" in r or "junior" in r:
            return discord.Color.from_rgb(255, 140, 0) # Dark Orange
        return discord.Color.from_rgb(255, 100, 0) # Orange
    # Moderation
    if "mod" in r:
        if "chief" in r:
            return discord.Color.from_rgb(0, 150, 255) # Bright Blue
        elif "senior" in r:
            return discord.Color.from_rgb(30, 144, 255) # Dodger Blue
        elif "trial" in r or "junior" in r:
            return discord.Color.from_rgb(135, 206, 250) # Light Sky Blue
        return discord.Color.from_rgb(0, 191, 255) # Deep Sky Blue
    # Mentorship
    if "mentor" in r:
        if "chief" in r:
            return discord.Color.from_rgb(0, 200, 100) # Mint Teal
        return discord.Color.from_rgb(46, 204, 113) # Emerald Green
    # Development
    if "dev" in r or "maintainer" in r or "code" in r:
        if "chief" in r:
            return discord.Color.from_rgb(241, 196, 15) # Gold
        elif "maintainer" in r:
            return discord.Color.from_rgb(211, 84, 0) # Amber
        return discord.Color.from_rgb(230, 126, 34) # Yellow Orange
    # Staff Observer / Trainee
    if "observer" in r or "trainee" in r:
        return discord.Color.from_rgb(149, 165, 166) # Slate Grey
    return discord.Color.from_rgb(88, 101, 242) # Blurple

def decode_permissions(bitmask: int) -> list[str]:
    if bitmask == -1 or bitmask == 0xFFFFFFFF or bitmask == 0x7FFFFFFF:
        return ["ALL (Host / Full Access)"]
    active = []
    for name, flag in PERMISSION_FLAGS.items():
        if name == "ALL":
            continue
        if bitmask & flag:
            active.append(name)
    return active

def normalize_rank_str(s: str) -> str:
    s = str(s).lower().strip()
    s = re.sub(r"^ns13\s+", "", s)
    s = re.sub(r"\badministrator\b", "admin", s)
    s = re.sub(r"\bjunior\b", "jr", s)
    s = re.sub(r"\bgame\s*master\b", "gm", s)
    s = re.sub(r"\bmoderator\b", "mod", s)
    return s.strip()

class StaffManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.byond = bot.byond
        self.bot.check_command_permission = self.check_command_access
        self.auto_sync_task.start()
        self.player_enforcement_loop.start()

    def cog_unload(self):
        self.auto_sync_task.cancel()
        self.player_enforcement_loop.cancel()

    def get_db_connection(self):
        db_conf = self.config.get("database", {})
        return mysql.connector.connect(
            host=db_conf.get("host", "127.0.0.1"),
            user=db_conf.get("user", "nova_station_app"),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", "paradise_gamedb")
        )

    def get_staff_tier(self, member: discord.Member) -> str:
        """
        Determines the staff tier for permissions.
        Returns: 'FOUNDER', 'ADMIN', 'MODERATOR', 'MENTOR', 'OBSERVER', or 'NONE'
        """
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return "FOUNDER"

        user_role_names = {r.name.lower() for r in member.roles}
        user_role_ids = {r.id for r in member.roles}

        # Check configured role IDs first
        roles_cfg = self.config.get("roles", {})
        if user_role_ids & set(roles_cfg.get("founder", [])):
            return "FOUNDER"
        if user_role_ids & set(roles_cfg.get("admin", [])):
            return "ADMIN"
        if user_role_ids & set(roles_cfg.get("moderator", [])):
            return "MODERATOR"
        if user_role_ids & set(roles_cfg.get("chief_mentor", [])):
            return "MODERATOR"
        if user_role_ids & set(roles_cfg.get("mentor", [])):
            return "MENTOR"

        # Check by name
        founder_names = {"founder", "community founder", "cv founder", "ns13 server host"}
        if any(name in user_role_names for name in founder_names):
            return "FOUNDER"

        admin_names = {
            "head of staff", "ns13 head of staff", "head administrator", "senior administrator",
            "administrator", "ns13 server admin", "game admin", "chief game master",
            "chief developer", "ns13 server gm"
        }
        if any(name in user_role_names for name in admin_names):
            return "ADMIN"

        mod_names = {
            "chief moderator", "senior moderator", "moderator", "ns13 server mod",
            "junior moderator", "trial moderator", "chief mentor", "ns13 server staff"
        }
        if any(name in user_role_names for name in mod_names):
            return "MODERATOR"

        mentor_names = {"mentor", "ns13 server mentor"}
        if any(name in user_role_names for name in mentor_names):
            return "MENTOR"

        observer_names = {"staff observer", "ns13 staff observer", "ns13 trial staff", "game master trainee"}
        if any(name in user_role_names for name in observer_names):
            return "OBSERVER"

        return "NONE"

    def check_command_access(self, member: discord.Member, command_name: str) -> tuple[bool, str]:
        """
        Checks if a member has permission to execute command_name based on config['command_permissions'].
        Returns: (is_allowed: bool, reason: str)
        """
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return True, "Administrator"

        cmd_perms = self.config.get("command_permissions", {})
        allowed_ranks = cmd_perms.get(command_name)

        # Fallback to default tier check if command is not configured
        if allowed_ranks is None:
            tier = self.get_staff_tier(member)
            if command_name in [
                "server_restart", "server_stop", "server_start", "update_staff",
                "rank_create", "rank_delete", "rank_permission", "bind_role",
                "create_discord_staff_roles", "configure_command_permission"
            ]:
                if tier in ["FOUNDER", "ADMIN"]:
                    return True, tier
                return False, f"Requires Admin/Management permissions for `/{command_name}`"
            else:
                if tier in ["FOUNDER", "ADMIN", "MODERATOR"]:
                    return True, tier
                return False, f"Requires Staff permissions for `/{command_name}`"

        allowed_normalized = {normalize_rank_str(str(r)) for r in allowed_ranks}
        allowed_lower = {str(r).strip().lower() for r in allowed_ranks}

        # 1. Check user Discord roles
        sync_map = self.config.get("auto_role_sync", {}).get("rank_to_role", {})
        role_to_ranks = {}
        for rank, rid in sync_map.items():
            if rid:
                role_to_ranks.setdefault(rid, []).append(rank.lower())

        for role in member.roles:
            norm_role = normalize_rank_str(role.name)
            if norm_role in allowed_normalized or role.name.lower() in allowed_lower:
                return True, role.name
            if str(role.id) in allowed_lower:
                return True, role.name
            mapped = role_to_ranks.get(role.id, [])
            for mr in mapped:
                if normalize_rank_str(mr) in allowed_normalized or mr in allowed_lower:
                    return True, mr.title()

        # 2. Check user's linked database CKEY rank
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ckey FROM discord_links WHERE discord_id = %s", (str(member.id),))
            link_row = cursor.fetchone()
            if link_row:
                ckey = link_row["ckey"]
                cursor.execute("SELECT rank FROM admin WHERE ckey = %s", (ckey,))
                admin_row = cursor.fetchone()
                if admin_row and admin_row.get("rank"):
                    db_rank = admin_row["rank"].strip().lower()
                    if normalize_rank_str(db_rank) in allowed_normalized or db_rank in allowed_lower:
                        cursor.close()
                        conn.close()
                        return True, admin_row["rank"]
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error checking DB rank in check_command_access: {e}")

        allowed_str = ", ".join(allowed_ranks)
        return False, f"Your rank does not have access to `/{command_name}`. Allowed ranks: `{allowed_str}`"

    def is_staff_member(self, member: discord.Member, system="admin") -> bool:
        cmd = "tickets"
        allowed, _ = self.check_command_access(member, cmd)
        return allowed

    def is_authorized_staff(self, member: discord.Member, require_admin=False):
        tier = self.get_staff_tier(member)
        if tier == "FOUNDER":
            return True
        if tier == "ADMIN":
            return True
        if not require_admin and tier == "MODERATOR":
            return True
        return False

    def get_highest_rank_for_member(self, member: discord.Member) -> str | None:
        sync_cfg = self.config.get("auto_role_sync", {})
        rank_to_role = sync_cfg.get("rank_to_role", {})
        hierarchy = sync_cfg.get("rank_hierarchy", [
            "NS13 Server Host", "Server Host", "NS13 Head Admin", "Head Admin",
            "Head Administrator", "NS13 Chief GM", "Chief GM", "Chief Game Master",
            "NS13 Chief Developer", "Chief Developer", "NS13 Senior Admin", "Senior Admin",
            "Senior Administrator", "NS13 Admin", "Admin", "Administrator",
            "NS13 Jr Admin", "Jr Admin", "Junior Administrator", "NS13 Trial Admin",
            "Trial Admin", "Trial Administrator", "NS13 GM", "GM", "Game Master",
            "NS13 GM Trainee", "GM Trainee", "Game Master Trainee", "NS13 Chief Mod",
            "Chief Mod", "Chief Moderator", "NS13 Senior Mod", "Senior Mod",
            "Senior Moderator", "NS13 Mod", "Mod", "Moderator", "NS13 Jr Mod",
            "Jr Mod", "Junior Moderator", "NS13 Trial Mod", "Trial Mod",
            "Trial Moderator", "NS13 Chief Mentor", "Chief Mentor", "NS13 Mentor",
            "Mentor", "NS13 Server Maintainer", "Server Maintainer", "NS13 Maintainers",
            "Maintainers", "NS13 Server Developer", "Server Developer", "NS13 Developer",
            "Developer", "NS13 Staff Observer", "Staff Observer", "Community Founder", "CV Founder"
        ])

        user_role_ids = {r.id for r in member.roles}
        user_role_names = {r.name.lower(): r.id for r in member.roles}
        user_role_names_norm = {normalize_rank_str(r.name): r.id for r in member.roles}

        for rank_name in hierarchy:
            # 1. Exact role ID mapped in config
            role_id = rank_to_role.get(rank_name)
            if role_id and role_id in user_role_ids:
                return rank_name

            # 2. Normalized role name matching
            norm_rank = normalize_rank_str(rank_name)
            if norm_rank in user_role_names_norm:
                return rank_name
            if rank_name.lower() in user_role_names:
                return rank_name

        # Fallback: if member has founder role, default to NS13 Server Host
        founder_role_ids = set(self.config.get("roles", {}).get("founder", []))
        founder_role_ids.add(1564610713216098394)
        if user_role_ids & founder_role_ids:
            return "NS13 Server Host"

        return None

    # -------------------------------------------------------------
    # Command Permissions Configuration
    # -------------------------------------------------------------

    @app_commands.command(name="configure_command_permission", description="Configure which server ranks or Discord roles can access a bot command")
    @app_commands.describe(
        command="The bot command to configure",
        action="Allow (grant) or Deny (remove) access for this rank/role",
        rank_name="Rank name (e.g. Moderator, Administrator, Chief Game Master, Mentor, etc.)",
        role="Select a Discord role (optional alternative to rank_name)"
    )
    @app_commands.choices(command=[
        app_commands.Choice(name="server_restart (Reboot Server)", value="server_restart"),
        app_commands.Choice(name="server_stop (Stop Server)", value="server_stop"),
        app_commands.Choice(name="server_start (Start Server)", value="server_start"),
        app_commands.Choice(name="announce (Make In-game Announcement)", value="announce"),
        app_commands.Choice(name="ban (Issue Bans)", value="ban"),
        app_commands.Choice(name="unban (Lift Bans)", value="unban"),
        app_commands.Choice(name="tickets (Claim, Reply, Resolve Tickets)", value="tickets"),
        app_commands.Choice(name="update_staff (Update Staff In-Game & Discord)", value="update_staff"),
        app_commands.Choice(name="rank_create (Create Server Rank)", value="rank_create"),
        app_commands.Choice(name="rank_delete (Delete Server Rank)", value="rank_delete"),
        app_commands.Choice(name="rank_permission (Edit Rank Permissions)", value="rank_permission"),
        app_commands.Choice(name="rank_list (List Server Ranks)", value="rank_list"),
        app_commands.Choice(name="rank_info (View Rank Detail)", value="rank_info"),
        app_commands.Choice(name="bind_role (Bind Server Rank to Role)", value="bind_role"),
        app_commands.Choice(name="create_discord_staff_roles (Generate Staff Roles)", value="create_discord_staff_roles"),
        app_commands.Choice(name="sync_discord_roles (Sync Discord Staff Roles)", value="sync_discord_roles"),
        app_commands.Choice(name="configure_command_permission (Self-Config)", value="configure_command_permission"),
        app_commands.Choice(name="bot_shutdown (Shut Down Discord Bot)", value="bot_shutdown"),
        app_commands.Choice(name="configure_welcome (Welcome Settings)", value="configure_welcome"),
        app_commands.Choice(name="configure_autorole (Auto-Role Settings)", value="configure_autorole"),
        app_commands.Choice(name="reaction_roles (Reaction Roles Setup)", value="reaction_roles"),
        app_commands.Choice(name="configure_automod (Auto-Mod Rules)", value="configure_automod"),
        app_commands.Choice(name="clear (Clear Chat Messages)", value="clear"),
        app_commands.Choice(name="timeout (Timeout Members)", value="timeout"),
        app_commands.Choice(name="configure_voice_system (Voice Channels)", value="configure_voice_system"),
    ], action=[
        app_commands.Choice(name="Allow (Grant access)", value="allow"),
        app_commands.Choice(name="Deny (Remove access)", value="deny")
    ])
    async def cmd_configure_command_permission(
        self,
        interaction: discord.Interaction,
        command: app_commands.Choice[str],
        action: app_commands.Choice[str],
        rank_name: str = None,
        role: discord.Role = None
    ):
        allowed, reason = self.check_command_access(interaction.user, "configure_command_permission")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        if not rank_name and not role:
            await interaction.response.send_message("❌ Please provide either a `rank_name` (e.g. `Moderator`, `Administrator`) or a `role`.", ephemeral=True)
            return

        target_identifier = role.name if role else rank_name.strip()
        cmd_key = command.value

        cmd_perms = self.config.setdefault("command_permissions", {})
        current_list = cmd_perms.setdefault(cmd_key, [])

        # Case-insensitive check
        lower_target = target_identifier.lower()
        existing_match = None
        for item in current_list:
            if item.lower() == lower_target:
                existing_match = item
                break

        if action.value == "allow":
            if existing_match:
                await interaction.response.send_message(f"ℹ️ **`{target_identifier}`** already has access to `/{cmd_key}`.", ephemeral=True)
                return
            current_list.append(target_identifier)
        else:
            if not existing_match:
                await interaction.response.send_message(f"ℹ️ **`{target_identifier}`** was not in the allowed list for `/{cmd_key}`.", ephemeral=True)
                return
            current_list.remove(existing_match)

        from main import save_config
        save_config(self.config)

        embed = discord.Embed(
            title="🛡️ Command Permissions Updated",
            description=f"Action: **{action.name}**\nTarget: **`{target_identifier}`**\nCommand: `/{cmd_key}`",
            color=discord.Color.green() if action.value == "allow" else discord.Color.red()
        )
        embed.add_field(
            name="Current Allowed Ranks/Roles",
            value=", ".join(f"`{r}`" for r in current_list) if current_list else "*None (Server Admins only)*",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="list_command_permissions", description="View all configured rank permissions for bot commands")
    @app_commands.describe(command="Specific command to view (leave blank for all)")
    @app_commands.choices(command=[
        app_commands.Choice(name="All Commands", value="all"),
        app_commands.Choice(name="server_restart", value="server_restart"),
        app_commands.Choice(name="server_stop", value="server_stop"),
        app_commands.Choice(name="server_start", value="server_start"),
        app_commands.Choice(name="announce", value="announce"),
        app_commands.Choice(name="ban", value="ban"),
        app_commands.Choice(name="unban", value="unban"),
        app_commands.Choice(name="tickets", value="tickets"),
        app_commands.Choice(name="update_staff", value="update_staff"),
        app_commands.Choice(name="rank_create", value="rank_create"),
        app_commands.Choice(name="rank_delete", value="rank_delete"),
        app_commands.Choice(name="rank_permission", value="rank_permission"),
        app_commands.Choice(name="rank_list", value="rank_list"),
        app_commands.Choice(name="rank_info", value="rank_info"),
        app_commands.Choice(name="bind_role", value="bind_role"),
        app_commands.Choice(name="create_discord_staff_roles", value="create_discord_staff_roles"),
        app_commands.Choice(name="sync_discord_roles", value="sync_discord_roles"),
        app_commands.Choice(name="configure_command_permission", value="configure_command_permission"),
    ])
    async def cmd_list_command_permissions(self, interaction: discord.Interaction, command: app_commands.Choice[str] = None):
        cmd_perms = self.config.get("command_permissions", {})
        filter_cmd = command.value if command else "all"

        if filter_cmd != "all" and filter_cmd in cmd_perms:
            allowed = cmd_perms[filter_cmd]
            embed = discord.Embed(
                title=f"🛡️ Permissions for `/{filter_cmd}`",
                description="Ranks and roles allowed to execute this command:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Allowed Ranks / Roles",
                value=", ".join(f"`{r}`" for r in allowed) if allowed else "*Server Admins only*",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
            return

        embeds = []
        items = list(cmd_perms.items())
        chunk_size = 9
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i+chunk_size]
            page_num = (i // chunk_size) + 1
            total_pages = (len(items) + chunk_size - 1) // chunk_size
            embed = discord.Embed(
                title=f"🛡️ Configured Command Permissions ({page_num}/{total_pages})",
                description="Which ranks/roles can execute each vital command:",
                color=discord.Color.blue()
            )
            for cmd_name, ranks in chunk:
                rank_str = ", ".join(ranks[:4])
                if len(ranks) > 4:
                    rank_str += f" *(+{len(ranks)-4} more)*"
                embed.add_field(
                    name=f"/{cmd_name}",
                    value=f"`{rank_str}`" if rank_str else "*Server Admins only*",
                    inline=True
                )
            embeds.append(embed)

        if embeds:
            embeds[-1].set_footer(text="Use /configure_command_permission to allow or deny ranks")
            await interaction.response.send_message(embeds=embeds[:10])
        else:
            await interaction.response.send_message("No command permissions configured yet.")

    # -------------------------------------------------------------
    # Create Staff Roles on Discord & Sync Command
    # -------------------------------------------------------------

    @app_commands.command(name="create_discord_staff_roles", description="Create all Discord roles matching the in-game staff database ranks in one click")
    async def cmd_create_discord_staff_roles(self, interaction: discord.Interaction):
        allowed, reason = self.check_command_access(interaction.user, "create_discord_staff_roles")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild

        # 1. Fetch all distinct rank names directly from the database
        def fetch_db_ranks():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT DISTINCT name FROM admin_ranks ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [r["name"].strip() for r in rows if r["name"] and r["name"].strip()]

        try:
            db_rank_names = await asyncio.to_thread(fetch_db_ranks)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to query staff database: {e}")
            return

        if not db_rank_names:
            await interaction.followup.send("⚠️ No staff ranks found in the `admin_ranks` table.")
            return

        existing_roles_map = {r.name.lower(): r for r in guild.roles}

        created = []
        already_existed = []
        bound = []
        failed = []

        sync_map = self.config.setdefault("auto_role_sync", {}).setdefault("rank_to_role", {})

        for rank_name in db_rank_names:
            lower_name = rank_name.lower()
            matched_role = existing_roles_map.get(lower_name)
            if not matched_role:
                # Also check common variations like NS13 prefix
                matched_role = (
                    existing_roles_map.get(f"ns13 {lower_name}") or
                    existing_roles_map.get(f"ns13 server {lower_name}") or
                    existing_roles_map.get(f"server {lower_name}")
                )

            if not matched_role:
                color = get_rank_color(rank_name)
                try:
                    matched_role = await guild.create_role(
                        name=rank_name,
                        color=color,
                        hoist=True,
                        mentionable=True,
                        reason="Auto-created from MariaDB staff database by CV-Nova-Helper"
                    )
                    existing_roles_map[matched_role.name.lower()] = matched_role
                    created.append(matched_role.name)
                except Exception as e:
                    logger.error(f"Failed to create Discord role for '{rank_name}': {e}")
                    failed.append(f"{rank_name} ({e})")
                    continue
            else:
                already_existed.append(matched_role.name)

            # Bind to auto_role_sync map
            sync_map[rank_name] = matched_role.id
            bound.append(f"• **{rank_name}** ⇄ {matched_role.mention}")

            # Assign to role categories
            r_lower = rank_name.lower()
            if "founder" in r_lower:
                if matched_role.id not in self.config["roles"]["founder"]:
                    self.config["roles"]["founder"].append(matched_role.id)
            elif "admin" in r_lower or "head" in r_lower or "game master" in r_lower:
                if matched_role.id not in self.config["roles"]["admin"]:
                    self.config["roles"]["admin"].append(matched_role.id)
            elif "chief mentor" in r_lower:
                if matched_role.id not in self.config["roles"]["chief_mentor"]:
                    self.config["roles"]["chief_mentor"].append(matched_role.id)
            elif "mod" in r_lower:
                if matched_role.id not in self.config["roles"]["moderator"]:
                    self.config["roles"]["moderator"].append(matched_role.id)
            elif "mentor" in r_lower:
                if matched_role.id not in self.config["roles"]["mentor"]:
                    self.config["roles"]["mentor"].append(matched_role.id)

        from main import save_config
        save_config(self.config)

        # Trigger sync across all guild members
        await self.sync_all_member_roles()

        embed = discord.Embed(
            title="🛡️ Discord Staff Roles Synced from Database",
            description=f"Scanned **{len(db_rank_names)}** database ranks from MariaDB `admin_ranks`.",
            color=discord.Color.green()
        )
        if created:
            embed.add_field(name=f"✨ Created Roles ({len(created)})", value=", ".join(created), inline=False)
        if already_existed:
            embed.add_field(name=f"✅ Matched Existing Roles ({len(already_existed)})", value=", ".join(already_existed), inline=False)
        if failed:
            embed.add_field(name=f"⚠️ Failed to Create ({len(failed)})", value=", ".join(failed), inline=False)

        embed.add_field(name=f"🔗 Active Role Bindings ({len(bound)})", value="\n".join(bound[:15]) + (f"\n*(+{len(bound)-15} more)*" if len(bound) > 15 else ""), inline=False)
        embed.set_footer(text="Important: Ensure CV-Nova-Helper role is placed ABOVE staff roles in Server Settings -> Roles!")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="sync_discord_roles", description="Reconcile and sync all staff roles between Discord and the server database")
    async def cmd_sync_discord_roles(self, interaction: discord.Interaction):
        allowed, reason = self.check_command_access(interaction.user, "sync_discord_roles")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        await self.sync_all_member_roles()
        await interaction.followup.send("✅ **Two-way staff role sync complete!** All linked members and database ranks have been synchronized.")

    @app_commands.command(name="update_bot", description="Update bot settings, refresh Discord staff roles, reload game ranks, and sync commands")
    @app_commands.describe(
        shorten_roles="Automatically rename any existing long-named Discord roles to shortened names (e.g. Administrator -> Admin)",
        reload_game_admins="Tell live game server to reload admin ranks from database"
    )
    async def cmd_update_bot(self, interaction: discord.Interaction, shorten_roles: bool = True, reload_game_admins: bool = True):
        allowed, reason = self.check_command_access(interaction.user, "update_bot")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild

        results = []

        # 1. Reload config from disk
        from main import load_config
        try:
            self.bot.config = load_config()
            self.config = self.bot.config
            results.append("✅ Config reloaded from disk")
        except Exception as e:
            results.append(f"⚠️ Config reload: {e}")

        # 2. Shorten/Update existing Discord roles if requested
        renamed_roles = []
        if shorten_roles:
            rename_rules = [
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?chief\s+game\s+master$", re.I), "NS13 Chief GM"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?chief\s+gm$", re.I), "NS13 Chief GM"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?game\s+master\s+trainee$", re.I), "NS13 GM Trainee"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?gm\s+trainee$", re.I), "NS13 GM Trainee"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?game\s+master$", re.I), "NS13 GM"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?gm$", re.I), "NS13 GM"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?head\s+administrator$", re.I), "NS13 Head Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?head\s+admin$", re.I), "NS13 Head Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?senior\s+administrator$", re.I), "NS13 Senior Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?senior\s+admin$", re.I), "NS13 Senior Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?junior\s+administrator$", re.I), "NS13 Jr Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?jr\s+admin$", re.I), "NS13 Jr Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?trial\s+administrator$", re.I), "NS13 Trial Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?trial\s+admin$", re.I), "NS13 Trial Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?administrator$", re.I), "NS13 Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?admin$", re.I), "NS13 Admin"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?chief\s+moderator$", re.I), "NS13 Chief Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?chief\s+mod$", re.I), "NS13 Chief Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?senior\s+moderator$", re.I), "NS13 Senior Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?senior\s+mod$", re.I), "NS13 Senior Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?junior\s+moderator$", re.I), "NS13 Jr Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?jr\s+mod$", re.I), "NS13 Jr Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?trial\s+moderator$", re.I), "NS13 Trial Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?trial\s+mod$", re.I), "NS13 Trial Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?moderator$", re.I), "NS13 Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?mod$", re.I), "NS13 Mod"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?chief\s+mentor$", re.I), "NS13 Chief Mentor"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?mentor$", re.I), "NS13 Mentor"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?chief\s+developer$", re.I), "NS13 Chief Developer"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?server\s+developer$", re.I), "NS13 Server Developer"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?server\s+maintainer$", re.I), "NS13 Server Maintainer"),
                (re.compile(r"^(?:ns13\s+)?(?:server\s+)?staff\s+observer$", re.I), "NS13 Staff Observer"),
            ]
            for role in guild.roles:
                old_name = role.name
                new_name = old_name
                for pattern, target in rename_rules:
                    if pattern.match(old_name):
                        new_name = target
                        break
                if new_name != old_name:
                    try:
                        await role.edit(name=new_name, reason="Prefixed NS13 and shortened staff role name via /update_bot")
                        renamed_roles.append(f"`{old_name}` ➔ **`{new_name}`**")
                    except Exception as e:
                        logger.warning(f"Could not rename role {old_name}: {e}")

            if renamed_roles:
                results.append(f"✨ Renamed {len(renamed_roles)} Discord role(s):\n" + "\n".join(renamed_roles[:12]))
            else:
                results.append("ℹ️ All Discord role names are already up-to-date")

        # 3. Reload game server admins via BYOND Topic
        if reload_game_admins:
            byond_res = await self.byond.reload_admins(sender=interaction.user.display_name)
            if byond_res:
                results.append("✅ Live SS13 game server reloaded admin ranks from MariaDB")
            else:
                results.append("⚠️ Could not contact BYOND game server (server might be rebooting)")

        # 4. Sync Discord roles with database
        try:
            await self.sync_all_member_roles()
            results.append("✅ Member roles reconciled with MariaDB staff database")
        except Exception as e:
            results.append(f"⚠️ Member role sync: {e}")

        # 5. Re-sync slash commands
        try:
            guild_obj = discord.Object(id=guild.id)
            self.bot.tree.copy_global_to(guild=guild_obj)
            synced = await self.bot.tree.sync(guild=guild_obj)
            results.append(f"✅ Synced {len(synced)} slash commands directly to Discord")
        except Exception as e:
            results.append(f"⚠️ Slash command sync: {e}")

        embed = discord.Embed(
            title="🔄 CV-Nova-Helper Update Complete",
            description="\n\n".join(results),
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Triggered by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    async def _execute_bot_shutdown(self, interaction: discord.Interaction, reason: str = "Staff requested shutdown"):
        allowed, rank_or_err = self.check_command_access(interaction.user, "bot_shutdown")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {rank_or_err}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛑 CV-Nova-Helper Shutting Down",
            description=f"Bot shutdown initiated by {interaction.user.mention}.\n**Reason:** `{reason}`\n\nThe Discord bot service (`cv-nova-helper.service`) is now stopping and will remain offline until manually restarted on the host.",
            color=discord.Color.red()
        )
        embed.set_footer(text="To restart, run: sudo systemctl start cv-nova-helper.service on the host")
        await interaction.response.send_message(embed=embed)

        admin_logs_id = self.config["channels"].get("admin_logs")
        if admin_logs_id and admin_logs_id != interaction.channel_id:
            ch = self.bot.get_channel(admin_logs_id)
            if ch:
                try:
                    await ch.send(embed=embed)
                except Exception:
                    pass

        async def execute_shutdown():
            await asyncio.sleep(1.5)
            logger.warning(f"Bot shutdown initiated by {interaction.user} (Reason: {reason})")
            try:
                subprocess.Popen(["sudo", "systemctl", "stop", "cv-nova-helper.service"])
            except Exception as e:
                logger.error(f"Error stopping cv-nova-helper service: {e}")
            await self.bot.close()
            sys.exit(0)

        asyncio.create_task(execute_shutdown())

    @app_commands.command(name="bot_shutdown", description="Safely shut down the CV-Nova-Helper Discord bot service")
    @app_commands.describe(reason="Reason for shutting down the bot (optional)")
    async def cmd_bot_shutdown(self, interaction: discord.Interaction, reason: str = "Staff requested shutdown"):
        await self._execute_bot_shutdown(interaction, reason)

    @app_commands.command(name="shutdown_bot", description="Safely shut down the CV-Nova-Helper Discord bot service (alias)")
    @app_commands.describe(reason="Reason for shutting down the bot (optional)")
    async def cmd_shutdown_bot(self, interaction: discord.Interaction, reason: str = "Staff requested shutdown"):
        await self._execute_bot_shutdown(interaction, reason)

    # -------------------------------------------------------------
    # Two-Way Role Sync (Discord <-> MariaDB)
    # -------------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        sync_cfg = self.config.get("auto_role_sync", {})
        if not sync_cfg.get("enabled", True) or not sync_cfg.get("bidirectional", True):
            return

        if before.roles == after.roles:
            return

        def get_ckey():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ckey FROM discord_links WHERE discord_id = %s", (str(after.id),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row["ckey"] if row else None

        ckey = await asyncio.to_thread(get_ckey)
        if not ckey:
            return

        highest_rank = self.get_highest_rank_for_member(after)

        def update_db():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            saved_name = None
            if highest_rank:
                cursor.execute("SELECT id, name FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (highest_rank.strip(),))
                rank_row = cursor.fetchone()
                if not rank_row:
                    cursor.execute("SELECT id, name FROM admin_ranks")
                    for r in cursor.fetchall():
                        if normalize_rank_str(r["name"]) == normalize_rank_str(highest_rank):
                            rank_row = r
                            break
                if rank_row:
                    saved_name = rank_row["name"]
                    cursor.execute("""
                        INSERT INTO admin (ckey, display_rank, permissions_rank, extra_permissions, removed_permissions)
                        VALUES (%s, %s, %s, 0, 0)
                        ON DUPLICATE KEY UPDATE display_rank = %s, permissions_rank = %s
                    """, (ckey, rank_row["name"], rank_row["id"], rank_row["name"], rank_row["id"]))
                    conn.commit()
            else:
                cursor.execute("DELETE FROM admin WHERE LOWER(ckey) = LOWER(%s)", (ckey,))
                conn.commit()
            cursor.close()
            conn.close()
            return saved_name

        saved_rank = await asyncio.to_thread(update_db)
        await self.byond.reload_admins(sender=f"Discord RoleSync ({after.name})")

        # Sync Circuit Member and NS13 Player status to database
        has_circuit = 1 if any(r.id == 1564609709418221668 or r.name.lower() == "circuit member" for r in after.roles) else 0
        has_player = 1 if any(r.id == 1566636003626713178 or r.name.lower() == "ns13 player" for r in after.roles) else 0

        # Check NS13 WL OR role change
        before_wl = any(r.name == "NS13 WL OR" for r in before.roles)
        after_wl = any(r.name == "NS13 WL OR" for r in after.roles)

        def update_member_access():
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE discord_links
                SET has_circuit_member = %s, has_ns13_player = %s
                WHERE discord_id = %s
            """, (has_circuit, has_player, str(after.id)))

            if before_wl != after_wl:
                wl_val = 1 if after_wl else 0
                cursor.execute("""
                    INSERT INTO player_access_flags (ckey, head_job_whitelist, job_playtime_override, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE head_job_whitelist = %s, job_playtime_override = %s, updated_by = %s, updated_at = NOW()
                """, (ckey, wl_val, wl_val, f"Discord Role ({after.name})", wl_val, wl_val, f"Discord Role ({after.name})"))

            conn.commit()
            cursor.close()
            conn.close()

        await asyncio.to_thread(update_member_access)

        if before_wl != after_wl:
            await self.byond.reload_access_flags(sender=f"Discord RoleSync ({after.name})")

        admin_logs_id = self.config["channels"].get("admin_logs")
        if admin_logs_id:
            ch = self.bot.get_channel(admin_logs_id)
            if ch:
                embed = discord.Embed(
                    title="🔄 Two-Way Staff Role Sync",
                    description=f"Discord role change for {after.mention} synced to game database.",
                    color=discord.Color.teal()
                )
                embed.add_field(name="CKey", value=f"`{ckey}`", inline=True)
                embed.add_field(name="Assigned Rank", value=saved_rank if saved_rank else (highest_rank if highest_rank else "*Removed (Non-staff)*"), inline=True)
                if before_wl != after_wl:
                    embed.add_field(name="NS13 WL OR (Overrides)", value="**ENABLED**" if after_wl else "DISABLED", inline=True)
                await ch.send(embed=embed)

    @tasks.loop(seconds=60.0)
    async def auto_sync_task(self):
        sync_cfg = self.config.get("auto_role_sync", {})
        if not sync_cfg.get("enabled", True):
            return
        try:
            await self.sync_all_member_roles()
        except Exception as e:
            logger.debug(f"Auto role sync error: {e}")

    async def sync_all_member_roles(self):
        sync_cfg = self.config.get("auto_role_sync", {})
        rank_to_role = sync_cfg.get("rank_to_role", {})
        bidirectional = sync_cfg.get("bidirectional", True)

        def fetch_all_data():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT discord_id, ckey FROM discord_links")
            links = cursor.fetchall()

            cursor.execute("""
                SELECT a.ckey, IFNULL(a.display_rank, r.name) AS rank_name
                FROM admin a
                LEFT JOIN admin_ranks r ON a.permissions_rank = r.id
            """)
            db_admins = {row["ckey"].lower(): row["rank_name"] for row in cursor.fetchall()}

            cursor.execute("SELECT ckey, head_job_whitelist, job_playtime_override FROM player_access_flags")
            db_access = {row["ckey"].lower(): (row["head_job_whitelist"], row["job_playtime_override"]) for row in cursor.fetchall()}

            cursor.close()
            conn.close()
            return links, db_admins, db_access

        links, db_admins, db_access = await asyncio.to_thread(fetch_all_data)

        # Protect founder and badge roles from being wiped during sync
        protected_roles = set(self.config.get("roles", {}).get("founder", []))
        protected_roles.add(1564610713216098394)  # Founder
        protected_roles.add(1566480612121124874)  # NS13 Server Staff
        protected_roles.add(1566482340820029531)  # NS13 Head Of Staff
        protected_roles.add(1566407352775610540)  # Community Ambassador
        protected_roles.add(1566625061467717752)  # Chief Community Officer
        protected_roles.add(1564609709418221668)  # Circuit Member
        protected_roles.add(1564609100502016100)  # Legacy Member
        protected_roles.add(1564612303100448881)  # Zero-Day Circle
        protected_roles.add(1566542581477933126)  # Circuit VIP Member

        managed_role_ids = {rid for rid in rank_to_role.values() if rid and rid not in protected_roles}

        # Track member updates for discord_links
        member_updates = []

        for guild in self.bot.guilds:
            # Ensure NS13 WL OR role exists in guild
            wl_or_role = discord.utils.get(guild.roles, name="NS13 WL OR")
            if not wl_or_role:
                try:
                    wl_or_role = await guild.create_role(
                        name="NS13 WL OR",
                        color=discord.Color.from_rgb(0, 200, 255),
                        reason="Automatic creation of Whitelist & Playtime Override role"
                    )
                except Exception as e:
                    logger.debug(f"Could not create NS13 WL OR role: {e}")

            for link in links:
                d_id = int(link["discord_id"])
                ckey = link["ckey"].lower()
                member = guild.get_member(d_id)
                if not member:
                    continue

                current_roles = set(member.roles)

                # 1. Update Circuit Member and NS13 Player flags
                has_circuit = 1 if any(r.id == 1564609709418221668 or r.name.lower() == "circuit member" for r in current_roles) else 0
                has_player = 1 if any(r.id == 1566636003626713178 or r.name.lower() == "ns13 player" for r in current_roles) else 0
                member_updates.append((has_circuit, has_player, str(member.id)))

                # 2. Two-way sync of NS13 WL OR <-> player_access_flags
                if wl_or_role:
                    has_wl_discord = wl_or_role in current_roles
                    db_flags = db_access.get(ckey, (0, 0))
                    is_wl_db = (db_flags[0] == 1 and db_flags[1] == 1)

                    if has_wl_discord and not is_wl_db:
                        # Role in Discord -> set DB flags
                        def grant_db_wl():
                            conn = self.get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO player_access_flags (ckey, head_job_whitelist, job_playtime_override, updated_by, updated_at)
                                VALUES (%s, 1, 1, 'Discord Role (NS13 WL OR)', NOW())
                                ON DUPLICATE KEY UPDATE head_job_whitelist = 1, job_playtime_override = 1, updated_by = 'Discord Role (NS13 WL OR)', updated_at = NOW()
                            """, (ckey,))
                            conn.commit()
                            cursor.close()
                            conn.close()
                        await asyncio.to_thread(grant_db_wl)
                        await self.byond.reload_access_flags(sender=f"Discord RoleSync ({member.name})")
                        db_access[ckey] = (1, 1)
                        logger.info(f"Synced NS13 WL OR from Discord to server for ckey '{ckey}'")

                    elif is_wl_db and not has_wl_discord:
                        # Granted by in-game admin -> grant role in Discord (Vice-Versa)
                        try:
                            await member.add_roles(wl_or_role, reason="Two-way sync: in-game admin granted Head Whitelist & Playtime Override")
                            logger.info(f"Granted NS13 WL OR role to {member.name} (ckey '{ckey}') synced from in-game database")
                        except discord.Forbidden:
                            logger.warning(f"Failed to add NS13 WL OR to {member.name} due to hierarchy.")

                    elif not is_wl_db and has_wl_discord:
                        # Revoked in game -> remove role in Discord
                        try:
                            await member.remove_roles(wl_or_role, reason="Two-way sync: in-game admin revoked Head Whitelist & Playtime Override")
                            logger.info(f"Removed NS13 WL OR from {member.name} (ckey '{ckey}') synced from in-game database")
                        except discord.Forbidden:
                            logger.warning(f"Failed to remove NS13 WL OR from {member.name}.")

                # 3. Staff Rank Sync
                db_rank = db_admins.get(ckey)
                if db_rank:
                    target_role_id = rank_to_role.get(db_rank)
                    target_role = guild.get_role(target_role_id) if target_role_id else None
                    if not target_role:
                        target_role = discord.utils.get(guild.roles, name=db_rank)
                        if not target_role:
                            for r in guild.roles:
                                if normalize_rank_str(r.name) == normalize_rank_str(db_rank):
                                    target_role = r
                                    break
                        if target_role:
                            rank_to_role[db_rank] = target_role.id
                            if target_role.id not in protected_roles:
                                managed_role_ids.add(target_role.id)

                    to_remove = [r for r in current_roles if r.id in managed_role_ids and (not target_role or r.id != target_role.id)]
                    to_add = [target_role] if (target_role and target_role not in current_roles) else []

                    try:
                        if to_remove:
                            await member.remove_roles(*to_remove, reason="Staff sync: rank updated in database")
                        if to_add:
                            await member.add_roles(*to_add, reason=f"Staff sync: DB rank {db_rank}")
                    except discord.Forbidden:
                        logger.warning(f"Missing permissions to manage roles for {member.name}. Check role hierarchy.")
                elif bidirectional:
                    highest_discord_rank = self.get_highest_rank_for_member(member)
                    if highest_discord_rank:
                        def set_db_rank():
                            conn = self.get_db_connection()
                            cursor = conn.cursor(dictionary=True)
                            cursor.execute("SELECT id, name FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (highest_discord_rank.strip(),))
                            rank_row = cursor.fetchone()
                            if not rank_row:
                                cursor.execute("SELECT id, name FROM admin_ranks")
                                for r in cursor.fetchall():
                                    if normalize_rank_str(r["name"]) == normalize_rank_str(highest_discord_rank):
                                        rank_row = r
                                        break
                            if rank_row:
                                cursor.execute("""
                                    INSERT INTO admin (ckey, display_rank, permissions_rank, extra_permissions, removed_permissions)
                                    VALUES (%s, %s, %s, 0, 0)
                                    ON DUPLICATE KEY UPDATE display_rank = %s, permissions_rank = %s
                                """, (ckey, rank_row["name"], rank_row["id"], rank_row["name"], rank_row["id"]))
                                conn.commit()
                            cursor.close()
                            conn.close()
                        await asyncio.to_thread(set_db_rank)
                        await self.byond.reload_admins(sender="Discord Auto-Sync")

        # Save all member verification flag updates
        if member_updates:
            def save_member_flags():
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.executemany("""
                    UPDATE discord_links
                    SET has_circuit_member = %s, has_ns13_player = %s
                    WHERE discord_id = %s
                """, member_updates)
                conn.commit()
                cursor.close()
                conn.close()
            await asyncio.to_thread(save_member_flags)

    # -------------------------------------------------------------
    # Active Player Enforcement Task (Circuit Member & NS13 Player 60 min)
    # -------------------------------------------------------------

    @tasks.loop(seconds=30.0)
    async def player_enforcement_loop(self):
        """
        Monitors connected players in real time:
        - Requires Circuit Member role to be in server.
        - Requires NS13 Player role within 60 minutes of joining or kicks player.
        """
        # Discord membership requirement toggle check
        if not self.config.get("discord_requirement_enabled", False):
            return

        try:
            players = await self.byond.get_players()
            if not players or not isinstance(players, list):
                return

            def fetch_verification_data():
                conn = self.get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT ckey, has_circuit_member, has_ns13_player,
                           TIMESTAMPDIFF(MINUTE, IFNULL(first_game_join, NOW()), NOW()) AS minutes_since_join
                    FROM discord_links
                """)
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                return {r["ckey"].lower(): r for r in rows}

            db_links = await asyncio.to_thread(fetch_verification_data)

            for player_key in players:
                if not player_key or not isinstance(player_key, str):
                    continue
                ckey_clean = player_key.strip().lower()
                if ckey_clean in ("chad98",):
                    continue

                link = db_links.get(ckey_clean)
                admin_logs_id = self.config["channels"].get("admin_logs")

                if not link or not link.get("has_circuit_member"):
                    # Missing Circuit Member role or not linked
                    await self.byond.kick_player(
                        ckey_clean,
                        reason="Access Denied: Circuit Member role required. Join our Discord at https://discord.com/invite/KmZgUPET9C and use /link_ckey.",
                        sender="CV-Nova-Helper"
                    )
                    logger.info(f"Kicked {ckey_clean}: Not linked or missing Circuit Member role.")
                    if admin_logs_id:
                        ch = self.bot.get_channel(admin_logs_id)
                        if ch:
                            embed = discord.Embed(
                                title="🚫 Player Kicked (Discord Verification Required)",
                                description=f"Player `{ckey_clean}` was kicked for missing **Circuit Member** role in Discord.\n**Discord Invite:** https://discord.com/invite/KmZgUPET9C",
                                color=discord.Color.red()
                            )
                            await ch.send(embed=embed)

                elif not link.get("has_ns13_player"):
                    min_since = link.get("minutes_since_join", 0)
                    if min_since is not None and min_since >= 60:
                        await self.byond.kick_player(
                            ckey_clean,
                            reason="Access Denied: You have exceeded 60 minutes without the NS13 Player role. Claim it in #welcome-channel at https://discord.com/invite/KmZgUPET9C to reconnect.",
                            sender="CV-Nova-Helper"
                        )
                        logger.info(f"Kicked {ckey_clean}: Exceeded 60 minutes without NS13 Player role.")
                        if admin_logs_id:
                            ch = self.bot.get_channel(admin_logs_id)
                            if ch:
                                embed = discord.Embed(
                                    title="⏱️ Player Kicked (NS13 Player Role Expired)",
                                    description=f"Player `{ckey_clean}` was kicked for exceeding 60 minutes without the **NS13 Player** role.\n**Discord Invite:** https://discord.com/invite/KmZgUPET9C",
                                    color=discord.Color.orange()
                                )
                                await ch.send(embed=embed)

        except Exception as e:
            logger.debug(f"Player enforcement loop error: {e}")

    def is_server_host(self, member: discord.Member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        if member.guild.owner_id == member.id or member.guild_permissions.administrator:
            return True
        host_role_id = 1566628233976352771
        for r in member.roles:
            if r.id == host_role_id or r.name.lower() in ("ns13 server host", "server host"):
                return True
        return False

    @commands.hybrid_command(
        name="toggle_discord_requirement",
        aliases=["discord_requirement", "toggle_verification"],
        description="Toggle whether players must be in the Circuit Verse Discord to join and play"
    )
    @app_commands.describe(enabled="Optionally set enabled (True) or disabled (False). Leave blank to flip current state.")
    async def cmd_toggle_discord_requirement(self, ctx: commands.Context, enabled: bool = None):
        author = ctx.author
        if not isinstance(author, discord.Member) and ctx.guild:
            author = ctx.guild.get_member(author.id) or author

        if not self.is_server_host(author):
            await ctx.send("🚫 **Access Denied**: This command is strictly restricted to members with the **NS13 Server Host** role.", ephemeral=True)
            return

        current_state = self.config.get("discord_requirement_enabled", False)
        new_state = (not current_state) if enabled is None else enabled
        self.config["discord_requirement_enabled"] = new_state
        from main import save_config
        save_config(self.config)

        if new_state:
            status_text = "🟢 **ENABLED**"
            desc = (
                "The Discord membership requirement is now **ACTIVE**.\n\n"
                "• Players must join the Circuit Verse Discord and have the required role to play on Nova Station 13.\n"
                "• Unlinked/unverified players connecting to the server will be automatically redirected to Discord."
            )
            color = discord.Color.green()
        else:
            status_text = "🔴 **DISABLED**"
            desc = (
                "The Discord membership requirement is now **LIFTED / DEACTIVATED**.\n\n"
                "• **Anyone can now connect and play on Nova Station 13 freely without needing to join Discord or verify an account.**\n"
                "• Use `/toggle_discord_requirement` (or `!toggle_discord_requirement`) whenever you wish to re-enable it."
            )
            color = discord.Color.orange()

        embed = discord.Embed(
            title=f"🔒 Discord Requirement Status: {status_text}",
            description=desc,
            color=color
        )
        embed.set_footer(text=f"Action executed by {author.display_name}")
        await ctx.send(embed=embed)

        admin_logs_id = self.config.get("channels", {}).get("admin_logs")
        if admin_logs_id:
            ch = self.bot.get_channel(admin_logs_id)
            if ch:
                log_embed = discord.Embed(
                    title="🛡️ Discord Verification Requirement Toggled",
                    description=f"**State:** {status_text}\n**Action by:** {author.mention} (`{author.display_name}`)",
                    color=color
                )
                await ch.send(embed=log_embed)

    @app_commands.command(name="link_ckey", description="Link a BYOND ckey to a Discord account for automatic two-way staff roles")
    @app_commands.describe(ckey="Your BYOND ckey", member="Discord member (Staff only: defaults to yourself)")
    async def cmd_link_ckey(self, interaction: discord.Interaction, ckey: str, member: discord.Member = None):
        target_member = member if (member and self.is_authorized_staff(interaction.user)) else interaction.user
        clean_ckey = ckey.strip().lower()

        def save_link():
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO discord_links (discord_id, ckey, linked_at)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE ckey = %s, linked_at = NOW()
            """, (str(target_member.id), clean_ckey, clean_ckey))
            conn.commit()
            cursor.close()
            conn.close()

        await asyncio.to_thread(save_link)
        await self.sync_all_member_roles()

        embed = discord.Embed(
            title="🔗 CKey Linked (Two-Way Sync Active)",
            description=f"Linked **{target_member.mention}** to BYOND ckey: `{clean_ckey}`.\nRoles and in-game database ranks will stay synchronized automatically.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="grant_wl_or", description="Grant Head Job Whitelist & Playtime Override (NS13 WL OR) to a player")
    @app_commands.describe(target="The Discord member or BYOND ckey to grant whitelist & playtime override")
    async def cmd_grant_wl_or(self, interaction: discord.Interaction, target: str):
        allowed, reason = self.check_command_access(interaction.user, "grant_wl_or")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild
        clean_target = target.strip()
        matched_member = None
        clean_ckey = clean_target.lower()

        # Check if mention or ID
        if clean_target.startswith("<@") and clean_target.endswith(">"):
            m_id = int(re.sub(r'\D', '', clean_target))
            matched_member = guild.get_member(m_id)
        elif clean_target.isdigit():
            matched_member = guild.get_member(int(clean_target))
        else:
            matched_member = discord.utils.get(guild.members, name=clean_target)

        def resolve_and_grant():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            resolved_ckey = clean_ckey
            resolved_discord_id = None

            if matched_member:
                cursor.execute("SELECT ckey FROM discord_links WHERE discord_id = %s", (str(matched_member.id),))
                row = cursor.fetchone()
                if row:
                    resolved_ckey = row["ckey"]
                    resolved_discord_id = str(matched_member.id)
            else:
                cursor.execute("SELECT discord_id FROM discord_links WHERE LOWER(ckey) = %s", (clean_ckey,))
                row = cursor.fetchone()
                if row:
                    resolved_discord_id = row["discord_id"]

            cursor.execute("""
                INSERT INTO player_access_flags (ckey, head_job_whitelist, job_playtime_override, updated_by, updated_at)
                VALUES (%s, 1, 1, %s, NOW())
                ON DUPLICATE KEY UPDATE head_job_whitelist = 1, job_playtime_override = 1, updated_by = %s, updated_at = NOW()
            """, (resolved_ckey, f"Staff ({interaction.user.name})", f"Staff ({interaction.user.name})"))
            conn.commit()
            cursor.close()
            conn.close()
            return resolved_ckey, resolved_discord_id

        actual_ckey, actual_d_id = await asyncio.to_thread(resolve_and_grant)

        # Reload flags in game
        await self.byond.reload_access_flags(sender=f"Discord Staff ({interaction.user.name})")

        # Add NS13 WL OR role to Discord member if found
        target_mem = matched_member or (guild.get_member(int(actual_d_id)) if actual_d_id else None)
        role_added = False
        if target_mem:
            wl_role = discord.utils.get(guild.roles, name="NS13 WL OR")
            if not wl_role:
                wl_role = await guild.create_role(name="NS13 WL OR", color=discord.Color.from_rgb(0, 200, 255))
            if wl_role:
                try:
                    await target_mem.add_roles(wl_role, reason=f"Granted by {interaction.user.name} via /grant_wl_or")
                    role_added = True
                except discord.Forbidden:
                    pass

        embed = discord.Embed(
            title="✨ Whitelist & Playtime Override Granted",
            description=f"Successfully granted Head Job Whitelist & Playtime Override to `{actual_ckey}`.",
            color=discord.Color.teal()
        )
        embed.add_field(name="BYOND CKey", value=f"`{actual_ckey}`", inline=True)
        embed.add_field(name="Discord Role", value=f"`NS13 WL OR` ({'Assigned' if role_added else 'Not linked/assigned'})", inline=True)
        embed.add_field(name="Server Effect", value="Overrides all job playtime restrictions, account age locks, and head-of-staff whitelist requirements.", inline=False)
        embed.set_footer(text=f"Granted by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="revoke_wl_or", description="Revoke Head Job Whitelist & Playtime Override (NS13 WL OR) from a player")
    @app_commands.describe(target="The Discord member or BYOND ckey to revoke whitelist & playtime override")
    async def cmd_revoke_wl_or(self, interaction: discord.Interaction, target: str):
        allowed, reason = self.check_command_access(interaction.user, "revoke_wl_or")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild
        clean_target = target.strip()
        matched_member = None
        clean_ckey = clean_target.lower()

        if clean_target.startswith("<@") and clean_target.endswith(">"):
            m_id = int(re.sub(r'\D', '', clean_target))
            matched_member = guild.get_member(m_id)
        elif clean_target.isdigit():
            matched_member = guild.get_member(int(clean_target))
        else:
            matched_member = discord.utils.get(guild.members, name=clean_target)

        def resolve_and_revoke():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            resolved_ckey = clean_ckey
            resolved_discord_id = None

            if matched_member:
                cursor.execute("SELECT ckey FROM discord_links WHERE discord_id = %s", (str(matched_member.id),))
                row = cursor.fetchone()
                if row:
                    resolved_ckey = row["ckey"]
                    resolved_discord_id = str(matched_member.id)
            else:
                cursor.execute("SELECT discord_id FROM discord_links WHERE LOWER(ckey) = %s", (clean_ckey,))
                row = cursor.fetchone()
                if row:
                    resolved_discord_id = row["discord_id"]

            cursor.execute("""
                UPDATE player_access_flags
                SET head_job_whitelist = 0, job_playtime_override = 0, updated_by = %s, updated_at = NOW()
                WHERE LOWER(ckey) = %s
            """, (f"Staff Revoke ({interaction.user.name})", resolved_ckey))
            conn.commit()
            cursor.close()
            conn.close()
            return resolved_ckey, resolved_discord_id

        actual_ckey, actual_d_id = await asyncio.to_thread(resolve_and_revoke)
        await self.byond.reload_access_flags(sender=f"Discord Staff ({interaction.user.name})")

        target_mem = matched_member or (guild.get_member(int(actual_d_id)) if actual_d_id else None)
        role_removed = False
        if target_mem:
            wl_role = discord.utils.get(guild.roles, name="NS13 WL OR")
            if wl_role and wl_role in target_mem.roles:
                try:
                    await target_mem.remove_roles(wl_role, reason=f"Revoked by {interaction.user.name} via /revoke_wl_or")
                    role_removed = True
                except discord.Forbidden:
                    pass

        embed = discord.Embed(
            title="🛡️ Whitelist & Playtime Override Revoked",
            description=f"Successfully revoked Head Job Whitelist & Playtime Override from `{actual_ckey}`.",
            color=discord.Color.red()
        )
        embed.add_field(name="BYOND CKey", value=f"`{actual_ckey}`", inline=True)
        embed.add_field(name="Discord Role", value=f"`NS13 WL OR` ({'Removed' if role_removed else 'None'})", inline=True)
        embed.set_footer(text=f"Revoked by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="check_player_access", description="Check a player's Discord verification, roles, and override status")
    @app_commands.describe(target="The Discord member or BYOND ckey to inspect")
    async def cmd_check_player_access(self, interaction: discord.Interaction, target: str):
        await interaction.response.defer()
        guild = interaction.guild
        clean_target = target.strip()
        matched_member = None
        clean_ckey = clean_target.lower()

        if clean_target.startswith("<@") and clean_target.endswith(">"):
            m_id = int(re.sub(r'\D', '', clean_target))
            matched_member = guild.get_member(m_id)
        elif clean_target.isdigit():
            matched_member = guild.get_member(int(clean_target))
        else:
            matched_member = discord.utils.get(guild.members, name=clean_target)

        def fetch_status():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            res_ckey = clean_ckey
            res_did = None

            if matched_member:
                cursor.execute("SELECT ckey, has_circuit_member, has_ns13_player, first_game_join, last_game_join, TIMESTAMPDIFF(MINUTE, first_game_join, NOW()) AS elapsed_minutes FROM discord_links WHERE discord_id = %s", (str(matched_member.id),))
                link_row = cursor.fetchone()
                if link_row:
                    res_ckey = link_row["ckey"]
                    res_did = str(matched_member.id)
            else:
                cursor.execute("SELECT discord_id, has_circuit_member, has_ns13_player, first_game_join, last_game_join, TIMESTAMPDIFF(MINUTE, first_game_join, NOW()) AS elapsed_minutes FROM discord_links WHERE LOWER(ckey) = %s", (clean_ckey,))
                link_row = cursor.fetchone()
                if link_row:
                    res_did = link_row["discord_id"]

            cursor.execute("SELECT head_job_whitelist, job_playtime_override, updated_by, updated_at FROM player_access_flags WHERE LOWER(ckey) = %s", (res_ckey,))
            flag_row = cursor.fetchone()

            cursor.close()
            conn.close()
            return res_ckey, res_did, link_row, flag_row

        ckey_found, did_found, link_data, flag_data = await asyncio.to_thread(fetch_status)
        discord_mem = matched_member or (guild.get_member(int(did_found)) if did_found else None)

        embed = discord.Embed(
            title="🔍 Player Access & Verification Status",
            color=discord.Color.blue()
        )
        embed.add_field(name="BYOND CKey", value=f"`{ckey_found}`", inline=True)
        embed.add_field(name="Discord Account", value=discord_mem.mention if discord_mem else (f"`{did_found}`" if did_found else "*Not linked*"), inline=True)

        if link_data:
            c_mem = "✅ Granted (Can join server)" if link_data.get("has_circuit_member") else "❌ Missing (Blocked from server)"
            p_mem = "✅ Granted" if link_data.get("has_ns13_player") else f"⚠️ Missing ({link_data.get('elapsed_minutes', 0)}/60 min elapsed)"
            embed.add_field(name="Circuit Member Role", value=c_mem, inline=False)
            embed.add_field(name="NS13 Player Role", value=p_mem, inline=False)
            embed.add_field(name="First Join", value=str(link_data.get("first_game_join")) if link_data.get("first_game_join") else "Never joined", inline=True)
            embed.add_field(name="Last Join", value=str(link_data.get("last_game_join")) if link_data.get("last_game_join") else "N/A", inline=True)
        else:
            embed.add_field(name="Verification", value="❌ **Account is NOT linked in database.** Player cannot connect to the server.", inline=False)

        if flag_data and flag_data.get("head_job_whitelist") and flag_data.get("job_playtime_override"):
            embed.add_field(name="NS13 WL OR (Admin Overrides)", value=f"✅ **ACTIVE**\nUpdated by `{flag_data.get('updated_by')}` at `{flag_data.get('updated_at')}`", inline=False)
        else:
            embed.add_field(name="NS13 WL OR (Admin Overrides)", value="❌ **INACTIVE** (Standard player locks apply)", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="bind_role", description="Bind an in-game server rank to a Discord role for two-way auto-sync")
    @app_commands.describe(
        rank="In-game database rank name (e.g. Community Founder, Head of Staff, Game Admin, Moderator)",
        role="The Discord role to associate with this rank"
    )
    async def cmd_bind_role(self, interaction: discord.Interaction, rank: str, role: discord.Role):
        allowed, reason = self.check_command_access(interaction.user, "bind_role")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        sync_map = self.config.setdefault("auto_role_sync", {}).setdefault("rank_to_role", {})
        clean_rank = rank.strip()
        sync_map[clean_rank] = role.id

        lower_r = clean_rank.lower()
        if "founder" in lower_r:
            if role.id not in self.config["roles"]["founder"]:
                self.config["roles"]["founder"].append(role.id)
            if role.id not in self.config["roles"]["admin"]:
                self.config["roles"]["admin"].append(role.id)
        elif "admin" in lower_r or "head" in lower_r or "host" in lower_r:
            if role.id not in self.config["roles"]["admin"]:
                self.config["roles"]["admin"].append(role.id)
        elif "mod" in lower_r:
            if role.id not in self.config["roles"]["moderator"]:
                self.config["roles"]["moderator"].append(role.id)
        elif "chief" in lower_r:
            if role.id not in self.config["roles"]["chief_mentor"]:
                self.config["roles"]["chief_mentor"].append(role.id)
        elif "mentor" in lower_r:
            if role.id not in self.config["roles"]["mentor"]:
                self.config["roles"]["mentor"].append(role.id)

        from main import save_config
        save_config(self.config)

        await self.sync_all_member_roles()

        embed = discord.Embed(
            title="🔗 Role Binding Saved",
            description=f"In-game rank **`{clean_rank}`** is now bound to Discord role {role.mention}.\nTwo-way role sync is actively updated.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="list_role_bindings", description="View all active bindings between server ranks and Discord roles")
    async def cmd_list_role_bindings(self, interaction: discord.Interaction):
        try:
            sync_map = self.config.get("auto_role_sync", {}).get("rank_to_role", {})
            items = list(sync_map.items())
            if not items:
                await interaction.response.send_message("No role bindings configured yet.", ephemeral=True)
                return

            embeds = []
            chunk_size = 20
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                page_num = (i // chunk_size) + 1
                total_pages = (len(items) + chunk_size - 1) // chunk_size
                embed = discord.Embed(
                    title=f"🛡️ Server Rank to Discord Role Bindings ({page_num}/{total_pages})",
                    description="Active mappings used for two-way role synchronization:",
                    color=discord.Color.blue()
                )
                for rank_name, role_id in chunk:
                    role = interaction.guild.get_role(role_id) if role_id else None
                    role_str = role.mention if role else (f"ID: `{role_id}` (Not Found)" if role_id else "*Unassigned*")
                    embed.add_field(name=rank_name, value=role_str, inline=True)
                embeds.append(embed)

            await interaction.response.send_message(embeds=embeds[:10])
        except Exception as e:
            logger.error(f"Error in list_role_bindings: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # -------------------------------------------------------------
    # Rank & Permission Management Commands
    # -------------------------------------------------------------

    @app_commands.command(name="rank_list", description="List all server ranks and their permission flags")
    async def cmd_rank_list(self, interaction: discord.Interaction):
        allowed, reason = self.check_command_access(interaction.user, "rank_list")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            def fetch_ranks():
                conn = self.get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, name, default_permissions FROM admin_ranks ORDER BY id ASC")
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                return rows

            ranks = await asyncio.to_thread(fetch_ranks)
            if not ranks:
                await interaction.followup.send("No ranks configured in database.")
                return

            embeds = []
            chunk_size = 15
            for i in range(0, len(ranks), chunk_size):
                chunk = ranks[i:i + chunk_size]
                page_num = (i // chunk_size) + 1
                total_pages = (len(ranks) + chunk_size - 1) // chunk_size
                embed = discord.Embed(
                    title=f"🛡️ Server Admin Ranks ({page_num}/{total_pages})",
                    description="Ranks configured in the MariaDB database:",
                    color=discord.Color.blue()
                )
                for r in chunk:
                    mask = r["default_permissions"]
                    flags = decode_permissions(mask)
                    flag_str = ", ".join(flags[:6])
                    if len(flags) > 6:
                        flag_str += f" *(+{len(flags)-6} more)*"
                    embed.add_field(
                        name=f"#{r['id']} {r['name']} (Bitmask: {mask})",
                        value=f"`{flag_str}`" if flag_str else "`None`",
                        inline=False
                    )
                embeds.append(embed)

            embeds[-1].set_footer(text="Use /rank_info <rank> to view all specific permission flags")
            await interaction.followup.send(embeds=embeds[:10])
        except Exception as e:
            logger.error(f"Error in rank_list: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error retrieving ranks: {e}")

    @app_commands.command(name="rank_info", description="View all detailed permission flags for a specific rank")
    @app_commands.describe(rank="Name of the rank")
    async def cmd_rank_info(self, interaction: discord.Interaction, rank: str):
        allowed, reason = self.check_command_access(interaction.user, "rank_info")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        def fetch_rank():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name, default_permissions FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (rank.strip(),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row

        r = await asyncio.to_thread(fetch_rank)
        if not r:
            await interaction.followup.send(f"❌ Rank `{rank}` not found in database.", ephemeral=True)
            return

        mask = r["default_permissions"]
        flags = decode_permissions(mask)

        embed = discord.Embed(
            title=f"🛡️ Rank Details: {r['name']}",
            color=discord.Color.teal()
        )
        embed.add_field(name="Rank ID", value=str(r["id"]), inline=True)
        embed.add_field(name="Raw Bitmask", value=str(mask), inline=True)
        embed.add_field(name="Active Permissions", value="\n".join([f"• `{f}`" for f in flags]), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rank_create", description="Create a new server rank in the database")
    @app_commands.describe(
        name="Name for the new rank",
        copy_from="Optional: copy permissions from an existing rank"
    )
    async def cmd_rank_create(self, interaction: discord.Interaction, name: str, copy_from: str = None):
        allowed, reason = self.check_command_access(interaction.user, "rank_create")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        clean_name = name.strip()

        def create():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (clean_name,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return False, f"Rank `{clean_name}` already exists!"

            default_perm = 0
            if copy_from:
                cursor.execute("SELECT default_permissions FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (copy_from.strip(),))
                copy_row = cursor.fetchone()
                if copy_row:
                    default_perm = copy_row["default_permissions"]

            cursor.execute("INSERT INTO admin_ranks (name, default_permissions) VALUES (%s, %s)", (clean_name, default_perm))
            conn.commit()
            new_id = cursor.lastrowid
            cursor.close()
            conn.close()
            return True, (new_id, default_perm)

        success, res = await asyncio.to_thread(create)
        if not success:
            await interaction.followup.send(f"❌ {res}", ephemeral=True)
            return

        new_id, perm = res
        await self.byond.reload_admins(sender=interaction.user.display_name)

        embed = discord.Embed(
            title="🛡️ New Rank Created",
            description=f"Created rank **{clean_name}** with ID `#{new_id}` (Bitmask: `{perm}`).",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Created by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rank_delete", description="Delete a server rank from the database")
    @app_commands.describe(name="Name of the rank to delete")
    async def cmd_rank_delete(self, interaction: discord.Interaction, name: str):
        allowed, reason = self.check_command_access(interaction.user, "rank_delete")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        clean_name = name.strip()

        def delete():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (clean_name,))
            rank_row = cursor.fetchone()
            if not rank_row:
                cursor.close()
                conn.close()
                return False, f"Rank `{clean_name}` does not exist."

            rank_id = rank_row["id"]
            cursor.execute("SELECT COUNT(*) AS count FROM admin WHERE permissions_rank = %s", (rank_id,))
            in_use = cursor.fetchone()["count"]
            if in_use > 0:
                cursor.close()
                conn.close()
                return False, f"Cannot delete `{clean_name}`: {in_use} staff member(s) currently have this rank assigned. Reassign them first."

            cursor.execute("DELETE FROM admin_ranks WHERE id = %s", (rank_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return True, rank_id

        success, res = await asyncio.to_thread(delete)
        if not success:
            await interaction.followup.send(f"❌ {res}", ephemeral=True)
            return

        await self.byond.reload_admins(sender=interaction.user.display_name)
        await interaction.followup.send(f"🗑️ Successfully deleted rank **{clean_name}** from the server database.")

    @app_commands.command(name="rank_permission", description="Grant or revoke a permission flag on a server rank")
    @app_commands.describe(
        rank="Name of the rank",
        flag="Permission flag (e.g. BAN, MOD, ADMIN, CHIEF_MENTOR, BUILDMODE, SERVER, VIEWRUNTIMES)",
        action="Grant or Revoke"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Grant (+)", value="GRANT"),
        app_commands.Choice(name="Revoke (-)", value="REVOKE")
    ])
    async def cmd_rank_permission(
        self,
        interaction: discord.Interaction,
        rank: str,
        flag: str,
        action: app_commands.Choice[str]
    ):
        allowed, reason = self.check_command_access(interaction.user, "rank_permission")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        flag_upper = flag.strip().upper()
        if flag_upper not in PERMISSION_FLAGS:
            available = ", ".join(PERMISSION_FLAGS.keys())
            await interaction.response.send_message(f"❌ Unknown flag `{flag}`. Available flags:\n`{available}`", ephemeral=True)
            return

        await interaction.response.defer()
        flag_val = PERMISSION_FLAGS[flag_upper]

        def update():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name, default_permissions FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (rank.strip(),))
            r = cursor.fetchone()
            if not r:
                cursor.close()
                conn.close()
                return False, f"Rank `{rank}` not found."

            current_mask = r["default_permissions"]
            if flag_upper == "ALL":
                new_mask = -1 if action.value == "GRANT" else 0
            else:
                if action.value == "GRANT":
                    new_mask = current_mask | flag_val if current_mask != -1 else -1
                else:
                    new_mask = current_mask & (~flag_val) if current_mask != -1 else 0

            cursor.execute("UPDATE admin_ranks SET default_permissions = %s WHERE id = %s", (new_mask, r["id"]))
            conn.commit()
            cursor.close()
            conn.close()
            return True, (r["name"], current_mask, new_mask)

        success, res = await asyncio.to_thread(update)
        if not success:
            await interaction.followup.send(f"❌ {res}", ephemeral=True)
            return

        rank_name, old_m, new_m = res
        await self.byond.reload_admins(sender=interaction.user.display_name)

        embed = discord.Embed(
            title="🛡️ Rank Permissions Updated",
            description=f"Updated permissions for **{rank_name}**.",
            color=discord.Color.green() if action.value == "GRANT" else discord.Color.orange()
        )
        embed.add_field(name="Flag", value=f"`{flag_upper}` ({action.value})", inline=True)
        embed.add_field(name="Old Bitmask", value=str(old_m), inline=True)
        embed.add_field(name="New Bitmask", value=str(new_m), inline=True)
        embed.add_field(name="In-Game Reload", value="✅ Synchronized in live game server", inline=False)
        embed.set_footer(text=f"Configured by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    async def _execute_rank_rename(
        self,
        interaction: discord.Interaction,
        current_rank: str,
        new_name: str,
        rename_discord_role: bool = True
    ):
        allowed, reason = self.check_command_access(interaction.user, "rank_rename")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        old_clean = current_rank.strip()
        new_clean = new_name.strip()

        if old_clean.lower() == new_clean.lower():
            await interaction.followup.send("❌ Current name and new name are identical.", ephemeral=True)
            return

        def db_rename():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Find old rank
            cursor.execute("SELECT id, name FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (old_clean,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                return False, f"Rank `{old_clean}` was not found in `admin_ranks` table."

            rank_id = row["id"]
            actual_old_name = row["name"]

            # Check if new name already exists on a different rank id
            cursor.execute("SELECT id FROM admin_ranks WHERE LOWER(name) = LOWER(%s) AND id != %s", (new_clean, rank_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return False, f"A rank named `{new_clean}` already exists in database (different ID)."

            # Update admin_ranks
            cursor.execute("UPDATE admin_ranks SET name = %s WHERE id = %s", (new_clean, rank_id))

            # Update admin table display_rank
            cursor.execute("UPDATE admin SET display_rank = %s WHERE permissions_rank = %s OR LOWER(display_rank) = LOWER(%s)", (new_clean, rank_id, actual_old_name))
            conn.commit()

            cursor.close()
            conn.close()
            return True, (rank_id, actual_old_name)

        success, res = await asyncio.to_thread(db_rename)
        if not success:
            await interaction.followup.send(f"❌ {res}", ephemeral=True)
            return

        rank_id, actual_old = res

        # 1. Reload live game server admin ranks
        reload_res = await self.byond.reload_admins(sender=interaction.user.display_name)

        # 2. Rename Discord role if requested
        discord_renamed = False
        matched_role = None
        if rename_discord_role and interaction.guild:
            sync_map = self.config.get("auto_role_sync", {}).get("rank_to_role", {})
            role_id = sync_map.get(actual_old) or sync_map.get(old_clean)
            if role_id:
                matched_role = interaction.guild.get_role(role_id)
            if not matched_role:
                matched_role = discord.utils.get(interaction.guild.roles, name=actual_old) or discord.utils.get(interaction.guild.roles, name=old_clean)
                if not matched_role:
                    for r in interaction.guild.roles:
                        if r.name.lower() in [actual_old.lower(), old_clean.lower()]:
                            matched_role = r
                            break

            if matched_role:
                try:
                    await matched_role.edit(name=new_clean, reason=f"Rank renamed from {actual_old} by {interaction.user.display_name}")
                    discord_renamed = True
                except Exception as e:
                    logger.warning(f"Could not rename Discord role {matched_role.name}: {e}")

        # 3. Update bot configuration bindings
        sync_map = self.config.setdefault("auto_role_sync", {}).setdefault("rank_to_role", {})
        if actual_old in sync_map:
            bound_role_id = sync_map.pop(actual_old)
            sync_map[new_clean] = bound_role_id
        elif matched_role:
            sync_map[new_clean] = matched_role.id

        # Update rank hierarchy
        hierarchy = self.config.get("auto_role_sync", {}).get("rank_hierarchy", [])
        for idx, h in enumerate(hierarchy):
            if h.lower() == actual_old.lower():
                hierarchy[idx] = new_clean

        # Update command permissions
        cmd_perms = self.config.get("command_permissions", {})
        for cmd_k, perm_list in cmd_perms.items():
            for idx, p in enumerate(perm_list):
                if p.lower() == actual_old.lower():
                    perm_list[idx] = new_clean

        from main import save_config
        save_config(self.config)

        # 4. Trigger auto-sync across all guild members
        await self.sync_all_member_roles()

        embed = discord.Embed(
            title="🏷️ Staff Rank Renamed Successfully",
            description=f"**`{actual_old}`** ➔ **`{new_clean}`**",
            color=discord.Color.green()
        )
        embed.add_field(name="Database Rank", value=f"Updated `admin_ranks` (ID #{rank_id})", inline=True)
        embed.add_field(name="In-Game Server", value="✅ Reloaded live admin ranks" if reload_res else "⚠️ Server may be reloading", inline=True)
        if matched_role:
            embed.add_field(name="Discord Role", value=f"{'✅ Renamed to ' if discord_renamed else '⚠️ Found '}{matched_role.mention}", inline=False)
        else:
            embed.add_field(name="Discord Role", value="ℹ️ No matching Discord role was found to rename.", inline=False)

        embed.set_footer(text=f"Renamed by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rank_rename", description="Rename a staff rank in the database and automatically rename its Discord role")
    @app_commands.describe(
        current_rank="The current name of the rank in the database",
        new_name="The new name for the rank",
        rename_discord_role="Also rename the associated Discord role if it exists (default: True)"
    )
    async def cmd_rank_rename(
        self,
        interaction: discord.Interaction,
        current_rank: str,
        new_name: str,
        rename_discord_role: bool = True
    ):
        await self._execute_rank_rename(interaction, current_rank, new_name, rename_discord_role)

    @app_commands.command(name="rename_role", description="Rename a server staff role both in Discord and in the game database")
    @app_commands.describe(
        current_role="Current role or rank name",
        new_name="New role or rank name"
    )
    async def cmd_rename_role(self, interaction: discord.Interaction, current_role: str, new_name: str):
        await self._execute_rank_rename(interaction, current_rank=current_role, new_name=new_name, rename_discord_role=True)

    # -------------------------------------------------------------
    # Remote Controls & Announcements
    # -------------------------------------------------------------

    @app_commands.command(name="update_staff", description="Add or update a staff member's rank in the database")
    @app_commands.describe(
        ckey="BYOND ckey of the staff member",
        rank="Rank name (e.g. Community Founder, Admin, Moderator, Chief Mentor, Mentor)"
    )
    async def cmd_update_staff(self, interaction: discord.Interaction, ckey: str, rank: str):
        allowed, reason = self.check_command_access(interaction.user, "update_staff")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        clean_ckey = ckey.strip().lower()

        def db_update():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM admin_ranks WHERE LOWER(name) = LOWER(%s)", (rank.strip(),))
            rank_row = cursor.fetchone()
            if not rank_row:
                cursor.close()
                conn.close()
                return False, f"Rank '{rank}' not found in database admin_ranks."

            rank_id = rank_row["id"]
            rank_name = rank_row["name"]

            cursor.execute("""
                INSERT INTO admin (ckey, display_rank, permissions_rank, extra_permissions, removed_permissions)
                VALUES (%s, %s, %s, 0, 0)
                ON DUPLICATE KEY UPDATE display_rank = %s, permissions_rank = %s
            """, (clean_ckey, rank_name, rank_id, rank_name, rank_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True, rank_name

        success, msg = await asyncio.to_thread(db_update)
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        reload_res = await self.byond.reload_admins(sender=interaction.user.display_name)
        await self.sync_all_member_roles()

        embed = discord.Embed(
            title="🛡️ Staff Rank Updated",
            description=f"Successfully set `{clean_ckey}` to **{msg}**.",
            color=discord.Color.blue()
        )
        embed.add_field(name="In-Game Reload", value="✅ Synchronized in live game server" if reload_res else "⚠️ Server may be reloading", inline=True)
        embed.set_footer(text=f"Updated by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="announce", description="Send an official server announcement")
    @app_commands.describe(
        message="Announcement text",
        in_game="Broadcast announcement to players in-game",
        discord_channel="Post announcement embed to Discord announcement channel"
    )
    async def cmd_announce(self, interaction: discord.Interaction, message: str, in_game: bool = True, discord_channel: bool = True):
        allowed, reason = self.check_command_access(interaction.user, "announce")
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await interaction.response.defer()
        sender = interaction.user.display_name

        in_game_success = False
        if in_game:
            res = await self.byond.send_announcement(msg=message, sender=sender)
            in_game_success = bool(res and isinstance(res, dict) and res.get("success"))

        discord_posted = False
        if discord_channel:
            ann_ch_id = self.config["channels"].get("announcements") or self.config["channels"].get("status")
            if ann_ch_id:
                ch = self.bot.get_channel(ann_ch_id)
                if ch:
                    embed = discord.Embed(
                        title="📢 Nova Station 13 Announcement",
                        description=message,
                        color=discord.Color.gold()
                    )
                    embed.set_author(name=f"Announced by {sender}", icon_url=interaction.user.display_avatar.url)
                    await ch.send(embed=embed)
                    discord_posted = True

        embed = discord.Embed(title="✅ Announcement Dispatched", color=discord.Color.green())
        if in_game:
            embed.add_field(name="In-Game Announcement", value="✅ Broadcast to server" if in_game_success else "⚠️ Could not reach server", inline=True)
        if discord_channel:
            embed.add_field(name="Discord Announcement", value="✅ Posted to channel" if discord_posted else "⚠️ Channel not set", inline=True)
        await interaction.followup.send(embed=embed)

    @commands.hybrid_command(name="server_restart", aliases=["restart", "restartserver", "serverrestart"], description="Restart the Nova Station server")
    async def cmd_server_restart(self, ctx: commands.Context):
        author = ctx.author
        if not isinstance(author, discord.Member) and ctx.guild:
            author = ctx.guild.get_member(author.id) or author

        allowed, reason = self.check_command_access(author, "server_restart")
        if not allowed:
            await ctx.send(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await ctx.defer()
        service = self.config.get("systemd_service", "novastation.service")
        try:
            await self.byond.remote_reboot(sender=author.display_name)
            await asyncio.sleep(2)
            await asyncio.to_thread(subprocess.run, ["sudo", "systemctl", "restart", service], check=True)
            await ctx.send(f"🟡 **Server restarted!** `{service}` has been rebooted by {author.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to restart server: {e}")

    async def _execute_server_stop(self, ctx: commands.Context):
        author = ctx.author
        if not isinstance(author, discord.Member) and ctx.guild:
            author = ctx.guild.get_member(author.id) or author

        allowed, reason = self.check_command_access(author, "server_stop")
        if not allowed:
            await ctx.send(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await ctx.defer()
        service = self.config.get("systemd_service", "novastation.service")
        try:
            await asyncio.to_thread(subprocess.run, ["sudo", "systemctl", "stop", service], check=True)
            await ctx.send(f"🔴 **Server stopped!** `{service}` has been shut down by {author.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to stop server: {e}")

    @commands.hybrid_command(name="server_stop", aliases=["serverstop", "stopserver"], description="Stop the Nova Station server")
    async def cmd_server_stop(self, ctx: commands.Context):
        await self._execute_server_stop(ctx)

    @commands.hybrid_command(name="server_shutdown", aliases=["shutdown", "stop", "servershutdown"], description="Shut down the Nova Station server")
    async def cmd_server_shutdown(self, ctx: commands.Context):
        await self._execute_server_stop(ctx)

    @commands.hybrid_command(name="server_start", aliases=["start", "startserver", "serverstart"], description="Start the Nova Station server")
    async def cmd_server_start(self, ctx: commands.Context):
        author = ctx.author
        if not isinstance(author, discord.Member) and ctx.guild:
            author = ctx.guild.get_member(author.id) or author

        allowed, reason = self.check_command_access(author, "server_start")
        if not allowed:
            await ctx.send(f"🚫 **Access Denied**: {reason}", ephemeral=True)
            return

        await ctx.defer()
        service = self.config.get("systemd_service", "novastation.service")
        try:
            await asyncio.to_thread(subprocess.run, ["sudo", "systemctl", "start", service], check=True)
            await ctx.send(f"🟢 **Server started!** `{service}` has been started by {author.mention}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to start server: {e}")

async def setup(bot):
    await bot.add_cog(StaffManagementCog(bot))
