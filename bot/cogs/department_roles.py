import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import re

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
    # COMMUNITY EXECUTIVE: GIVEROLE COMMAND
    # ==========================================
    def is_community_executive(self, member: discord.Member) -> bool:
        """
        Verify if member holds the Community Executive role, higher executive leadership,
        or server administrator permissions.
        """
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return True

        comm_exec_cfg_id = self.bot.config.get("roles", {}).get("comm_executive")
        if comm_exec_cfg_id and any(r.id == comm_exec_cfg_id for r in member.roles):
            return True

        exec_ids = {
            1567495181794807838,  # Community Executive
            1567477045964054598,  # Executive Director
            1567482219495301191,  # Community Director
            1566625061467717752,  # Chief Community Officer
            1567474473404338216,  # Community Management
            1564610713216098394,  # Founder
            1567449658639384678,  # Founder
        }
        founder_cfg = self.bot.config.get("roles", {}).get("founder", [])
        if isinstance(founder_cfg, list):
            exec_ids.update(founder_cfg)

        member_role_ids = {r.id for r in member.roles}
        if member_role_ids & exec_ids:
            return True

        allowed_names = {
            "community executive",
            "executive director",
            "community director",
            "chief community officer",
            "community management",
            "founder",
        }
        member_role_names = {r.name.lower().strip() for r in member.roles}
        if member_role_names & allowed_names:
            return True

        return False

    async def execute_giverole(
        self,
        guild: discord.Guild,
        issuer: discord.Member,
        role: discord.Role,
        targets_str: str,
        reason: str | None = None,
        interaction: discord.Interaction | None = None,
        ctx: commands.Context | None = None,
    ):
        # 1. Authorization check
        if not self.is_community_executive(issuer):
            err_msg = "❌ Access Denied: This command is restricted to Community Executives."
            if interaction:
                return await interaction.followup.send(err_msg, ephemeral=True)
            elif ctx:
                return await ctx.send(err_msg)

        # 2. Hierarchy and safety checks
        if role == guild.default_role:
            err_msg = "❌ Error: Cannot assign the `@everyone` default role."
            if interaction:
                return await interaction.followup.send(err_msg, ephemeral=True)
            elif ctx:
                return await ctx.send(err_msg)

        if role.managed:
            err_msg = f"❌ Error: Role **{role.name}** is managed by an external integration/bot and cannot be manually assigned."
            if interaction:
                return await interaction.followup.send(err_msg, ephemeral=True)
            elif ctx:
                return await ctx.send(err_msg)

        if role >= guild.me.top_role:
            err_msg = f"❌ Hierarchy Error: The bot cannot assign **{role.name}** because it is equal to or higher than the bot's highest role ({guild.me.top_role.name})."
            if interaction:
                return await interaction.followup.send(err_msg, ephemeral=True)
            elif ctx:
                return await ctx.send(err_msg)

        if issuer != guild.owner and role >= issuer.top_role:
            err_msg = f"❌ Hierarchy Error: You cannot assign **{role.name}** because it is equal to or higher than your highest role ({issuer.top_role.name})."
            if interaction:
                return await interaction.followup.send(err_msg, ephemeral=True)
            elif ctx:
                return await ctx.send(err_msg)

        # 3. Target parsing: "everyone" vs multiple members
        clean_targets = targets_str.strip()
        is_everyone = bool(re.search(r"\b(everyone|@everyone|all)\b", clean_targets, re.IGNORECASE))

        target_members: list[discord.Member] = []

        if is_everyone:
            if not guild.chunked:
                await guild.chunk()
            # Target all non-bot members
            target_members = [m for m in guild.members if not m.bot]
        else:
            seen_ids = set()

            # Mentions from context if prefix command
            if ctx and ctx.message.mentions:
                for m in ctx.message.mentions:
                    if m.id not in seen_ids:
                        seen_ids.add(m.id)
                        target_members.append(m)

            # Mentions matching <@!12345> or <@12345>
            for mid in re.findall(r"<@!?(\d{17,20})>", clean_targets):
                uid = int(mid)
                if uid not in seen_ids:
                    mem = guild.get_member(uid)
                    if mem:
                        seen_ids.add(uid)
                        target_members.append(mem)

            # Raw snowflake IDs
            for mid in re.findall(r"\b\d{17,20}\b", clean_targets):
                uid = int(mid)
                if uid not in seen_ids and uid != role.id:
                    mem = guild.get_member(uid)
                    if mem:
                        seen_ids.add(uid)
                        target_members.append(mem)

            # Usernames / Nicknames if no members matched yet
            if not target_members:
                tokens = [t.strip().strip(",;\"'") for t in clean_targets.split() if t.strip()]
                for tok in tokens:
                    if not tok or tok.startswith("@&"):
                        continue
                    mem = guild.get_member_named(tok) or discord.utils.find(
                        lambda m: m.name.lower() == tok.lower() or (m.nick and m.nick.lower() == tok.lower()),
                        guild.members,
                    )
                    if mem and mem.id not in seen_ids:
                        seen_ids.add(mem.id)
                        target_members.append(mem)

        if not target_members:
            err_msg = "❌ Target Error: No valid members found. Specify target members via mention (`@user`), user IDs, or use `'everyone'`."
            if interaction:
                return await interaction.followup.send(err_msg, ephemeral=True)
            elif ctx:
                return await ctx.send(err_msg)

        to_add = [m for m in target_members if role not in m.roles]
        already_have = [m for m in target_members if role in m.roles]

        if not to_add:
            msg = f"ℹ️ All {len(target_members)} target member(s) already possess the **{role.name}** role."
            if interaction:
                return await interaction.followup.send(msg, ephemeral=False)
            elif ctx:
                return await ctx.send(msg)

        # 4. Status update
        scope_desc = "`@everyone` (Server-Wide)" if is_everyone else f"{len(target_members)} member(s)"
        status_text = f"⏳ **Assigning role {role.mention} to {len(to_add)} member(s)...** (Scope: {scope_desc})"
        progress_msg = None
        if interaction:
            progress_msg = await interaction.followup.send(status_text)
        elif ctx:
            progress_msg = await ctx.send(status_text)

        # 5. Process role assignments with rate-limit handling
        success_count = 0
        failed_count = 0
        audit_reason = f"Executive bulk role grant by {issuer.name} ({issuer.id}) via giverole"
        if reason:
            audit_reason += f": {reason}"

        for i, member in enumerate(to_add, 1):
            try:
                await member.add_roles(role, reason=audit_reason)
                success_count += 1
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException as e:
                failed_count += 1
                logger.error(f"Failed to add role {role.name} to {member.name}: {e}")

            if len(to_add) > 10 and (i % 10 == 0 or i == len(to_add)):
                if progress_msg:
                    try:
                        await progress_msg.edit(content=f"⏳ **Assigning role {role.mention}...** ({i}/{len(to_add)} processed)")
                    except Exception:
                        pass

            if len(to_add) > 1:
                await asyncio.sleep(0.4)

        # 6. Final Summary Embed
        embed = discord.Embed(
            title="✅ Role Distribution Completed",
            description=f"Successfully distributed **{role.mention}**.",
            color=role.color if role.color.value != 0 else discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🏷️ Role", value=f"{role.mention} (`{role.name}`)", inline=True)
        embed.add_field(name="🎯 Scope", value=scope_desc, inline=True)
        embed.add_field(name="👑 Authorized By", value=f"{issuer.mention} (`{issuer.name}`)", inline=True)
        embed.add_field(name="➕ Granted", value=f"**{success_count}** member(s)", inline=True)
        embed.add_field(name="⏩ Already Had Role", value=f"{len(already_have)} member(s)", inline=True)
        if failed_count > 0:
            embed.add_field(name="⚠️ Failed / Skipped", value=f"{failed_count} member(s)", inline=True)
        if reason:
            embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Circuit Verse • Executive Role Distribution")

        if progress_msg:
            try:
                await progress_msg.edit(content=None, embed=embed)
            except Exception:
                if interaction:
                    await interaction.followup.send(embed=embed)
                elif ctx:
                    await ctx.send(embed=embed)
        else:
            if interaction:
                await interaction.followup.send(embed=embed)
            elif ctx:
                await ctx.send(embed=embed)

        # 7. Audit Log Channel
        log_ch = self.get_log_channel(guild)
        if log_ch:
            log_embed = discord.Embed(
                title="🛡️ Executive Role Distribution Log",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            log_embed.add_field(name="Role Granted", value=f"{role.name} (`{role.id}`)", inline=True)
            log_embed.add_field(name="Scope", value=scope_desc, inline=True)
            log_embed.add_field(name="Authorized By", value=f"{issuer.mention} (`{issuer.id}`)", inline=True)
            log_embed.add_field(name="Granted Count", value=str(success_count), inline=True)
            log_embed.add_field(name="Skipped (Already Held)", value=str(len(already_have)), inline=True)
            log_embed.add_field(name="Failed", value=str(failed_count), inline=True)
            if reason:
                log_embed.add_field(name="Reason", value=reason, inline=False)
            try:
                await log_ch.send(embed=log_embed)
            except Exception as e:
                logger.error(f"Failed to post to audit log channel: {e}")

    @app_commands.command(
        name="giverole",
        description="Assign a role to multiple members or everyone (Restricted to Community Executives)",
    )
    @app_commands.describe(
        role="The Discord role to grant",
        targets="Target members (@user1 @user2, user IDs, or 'everyone')",
        reason="Optional reason for the audit log",
    )
    async def slash_giverole(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        targets: str,
        reason: str | None = None,
    ):
        await interaction.response.defer(ephemeral=False)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.followup.send("❌ Error: Could not verify server member.", ephemeral=True)

        await self.execute_giverole(
            guild=interaction.guild,
            issuer=interaction.user,
            role=role,
            targets_str=targets,
            reason=reason,
            interaction=interaction,
        )

    @commands.command(name="giverole", aliases=["addrole", "grole"])
    async def prefix_giverole(self, ctx: commands.Context, *, args: str):
        """
        Assign a role to multiple members or everyone. Restricted to Community Executives.
        Usage:
          !giverole @Role @user1 @user2
          !giverole @Role everyone
          !giverole "Role Name" 123456789012345678, 234567890123456789
          !giverole @Role everyone reason: Event Participation
        """
        if not isinstance(ctx.author, discord.Member):
            return

        target_role: discord.Role | None = None
        remaining_args = args
        reason: str | None = None

        # Check for optional reason:
        if "reason:" in remaining_args.lower():
            parts = re.split(r"reason:", remaining_args, flags=re.IGNORECASE, maxsplit=1)
            remaining_args = parts[0].strip()
            reason = parts[1].strip()

        # 1. Check if role was mentioned
        if ctx.message.role_mentions:
            target_role = ctx.message.role_mentions[0]
            remaining_args = re.sub(rf"<@&{target_role.id}>", "", remaining_args).strip()
        else:
            # 2. Check for role name match
            matched_role = None
            for r in sorted(ctx.guild.roles, key=lambda x: len(x.name), reverse=True):
                if r == ctx.guild.default_role:
                    continue
                pattern = rf'(?:^|\s)[\"\']?{re.escape(r.name)}[\"\']?(?:\s|$)'
                match = re.search(pattern, remaining_args, re.IGNORECASE)
                if match:
                    matched_role = r
                    remaining_args = remaining_args[: match.start()] + " " + remaining_args[match.end() :]
                    remaining_args = remaining_args.strip()
                    break

            if not matched_role:
                # 3. Check for numeric role ID
                for token in remaining_args.split():
                    if token.isdigit():
                        r = ctx.guild.get_role(int(token))
                        if r:
                            matched_role = r
                            remaining_args = remaining_args.replace(token, "", 1).strip()
                            break

            target_role = matched_role

        if not target_role:
            return await ctx.send(
                "❌ Could not determine target role.\n"
                "**Usage:** `!giverole <@Role or \"Role Name\"> <@user1 @user2 ... or 'everyone'> [reason: ...]`"
            )

        if not remaining_args:
            return await ctx.send(
                f"❌ Please specify target members or `everyone`.\n"
                f"**Example:** `!giverole {target_role.mention} @User1 @User2` or `!giverole {target_role.mention} everyone`"
            )

        await self.execute_giverole(
            guild=ctx.guild,
            issuer=ctx.author,
            role=target_role,
            targets_str=remaining_args,
            reason=reason,
            ctx=ctx,
        )

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
