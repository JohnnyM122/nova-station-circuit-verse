import discord
from discord.ext import commands
from discord import ui
import asyncio
import logging
import io

logger = logging.getLogger("CVNovaHelper.support_tickets")

CATEGORY_CONFIG = {
    "comm_support": {
        "name": "Community Support",
        "emoji": "🤝",
        "prefix": "comm",
        "color": "#3498db",
        "target_category_name": "Community Tickets",
        "subject_placeholder": "e.g. Website login issue, Discord roles, general question",
        "identity_label": "Discord Username / Website Account",
        "identity_placeholder": "Your username or registered account name",
        "details_placeholder": "Please explain your question or issue in detail...",
        "staff_roles": [1567491705266245713, 1567491704544698428, 1567474473404338216, 1567475021906186270], # Comm Ticket Support, Comm Ticket Admin, Comm Management, Dept.Director GC
        "relay_channel_id": None,
    },
    "mc_support": {
        "name": "MC Staff Support",
        "emoji": "⛏️",
        "prefix": "mc-supp",
        "color": "#2ecc71",
        "target_category_name": "MC Staff Tickets",
        "subject_placeholder": "e.g. Land claim dispute, voice chat trouble, spawn issue",
        "identity_label": "Minecraft Username (IGN)",
        "identity_placeholder": "e.g. Steve123",
        "details_placeholder": "Please provide your in-game coordinates, world, and what happened...",
        "staff_roles": [1567474481180446761, 1567491706935447562, 1567491706335789056, 1567475022405173320, 1567449697101287467], # MC Ticket Support, MC Ticket Admin, MC Staff, Dept.Director MC, MC Host
        "relay_channel_id": None,
    },
    "mc_bug": {
        "name": "MC Bug Report",
        "emoji": "🐛",
        "prefix": "mc-bug",
        "color": "#e67e22",
        "target_category_name": "MC Staff Tickets",
        "subject_placeholder": "e.g. Duplication glitch, block glitch, voice chat disconnect",
        "identity_label": "Minecraft Username & Coords",
        "identity_placeholder": "e.g. Alex at X: 150 Y: 64 Z: -320",
        "details_placeholder": "Steps to reproduce:\n1. ...\n2. ...\nExpected behavior vs actual behavior:\n...",
        "staff_roles": [1567491706935447562, 1567491706335789056, 1567474481180446761, 1567475022405173320], # MC Ticket Support, MC Ticket Admin, MC Staff, MC Director
        "relay_channel_id": None,
    },
    "mc_report": {
        "name": "MC Player/Staff Report",
        "emoji": "⚖️",
        "prefix": "mc-rep",
        "color": "#e74c3c",
        "target_category_name": "MC Staff Tickets",
        "subject_placeholder": "e.g. Griefing at base, X-ray usage, harassment, staff misconduct",
        "identity_label": "Reported Player / Staff IGN",
        "identity_placeholder": "IGN of the accused person(s)",
        "details_placeholder": "Date & Time:\nLocation/Coords:\nRule Violated:\nWitnesses & Evidence:\nFull Description:\n...",
        "staff_roles": [1567491706335789056, 1567449697101287467, 1567475022405173320, 1567477045964054598], # Confidential: MC Ticket Admin, MC Host, MC Director, Executive Director
        "relay_channel_id": None,
    },
    "ns13_support": {
        "name": "NS13 Staff Support",
        "emoji": "🚀",
        "prefix": "ns13-supp",
        "color": "#3498db",
        "target_category_name": "NS13 Staff Tickets",
        "subject_placeholder": "e.g. Ban appeal, note dispute, rule clarification, ticket follow-up",
        "identity_label": "BYOND Ckey & Character Name",
        "identity_placeholder": "e.g. Ckey: SpaceGuy, Char: John Doe",
        "details_placeholder": "Please provide Round ID (if known), admin involved (if known), and detailed explanation...",
        "staff_roles": [1567491708814364692, 1567491707803799572, 1567449653233057912, 1567475022724079637, 1567449658639384678], # NS13 Ticket Support, NS13 Ticket Admin, NS13 Staff, NS13 Director, NS13 Host
        "relay_channel_id": None,
    },
    "ns13_mentor": {
        "name": "NS13 Mentor Support",
        "emoji": "🩺",
        "prefix": "ns13-mentor",
        "color": "#1abc9c",
        "target_category_name": "NS13 Staff Tickets",
        "subject_placeholder": "e.g. How to set up TEG engine, chemistry recipes, surgery guide",
        "identity_label": "BYOND Ckey & Job Role",
        "identity_placeholder": "e.g. Ckey: NewPlayer, Job: Station Engineer",
        "details_placeholder": "What department or mechanic do you need guidance on? Ask any questions...",
        "staff_roles": [1567491711398191155, 1567491710643343470, 1567449587839410209, 1567449590733602847, 1567491708814364692, 1567491707803799572], # NS13 Mentor Ticket Support/Admin, Mentors, NS13 Ticket Support/Admin
        "relay_channel_id": None,
    },
    "ns13_bug": {
        "name": "NS13 Bug Report",
        "emoji": "🐛",
        "prefix": "ns13-bug",
        "color": "#9b59b6",
        "target_category_name": "NS13 Staff Tickets",
        "subject_placeholder": "e.g. Atmospheric pipe runtime, item duplication, map glitch",
        "identity_label": "Round ID & Ckey",
        "identity_placeholder": "e.g. Round 451, Ckey: TechGuy",
        "details_placeholder": "Steps to reproduce:\n1. ...\n2. ...\nExpected behavior vs runtime error/glitch:\n...",
        "staff_roles": [1567491708814364692, 1567491707803799572, 1567449653233057912, 1567475022724079637], # NS13 Ticket Support, NS13 Ticket Admin, NS13 Staff, NS13 Director
        "relay_channel_id": None,
    },
    "ns13_report": {
        "name": "NS13 Player/Staff Report",
        "emoji": "⚖️",
        "prefix": "ns13-rep",
        "color": "#c0392b",
        "target_category_name": "NS13 Staff Tickets",
        "subject_placeholder": "e.g. Griefing, self-antagging, admin abuse, discord rule violation",
        "identity_label": "Accused Ckey / Admin / Character",
        "identity_placeholder": "Ckey and character name of the accused",
        "details_placeholder": "Round ID & Timestamp:\nRule Violated:\nWitnesses / Logs:\nFull Description:\n...",
        "staff_roles": [1567491707803799572, 1567449658639384678, 1567475022724079637, 1567477045964054598], # Confidential: NS13 Ticket Admin, NS13 Host, NS13 Director, Executive Director
        "relay_channel_id": None,
    },
    "pz_support": {
        "name": "Project Zomboid Support",
        "emoji": "🧟",
        "prefix": "pz-supp",
        "color": "#e74c3c",
        "target_category_name": "PZ Staff Tickets",
        "subject_placeholder": "e.g. Safehouse claim, lost character, server connection issue",
        "identity_label": "PZ Username / Steam Name",
        "identity_placeholder": "Your in-game character or Steam profile name",
        "details_placeholder": "Please provide server, coordinates, and details of your request...",
        "staff_roles": [1567692607054942318, 1567692604340969713, 1567692601291702432, 1567692582849351711], # PZ Ticket Support, PZ Ticket Admin, PZ Staff, PZ Host
        "relay_channel_id": None,
    },
    "pz_report": {
        "name": "PZ Player/Staff Report",
        "emoji": "⚖️",
        "prefix": "pz-rep",
        "color": "#c0392b",
        "target_category_name": "PZ Staff Tickets",
        "subject_placeholder": "e.g. Safehouse griefing, theft, non-PvP zone attack, misconduct",
        "identity_label": "Reported Player / Staff Name",
        "identity_placeholder": "In-game character name or Steam name of the accused",
        "details_placeholder": "Date & Time:\nLocation/Coords:\nRule Violated:\nWitnesses & Evidence:\nFull Description:\n...",
        "staff_roles": [1567692604340969713, 1567692582849351711, 1567477045964054598], # PZ Ticket Admin, PZ Host, Executive Director
        "relay_channel_id": None,
    },
    "unturned_support": {
        "name": "Unturned Staff Support",
        "emoji": "🌲",
        "prefix": "unt-supp",
        "color": "#27ae60",
        "target_category_name": "Unturned Staff Tickets",
        "subject_placeholder": "e.g. Base claim dispute, kit issue, connection trouble",
        "identity_label": "Unturned In-Game Name / Steam64 ID",
        "identity_placeholder": "Your character name or Steam64 ID",
        "details_placeholder": "Please provide details, map location, and what happened...",
        "staff_roles": [1568805610219372690, 1568805609158082641, 1568805607836745910, 1568805606192848993, 1568805604447752263], # Unturned Staff, Mod, Admin, Manager, Host
        "relay_channel_id": None,
    },
    "unturned_report": {
        "name": "Unturned Player/Staff Report",
        "emoji": "⚖️",
        "prefix": "unt-rep",
        "color": "#e74c3c",
        "target_category_name": "Unturned Staff Tickets",
        "subject_placeholder": "e.g. Cheating, hacking, base glitching, combat logging, staff misconduct",
        "identity_label": "Reported Player / Staff Name / Steam ID",
        "identity_placeholder": "Name or Steam ID of the accused player",
        "details_placeholder": "Date & Time:\nLocation/Coords:\nRule Violated:\nWitnesses & Evidence (Video/Screenshots):\nFull Description:\n...",
        "staff_roles": [1568805607836745910, 1568805606192848993, 1568805604447752263, 1567477045964054598], # Admin, Manager, Host, Executive Director
        "relay_channel_id": None,
    }
}

class TicketCreateModal(ui.Modal):
    def __init__(self, bot, category_key: str):
        self.bot = bot
        self.category_key = category_key
        category_info = CATEGORY_CONFIG.get(category_key, CATEGORY_CONFIG["comm_support"])
        super().__init__(title=f"Open: {category_info['name'][:30]}")

        self.subject = ui.TextInput(
            label="Subject / Topic",
            placeholder=category_info["subject_placeholder"],
            max_length=100,
            required=True
        )
        self.identity = ui.TextInput(
            label=category_info["identity_label"],
            placeholder=category_info["identity_placeholder"],
            max_length=100,
            required=False
        )
        self.details = ui.TextInput(
            label="Details & Context",
            style=discord.TextStyle.paragraph,
            placeholder=category_info["details_placeholder"],
            max_length=2000,
            required=True
        )

        self.add_item(self.subject)
        self.add_item(self.identity)
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ This command must be used in the server.", ephemeral=True)
            return

        category_info = CATEGORY_CONFIG.get(self.category_key, CATEGORY_CONFIG["comm_support"])

        # Target Dedicated Ticket Category
        target_cat_name = category_info.get("target_category_name", "Community Tickets")
        target_category = None
        for cat in guild.categories:
            if target_cat_name.lower() in cat.name.lower():
                target_category = cat
                break

        if not target_category:
            # Fallback to Community Support Area if not found
            for cat in guild.categories:
                if "community support" in cat.name.lower() or "support area" in cat.name.lower():
                    target_category = cat
                    break

        safe_username = "".join(c for c in interaction.user.name.lower() if c.isalnum() or c in "-_")[:12]
        expected_channel_name = f"{category_info['prefix']}-{safe_username}"

        # Prevent duplicate tickets in same category
        for ch in guild.text_channels:
            if expected_channel_name in ch.name and ch.category == target_category:
                await interaction.response.send_message(
                    f"⚠️ You already have an active ticket open in this category: {ch.mention}", ephemeral=True
                )
                return

        # Setup fine-grained permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True, embed_links=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_channels=True, manage_messages=True, embed_links=True
            )
        }

        notified_roles = []
        for role_id in category_info["staff_roles"]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, attach_files=True, read_message_history=True
                )
                notified_roles.append(role)

        try:
            ticket_channel = await guild.create_text_channel(
                name=f"{category_info['emoji']}・{expected_channel_name}",
                category=target_category,
                overwrites=overwrites,
                topic=f"Circuit Verse Ticket [{category_info['name']}] for {interaction.user.name} ({interaction.user.id}) | {self.subject.value}"
            )
        except Exception as e:
            logger.error(f"Failed to create ticket channel: {e}")
            await interaction.response.send_message(f"❌ Failed to create ticket channel: `{e}`", ephemeral=True)
            return

        # Ticket Welcome Embed
        embed = discord.Embed(
            title=f"{category_info['emoji']} {category_info['name']}: {self.subject.value}",
            description=(
                f"Welcome {interaction.user.mention} to Circuit Verse Support!\n\n"
                f"Your request has been routed to our dedicated **{category_info['name']} Team**.\n\n"
                f"**Submitted Identifier / Reference**:\n`{self.identity.value if self.identity.value else 'None provided'}`\n\n"
                f"**Issue Description**:\n```\n{self.details.value}\n```\n"
                "Please attach any relevant screenshots, crash logs, or coordinates below to speed up resolution."
            ),
            color=discord.Color.from_str(category_info["color"])
        )
        embed.add_field(name="Ticket Creator", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="Category", value=category_info["name"], inline=True)
        embed.set_footer(text="Use the buttons below to claim or close this ticket.")

        view = PersistentCloseView(self.bot, creator_id=interaction.user.id)
        
        # Ping creator and relevant staff
        mention_pings = [interaction.user.mention]
        if notified_roles:
            mention_pings.append(notified_roles[0].mention)

        await ticket_channel.send(content=" ".join(mention_pings), embed=embed, view=view)

        await interaction.response.send_message(
            f"✅ Your ticket has been opened successfully: {ticket_channel.mention}", ephemeral=True
        )

class TicketCategorySelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Community Support",
                value="comm_support",
                description="General help, Discord roles, website support, account inquiries",
                emoji="🤝"
            ),
            discord.SelectOption(
                label="MC Staff Support",
                value="mc_support",
                description="Minecraft gameplay help, voice chat, claims, land issues",
                emoji="⛏️"
            ),
            discord.SelectOption(
                label="MC Bug Report",
                value="mc_bug",
                description="Minecraft glitches, plugin errors, dupes, or server crashes",
                emoji="🐛"
            ),
            discord.SelectOption(
                label="MC Player/Staff Report",
                value="mc_report",
                description="Confidential report on Minecraft griefing, cheating, or misconduct",
                emoji="⚖️"
            ),
            discord.SelectOption(
                label="NS13 Staff Support",
                value="ns13_support",
                description="Nova Station 13 game issues, ban appeals, and ahelp follow-ups",
                emoji="🚀"
            ),
            discord.SelectOption(
                label="NS13 Mentor Support",
                value="ns13_mentor",
                description="Nova Station 13 mechanics, jobs, chemistry, surgery, how to play",
                emoji="🩺"
            ),
            discord.SelectOption(
                label="NS13 Bug Report",
                value="ns13_bug",
                description="Nova Station 13 BYOND runtimes, mapping bugs, code flaws, exploits",
                emoji="🐛"
            ),
            discord.SelectOption(
                label="NS13 Player/Staff Report",
                value="ns13_report",
                description="Confidential report on NS13 rule violations, griefing, or misconduct",
                emoji="⚖️"
            ),
            discord.SelectOption(
                label="Project Zomboid Support",
                value="pz_support",
                description="Project Zomboid gameplay, safehouse claims, connection support",
                emoji="🧟"
            ),
            discord.SelectOption(
                label="PZ Player/Staff Report",
                value="pz_report",
                description="Confidential report on PZ safehouse griefing, theft, or misconduct",
                emoji="⚖️"
            ),
            discord.SelectOption(
                label="Unturned Staff Support",
                value="unturned_support",
                description="Unturned gameplay help, base claims, kit issues, server support",
                emoji="🌲"
            ),
            discord.SelectOption(
                label="Unturned Player/Staff Report",
                value="unturned_report",
                description="Confidential report on Unturned cheats, exploits, or misconduct",
                emoji="⚖️"
            ),
        ]
        super().__init__(
            placeholder="Select a Ticket Category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select_v3"
        )

    async def callback(self, interaction: discord.Interaction):
        category_key = self.values[0]
        modal = TicketCreateModal(self.view.bot, category_key)
        await interaction.response.send_modal(modal)

class PersistentTicketView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketCategorySelect())

class PersistentCloseView(ui.View):
    def __init__(self, bot, creator_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.creator_id = creator_id

    @ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="🙋", custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        cfg = self.bot.config
        ticket_roles = cfg.get("ticket_roles", {})

        # Staff can claim
        is_staff = interaction.user.guild_permissions.administrator or any(
            r.id in ticket_roles.values() for r in interaction.user.roles
        ) or any(any(k in r.name for k in ["Staff", "Admin", "Mod", "Mentor", "Support", "Ticket", "Director", "Manager"]) for r in interaction.user.roles)

        if not is_staff:
            await interaction.response.send_message("🚫 Only staff members can claim tickets.", ephemeral=True)
            return

        button.label = f"Claimed by {interaction.user.display_name}"
        button.disabled = True
        button.style = discord.ButtonStyle.success
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🙋 **{interaction.user.display_name}** has claimed this ticket and will be assisting you.")

    @ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        await interaction.response.send_message("🔒 **Ticket Closing**: Generating transcript and closing channel in **5 seconds**...")

        # Build transcript
        transcript_lines = [
            f"=== CIRCUIT VERSE TICKET TRANSCRIPT ===",
            f"Channel: {channel.name}",
            f"Closed by: {interaction.user.name} ({interaction.user.id})",
            f"Date: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"======================================\n"
        ]

        async for msg in channel.history(limit=500, oldest_first=True):
            author_str = f"[{msg.created_at.strftime('%Y-%m-%d %H:%M')}] {msg.author.name}"
            content_str = msg.content
            if msg.attachments:
                att_str = " | Attachments: " + ", ".join([a.url for a in msg.attachments])
                content_str += att_str
            transcript_lines.append(f"{author_str}: {content_str}")

        transcript_data = "\n".join(transcript_lines)
        file_obj = discord.File(io.BytesIO(transcript_data.encode("utf-8")), filename=f"{channel.name}-transcript.txt")

        # Send to discord-logs channel if available
        log_channel = None
        for ch in guild.text_channels:
            if "discord-logs" in ch.name:
                log_channel = ch
                break

        if log_channel:
            log_embed = discord.Embed(
                title=f"📁 Ticket Closed: {channel.name}",
                description=f"Ticket closed by {interaction.user.mention}.",
                color=discord.Color.dark_gray(),
                timestamp=discord.utils.utcnow()
            )
            try:
                await log_channel.send(embed=log_embed, file=file_obj)
            except Exception as e:
                logger.error(f"Failed to post transcript: {e}")

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Failed to delete channel: {e}")

class SupportTicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(PersistentTicketView(bot))
        self.bot.add_view(PersistentCloseView(bot))

    @commands.command(name="post_ticket_panel")
    @commands.has_permissions(administrator=True)
    async def post_panel_command(self, ctx: commands.Context):
        """Re-post the unified ticket guidance manual & persistent selection panel"""
        # 1. Guide Embed with all templates
        guide_embed = discord.Embed(
            title="🎫 Circuit Verse Support Desk & Issue Submission Guidelines",
            description=(
                "Welcome to the **Circuit Verse Official Helpdesk**. To guarantee the fastest resolution, "
                "please review the submission templates below before selecting your ticket category.\n\n"
                "All tickets create a private, confidential channel routed to the designated server staff category."
            ),
            color=discord.Color.from_str("#3498db")
        )

        guide_embed.add_field(
            name="🐛 Bug Report Templates (MC / NS13 / PZ / Unturned)",
            value=(
                "```markdown\n"
                "• Service / Server: (Minecraft / Nova Station 13 / Project Zomboid / Unturned)\n"
                "• IGN / Ckey / Steam ID: (e.g. Ckey: SpaceGuy, IGN: Player1)\n"
                "• Coordinates / Location: (e.g. X: 120, Y: 65, Z: -300 or Station Medbay)\n"
                "• Description of Bug: (What happened?)\n"
                "• Steps to Reproduce:\n"
                "  1. Step one...\n"
                "  2. Step two...\n"
                "• Expected vs Actual Result:\n"
                "• Error Logs / Screenshots: (Attach images/files)\n"
                "```"
            ),
            inline=False
        )

        guide_embed.add_field(
            name="⚖️ Player & Staff Misconduct Report Template",
            value=(
                "```markdown\n"
                "• Server / Platform: (Minecraft / NS13 / PZ / Unturned / Discord)\n"
                "• Accused Player / Staff: (IGN, Ckey, Steam ID, or Discord User)\n"
                "• Date, Time & Timezone: (e.g. Nov 7, 09:30 PM EST)\n"
                "• Rule Broken: (Griefing, Cheating, Harassment, Self-Antagging, Abuse)\n"
                "• Witnesses / Evidence: (Video, screenshots, logs)\n"
                "• Detailed Narrative: (Objective account of the incident)\n"
                "```\n"
                "*Note: Player and staff misconduct reports are strictly confidential and visible only to Executive Management.*"
            ),
            inline=False
        )

        guide_embed.set_footer(text="Circuit Verse Helpdesk Standards • Respectful & Objective Reports Only")

        # 2. Ticket Selector Panel Embed
        panel_embed = discord.Embed(
            title="📬 Open a Support Ticket",
            description=(
                "Select the appropriate department from the dropdown menu below to begin:\n\n"
                "🤝 **Community Support** — General inquiries, Discord roles, website help.\n"
                "⛏️ **MC Staff Support & Reports** — Minecraft gameplay, claims, bug & player reports.\n"
                "🚀 **NS13 Staff Support & Mentors** — Nova Station 13 disputes, mentor tutorials, bugs.\n"
                "🧟 **Project Zomboid Support** — PZ gameplay, safehouse claims, player reports.\n"
                "🌲 **Unturned Support** — Unturned gameplay, base claims, reports & technical help."
            ),
            color=discord.Color.from_str("#00f0ff")
        )
        panel_embed.set_footer(text="Circuit Verse Automated Ticket System • Powered by Circuit Verse Helper")

        view = PersistentTicketView(self.bot)
        await ctx.send(embed=guide_embed)
        await ctx.send(embed=panel_embed, view=view)
        try:
            await ctx.message.delete()
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(SupportTicketsCog(bot))
