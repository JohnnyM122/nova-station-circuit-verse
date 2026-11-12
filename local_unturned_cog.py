import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import logging
import asyncio
import socket
import json
import os
import time
from datetime import datetime, timezone

logger = logging.getLogger("CVNovaHelper.unturned")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def unturned_rcon_sync(host: str, port: int, password: str, cmd: str, timeout: float = 5.0) -> str:
    """Execute a command via RocketMod RCON over TCP socket."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        banner = s.recv(1024)
        # RocketMod RCON sends banner on connection, then expects 'login <password>'
        s.sendall(f"login {password}\r\n".encode("utf-8"))
        # RocketMod does NOT reply on successful login, so send command immediately
        s.sendall(f"{cmd}\r\n".encode("utf-8"))
        time.sleep(0.35)
        res = s.recv(8192).decode("utf-8", errors="replace")
        if "invalid password" in res.lower() or "good bye" in res.lower():
            raise PermissionError("RocketMod RCON login failed.")
        lines = [line.strip() for line in res.splitlines() if line.strip()]
        if lines and lines[0].lower().startswith(cmd.lower()):
            lines = lines[1:]
        return "\n".join(lines).strip()
    finally:
        s.close()


class UnturnedCog(commands.Cog):
    """
    Comprehensive Circuit Verse Unturned Administration, Live Status Monitoring,
    In-game Broadcasts, Moderation, Staff Logs & Web Panel Integration.
    """

    def __init__(self, bot):
        self.bot = bot
        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    async def run_rcon(self, cmd: str) -> str:
        cfg = load_config()
        u = cfg.get("unturned_server", {})
        host = u.get("host", "91.107.198.243")
        port = int(u.get("rcon_port", 27115))
        password = u.get("rcon_password", "CircuitVerseUnturned2026!")
        return await asyncio.to_thread(unturned_rcon_sync, host, port, password, cmd)

    def has_unturned_tier(self, user: discord.Member, tiers: list) -> bool:
        """Check if user has required Unturned staff permissions."""
        if not hasattr(user, "roles"):
            return False

        user_role_ids = {r.id for r in user.roles}
        cfg = load_config()
        u_roles = cfg.get("unturned_roles", {})

        # Executive override
        exec_ids = {1564610713216098394, 1567482219495301191, 1567477045964054598}
        if user_role_ids & exec_ids:
            return True

        tier_map = {
            "host": {u_roles.get("Unturned Server Host", 1568805604447752263)},
            "manager": {
                u_roles.get("Unturned Server Host", 1568805604447752263),
                u_roles.get("Unturned Server Manager", 1568805606192848993),
            },
            "admin": {
                u_roles.get("Unturned Server Host", 1568805604447752263),
                u_roles.get("Unturned Server Manager", 1568805606192848993),
                u_roles.get("Unturned Server Admin", 1568805607836745910),
            },
            "mod": {
                u_roles.get("Unturned Server Host", 1568805604447752263),
                u_roles.get("Unturned Server Manager", 1568805606192848993),
                u_roles.get("Unturned Server Admin", 1568805607836745910),
                u_roles.get("Unturned Server Mod", 1568805609158082641),
            },
            "staff": {
                u_roles.get("Unturned Server Host", 1568805604447752263),
                u_roles.get("Unturned Server Manager", 1568805606192848993),
                u_roles.get("Unturned Server Admin", 1568805607836745910),
                u_roles.get("Unturned Server Mod", 1568805609158082641),
                u_roles.get("Unturned Server Staff", 1568805610219372690),
            },
        }

        required_ids = set()
        for t in tiers:
            required_ids.update(tier_map.get(t, set()))

        return bool(user_role_ids & required_ids)

    async def record_audit(self, guild: discord.Guild, actor: discord.Member, action: str, target: str, reason: str = "", output: str = ""):
        """Send embed to the staff logs channel."""
        cfg = load_config()
        u = cfg.get("unturned_server", {})
        log_ch_id = u.get("staff_logs_channel", 1568805627810029569)
        if not guild or not log_ch_id:
            return

        ch = guild.get_channel(int(log_ch_id))
        if not ch:
            return

        embed = discord.Embed(
            title=f"📑 Unturned Staff Audit: {action}",
            color=discord.Color.dark_teal(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Staff Member", value=f"{actor.mention} (`{actor.name}`)", inline=True)
        embed.add_field(name="Target / Player", value=f"`{target}`", inline=True)
        if reason:
            embed.add_field(name="Reason / Note", value=reason, inline=False)
        if output:
            embed.add_field(name="Server Response", value=f"```{output[:500]}```", inline=False)
        embed.set_footer(text="Circuit Verse Unturned Staff Logs")
        try:
            await ch.send(embed=embed)
        except Exception as e:
            logger.debug(f"Failed to send unturned audit log: {e}")

    # ==========================================
    # LIVE STATUS UPDATE LOOP
    # ==========================================
    @tasks.loop(seconds=60)
    async def status_loop(self):
        await self.bot.wait_until_ready()
        try:
            logger.info("Running Unturned update_status_embed()...")
            await self.update_status_embed()
        except Exception as e:
            logger.error(f"Unturned status loop error: {e}", exc_info=True)

    async def update_status_embed(self):
        cfg = load_config()
        u = cfg.get("unturned_server", {})
        guild_id = cfg.get("guild_id")
        status_ch_id = u.get("status_channel", 1568805619522343095)
        if not guild_id or not status_ch_id:
            return

        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            logger.error(f"Unturned status: Guild {guild_id} not found by bot")
            return
        ch = guild.get_channel(int(status_ch_id))
        if not ch:
            logger.error(f"Unturned status: Channel {status_ch_id} not found by bot")
            return

        online = False
        players_list = []
        try:
            raw = await self.run_rcon("players")
            online = True
            for line in raw.splitlines():
                line = line.strip()
                if (line and 
                    not line.lower().startswith("players:") and 
                    not line.lower().startswith("total:") and 
                    "executed command" not in line.lower() and 
                    "failed to find any players" not in line.lower() and
                    not any(skip in line.lower() for skip in ["enabling", "loaded", "loading", "overriding", "warn", "info", "error", "saving", "save", "exception", "rocket", "uessentials"])):
                    players_list.append(line)
        except Exception as e:
            logger.warning(f"Unturned RCON check failed: {e}")
            online = False

        color = discord.Color.green() if online else discord.Color.red()
        status_badge = "🟢 **ONLINE & OPERATIONAL**" if online else "🔴 **OFFLINE / RESTARTING**"

        embed = discord.Embed(
            title="🌲 Circuit Verse • Unturned Dedicated Server",
            description=(
                "Official Unturned Survival & Base Building Server running on high-speed NVMe cloud infrastructure with RocketMod plugin architecture.\n\n"
                "📢 **Staff Notice:** We are actively hiring Server & Community Staff! Inquire in Discord or open a support ticket in <#1567464252674150410>!"
            ),
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📡 Server Status", value=status_badge, inline=True)
        embed.add_field(name="👥 Survivors Online", value=f"**{len(players_list)} / 32**", inline=True)
        embed.add_field(name="🌍 Region & Ping", value="EU-Central (Germany • Low Latency)", inline=True)

        embed.add_field(
            name="🔌 Direct Connection Details",
            value=(
                "• **Server Address:** `unturned.circuitverse.online` (or `91.107.198.243`)\n"
                "• **Game Port:** `27015` (UDP)\n"
                "• **Query Port:** `27016` (UDP)\n"
                "• **Map:** `PEI`\n"
                "• **Anti-Cheat:** 🛡️ BattlEye & Valve Anti-Cheat (VAC) Enforced\n"
                "• **Access:** 🌐 Open to Public (No Whitelist Required) — Discord: https://discord.gg/M7R8EY28q6"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ World & Gameplay Configuration",
            value=(
                "• **Perspective:** Both (1st & 3rd Person Toggle)\n"
                "• **Cheats:** Enabled for Server Staff & Admins\n"
                "• **Plugin Framework:** RocketMod 4.9.3 Native Engine\n"
                "• **Web Command Center:** [panel.circuitverse.online](https://panel.circuitverse.online) (Discord SSO)"
            ),
            inline=False
        )
        if players_list:
            embed.add_field(
                name="🏕️ Connected Survivors",
                value=", ".join(f"`{p}`" for p in players_list[:25]),
                inline=False
            )

        embed.set_footer(text="Updated automatically every 60s • Circuit Verse Helper")

        # Anti-duplicate search and edit logic
        msg_id = u.get("status_message_id")
        target_msg = None

        if msg_id:
            try:
                target_msg = await ch.fetch_message(int(msg_id))
            except Exception:
                target_msg = None

        if not target_msg:
            async for m in ch.history(limit=25):
                if m.author == self.bot.user and m.embeds:
                    if "Unturned Dedicated Server" in (m.embeds[0].title or ""):
                        target_msg = m
                        cfg["unturned_server"]["status_message_id"] = target_msg.id
                        save_config(cfg)
                        break

        if target_msg:
            await target_msg.edit(embed=embed)
            # Delete any rogue duplicate status embeds in the channel
            try:
                async for extra_m in ch.history(limit=25):
                    if extra_m.id != target_msg.id and extra_m.author == self.bot.user and extra_m.embeds:
                        if "Unturned Dedicated Server" in (extra_m.embeds[0].title or ""):
                            await extra_m.delete()
            except Exception:
                pass
            return

        # Send new message if none exists
        new_msg = await ch.send(embed=embed)
        cfg["unturned_server"]["status_message_id"] = new_msg.id
        save_config(cfg)

    # ==========================================
    # SLASH COMMAND GROUP
    # ==========================================
    unturned_group = app_commands.Group(name="unturned", description="Circuit Verse Unturned Dedicated Server Commands")

    @unturned_group.command(name="players", description="👥 View connected Unturned players and live server status")
    async def unturned_players(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            raw = await self.run_rcon("players")
            players = []
            for line in raw.splitlines():
                line = line.strip()
                if (line and 
                    not line.lower().startswith("players:") and 
                    not line.lower().startswith("total:") and 
                    "executed command" not in line.lower() and 
                    "failed to find any players" not in line.lower() and
                    not any(skip in line.lower() for skip in ["enabling", "loaded", "loading", "overriding", "warn", "info", "error", "saving", "save", "exception", "rocket", "uessentials"])):
                    players.append(line)

            embed = discord.Embed(
                title="🌲 Unturned Live Survivors",
                description=f"Currently **{len(players)} / 32** survivors connected to `unturned.circuitverse.online:27015`.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            if players:
                embed.add_field(name="Active Players", value="\n".join(f"• `{p}`" for p in players), inline=False)
            else:
                embed.add_field(name="Active Players", value="*No survivors currently online. Be the first to join!*", inline=False)

            embed.set_footer(text="Circuit Verse Unturned")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to reach Unturned server via RCON: `{e}`", ephemeral=True)

    @unturned_group.command(name="broadcast", description="📢 Send a server-wide announcement in Unturned chat")
    @app_commands.describe(message="The message to display to all connected players")
    async def unturned_broadcast(self, interaction: discord.Interaction, message: str):
        if not self.has_unturned_tier(interaction.user, ["staff"]):
            return await interaction.response.send_message("❌ Only Unturned Staff can broadcast announcements.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f"broadcast {message}")
            await self.record_audit(interaction.guild, interaction.user, "In-Game Broadcast", "All Players", message, res)
            await interaction.followup.send(f"📢 Broadcasted to Unturned server:\n> **{message}**")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Broadcast failed: `{e}`", ephemeral=True)

    @unturned_group.command(name="kick", description="👢 Kick an in-game player from the Unturned server")
    @app_commands.describe(player="Character name or Steam64 ID", reason="Reason for kicking player")
    async def unturned_kick(self, interaction: discord.Interaction, player: str, reason: str = "Staff Disciplinary Action"):
        if not self.has_unturned_tier(interaction.user, ["mod"]):
            return await interaction.response.send_message("❌ Only Unturned Moderators or Admins can kick players.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f"kick {player}/{reason}")
            await self.record_audit(interaction.guild, interaction.user, "Player Kick", player, reason, res)
            await interaction.followup.send(f"👢 Kicked `{player}` from the Unturned server. Reason: *{reason}*")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @unturned_group.command(name="ban", description="🔨 Ban a player from the Unturned server")
    @app_commands.describe(player="Character name or Steam64 ID", reason="Reason for banning player")
    async def unturned_ban(self, interaction: discord.Interaction, player: str, reason: str = "Staff Disciplinary Action"):
        if not self.has_unturned_tier(interaction.user, ["admin"]):
            return await interaction.response.send_message("❌ Only Unturned Admins can ban players.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(f"ban {player}/{reason}/0")
            await self.record_audit(interaction.guild, interaction.user, "Player Ban", player, reason, res)
            await interaction.followup.send(f"🔨 Banned `{player}` from the Unturned server. Reason: *{reason}*")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @unturned_group.command(name="save", description="💾 Force an immediate world save on the Unturned server")
    async def unturned_save(self, interaction: discord.Interaction):
        if not self.has_unturned_tier(interaction.user, ["staff"]):
            return await interaction.response.send_message("❌ Only Unturned Staff can trigger manual world saves.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon("save")
            await self.record_audit(interaction.guild, interaction.user, "Save World", "Server", "Manual trigger", res)
            await interaction.followup.send("💾 Unturned server world data saved successfully!")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    @unturned_group.command(name="rcon", description="💻 Execute a raw RocketMod console command (Host/Admin only)")
    @app_commands.describe(command="Console command (e.g. p reload, day, night, weather none)")
    async def unturned_rcon_cmd(self, interaction: discord.Interaction, command: str):
        if not self.has_unturned_tier(interaction.user, ["admin"]):
            return await interaction.response.send_message("❌ Only Unturned Server Admins or Host can execute raw RCON commands.", ephemeral=True)

        await interaction.response.defer()
        try:
            res = await self.run_rcon(command)
            await self.record_audit(interaction.guild, interaction.user, "Raw RCON Command", "Console", f"Command: {command}", res)
            await interaction.followup.send(f"💻 Console execution (`{command}`):\n```{res[:1800] if res else 'Executed successfully (no output)'}```")
        except Exception as e:
            await interaction.followup.send(f"❌ RCON Error: `{e}`", ephemeral=True)

    # Prefix Commands for staff text channels
    @commands.group(name="unturned", invoke_without_command=True)
    async def unturned_prefix(self, ctx):
        await ctx.send("🌲 **Circuit Verse Unturned:** Available subcommands: `players`, `broadcast`, `kick`, `ban`, `save`, `rcon` or manage via <https://panel.circuitverse.online>")


async def setup(bot):
    await bot.add_cog(UnturnedCog(bot))
