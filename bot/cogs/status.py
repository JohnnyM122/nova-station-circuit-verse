import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
import subprocess

logger = logging.getLogger("CVNovaHelper.status")

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.byond = bot.byond
        self.config = bot.config
        self.last_status = None
        self.last_state = "UNKNOWN"
        self.current_round_id = None
        self.round_started_announced = False
        self.round_ended_announced = False
        self.status_message_id = None
        self.cleaned_old_transient_messages = False
        self.monitor_task.start()

    def cog_unload(self):
        self.monitor_task.cancel()

    def get_service_status(self):
        try:
            res = subprocess.run(
                ["systemctl", "is-active", self.config.get("systemd_service", "novastation.service")],
                capture_output=True, text=True, timeout=3
            )
            return res.stdout.strip()
        except Exception:
            return "unknown"

    async def cleanup_old_transient_messages(self, channel):
        try:
            now = discord.utils.utcnow()
            async for msg in channel.history(limit=50):
                if msg.author == self.bot.user and len(msg.embeds) > 0:
                    title = msg.embeds[0].title or ""
                    if any(t in title for t in ["Server is Online", "Server is Rebooting", "Server is Offline"]):
                        age = (now - msg.created_at).total_seconds()
                        if age >= 60:
                            try:
                                await msg.delete()
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Error cleaning old transient status messages: {e}")

    async def announce_round_end(self, channel, round_id):
        if not round_id or self.round_ended_announced:
            return
        end_embed = discord.Embed(
            title=f"🏁 Round #{round_id} Ended",
            description=f"Round #{round_id} has concluded.",
            color=discord.Color.purple()
        )
        await channel.send(embed=end_embed)
        self.round_ended_announced = True

    async def announce_round_start(self, channel, status_data):
        round_id = status_data.get("round_id")
        if not round_id or self.round_started_announced:
            return
        mode_str = str(status_data.get("mode", "Unknown")).capitalize()
        map_str = status_data.get("map_name", "Unknown")
        start_embed = discord.Embed(
            title=f"🚀 Round #{round_id} Started!",
            description=f"Map: **{map_str}**\nMode: **{mode_str}**",
            color=discord.Color.blue()
        )
        await channel.send(embed=start_embed)
        self.round_started_announced = True

    @tasks.loop(seconds=10.0)
    async def monitor_task(self):
        status_channel_id = self.config["channels"].get("status")
        if not status_channel_id:
            return

        channel = self.bot.get_channel(status_channel_id)
        if not channel:
            return

        # Purge any lingering transient messages
        await self.cleanup_old_transient_messages(channel)

        service_active = self.get_service_status() == "active"
        status_data = await self.byond.get_status()

        current_state = "OFFLINE"
        if service_active and status_data and isinstance(status_data, dict):
            current_state = "ONLINE"
        elif service_active and (not status_data):
            current_state = "REBOOTING"
        else:
            current_state = "OFFLINE"

        # In-game state from status_data:
        # 0: Startup, 1: Pregame/Lobby, 2: Setting up, 3: Playing, 4: Finished/Queued to reboot
        ticker_state = status_data.get("ticker_state") if isinstance(status_data, dict) else None
        round_id = str(status_data.get("round_id", "")).strip() if isinstance(status_data, dict) else None
        roundtime = status_data.get("roundtime", "00:00:00") if isinstance(status_data, dict) else "00:00:00"

        # 1. State change alerts (Online, Reboot, Offline) - Transient alerts disappear after 1 minute (60s)
        if self.last_state != "UNKNOWN" and self.last_state != current_state:
            if current_state == "ONLINE":
                embed = discord.Embed(
                    title="🟢 Server is Online!",
                    description="Nova Station 13 is up and accepting connections.",
                    color=discord.Color.green()
                )
                if isinstance(status_data, dict):
                    embed.add_field(name="Map", value=status_data.get("map_name", "Unknown"), inline=True)
                    embed.add_field(name="Round ID", value=str(status_data.get("round_id", "N/A")), inline=True)
                # Disappear after 1 minute
                await channel.send(embed=embed, delete_after=60)

            elif current_state == "REBOOTING":
                embed = discord.Embed(
                    title="🟡 Server is Rebooting...",
                    description="The server is currently restarting. Please wait a moment while it initializes.",
                    color=discord.Color.gold()
                )
                # Disappear after 1 minute
                await channel.send(embed=embed, delete_after=60)

                # Server is queued to reboot / restarting: announce round end immediately
                if self.current_round_id and not self.round_ended_announced:
                    await self.announce_round_end(channel, self.current_round_id)

            elif current_state == "OFFLINE":
                embed = discord.Embed(
                    title="🔴 Server is Offline",
                    description="The server has shut down.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed, delete_after=60)

        # 2. Check for in-game round finished (queued to reboot before DreamDaemon process restarts)
        if ticker_state == 4 and self.current_round_id and not self.round_ended_announced:
            await self.announce_round_end(channel, self.current_round_id)

        # 3. Round tracking and start detection (only when officially started!)
        if current_state == "ONLINE" and isinstance(status_data, dict) and round_id:
            if self.current_round_id is None:
                # First run after bot startup: adopt current round ID
                self.current_round_id = round_id
                # If round is already playing, mark start as announced so we don't duplicate
                if ticker_state == 3 or (roundtime and roundtime != "00:00:00"):
                    self.round_started_announced = True
                self.round_ended_announced = False
            elif round_id != self.current_round_id:
                # Next round appeared! Do NOT announce round end after the round has officially started / rotated.
                self.current_round_id = round_id
                self.round_started_announced = False
                self.round_ended_announced = False

            # Determine if the round has officially started (not lobby/pregame)
            officially_started = False
            if ticker_state is not None:
                officially_started = (ticker_state == 3) # GAME_STATE_PLAYING
            else:
                officially_started = (roundtime != "00:00:00" and status_data.get("real_mode") is not None)

            if officially_started and not self.round_started_announced:
                await self.announce_round_start(channel, status_data)

        self.last_state = current_state
        self.last_status = status_data

        # 4. Dynamic Live Status Dashboard (updates in place)
        await self.update_dashboard(channel, current_state, status_data)

    async def update_dashboard(self, channel, state, data):
        embed = discord.Embed(title="⚡ Nova Station 13 - Live Server Status")
        if state == "ONLINE" and isinstance(data, dict):
            embed.color = discord.Color.green()
            embed.description = "🟢 **Server is Online and Active**"
            embed.add_field(name="🗺️ Current Map", value=data.get("map_name", "Unknown"), inline=True)
            embed.add_field(name="🎲 Game Mode", value=data.get("mode", "Unknown").capitalize(), inline=True)
            embed.add_field(name="🆔 Round ID", value=f"#{data.get('round_id', 'N/A')}", inline=True)
            embed.add_field(name="⏱️ Station Time", value=data.get("stationtime", "00:00"), inline=True)
            embed.add_field(name="⏳ Elapsed Time", value=data.get("roundtime", "00:00:00"), inline=True)
            embed.add_field(name="👥 Players Online", value=f"**{data.get('players', 0)}**", inline=True)

            # Query adminwho for detailed staff list
            admin_data = await self.byond.get_adminwho()
            staff_list = []
            if isinstance(admin_data, list) and len(admin_data) > 0:
                for a in admin_data:
                    rank = a.get("rank", "Staff")
                    ckey = a.get("ckey", "unknown")
                    afk = " (AFK)" if a.get("afk", 0) > 3000 else ""
                    staff_list.append(f"• `{ckey}` ({rank}){afk}")
            staff_val = "\n".join(staff_list) if staff_list else "None online"
            embed.add_field(name="🛡️ Staff Online", value=staff_val, inline=False)
            embed.add_field(
                name="🌐 Domain & Connectivity",
                value="✨ **Now Hosted on Private Domain! [CircuitVerse.Online](https://circuitverse.online)**\n"
                      "🔗 **SS13 Server Connect:** **[Click to Join (BYOND)](byond://game.circuitverse.online:7777)** (`game.circuitverse.online:7777`)\n"
                      "📻 **CV-Radio Subdomain:** **[radio.circuitverse.online](https://radio.circuitverse.online)**\n"
                      "⛏️ **Minecraft Server:** `play.circuitverse.online` *(Proximity Voice Chat + Bedrock Crossplay)*",
                inline=False
            )
            embed.add_field(name="🖥️ Infrastructure & Hosting", value="Hosted on **[Hetzner Cloud](https://www.hetzner.com/cloud)** (Dedicated Server)", inline=False)
            embed.set_footer(text="Updated live every 15 seconds • CircuitVerse.Online • Hosted on Hetzner Cloud • CV-Nova-Helper")
        elif state == "REBOOTING":
            embed.color = discord.Color.gold()
            embed.description = "🟡 **Server is currently rebooting / initializing...**"
            embed.add_field(
                name="🌐 Domain & Connectivity",
                value="✨ **Now Hosted on Private Domain! [CircuitVerse.Online](https://circuitverse.online)**\n"
                      "🔗 **SS13 Server Connect:** **[Click to Join (BYOND)](byond://game.circuitverse.online:7777)** (`game.circuitverse.online:7777`)\n"
                      "📻 **CV-Radio Subdomain:** **[radio.circuitverse.online](https://radio.circuitverse.online)**\n"
                      "⛏️ **Minecraft Server:** `play.circuitverse.online` *(Proximity Voice Chat + Bedrock Crossplay)*",
                inline=False
            )
            embed.add_field(name="🖥️ Infrastructure & Hosting", value="Hosted on **[Hetzner Cloud](https://www.hetzner.com/cloud)** (Dedicated Server)", inline=False)
            embed.set_footer(text="Will refresh automatically when online • CircuitVerse.Online • Hosted on Hetzner Cloud")
        else:
            embed.color = discord.Color.red()
            embed.description = "🔴 **Server is Offline**"
            embed.add_field(
                name="🌐 Domain & Connectivity",
                value="✨ **Now Hosted on Private Domain! [CircuitVerse.Online](https://circuitverse.online)**\n"
                      "🔗 **SS13 Server Connect:** `game.circuitverse.online:7777`\n"
                      "📻 **CV-Radio Subdomain:** **[radio.circuitverse.online](https://radio.circuitverse.online)**\n"
                      "⛏️ **Minecraft Server:** `play.circuitverse.online` *(Proximity Voice Chat + Bedrock Crossplay)*",
                inline=False
            )
            embed.add_field(name="🖥️ Infrastructure & Hosting", value="Hosted on **[Hetzner Cloud](https://www.hetzner.com/cloud)** (Dedicated Server)", inline=False)
            embed.set_footer(text="Waiting for server to start • CircuitVerse.Online • Hosted on Hetzner Cloud")

        try:
            if self.status_message_id:
                try:
                    msg = await channel.fetch_message(self.status_message_id)
                    await msg.edit(embed=embed)
                    return
                except discord.NotFound:
                    self.status_message_id = None

            # Look for recent bot dashboard message in channel and cleanup duplicates
            old_status_msgs = []
            async for msg in channel.history(limit=15):
                if msg.author == self.bot.user and len(msg.embeds) > 0 and "Live Server Status" in (msg.embeds[0].title or ""):
                    old_status_msgs.append(msg)

            if old_status_msgs:
                primary = old_status_msgs[0]
                self.status_message_id = primary.id
                await primary.edit(embed=embed)
                for dup in old_status_msgs[1:]:
                    try:
                        await dup.delete()
                    except Exception:
                        pass
                return

            msg = await channel.send(embed=embed)
            self.status_message_id = msg.id
        except Exception as e:
            logger.error(f"Error updating status dashboard: {e}")

    @commands.hybrid_command(name="status", aliases=["serverstatus"], description="Get current Nova Station 13 status")
    async def cmd_status(self, ctx: commands.Context):
        status_data = await self.byond.get_status()
        service_active = self.get_service_status() == "active"
        if not service_active or not status_data or not isinstance(status_data, dict):
            await ctx.send("🔴 **Server is currently offline or unreachable.**")
            return

        embed = discord.Embed(
            title=f"Nova Station 13 - Round #{status_data.get('round_id', 'N/A')}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value="🟢 Online", inline=True)
        embed.add_field(name="Map", value=status_data.get("map_name", "Unknown"), inline=True)
        embed.add_field(name="Mode", value=status_data.get("mode", "Unknown").capitalize(), inline=True)
        embed.add_field(name="Players", value=str(status_data.get("players", 0)), inline=True)
        embed.add_field(name="Admins", value=str(status_data.get("admins", 0)), inline=True)
        embed.add_field(name="Round Duration", value=status_data.get("roundtime", "00:00:00"), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="manifest", aliases=["crew", "roster"], description="View the current station crew manifest")
    async def cmd_manifest(self, ctx: commands.Context):
        await ctx.defer()
        manifest_data = await self.byond.get_manifest()
        if not manifest_data or not isinstance(manifest_data, dict):
            await ctx.send("❌ Unable to retrieve crew manifest (server may be loading or offline).")
            return

        dept_labels = {
            "heads": "🎖️ Command",
            "sec": "🛡️ Security",
            "eng": "🔧 Engineering",
            "med": "⚕️ Medical",
            "sci": "🔬 Science",
            "car": "📦 Supply / Cargo",
            "srv": "🍸 Service",
            "ast": "🎒 Assistants",
            "bot": "🤖 Non-Human / Silicons",
            "misc": "📁 Miscellaneous"
        }

        embed = discord.Embed(
            title="📋 Station Crew Manifest",
            color=discord.Color.teal()
        )

        has_any = False
        for key, label in dept_labels.items():
            members = manifest_data.get(key)
            if members and isinstance(members, dict) and len(members) > 0:
                has_any = True
                lines = [f"`{rank}` **{name}**" for name, rank in members.items()]
                embed.add_field(name=label, value="\n".join(lines[:15]), inline=False)

        if not has_any:
            embed.description = "No crew members are currently registered in the manifest."

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StatusCog(bot))
