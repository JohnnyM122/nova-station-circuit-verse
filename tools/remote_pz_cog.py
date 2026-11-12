import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import logging
import asyncio
import socket
import struct
import json
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("CVNovaHelper.project_zomboid")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
AUDIT_HISTORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pz_audit_history.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_audit_data():
    if not os.path.exists(AUDIT_HISTORY_PATH):
        return {"punishments": [], "notes": {}, "actions": []}
    try:
        with open(AUDIT_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"punishments": [], "notes": {}, "actions": []}


def save_audit_data(data):
    with open(AUDIT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def pz_rcon_command(host: str, port: int, password: str, cmd: str, timeout: float = 5.0) -> str:
    """Execute a Source RCON command against the Project Zomboid server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        # 1. Auth packet (Type 3)
        payload = password.encode("utf-8") + b"\x00\x00"
        packet = struct.pack("<iii", len(payload) + 8, 1001, 3) + payload
        s.sendall(packet)

        resp = s.recv(4096)
        if len(resp) >= 12:
            _, req_id, _ = struct.unpack("<iii", resp[:12])
            if req_id == -1:
                raise PermissionError("RCON authentication failed.")

        # 2. Exec command packet (Type 2)
        cmd_payload = cmd.encode("utf-8") + b"\x00\x00"
        cmd_packet = struct.pack("<iii", len(cmd_payload) + 8, 2002, 2) + cmd_payload
        s.sendall(cmd_packet)

        cmd_resp = s.recv(8192)
        if len(cmd_resp) >= 12:
            body = cmd_resp[12:-2].decode("utf-8", errors="replace")
            return body.strip()
        return ""
    finally:
        s.close()


class PermBanApprovalView(ui.View):
    """Interactive approval view for permanent bans requiring Leadership / Head Mod sign-off."""
    def __init__(self, cog, target_player: str, reason: str, requester_id: int, requester_name: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.target_player = target_player
        self.reason = reason
        self.requester_id = requester_id
        self.requester_name = requester_name

    @ui.button(label="Approve Permanent Ban", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="pz_permban_approve")
    async def approve_btn(self, interaction: discord.Interaction, button: ui.Button):
        if not self.cog.has_pz_tier(interaction.user, ["leadership", "head_mod"]):
            return await interaction.response.send_message(
                "❌ Only **Head Moderator**, **PZ Server Host**, or **Department Director** can approve permanent bans.",
                ephemeral=True
            )

        await interaction.response.defer()
        try:
            res = await self.cog.run_rcon(f'banuser "{self.target_player}" -r "{self.reason}"')
        except Exception as e:
            return await interaction.followup.send(f"❌ RCON Error executing ban: `{e}`", ephemeral=True)

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_red()
        embed.title = "🔨 Permanent Ban Approved & Executed"
        embed.add_field(name="✅ Approved By", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=False)
        if res:
            embed.add_field(name="🖥️ Server Output", value=f"```{res[:500]}```", inline=False)

        await interaction.message.edit(embed=embed, view=self)
        await self.cog.record_audit(
            interaction.guild,
            actor=interaction.user,
            action="Permanent Ban Approved",
            target=self.target_player,
            reason=f"{self.reason} (Requested by {self.requester_name})"
        )

    @ui.button(label="Deny Request", style=discord.ButtonStyle.secondary, emoji="✖️", custom_id="pz_permban_deny")
    async def deny_btn(self, interaction: discord.Interaction, button: ui.Button):
        if not self.cog.has_pz_tier(interaction.user, ["leadership", "head_mod"]):
            return await interaction.response.send_message(
                "❌ Only **Head Moderator** or **Server Leadership** can deny permanent ban requests.",
                ephemeral=True
            )

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.light_grey()
        embed.title = "✖️ Permanent Ban Request Denied"
        embed.add_field(name="🛑 Denied By", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)
        await self.cog.record_audit(
            interaction.guild,
            actor=interaction.user,
            action="Permanent Ban Denied",
            target=self.target_player,
            reason=f"Denied request from {self.requester_name}"
        )


class RescueClaimView(ui.View):
    """Interactive claim view for Survivor Rescue Service requests."""
    def __init__(self, cog, survivor_name: str, location_desc: str, discord_user_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.survivor_name = survivor_name
        self.location_desc = location_desc
        self.discord_user_id = discord_user_id

    @ui.button(label="Claim & Teleport (In-Game)", style=discord.ButtonStyle.success, emoji="🚁", custom_id="pz_rescue_claim")
    async def claim_btn(self, interaction: discord.Interaction, button: ui.Button):
        if not self.cog.has_pz_tier(interaction.user, ["leadership", "moderation", "support", "gm"]):
            return await interaction.response.send_message("❌ Only authorized PZ Staff can claim rescue tickets.", ephemeral=True)

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "🚁 Survivor Rescue Claimed"
        embed.add_field(name="🛡️ Responded By", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)
        await self.cog.record_audit(
            interaction.guild,
            actor=interaction.user,
            action="Survivor Rescue Claimed",
            target=self.survivor_name,
            reason=f"Location/Issue: {self.location_desc}"
        )


class ProjectZomboidCog(commands.Cog):
    """
    Comprehensive Project Zomboid Administration, Live Monitoring, Event Management,
    Survivor Rescue Service, Accountability & Audit Logging Suite.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.was_offline = None
        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    def get_pz_cfg(self):
        cfg = load_config()
        return cfg.get("pz_server", {}), cfg.get("pz_roles", {})

    async def run_rcon(self, cmd: str) -> str:
        pz_cfg, _ = self.get_pz_cfg()
        host = pz_cfg.get("host", "127.0.0.1")
        port = int(pz_cfg.get("rcon_port", 27015))
        pw = pz_cfg.get("rcon_password", "CircuitVerseAdminPZ2026!")
        return await asyncio.to_thread(pz_rcon_command, host, port, pw, cmd)

    def has_pz_tier(self, member: discord.Member, allowed_tiers: list[str]) -> bool:
        """Check if a Discord member holds the required PZ staff tier based on the official org chart."""
        if member.guild_permissions.administrator:
            return True

        _, pz_roles = self.get_pz_cfg()
        member_role_ids = {r.id for r in member.roles}

        # Global Executive / Founder bypass
        exec_ids = {
            1564610713216098394,  # Founder
            1567495181794807838,  # Community Executive
            1567482219495301191,  # Community Director
            1567477045964054598,  # Executive Director
            pz_roles.get("Dept.Director (PZ)", 0)
        }
        if member_role_ids & exec_ids:
            return True

        tier_map = {
            "leadership": [
                pz_roles.get("PZ Server Host", 0),
                pz_roles.get("Dept.Director (PZ)", 0)
            ],
            "tech": [
                pz_roles.get("PZ Server Technician", 0),
                pz_roles.get("PZ Lead Developer", 0),
                pz_roles.get("PZ Developer", 0)
            ],
            "head_mod": [
                pz_roles.get("PZ Head Moderator", 0)
            ],
            "moderation": [
                pz_roles.get("PZ Head Moderator", 0),
                pz_roles.get("PZ Senior Moderator", 0),
                pz_roles.get("PZ Moderator", 0)
            ],
            "gm": [
                pz_roles.get("PZ Chief Game Master", 0),
                pz_roles.get("PZ Senior Game Master", 0),
                pz_roles.get("PZ Game Master", 0),
                pz_roles.get("PZ GM Trainee", 0)
            ],
            "gm_senior": [
                pz_roles.get("PZ Chief Game Master", 0),
                pz_roles.get("PZ Senior Game Master", 0)
            ],
            "support": [
                pz_roles.get("PZ Head Support", 0),
                pz_roles.get("PZ Senior Support", 0),
                pz_roles.get("PZ Support Team", 0)
            ],
            "observer": [
                pz_roles.get("PZ Staff Observer", 0)
            ]
        }

        for t in allowed_tiers:
            role_ids = set(tier_map.get(t, [])) - {0}
            if member_role_ids & role_ids:
                return True
        return False

    def check_staff_channel(self, interaction: discord.Interaction) -> bool:
        pz_cfg, _ = self.get_pz_cfg()
        allowed_ch = pz_cfg.get("staff_commands_channel")
        if allowed_ch and interaction.channel_id != allowed_ch:
            return False
        return True

    async def record_audit(self, guild: discord.Guild, actor: discord.Member, action: str, target: str, reason: str, details: str = None):
        """Log every significant staff action to Discord #pz-staff-logs and persistent JSON audit trail."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        audit_data = load_audit_data()
        entry = {
            "timestamp": now_str,
            "actor_id": actor.id,
            "actor_name": actor.name,
            "action": action,
            "target": target,
            "reason": reason,
            "details": details or ""
        }
        audit_data.setdefault("actions", []).append(entry)
        if any(k in action.lower() for k in ["ban", "kick", "warn", "mute"]):
            audit_data.setdefault("punishments", []).append(entry)
        save_audit_data(audit_data)

        pz_cfg, _ = self.get_pz_cfg()
        log_ch_id = pz_cfg.get("staff_logs_channel")
        if log_ch_id and guild:
            log_ch = guild.get_channel(log_ch_id)
            if log_ch:
                embed = discord.Embed(
                    title=f"🛡️ PZ Staff Audit Log — {action}",
                    color=discord.Color.orange(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="👤 Staff Member", value=f"{actor.mention} (`{actor.name}`)", inline=True)
                embed.add_field(name="🎯 Target", value=f"`{target}`", inline=True)
                embed.add_field(name="📝 Reason / Context", value=reason or "N/A", inline=False)
                if details:
                    embed.add_field(name="🖥️ Details", value=f"```{details[:800]}```", inline=False)
                embed.set_footer(text="Circuit Verse • Project Zomboid Accountability System")
                try:
                    await log_ch.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send PZ audit embed: {e}")

    # ==========================================
    # LIVE SERVER STATUS LOOP
    # ==========================================
    
    async def send_status_channel_alert(self, title: str, description: str, color: discord.Color):
        try:
            cfg = load_config()
            ch_id = cfg.get("pz_server", {}).get("status_channel")
            if not ch_id:
                return
            ch = self.bot.get_channel(int(ch_id))
            if ch:
                embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
                embed.set_footer(text="Circuit Verse • Project Zomboid Server Alert")
                await ch.send(embed=embed, delete_after=300)
        except Exception as e:
            logger.error(f"Failed to send PZ status alert: {e}")


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.guild.id != 1564605314752585797:
            return
        # Auto-clear any and each message in PZ-server-logs after 5 minutes (300 seconds)
        if message.channel.id in (1570270312560468041, 1567702389283102813):
            if message.pinned:
                return
            try:
                await message.delete(delay=300)
            except Exception as e:
                logger.debug(f"Failed to schedule delete for PZ log message {message.id}: {e}")

    @tasks.loop(seconds=60)
    async def status_loop(self):
        await self.bot.wait_until_ready()
        try:
            await self.update_status_embed()
        except Exception as e:
            logger.debug(f"PZ status loop error: {e}")

    async def update_status_embed(self):
        cfg = load_config()
        pz_cfg = cfg.get("pz_server", {})
        guild_id = cfg.get("guild_id")
        status_ch_id = pz_cfg.get("status_channel")
        if not guild_id or not status_ch_id:
            return

        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return
        ch = guild.get_channel(int(status_ch_id))
        if not ch:
            return

        online = False
        players_list = []
        try:
            raw = await self.run_rcon("players")
            online = True
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("-"):
                    players_list.append(line.lstrip("-").strip())
        except Exception:
            online = False

        
        if self.was_offline is not None:
            if online and self.was_offline:
                self.was_offline = False
                await self.send_status_channel_alert(
                    "🟢 Project Zomboid Server Online & Operational",
                    "• **Action**: Server initialization complete.\n"
                    "• **Game Version**: Build 42 Dedicated Multi-player\n"
                    "• **Direct Connect**: `pz.circuitverse.online:16261` (or `62.238.81.224:16261`)\n"
                    "• **Web Admin**: **[zcp.circuitverse.online](https://zcp.circuitverse.online)**\n"
                    "• Ready for survivors! Welcome back!",
                    discord.Color.green()
                )
            elif not online and not self.was_offline:
                self.was_offline = True
                await self.send_status_channel_alert(
                    "🔴 Project Zomboid Server Offline / Restarting",
                    "• **Action**: Project Zomboid server process is restarting or undergoing maintenance.\n"
                    "• **Notice**: Player saves and world state are preserved. The server will be back online shortly.",
                    discord.Color.red()
                )
        else:
            self.was_offline = not online

        color = discord.Color.green() if online else discord.Color.red()
        status_badge = "🟢 **ONLINE**" if online else "🔴 **OFFLINE / RESTARTING**"

        embed = discord.Embed(
            title="🧟 Circuit Verse • Project Zomboid Dedicated Server",
            description="Official Survival & Co-op Community Server running **Build 42** on dedicated NVMe Hetzner EX63 Dedicated Server.",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📡 Server Status", value=status_badge, inline=True)
        embed.add_field(name="👥 Survivors Online", value=f"**{len(players_list)} / 32**", inline=True)
        embed.add_field(name="🌍 Region & Ping", value="EU-Central (Low Latency)", inline=True)

        embed.add_field(
            name="🔌 Direct Connection Details",
            value=(
                "• **Server Address:** `pz.circuitverse.online` (Direct IP: `62.238.81.224`)\n"
                "• **Web Panel:** **[zcp.circuitverse.online](https://zcp.circuitverse.online)**\n"
                "• **Game Port:** `16261` (UDP)\n"
                "• **Password:** *None (Open to Community)*"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ World & Gameplay Configuration",
            value=(
                "• **Zombie Population:** Normal (`1.0x` Start ➔ `1.3x` Peak Day 28)\n"
                "• **Day Length:** 1 Real Hour = 1 In-Game Day\n"
                "• **Mode:** Friendly PvE / Co-op Survival (`PVP=false`)\n"
                "• **Admin Suite:** Wess Admin Tools (`F6` In-Game Panel) + RBAC Roles"
            ),
            inline=False
        )

        if players_list:
            embed.add_field(
                name="🏕️ Active Survivors",
                value=", ".join(f"`{p}`" for p in players_list[:25]),
                inline=False
            )


        # Auto-prune PZ server logs older than 5 minutes (300s)
        for log_cid in (1570270312560468041, 1567702389283102813):
            try:
                log_ch = guild.get_channel(log_cid)
                if log_ch:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                    async for m in log_ch.history(limit=50):
                        if not m.pinned and m.created_at < cutoff:
                            try:
                                await m.delete()
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Error pruning PZ log channel {log_cid}: {e}")

        # Auto-prune PZ status transition alerts in status channel older than 5 minutes
        try:
            status_msg_id = pz_cfg.get("status_message_id", 1568828761468698668)
            if ch:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                async for m in ch.history(limit=50):
                    if status_msg_id and m.id == int(status_msg_id):
                        continue
                    if m.pinned:
                        continue
                    if m.author.id == self.bot.user.id and m.created_at < cutoff:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error pruning PZ status alerts: {e}")

        embed.set_footer(text="Updated automatically every 60s • Circuit Verse Helper")

        # Anti-duplicate search and edit logic
        msg_id = pz_cfg.get("status_message_id")
        target_msg = None

        if msg_id:
            try:
                target_msg = await ch.fetch_message(int(msg_id))
            except Exception:
                target_msg = None

        if not target_msg:
            async for m in ch.history(limit=25):
                if m.author == self.bot.user and m.embeds:
                    if "Project Zomboid Dedicated Server" in (m.embeds[0].title or ""):
                        target_msg = m
                        cfg["pz_server"]["status_message_id"] = target_msg.id
                        save_config(cfg)
                        break

        if target_msg:
            await target_msg.edit(embed=embed)
            # Delete any rogue duplicate status embeds in the channel
            try:
                async for extra_m in ch.history(limit=25):
                    if extra_m.id != target_msg.id and extra_m.author == self.bot.user and extra_m.embeds:
                        if "Project Zomboid Dedicated Server" in (extra_m.embeds[0].title or ""):
                            await extra_m.delete()
            except Exception:
                pass
            return

        # Send new message if none exists
        new_msg = await ch.send(embed=embed, delete_after=300)
        cfg["pz_server"]["status_message_id"] = new_msg.id
        save_config(cfg)

    # ==========================================
    # 1. LIVE PLAYER MONITORING COMMANDS
    # ==========================================
    @app_commands.command(name="pz_players", description="View connected Project Zomboid players and live server status")
    async def pz_players(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            raw = await self.run_rcon("players")
            players = [l.lstrip("-").strip() for l in raw.splitlines() if l.strip().startswith("-")]
            embed = discord.Embed(
                title="🧟 Project Zomboid — Connected Survivors",
                description=f"Currently **{len(players)} / 32** survivors connected to `pz.circuitverse.online:16261`.",
                color=discord.Color.green()
            )
            if players:
                embed.add_field(name="Player List", value="\n".join(f"• `{p}`" for p in players), inline=False)
            else:
                embed.add_field(name="Player List", value="*No survivors currently online.*", inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Could not query server via RCON: `{e}`", ephemeral=True)

    @app_commands.command(name="pz_teleport", description="[PZ Staff] Teleport a player to another player or coordinates")
    @app_commands.describe(player1="Player to teleport", player2="Target player to teleport to")
    async def pz_teleport(self, interaction: discord.Interaction, player1: str, player2: str):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "moderation", "gm", "support", "tech"]):
            return await interaction.response.send_message("❌ You do not have permission to use `/pz_teleport`.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f'teleport "{player1}" "{player2}"')
            await self.record_audit(interaction.guild, interaction.user, "Player Teleport", f"{player1} -> {player2}", "Staff teleport command", res)
            await interaction.followup.send(f"✅ Teleported `{player1}` to `{player2}`.\n```{res or 'Success'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    # ==========================================
    # 2. EVENT MANAGEMENT & EMERGENCY BROADCASTS
    # ==========================================
    @app_commands.command(name="pz_broadcast", description="[PZ Staff] Broadcast an official announcement or Emergency Broadcast System alert")
    @app_commands.describe(
        message="Message content to broadcast in-game",
        alert_type="Type of broadcast",
        also_post_discord="Also post to #🎉・pz-events in Discord"
    )
    @app_commands.choices(alert_type=[
        app_commands.Choice(name="📢 Standard Server Announcement", value="standard"),
        app_commands.Choice(name="🚨 Emergency Broadcast System (EBS)", value="ebs"),
        app_commands.Choice(name="🪖 Military Containment Warning", value="military"),
        app_commands.Choice(name="🚁 Evacuation & Supply Drop Alert", value="evac")
    ])
    async def pz_broadcast(
        self,
        interaction: discord.Interaction,
        message: str,
        alert_type: str = "standard",
        also_post_discord: bool = False
    ):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "moderation", "gm", "support"]):
            return await interaction.response.send_message("❌ Insufficient permissions.", ephemeral=True)

        await interaction.response.defer()
        prefix_map = {
            "standard": "[SERVER]",
            "ebs": "[EMERGENCY BROADCAST SYSTEM]",
            "military": "[KNOX CONTAINMENT COMMAND]",
            "evac": "[EVACUATION & AIRDROP ALERT]"
        }
        prefix = prefix_map.get(alert_type, "[SERVER]")
        formatted = f"{prefix} {message}"

        try:
            res = await self.run_rcon(f'servermsg "{formatted}"')
            await self.record_audit(interaction.guild, interaction.user, f"Broadcast ({alert_type.upper()})", "All Players", message, res)

            if also_post_discord:
                pz_cfg, _ = self.get_pz_cfg()
                events_ch_id = 1567702362456465428
                events_ch = interaction.guild.get_channel(events_ch_id)
                if events_ch:
                    ebs_embed = discord.Embed(
                        title=f"📻 {prefix}",
                        description=f"**{message}**",
                        color=discord.Color.red() if alert_type in ("ebs", "military") else discord.Color.gold(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    ebs_embed.set_footer(text=f"Issued by {interaction.user.display_name} • Automated Emergency Broadcast System")
                    await events_ch.send(embed=ebs_embed)

            await interaction.followup.send(f"✅ Broadcast sent in-game: `{formatted}`")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @app_commands.command(name="pz_event", description="[PZ GM / Leadership] Trigger world events, weather, or zombie hordes")
    @app_commands.describe(
        event_type="Event to trigger",
        target_player="Target player (required for createhorde)",
        horde_count="Number of zombies to spawn (1-250, for createhorde)"
    )
    @app_commands.choices(event_type=[
        app_commands.Choice(name="🚁 Trigger Helicopter Event (chopper)", value="chopper"),
        app_commands.Choice(name="🔫 Trigger Gunshot Sound Event (gunshot)", value="gunshot"),
        app_commands.Choice(name="🚨 Trigger Building Alarm (alarm)", value="alarm"),
        app_commands.Choice(name="🌧️ Start Rainstorm (startrain)", value="startrain"),
        app_commands.Choice(name="☀️ Stop Rainstorm (stoprain)", value="stoprain"),
        app_commands.Choice(name="🧟 Spawn Zombie Horde (createhorde)", value="createhorde")
    ])
    async def pz_event(
        self,
        interaction: discord.Interaction,
        event_type: str,
        target_player: str = None,
        horde_count: app_commands.Range[int, 1, 250] = 25
    ):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "gm"]):
            return await interaction.response.send_message("❌ Only **Game Masters** and **Server Leadership** can trigger events.", ephemeral=True)

        await interaction.response.defer()
        if event_type == "createhorde":
            if not target_player:
                return await interaction.followup.send("❌ You must specify `target_player` when spawning a zombie horde.", ephemeral=True)
            cmd = f'createhorde {horde_count} "{target_player}"'
            target_desc = f"{target_player} ({horde_count} zombies)"
        else:
            cmd = event_type
            target_desc = "World"

        try:
            res = await self.run_rcon(cmd)
            await self.record_audit(interaction.guild, interaction.user, f"Event Trigger: {event_type}", target_desc, f"Command: {cmd}", res)
            await interaction.followup.send(f"🎉 Triggered event **`{event_type}`** on `{target_desc}`!\n```{res or 'Executed successfully'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    # ==========================================
    # 3. MODERATION, SAFEHOUSE & PUNISHMENT LOGS
    # ==========================================
    @app_commands.command(name="pz_kick", description="[PZ Mod / Leadership] Kick a player from the Project Zomboid server")
    @app_commands.describe(player="In-game username", reason="Reason for the kick")
    async def pz_kick(self, interaction: discord.Interaction, player: str, reason: str):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "moderation"]):
            return await interaction.response.send_message("❌ Only **Moderators** and **Server Leadership** can kick players.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f'kick "{player}" -r "{reason}"')
            await self.record_audit(interaction.guild, interaction.user, "Player Kick", player, reason, res)
            await interaction.followup.send(f"👢 Kicked **`{player}`** for: *{reason}*\n```{res or 'Done'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @app_commands.command(name="pz_ban", description="[PZ Mod / Leadership] Ban a player (Permanent bans by regular Mods require approval)")
    @app_commands.describe(player="In-game username", reason="Reason for the ban", permanent="Is this a permanent ban?")
    async def pz_ban(self, interaction: discord.Interaction, player: str, reason: str, permanent: bool = False):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "moderation"]):
            return await interaction.response.send_message("❌ Only **Moderators** and **Server Leadership** can ban players.", ephemeral=True)

        # Policy enforcement: Permanent bans require Head Moderator or Leadership approval
        if permanent and not self.has_pz_tier(interaction.user, ["leadership", "head_mod"]):
            view = PermBanApprovalView(self, player, reason, interaction.user.id, interaction.user.name)
            embed = discord.Embed(
                title="⚠️ Permanent Ban Approval Required",
                description=(
                    f"{interaction.user.mention} has requested a **Permanent Ban** on player **`{player}`**.\n"
                    "Per Circuit Verse security policy, permanent bans require sign-off from a **Head Moderator**, **PZ Server Host**, or **Department Director**."
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="🎯 Target Player", value=f"`{player}`", inline=True)
            embed.add_field(name="👮 Requested By", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed, view=view)
            await self.record_audit(interaction.guild, interaction.user, "Permanent Ban Requested", player, reason)
            return

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f'banuser "{player}" -r "{reason}"')
            ban_type = "Permanent Ban" if permanent else "Temporary Ban"
            await self.record_audit(interaction.guild, interaction.user, ban_type, player, reason, res)
            await interaction.followup.send(f"🔨 Executed **{ban_type}** on **`{player}`** for: *{reason}*\n```{res or 'Done'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @app_commands.command(name="pz_unban", description="[PZ Head Mod / Leadership] Unban a player from the server")
    @app_commands.describe(player="In-game username", reason="Reason for unbanning")
    async def pz_unban(self, interaction: discord.Interaction, player: str, reason: str):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "head_mod"]):
            return await interaction.response.send_message("❌ Only **Head Moderator** or **Server Leadership** can unban players.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f'unbanuser "{player}"')
            await self.record_audit(interaction.guild, interaction.user, "Player Unban", player, reason, res)
            await interaction.followup.send(f"✅ Unbanned **`{player}`** (Reason: *{reason}*)\n```{res or 'Done'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @app_commands.command(name="pz_safehouse", description="[PZ Mod / Support] Release a bugged or griefed safehouse")
    @app_commands.describe(reason="Case notes or dispute reason")
    async def pz_safehouse(self, interaction: discord.Interaction, reason: str):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "moderation", "support"]):
            return await interaction.response.send_message("❌ Insufficient permissions.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon("releasesafehouse")
            await self.record_audit(interaction.guild, interaction.user, "Safehouse Release", "Safehouse System", reason, res)
            await interaction.followup.send(f"🏠 Executed safehouse release check (Reason: *{reason}*)\n```{res or 'Done'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    # ==========================================
    # 4. STAFF NOTES, HISTORY & ROLE ASSIGNMENT
    # ==========================================
    @app_commands.command(name="pz_note", description="[PZ Staff] Add or view internal staff notes & punishment history for a player")
    @app_commands.describe(player="In-game username", add_note="Optional new note to attach to this player's record")
    async def pz_note(self, interaction: discord.Interaction, player: str, add_note: str = None):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "moderation", "support", "gm", "observer"]):
            return await interaction.response.send_message("❌ Insufficient permissions.", ephemeral=True)

        audit_data = load_audit_data()
        key = player.lower()

        if add_note:
            if not self.has_pz_tier(interaction.user, ["leadership", "moderation", "support"]):
                return await interaction.response.send_message("❌ Observers cannot add notes.", ephemeral=True)
            note_entry = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "author": interaction.user.name,
                "note": add_note
            }
            audit_data.setdefault("notes", {}).setdefault(key, []).append(note_entry)
            save_audit_data(audit_data)
            await self.record_audit(interaction.guild, interaction.user, "Staff Note Added", player, add_note)

        notes = audit_data.get("notes", {}).get(key, [])
        punishments = [
            p for p in audit_data.get("punishments", [])
            if p.get("target", "").lower() == key
        ]

        embed = discord.Embed(
            title=f"📋 Player Dossier & History — `{player}`",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        if punishments:
            p_lines = [f"• `{p['timestamp']}` — **{p['action']}** by `{p['actor_name']}`: *{p['reason']}*" for p in punishments[-10:]]
            embed.add_field(name=f"⚖️ Punishment History ({len(punishments)})", value="\n".join(p_lines), inline=False)
        else:
            embed.add_field(name="⚖️ Punishment History", value="*Clean record — no punishments logged.*", inline=False)

        if notes:
            n_lines = [f"• `{n['timestamp']}` (`{n['author']}`): {n['note']}" for n in notes[-10:]]
            embed.add_field(name=f"📝 Staff Notes ({len(notes)})", value="\n".join(n_lines), inline=False)
        else:
            embed.add_field(name="📝 Staff Notes", value="*No staff notes recorded.*", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pz_setrole", description="[PZ Leadership] Assign an official Circuit Verse in-game staff role to a player")
    @app_commands.describe(username="In-game player username", role_name="Official PZ Staff Role")
    @app_commands.choices(role_name=[
        app_commands.Choice(name="PZ Server Host (Full Operational Admin)", value="PZ Server Host"),
        app_commands.Choice(name="Server Technician (Infrastructure)", value="Server Technician"),
        app_commands.Choice(name="Lead Developer (Technical Dev)", value="Lead Developer"),
        app_commands.Choice(name="Developer (Dev & Testing)", value="Developer"),
        app_commands.Choice(name="Head Moderator (Full Moderation)", value="Head Moderator"),
        app_commands.Choice(name="Senior Moderator (Advanced Moderation)", value="Senior Moderator"),
        app_commands.Choice(name="Moderator (Standard Moderation)", value="Moderator"),
        app_commands.Choice(name="Chief Game Master (Full Events)", value="Chief Game Master"),
        app_commands.Choice(name="Senior Game Master (Advanced Events)", value="Senior Game Master"),
        app_commands.Choice(name="Game Master (Standard Events)", value="Game Master"),
        app_commands.Choice(name="GM Trainee (Supervised Events)", value="GM Trainee"),
        app_commands.Choice(name="Head Support (Support Oversight)", value="Head Support"),
        app_commands.Choice(name="Senior Support (Advanced Assistance)", value="Senior Support"),
        app_commands.Choice(name="Support Team (Basic Assistance)", value="Support Team"),
        app_commands.Choice(name="Support Trainee (Player Access)", value="Support Trainee"),
        app_commands.Choice(name="PZ Staff Observer (Read-Only Observation)", value="PZ Staff Observer"),
        app_commands.Choice(name="Player / User (Remove Staff Access)", value="user")
    ])
    async def pz_setrole(self, interaction: discord.Interaction, username: str, role_name: str):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership"]):
            return await interaction.response.send_message("❌ Only **PZ Server Host** or **Department Director** can assign in-game staff roles.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f'setaccesslevel "{username}" "{role_name}"')
            await self.record_audit(interaction.guild, interaction.user, "In-Game Role Assigned", username, f"Assigned role: {role_name}", res)
            await interaction.followup.send(f"🎖️ Assigned in-game role **`{role_name}`** to player **`{username}`**.\n```{res or 'Role updated'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @app_commands.command(name="pz_command", description="[PZ Leadership / Tech] Execute a raw RCON command on the Project Zomboid server")
    @app_commands.describe(command="RCON command string (e.g. save, reloadoptions, checkModsNeedUpdate)")
    async def pz_command(self, interaction: discord.Interaction, command: str):
        if not self.check_staff_channel(interaction):
            return await interaction.response.send_message("❌ Use this command inside `#💻・pz-staff-commands`.", ephemeral=True)
        if not self.has_pz_tier(interaction.user, ["leadership", "tech"]):
            return await interaction.response.send_message("❌ Restricted to **PZ Server Leadership** and **Server Technicians**.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(command)
            await self.record_audit(interaction.guild, interaction.user, "Raw RCON Command", "Server Console", f"Command: {command}", res)
            await interaction.followup.send(f"🖥️ Executed `{command}`:\n```{res[:1800] if res else 'Command executed (no output)'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    # ==========================================
    # 5. UNIQUE COMMUNITY FEATURES (RESCUE, BOUNTY, REPORT)
    # ==========================================
    @app_commands.command(name="pz_rescue", description="🚁 Survivor Rescue Service: Request staff rescue if stuck, glitched, or trapped by a bug")
    @app_commands.describe(survivor_name="Your in-game character/account name", issue_and_location="Describe where you are stuck and what happened")
    async def pz_rescue(self, interaction: discord.Interaction, survivor_name: str, issue_and_location: str):
        pz_cfg, _ = self.get_pz_cfg()
        tickets_ch_id = pz_cfg.get("staff_tickets_channel")
        tickets_ch = interaction.guild.get_channel(tickets_ch_id) if tickets_ch_id else None

        embed = discord.Embed(
            title="🚁 Incoming Survivor Rescue Request",
            description="A survivor has requested emergency unstuck / bug recovery assistance.",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 Discord User", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="🧟 In-Game Name", value=f"`{survivor_name}`", inline=True)
        embed.add_field(name="📍 Location & Issue", value=issue_and_location, inline=False)

        # Auto-prune PZ server logs older than 5 minutes (300s)
        for log_cid in (1570270312560468041, 1567702389283102813):
            try:
                log_ch = guild.get_channel(log_cid)
                if log_ch:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                    async for m in log_ch.history(limit=50):
                        if not m.pinned and m.created_at < cutoff:
                            try:
                                await m.delete()
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Error pruning PZ log channel {log_cid}: {e}")

        # Auto-prune PZ status transition alerts in status channel older than 5 minutes
        try:
            status_msg_id = pz_cfg.get("status_message_id", 1568828761468698668)
            if ch:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                async for m in ch.history(limit=50):
                    if status_msg_id and m.id == int(status_msg_id):
                        continue
                    if m.pinned:
                        continue
                    if m.author.id == self.bot.user.id and m.created_at < cutoff:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error pruning PZ status alerts: {e}")

        embed.set_footer(text="Circuit Verse • Survivor Rescue Service")

        view = RescueClaimView(self, survivor_name, issue_and_location, interaction.user.id)
        if tickets_ch:
            await tickets_ch.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"🚁 **Survivor Rescue Dispatched!** Your request for `{survivor_name}` has been sent to the **PZ Support & Moderation Team**.",
            ephemeral=True
        )

    @app_commands.command(name="pz_report", description="🚨 Submit a player misconduct, griefing, or safehouse dispute report to PZ Staff")
    @app_commands.describe(reported_player="In-game name of the player (or 'Unknown')", category="Type of incident", details="Detailed description and coordinates/time")
    @app_commands.choices(category=[
        app_commands.Choice(name="🏠 Safehouse Griefing / Stolen Loot", value="Safehouse Griefing"),
        app_commands.Choice(name="⚔️ Rule Violation / Harassment", value="Rule Violation"),
        app_commands.Choice(name="🐛 Character Loss / Server Bug", value="Lost Survivor Recovery"),
        app_commands.Choice(name="🛡️ Staff Misconduct Report", value="Staff Report")
    ])
    async def pz_report(self, interaction: discord.Interaction, reported_player: str, category: str, details: str):
        pz_cfg, _ = self.get_pz_cfg()
        tickets_ch_id = pz_cfg.get("staff_tickets_channel")
        tickets_ch = interaction.guild.get_channel(tickets_ch_id) if tickets_ch_id else None

        embed = discord.Embed(
            title=f"🚨 PZ Incident Report — {category}",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📩 Reporter", value=f"{interaction.user.mention} (`{interaction.user.name}`)", inline=True)
        embed.add_field(name="🎯 Subject / Player", value=f"`{reported_player}`", inline=True)
        embed.add_field(name="📂 Category", value=category, inline=True)
        embed.add_field(name="📝 Incident Details", value=details, inline=False)

        # Auto-prune PZ server logs older than 5 minutes (300s)
        for log_cid in (1570270312560468041, 1567702389283102813):
            try:
                log_ch = guild.get_channel(log_cid)
                if log_ch:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                    async for m in log_ch.history(limit=50):
                        if not m.pinned and m.created_at < cutoff:
                            try:
                                await m.delete()
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Error pruning PZ log channel {log_cid}: {e}")

        # Auto-prune PZ status transition alerts in status channel older than 5 minutes
        try:
            status_msg_id = pz_cfg.get("status_message_id", 1568828761468698668)
            if ch:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                async for m in ch.history(limit=50):
                    if status_msg_id and m.id == int(status_msg_id):
                        continue
                    if m.pinned:
                        continue
                    if m.author.id == self.bot.user.id and m.created_at < cutoff:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error pruning PZ status alerts: {e}")

        embed.set_footer(text="Circuit Verse • Player Report Center")

        if tickets_ch:
            await tickets_ch.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Your **{category}** report has been logged with the Project Zomboid Staff Team (`#🎫・pz-staff-tickets`).",
            ephemeral=True
        )

    @app_commands.command(name="pz_bounty", description="🎯 [PZ GM / Staff] Post an official challenge to the Community Bounty Board")
    @app_commands.describe(title="Bounty title", objective="What survivors need to accomplish", reward="In-game reward or badge")
    async def pz_bounty(self, interaction: discord.Interaction, title: str, objective: str, reward: str):
        if not self.has_pz_tier(interaction.user, ["leadership", "gm", "moderation"]):
            return await interaction.response.send_message("❌ Only **Game Masters** and **Staff** can post official bounties.", ephemeral=True)

        events_ch_id = 1567702362456465428
        events_ch = interaction.guild.get_channel(events_ch_id)
        if not events_ch:
            return await interaction.response.send_message("❌ Events channel not found.", ephemeral=True)

        embed = discord.Embed(
            title=f"🎯 COMMUNITY BOUNTY BOARD: {title}",
            description=objective,
            color=discord.Color.dark_gold(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="🏆 Reward", value=reward, inline=True)
        embed.add_field(name="🎬 Posted By", value=interaction.user.mention, inline=True)

        # Auto-prune PZ server logs older than 5 minutes (300s)
        for log_cid in (1570270312560468041, 1567702389283102813):
            try:
                log_ch = guild.get_channel(log_cid)
                if log_ch:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                    async for m in log_ch.history(limit=50):
                        if not m.pinned and m.created_at < cutoff:
                            try:
                                await m.delete()
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Error pruning PZ log channel {log_cid}: {e}")

        # Auto-prune PZ status transition alerts in status channel older than 5 minutes
        try:
            status_msg_id = pz_cfg.get("status_message_id", 1568828761468698668)
            if ch:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                async for m in ch.history(limit=50):
                    if status_msg_id and m.id == int(status_msg_id):
                        continue
                    if m.pinned:
                        continue
                    if m.author.id == self.bot.user.id and m.created_at < cutoff:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error pruning PZ status alerts: {e}")

        embed.set_footer(text="Circuit Verse • Knox County Survivor Bounty Board")

        await events_ch.send(embed=embed)
        await self.record_audit(interaction.guild, interaction.user, "Bounty Posted", title, f"Reward: {reward}")
        await interaction.response.send_message(f"✅ Posted bounty **{title}** to {events_ch.mention}!", ephemeral=True)

    @app_commands.command(name="panel", description="🔐 Open the Circuit Verse Unified Web Control Panels (One-Click Discord Login)")
    async def panel_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔐 Circuit Verse — Unified Web Control Panels",
            description=(
                "Click any button below to launch the web control panels with **One-Click Discord Login**.\n"
                "Your live Discord server roles in **Circuit Verse** automatically determine your exact access tier!"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="🧟 Zomboid Control Panel",
            value="• **Hub:** https://panel.circuitverse.online/?panel=pz\n• **Direct ZCP:** https://zcp.circuitverse.online",
            inline=False
        )
        embed.add_field(
            name="⛏️ Minecraft & 🚀 Nova Station 13 Panels",
            value="• **Minecraft Panel:** https://panel.circuitverse.online/?panel=mc\n• **NS13 Panel:** https://panel.circuitverse.online/?panel=ns13",
            inline=False
        )
        embed.add_field(
            name="📻 CV-Radio Broadcast Control Panel",
            value="• **Radio Panel:** https://panel.circuitverse.online/?panel=radio\n• **Required Role:** `CV-Radio-Access` (or Radio Staff / Executive Staff)",
            inline=False
        )
        embed.add_field(
            name="👑 Executive All-in-One Master Control Panel",
            value=(
                "• **Master Panel:** https://panel.circuitverse.online/?panel=master\n"
                "• **Restricted To:** `Founder`, `Chief Community Officer`, `Community Director` (+ Master Password)"
            ),
            inline=False
        )

        # Auto-prune PZ server logs older than 5 minutes (300s)
        for log_cid in (1570270312560468041, 1567702389283102813):
            try:
                log_ch = guild.get_channel(log_cid)
                if log_ch:
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                    async for m in log_ch.history(limit=50):
                        if not m.pinned and m.created_at < cutoff:
                            try:
                                await m.delete()
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"Error pruning PZ log channel {log_cid}: {e}")

        # Auto-prune PZ status transition alerts in status channel older than 5 minutes
        try:
            status_msg_id = pz_cfg.get("status_message_id", 1568828761468698668)
            if ch:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                async for m in ch.history(limit=50):
                    if status_msg_id and m.id == int(status_msg_id):
                        continue
                    if m.pinned:
                        continue
                    if m.author.id == self.bot.user.id and m.created_at < cutoff:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error pruning PZ status alerts: {e}")

        embed.set_footer(text="Circuit Verse • Unified Discord OAuth2 SSO Gateway")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🔐 Unified Hub (Discord Login)", url="https://panel.circuitverse.online/auth/login", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="🧟 Zomboid Panel", url="https://panel.circuitverse.online/?panel=pz", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="⛏️ Minecraft Panel", url="https://panel.circuitverse.online/?panel=mc", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="🚀 NS13 Panel", url="https://panel.circuitverse.online/?panel=ns13", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="📻 CV-Radio Panel", url="https://panel.circuitverse.online/?panel=radio", style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="👑 Executive Master Panel", url="https://panel.circuitverse.online/?panel=master", style=discord.ButtonStyle.link))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProjectZomboidCog(bot))