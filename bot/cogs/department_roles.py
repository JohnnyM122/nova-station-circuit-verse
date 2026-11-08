import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio

logger = logging.getLogger("CVNovaHelper.department_roles")

DISCORD_LOGS_CH_ID = 1566986370910654517

# Designated Bot Command Channels
MC_COMMAND_CHANNEL_ID = 1567533238832857178     # 💻・mc-staff-commands
NS13_COMMAND_CHANNEL_ID = 1566608878731268148   # 🤖・ns13-staff-bot
GC_COMMAND_CHANNEL_ID = 1567671208797937714
PZ_COMMAND_CHANNEL_ID = 1567702401236860999   # 💻・pz-staff-commands     # 🤖community-bot-commands

# Authorized Department Category IDs
MC_CATEGORY_IDS = {
    1567426382664040459, # ⛏️・CircuitVerse-Minecraft
    1567464236177817620, # ⛏️・Minecraft Staff Area
    1567537293357486261, # 🚨Incident Managment Tickets
}

NS13_CATEGORY_IDS = {
    1566607420275564638, # 🚀・Nova Station 13
    1566608607829692696, # 🚀・NS13 Staff Area
}


PZ_CATEGORY_IDS = {
    1567692616202719405, # 🧟・CircuitVerse-Zomboid
    1567692617112756407, # 🧟・Zomboid Staff Area
}

GC_CATEGORY_IDS = {
    1566679559481462864, # 📊・Community Dashboard
    1564605316849733723, # 💬・Community General
    1564605316849733724, # 🔊・Voice Channels
    1566680487504650330, # 🛡️・Community Staff Area
    1567435050331537468, # 🎫・Community Support Area
    1567345837510758430, # 📻・CV Radio Station
}

# Protected Channels that can never be deleted by Department Directors
PROTECTED_CHANNELS = {
    1566600269649678467, # 📜・discord-rules
    1567427447811739698, # 📢・announcements-and-news
    1567434275928809544, # 📌・community-info
    1564605316849733725, # 👋・welcome
    1566635359641669652, # 💬・general-chat
    1566986370910654517, # 📜・discord-logs
    1567474488059363418, # 🏛️・executives
    1567464237108822087, # 👑・management
    1567464248215470152, # 👑・ns13-management
    1567464244159717528, # 👑・mc-management
    1567533238832857178, # 💻・mc-staff-commands
    1566608878731268148, # 🤖・ns13-staff-bot
    1567671208797937714, # 🤖community-bot-commands
    1567464241131421778, # 📜・staff-info
    1567466094111883309, # 📜・mc-staff-info
    1567466166333604023, # 📜・ns13-staff-info
    1567702337961594883, # ℹ️・pz-server-status
    1567702397113995264, # 👑・pz-management
    1567702375156940815, # 📜・pz-staff-info
    1567702401236860999, # 💻・pz-staff-commands
}

# ==========================================
# MINECRAFT DEPARTMENT ROLES
# ==========================================
MC_ROLES = {
    "MC Server Host",
    "MC Server Head Admin",
    "MC Server Admin",
    "MC Server Head Mod",
    "MC Server Mod",
    "MC Server Staff",
    "MC Ticket Admin",
    "MC Ticket Support",
    "MC VIP Member",
    "MC Player",
    "MC Ping Me",
    "🌟 Realm Legend",
    "🏆 Server Veteran",
    "💎 Seasoned Adventurer",
    "🌲 Wilderness Survivor",
    "🧭 Explorer",
    "🌱 New Adventurer",
    "⛏️ Miner",
    "🏗️ Master Builder",
    "🌾 Homesteader",
    "⚔️ Warrior",
    "🐉 Dragon Slayer",
    "💎 Treasure Hunter",
    "🎨 Creative Architect",
    "🤝 Helpful Adventurer",
    "🏰 Trusted Builder",
    "💎 Master Artisan",
}

# ==========================================
# NOVA STATION 13 DEPARTMENT ROLES
# ==========================================
NS13_ROLES = {
    "NS13 Server Host",
    "NS13 Head Admin",
    "NS13 Senior Admin",
    "NS13 Admin",
    "NS13 Jr Admin",
    "NS13 Trial Admin",
    "NS13 Chief GM",
    "NS13 GM",
    "NS13 GM Trainee",
    "NS13 Chief Mod",
    "NS13 Senior Mod",
    "NS13 Mod",
    "NS13 Jr Mod",
    "NS13 Trial Mod",
    "NS13 Chief Mentor",
    "NS13 Mentor",
    "NS13 Chief Developer",
    "NS13 Server Maintainer",
    "NS13 Server Developer",
    "NS13 Server Staff",
    "NS13 Staff Observer",
    "NS13 Ticket Admin",
    "NS13 Mentor Ticket Admin",
    "NS13 Ticket Support",
    "NS13 Mentor Ticket Support",
    "NS13 WL OR",
    "NS13 Player",
    "NS13 Ping Me",
    "🌟 Legend of the Station",
    "🏅 Station Veteran",
    "⭐ Veteran Crewman",
    "🛰️ Station Regular",
    "🧑🚀 Junior Crewman",
    "🚀 Station Crew",
    "🪐 Fresh Arrival",
    "🔬 Research Associate",
    "🛡️ Security Auxiliary",
    "🩺 Medical Associate",
    "🔧 Engineering Specialist",
    "📡 Communications Officer",
    "🎭 Roleplay Enthusiast",
    "🎉 Event Participant",
}

# ==========================================
# GENERAL COMMUNITY (GC) ROLES
# ==========================================
GC_ROLES = {
    "Senior Admin",
    "Admin",
    "Jr.Admin",
    "Head Mod",
    "Sr Mod",
    "Mod",
    "Jr Mod",
    "Community Trial Staff",
    "General Community Support",
    "Community Ambassador",
    "Staff Observer",
    "Ticket Admin",
    "Comm Ticket Admin",
    "Comm Ticket Support",
    "Zero-Day Circle",
    "Circuit VIP Member",
    "🌌 The Founders' Circle",
    "🏛️ Founding Member",
    "⚡ Circuit Pioneer",
    "🥇 First Generation",
    "🎖️ Community Legend",
    "💠 Circuit Elite",
    "🛰️ Community Veteran",
    "💜 Community Pillar",
    "🛡️ Guardian of the Circuit",
    "🎖️ Hall of Fame",
    "🌟 Community Hero",
    "🤝 Server Ambassador",
    "🛡️ Trusted Sentinel",
    "🎨 Creative Mind",
    "🛠️ Community Contributor",
    "🤝 Community Supporter",
    "🧩 Problem Solver",
    "🎮 Multi-World Member",
    "🌐 Circuit Traveler",
    "🔷 Community Regular",
    "🌠 Rising Star",
    "🔥 Event Champion",
    "🌌 Multiverse Explorer",
    "Circuit Member",
    "Legacy Member",
    "Circuit Verse Ping Me",
    "CV-Radio-Access",
}

RADIO_ROLES = {
    "CV-Radio-Access",
    "Station Manager",
    "Senior Radio Host",
    "Radio Host / DJ",
    "Trainee Radio Host",
}


# ==========================================
# PROJECT ZOMBOID DEPARTMENT ROLES
# ==========================================
PZ_ROLES = {
    "PZ Server Host",
    "PZ Server Technician",
    "PZ Lead Developer",
    "PZ Developer",
    "PZ Head Moderator",
    "PZ Senior Moderator",
    "PZ Moderator",
    "PZ Chief Game Master",
    "PZ Senior Game Master",
    "PZ Game Master",
    "PZ GM Trainee",
    "PZ Head Support",
    "PZ Senior Support",
    "PZ Support Team",
    "PZ Support Trainee",
    "PZ Staff Observer",
    "PZ Server Staff",
    "PZ Ticket Admin",
    "PZ Ticket Support",
    "PZ Player",
    "PZ Ping Me",
}

MANAGEMENT_AND_EXEC_ROLES = {
    "Founder",
    "Chief Community Officer",
    "Community Executive",
    "Community Director",
    "Executive Director",
    "Community Management",
}

PROTECTED_SYSTEM_ROLES = {
    "Circuit Verse Helper",
    "Founder",
    "Chief Community Officer",
    "Community Executive",
    "Community Director",
    "Executive Director",
    "Community Management",
    "Dept.Director (GC)",
    "Dept.Director (MC)",
    "Dept.Director (NS13)",
    "NS13 Server Director",
    "Dept.Director (CV Radio)",
    "Dept.Director (PZ)",
}

class DepartmentRoles(commands.Cog):
    """
    Departmental Governance:
    1. Role Assignment & Boundary Enforcement for Department Directors.
    2. Category-Scoped Channel Management (/channel_create, /channel_setup, /channel_delete)
       restricted to designated command channels and departmental categories.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reverting_updates = set()

    def get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        ch_id = self.bot.config.get("channels", {}).get("discord_logs", DISCORD_LOGS_CH_ID)
        return guild.get_channel(ch_id) or self.bot.get_channel(ch_id)

    def get_director_scope(self, member: discord.Member) -> set[str]:
        member_role_names = {r.name for r in member.roles}
        if any(r in member_role_names for r in MANAGEMENT_AND_EXEC_ROLES):
            return MC_ROLES | NS13_ROLES | GC_ROLES | PZ_ROLES | RADIO_ROLES

        allowed = set()
        if "Dept.Director (MC)" in member_role_names:
            allowed |= MC_ROLES
        if "Dept.Director (NS13)" in member_role_names or "NS13 Server Director" in member_role_names:
            allowed |= NS13_ROLES
        if "Dept.Director (GC)" in member_role_names:
            allowed |= GC_ROLES
        if "Dept.Director (PZ)" in member_role_names:
            allowed |= PZ_ROLES
        if "Dept.Director (CV Radio)" in member_role_names:
            allowed |= RADIO_ROLES

        return allowed

    def get_director_department(self, member: discord.Member) -> str | None:
        """Returns 'MC', 'NS13', 'GC', 'MGMT', or None."""
        role_names = {r.name for r in member.roles}
        if any(r in role_names for r in MANAGEMENT_AND_EXEC_ROLES):
            return "MGMT"
        if "Dept.Director (MC)" in role_names:
            return "MC"
        if "Dept.Director (NS13)" in role_names or "NS13 Server Director" in role_names:
            return "NS13"
        if "Dept.Director (GC)" in role_names:
            return "GC"
        if "Dept.Director (PZ)" in role_names:
            return "PZ"
        return None

    def validate_channel_command_environment(self, interaction: discord.Interaction) -> tuple[bool, str]:
        """Validates that the command is executed in the designated channel and by an authorized director."""
        if not isinstance(interaction.user, discord.Member):
            return False, "❌ Error: Could not verify server member."

        dept = self.get_director_department(interaction.user)
        if not dept:
            return False, "❌ Access Denied: You do not hold a Department Director or Management role."

        ch_id = interaction.channel_id
        if dept == "MGMT":
            return True, "OK"

        if dept == "MC" and ch_id != MC_COMMAND_CHANNEL_ID:
            return False, f"❌ Command Channel Restriction: Minecraft channel commands must be executed in <#{MC_COMMAND_CHANNEL_ID}>."

        if dept == "NS13" and ch_id != NS13_COMMAND_CHANNEL_ID:
            return False, f"❌ Command Channel Restriction: Nova Station 13 channel commands must be executed in <#{NS13_COMMAND_CHANNEL_ID}>."

        if dept == "GC" and ch_id != GC_COMMAND_CHANNEL_ID:
            return False, f"❌ Command Channel Restriction: Community channel commands must be executed in <#{GC_COMMAND_CHANNEL_ID}>."

        if dept == "PZ" and ch_id != PZ_COMMAND_CHANNEL_ID:
            return False, f"❌ Command Channel Restriction: Project Zomboid channel commands must be executed in <#{PZ_COMMAND_CHANNEL_ID}>."

        return True, "OK"

    def is_category_authorized(self, member: discord.Member, category_id: int) -> bool:
        dept = self.get_director_department(member)
        if dept == "MGMT":
            return True
        if dept == "MC" and category_id in MC_CATEGORY_IDS:
            return True
        if dept == "NS13" and category_id in NS13_CATEGORY_IDS:
            return True
        if dept == "GC" and category_id in GC_CATEGORY_IDS:
            return True
        if dept == "PZ" and category_id in PZ_CATEGORY_IDS:
            return True
        return False

    # ==========================================
    # 1. ROLE MANAGEMENT COMMANDS
    # ==========================================
    async def role_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        if not isinstance(interaction.user, discord.Member):
            return []
        
        allowed_roles = self.get_director_scope(interaction.user)
        if not allowed_roles:
            return []

        choices = [
            app_commands.Choice(name=name[:100], value=name)
            for name in sorted(allowed_roles)
            if current.lower() in name.lower()
        ]
        return choices[:25]

    @app_commands.command(
        name="dept_give_role",
        description="Assign a departmental role to a member (scoped strictly to your Department)"
    )
    @app_commands.describe(
        member="Target Discord member",
        role_name="Role to grant (autocomplete filtered to your department)",
        reason="Reason for granting this role (optional)"
    )
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def dept_give_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role_name: str,
        reason: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        issuer = interaction.user
        if not isinstance(issuer, discord.Member):
            return await interaction.followup.send("❌ Error: Could not verify server member.", ephemeral=True)

        allowed_scope = self.get_director_scope(issuer)
        if not allowed_scope:
            return await interaction.followup.send("❌ Access Denied: You do not hold a Department Director or Management role.", ephemeral=True)

        if role_name in PROTECTED_SYSTEM_ROLES and not any(r.name in MANAGEMENT_AND_EXEC_ROLES for r in issuer.roles):
            return await interaction.followup.send(f"❌ Protected Role: '{role_name}' can only be granted by Executive Management.", ephemeral=True)

        if role_name not in allowed_scope:
            return await interaction.followup.send(
                f"❌ Departmental Restriction: You are not authorized to assign '{role_name}'. You can only manage roles within your assigned department.",
                ephemeral=True
            )

        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            return await interaction.followup.send(f"❌ Error: Role '{role_name}' does not exist on this server.", ephemeral=True)

        if role in member.roles:
            return await interaction.followup.send(f"ℹ️ {member.mention} already has the **{role.name}** role.", ephemeral=True)

        try:
            audit_reason = f"Granted by {issuer.name} ({issuer.id}) via /dept_give_role"
            if reason:
                audit_reason += f": {reason}"
            await member.add_roles(role, reason=audit_reason)
        except discord.Forbidden:
            return await interaction.followup.send("❌ Discord Permission Error: The bot cannot assign this role (check role hierarchy).", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to assign role: {e}", ephemeral=True)

        embed = discord.Embed(
            title="✅ Department Role Granted",
            description=f"Successfully granted **{role.name}** to {member.mention}.",
            color=role.color if role.color.value != 0 else discord.Color.green()
        )
        embed.add_field(name="👤 Target Member", value=f"{member.mention} (`{member.name}`)", inline=True)
        embed.add_field(name="👑 Authorized By", value=f"{issuer.mention} (`{issuer.name}`)", inline=True)
        if reason:
            embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Circuit Verse • Departmental Role Management")

        await interaction.followup.send(embed=embed, ephemeral=False)

        log_ch = self.get_log_channel(interaction.guild)
        if log_ch:
            log_embed = discord.Embed(
                title="🛡️ Department Role Assigned",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Target", value=f"{member.mention} (`{member.id}`)", inline=True)
            log_embed.add_field(name="Role Granted", value=role.mention, inline=True)
            log_embed.add_field(name="Assigned By", value=f"{issuer.mention} (`{issuer.id}`)", inline=True)
            if reason:
                log_embed.add_field(name="Reason", value=reason, inline=False)
            await log_ch.send(embed=log_embed)

    @app_commands.command(
        name="dept_remove_role",
        description="Remove a departmental role from a member (scoped strictly to your Department)"
    )
    @app_commands.describe(
        member="Target Discord member",
        role_name="Role to remove (autocomplete filtered to your department)",
        reason="Reason for removing this role (optional)"
    )
    @app_commands.autocomplete(role_name=role_autocomplete)
    async def dept_remove_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role_name: str,
        reason: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        issuer = interaction.user
        if not isinstance(issuer, discord.Member):
            return await interaction.followup.send("❌ Error: Could not verify server member.", ephemeral=True)

        allowed_scope = self.get_director_scope(issuer)
        if not allowed_scope:
            return await interaction.followup.send("❌ Access Denied: You do not hold a Department Director or Management role.", ephemeral=True)

        if role_name in PROTECTED_SYSTEM_ROLES and not any(r.name in MANAGEMENT_AND_EXEC_ROLES for r in issuer.roles):
            return await interaction.followup.send(f"❌ Protected Role: '{role_name}' can only be removed by Executive Management.", ephemeral=True)

        if role_name not in allowed_scope:
            return await interaction.followup.send(
                f"❌ Departmental Restriction: You are not authorized to remove '{role_name}'. You can only manage roles within your assigned department.",
                ephemeral=True
            )

        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            return await interaction.followup.send(f"❌ Error: Role '{role_name}' does not exist on this server.", ephemeral=True)

        if role not in member.roles:
            return await interaction.followup.send(f"ℹ️ {member.mention} does not have the **{role.name}** role.", ephemeral=True)

        try:
            audit_reason = f"Removed by {issuer.name} ({issuer.id}) via /dept_remove_role"
            if reason:
                audit_reason += f": {reason}"
            await member.remove_roles(role, reason=audit_reason)
        except discord.Forbidden:
            return await interaction.followup.send("❌ Discord Permission Error: The bot cannot remove this role (check role hierarchy).", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to remove role: {e}", ephemeral=True)

        embed = discord.Embed(
            title="🗑️ Department Role Removed",
            description=f"Successfully removed **{role.name}** from {member.mention}.",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Target Member", value=f"{member.mention} (`{member.name}`)", inline=True)
        embed.add_field(name="👑 Authorized By", value=f"{issuer.mention} (`{issuer.name}`)", inline=True)
        if reason:
            embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Circuit Verse • Departmental Role Management")

        await interaction.followup.send(embed=embed, ephemeral=False)

        log_ch = self.get_log_channel(interaction.guild)
        if log_ch:
            log_embed = discord.Embed(
                title="🛡️ Department Role Removed",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Target", value=f"{member.mention} (`{member.id}`)", inline=True)
            log_embed.add_field(name="Role Removed", value=role.name, inline=True)
            log_embed.add_field(name="Removed By", value=f"{issuer.mention} (`{issuer.id}`)", inline=True)
            if reason:
                log_embed.add_field(name="Reason", value=reason, inline=False)
            await log_ch.send(embed=log_embed)

    # ==========================================
    # 2. DEPARTMENT CHANNEL MANAGEMENT COMMANDS
    # ==========================================
    @app_commands.command(
        name="channel_create",
        description="Create a new channel under your department category (run in your designated bot channel)"
    )
    @app_commands.describe(
        name="Name of the new channel",
        category="Target category (must be in your department)",
        channel_type="Type of channel (Text or Voice)",
        topic="Channel topic description (optional)",
        slowmode="Slowmode in seconds (optional)",
        sync_category_perms="Sync channel permissions with category (default True)"
    )
    @app_commands.choices(channel_type=[
        app_commands.Choice(name="Text Channel", value="text"),
        app_commands.Choice(name="Voice Channel", value="voice"),
        app_commands.Choice(name="Announcement Channel (News)", value="announcement"),
        app_commands.Choice(name="Forum Channel", value="forum"),
        app_commands.Choice(name="Stage Channel", value="stage"),
    ])
    async def channel_create(
        self,
        interaction: discord.Interaction,
        name: str,
        category: discord.CategoryChannel,
        channel_type: str = "text",
        topic: str | None = None,
        slowmode: int = 0,
        sync_category_perms: bool = True
    ):
        await interaction.response.defer(ephemeral=True)
        ok, msg = self.validate_channel_command_environment(interaction)
        if not ok:
            return await interaction.followup.send(msg, ephemeral=True)

        issuer = interaction.user
        if not self.is_category_authorized(issuer, category.id):
            return await interaction.followup.send(
                f"❌ Department Restriction: You are not authorized to create channels under **{category.name}**.",
                ephemeral=True
            )

        guild = interaction.guild
        clean_name = name.strip().lower().replace(" ", "-")

        try:
            audit_reason = f"Created by {issuer.name} ({issuer.id}) via /channel_create"
            if channel_type == "voice":
                new_ch = await guild.create_voice_channel(
                    name=name.strip(),
                    category=category,
                    reason=audit_reason
                )
            elif channel_type == "stage":
                new_ch = await guild.create_stage_channel(
                    name=name.strip(),
                    category=category,
                    topic=topic,
                    reason=audit_reason
                )
            elif channel_type == "forum":
                new_ch = await guild.create_forum(
                    name=clean_name,
                    category=category,
                    topic=topic,
                    slowmode_delay=slowmode,
                    reason=audit_reason
                )
            elif channel_type == "announcement":
                new_ch = await guild.create_text_channel(
                    name=clean_name,
                    category=category,
                    news=True,
                    topic=topic,
                    slowmode_delay=slowmode,
                    reason=audit_reason
                )
            else:
                new_ch = await guild.create_text_channel(
                    name=clean_name,
                    category=category,
                    topic=topic,
                    slowmode_delay=slowmode,
                    reason=audit_reason
                )

            if sync_category_perms:
                await new_ch.edit(sync_permissions=True)

        except discord.Forbidden:
            return await interaction.followup.send("❌ Discord Permission Error: Bot lacks permissions to create channel in this category.", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to create channel: {e}", ephemeral=True)

        embed = discord.Embed(
            title="✅ Department Channel Created",
            description=f"Successfully created {new_ch.mention} under **{category.name}**.",
            color=discord.Color.green()
        )
        embed.add_field(name="📁 Category", value=category.name, inline=True)
        embed.add_field(name="⚙️ Type", value=channel_type.capitalize(), inline=True)
        embed.add_field(name="👑 Authorized By", value=f"{issuer.mention} (`{issuer.name}`)", inline=True)
        if topic:
            embed.add_field(name="📝 Topic", value=topic, inline=False)
        embed.set_footer(text="Circuit Verse • Channel Governance")

        await interaction.followup.send(embed=embed, ephemeral=False)

        log_ch = self.get_log_channel(guild)
        if log_ch:
            log_embed = discord.Embed(
                title="📁 Department Channel Created",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Channel", value=f"{new_ch.mention} (`{new_ch.id}`)", inline=True)
            log_embed.add_field(name="Category", value=category.name, inline=True)
            log_embed.add_field(name="Created By", value=f"{issuer.mention} (`{issuer.id}`)", inline=True)
            await log_ch.send(embed=log_embed)

    @app_commands.command(
        name="channel_setup",
        description="Configure topic, slowmode, or name of a channel in your department"
    )
    @app_commands.describe(
        channel="Target channel in your department",
        new_name="New channel name (optional)",
        topic="New channel topic (optional, text channels only)",
        slowmode="Slowmode delay in seconds (optional, text channels only)",
        sync_category_perms="Sync channel permissions with parent category (optional)"
    )
    async def channel_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        new_name: str | None = None,
        topic: str | None = None,
        slowmode: int | None = None,
        sync_category_perms: bool | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        ok, msg = self.validate_channel_command_environment(interaction)
        if not ok:
            return await interaction.followup.send(msg, ephemeral=True)

        issuer = interaction.user
        category_id = getattr(channel, "category_id", None)
        if not category_id or not self.is_category_authorized(issuer, category_id):
            return await interaction.followup.send(
                f"❌ Department Restriction: You are not authorized to configure {channel.mention} (outside your department).",
                ephemeral=True
            )

        edit_kwargs = {"reason": f"Configured by {issuer.name} ({issuer.id}) via /channel_setup"}
        if new_name:
            edit_kwargs["name"] = new_name.strip().lower().replace(" ", "-") if isinstance(channel, discord.TextChannel) else new_name.strip()
        if topic is not None and isinstance(channel, (discord.TextChannel, discord.StageChannel, discord.ForumChannel)):
            edit_kwargs["topic"] = topic
        if slowmode is not None and isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
            edit_kwargs["slowmode_delay"] = slowmode
        if sync_category_perms is not None:
            edit_kwargs["sync_permissions"] = sync_category_perms

        try:
            await channel.edit(**edit_kwargs)
        except discord.Forbidden:
            return await interaction.followup.send("❌ Discord Permission Error: Bot lacks permissions to edit this channel.", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to update channel: {e}", ephemeral=True)

        embed = discord.Embed(
            title="⚙️ Channel Configured",
            description=f"Successfully updated configuration for {channel.mention}.",
            color=discord.Color.blue()
        )
        embed.add_field(name="📁 Category", value=getattr(channel.category, "name", "None"), inline=True)
        embed.add_field(name="👑 Authorized By", value=f"{issuer.mention} (`{issuer.name}`)", inline=True)
        if new_name:
            embed.add_field(name="🏷️ New Name", value=channel.name, inline=True)
        if topic is not None:
            embed.add_field(name="📝 Topic", value=topic, inline=False)
        if slowmode is not None:
            embed.add_field(name="⏱️ Slowmode", value=f"{slowmode}s", inline=True)
        embed.set_footer(text="Circuit Verse • Channel Governance")

        await interaction.followup.send(embed=embed, ephemeral=False)

        log_ch = self.get_log_channel(interaction.guild)
        if log_ch:
            log_embed = discord.Embed(
                title="⚙️ Department Channel Updated",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Channel", value=f"{channel.mention} (`{channel.id}`)", inline=True)
            log_embed.add_field(name="Updated By", value=f"{issuer.mention} (`{issuer.id}`)", inline=True)
            await log_ch.send(embed=log_embed)

    @app_commands.command(
        name="channel_delete",
        description="Safely delete a channel in your department category"
    )
    @app_commands.describe(
        channel="Channel to delete (must be within your department)",
        confirm="Confirm deletion (must set to True)",
        reason="Reason for deleting this channel (optional)"
    )
    async def channel_delete(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        confirm: bool,
        reason: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        if not confirm:
            return await interaction.followup.send("❌ Deletion Cancelled: You must set `confirm: True` to delete a channel.", ephemeral=True)

        ok, msg = self.validate_channel_command_environment(interaction)
        if not ok:
            return await interaction.followup.send(msg, ephemeral=True)

        issuer = interaction.user
        category_id = getattr(channel, "category_id", None)
        if not category_id or not self.is_category_authorized(issuer, category_id):
            return await interaction.followup.send(
                f"❌ Department Restriction: You are not authorized to delete {channel.name} (outside your department).",
                ephemeral=True
            )

        if channel.id in PROTECTED_CHANNELS:
            return await interaction.followup.send(
                f"❌ Protected Channel: **#{channel.name}** is a critical system/staff channel and cannot be deleted.",
                ephemeral=True
            )

        ch_name = channel.name
        ch_id = channel.id
        cat_name = getattr(channel.category, "name", "None")

        try:
            audit_reason = f"Deleted by {issuer.name} ({issuer.id}) via /channel_delete"
            if reason:
                audit_reason += f": {reason}"
            await channel.delete(reason=audit_reason)
        except discord.Forbidden:
            return await interaction.followup.send("❌ Discord Permission Error: Bot lacks permissions to delete this channel.", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to delete channel: {e}", ephemeral=True)

        embed = discord.Embed(
            title="🗑️ Department Channel Deleted",
            description=f"Successfully deleted channel **#{ch_name}** from category **{cat_name}**.",
            color=discord.Color.red()
        )
        embed.add_field(name="👑 Authorized By", value=f"{issuer.mention} (`{issuer.name}`)", inline=True)
        if reason:
            embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Circuit Verse • Channel Governance")

        await interaction.followup.send(embed=embed, ephemeral=False)

        log_ch = self.get_log_channel(interaction.guild)
        if log_ch:
            log_embed = discord.Embed(
                title="🗑️ Department Channel Deleted",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            log_embed.add_field(name="Channel", value=f"#{ch_name} (`{ch_id}`)", inline=True)
            log_embed.add_field(name="Category", value=cat_name, inline=True)
            log_embed.add_field(name="Deleted By", value=f"{issuer.mention} (`{issuer.id}`)", inline=True)
            if reason:
                log_embed.add_field(name="Reason", value=reason, inline=False)
            await log_ch.send(embed=log_embed)

    # ==========================================
    # 3. NATIVE DISCORD UI GUARD (ROLES)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return

        guild = after.guild
        update_key = (after.id, tuple(sorted(r.id for r in after.roles)))
        if update_key in self._reverting_updates:
            self._reverting_updates.remove(update_key)
            return

        await asyncio.sleep(0.7)
        actor = None
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                    actor = entry.user
                    break
        except Exception:
            return

        if not actor or actor.id == self.bot.user.id or actor.bot:
            return

        actor_member = guild.get_member(actor.id)
        if not actor_member:
            return

        actor_role_names = {r.name for r in actor_member.roles}
        if any(r in actor_role_names for r in MANAGEMENT_AND_EXEC_ROLES):
            return

        is_mc_director = "Dept.Director (MC)" in actor_role_names
        is_ns13_director = "Dept.Director (NS13)" in actor_role_names or "NS13 Server Director" in actor_role_names
        is_gc_director = "Dept.Director (GC)" in actor_role_names

        if not (is_mc_director or is_ns13_director or is_gc_director):
            return

        allowed_scope = self.get_director_scope(actor_member)
        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]

        unauthorized_added = [r for r in added_roles if r.name not in allowed_scope]
        unauthorized_removed = [r for r in removed_roles if r.name not in allowed_scope]

        if not unauthorized_added and not unauthorized_removed:
            return

        logger.warning(
            f"Department boundary violation: {actor_member.name} attempted unauthorized role update on {after.name}. "
            f"Added: {[r.name for r in unauthorized_added]}, Removed: {[r.name for r in unauthorized_removed]}"
        )

        reverted_roles = list(after.roles)
        for r in unauthorized_added:
            if r in reverted_roles:
                reverted_roles.remove(r)
        for r in unauthorized_removed:
            if r not in reverted_roles:
                reverted_roles.append(r)

        revert_key = (after.id, tuple(sorted(r.id for r in reverted_roles)))
        self._reverting_updates.add(revert_key)

        try:
            await after.edit(
                roles=reverted_roles,
                reason=f"Automated Revert: Department boundary enforced against {actor_member.name}"
            )
        except Exception as e:
            logger.error(f"Failed to revert unauthorized role update: {e}")
            return

        log_ch = self.get_log_channel(guild)
        if log_ch:
            alert_embed = discord.Embed(
                title="🛡️ Department Boundary Enforced (Action Reverted)",
                description=(
                    f"**{actor_member.mention}** attempted to modify roles outside their departmental jurisdiction.\n"
                    f"The unauthorized role modification was **automatically blocked & reverted**."
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            alert_embed.add_field(name="Staff Actor", value=f"{actor_member.mention} (`{actor_member.name}`)", inline=True)
            alert_embed.add_field(name="Target Member", value=f"{after.mention} (`{after.name}`)", inline=True)
            if unauthorized_added:
                alert_embed.add_field(name="Blocked Role Additions", value=", ".join(r.mention for r in unauthorized_added), inline=False)
            if unauthorized_removed:
                alert_embed.add_field(name="Blocked Role Removals", value=", ".join(r.name for r in unauthorized_removed), inline=False)
            alert_embed.set_footer(text="Circuit Verse • Security & Department Governance")
            await log_ch.send(embed=alert_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(DepartmentRoles(bot))
