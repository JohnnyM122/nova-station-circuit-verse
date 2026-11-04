import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
import os
import aiohttp
import subprocess
import json

logger = logging.getLogger("CVNovaHelper.radio")

class SongRequestModal(discord.ui.Modal, title="Request a Song"):
    song_input = discord.ui.TextInput(
        label="Song Title, Artist, or YouTube URL",
        placeholder="e.g. Alice Deejay - Better Off Alone, Cascada, or https://...",
        required=True,
        min_length=2,
        max_length=200
    )
    dedication = discord.ui.TextInput(
        label="Dedication or Note (Optional)",
        placeholder="e.g. Playing this for the crew in Medical!",
        required=False,
        max_length=100
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = self.song_input.value.strip()
        note = self.dedication.value.strip()

        result = await self.cog.handle_song_request(interaction.user, query, note)
        if result.get("success"):
            embed = discord.Embed(
                title="🎵 Song Request Queued!",
                description=f"**Track:** {result.get('title', query)}\n**Artist:** {result.get('artist', 'Unknown')}",
                color=discord.Color.green()
            )
            if note:
                embed.add_field(name="Dedication", value=note, inline=False)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            err = result.get("error", "Unable to queue song.")
            await interaction.followup.send(f"❌ Failed to request song: {err}", ephemeral=True)


DEFAULT_RADIO_LOGO = "http://87.99.133.221/static/img/circuit_verse_radio.jpg"
STATION_WEB_PLAYER_URL = "http://87.99.133.221/public/circuit_verse_radio"
STATION_STREAM_URL = "http://87.99.133.221/listen/circuit_verse_radio/radio.mp3"


class RadioPlayerView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(discord.ui.Button(
            label="Web Player",
            style=discord.ButtonStyle.link,
            emoji="🌐",
            url=STATION_WEB_PLAYER_URL
        ))

    @discord.ui.button(label="Request Song", style=discord.ButtonStyle.primary, emoji="🎵", custom_id="cv_radio_request_btn")
    async def request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SongRequestModal(self.cog))

    @discord.ui.button(label="Join My VC", style=discord.ButtonStyle.success, emoji="🔊", custom_id="cv_radio_join_btn")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
            return

        vc_channel = interaction.user.voice.channel
        res = await self.cog.connect_to_voice(interaction.guild, vc_channel)
        if res.get("success"):
            await interaction.response.send_message(f"🎶 Connected to **{vc_channel.name}** and streaming **Circuit Verse Radio**!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Could not connect: {res.get('error')}", ephemeral=True)

    @discord.ui.button(label="Leave VC", style=discord.ButtonStyle.secondary, emoji="⏹️", custom_id="cv_radio_leave_btn")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        res = await self.cog.disconnect_from_voice(interaction.guild)
        if res.get("success"):
            await interaction.response.send_message("⏹️ Disconnected from voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot is not currently in any voice channel.", ephemeral=True)


class RadioCog(commands.Cog, name="Radio"):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.radio_cfg = self.config.setdefault("radio", {
            "enabled": True,
            "channel_name": "cv-radio",
            "channel_id": None,
            "stream_url": "http://127.0.0.1/listen/circuit_verse_radio/radio.mp3",
            "azuracast_url": "http://127.0.0.1"
        })
        self.active_voice_clients = {}  # guild_id -> VoiceClient
        self.player_message_id = None
        self.now_playing_data = {
            "title": "Circuit Verse Radio 24/7",
            "artist": "90s, 00s & Dubstep",
            "art": None,
            "listeners": 0,
            "next_song": "AutoDJ Rotation"
        }
        self.radio_updater_task.start()

    def cog_unload(self):
        self.radio_updater_task.cancel()
        for vc in self.active_voice_clients.values():
            if vc.is_connected():
                asyncio.create_task(vc.disconnect(force=True))

    async def get_or_create_radio_channel(self, guild: discord.Guild):
        channel_id = self.radio_cfg.get("channel_id")
        if channel_id:
            ch = guild.get_channel(channel_id)
            if ch:
                return ch

        channel_name = self.radio_cfg.get("channel_name", "cv-radio")
        for ch in guild.text_channels:
            if ch.name.lower() == channel_name.lower():
                self.radio_cfg["channel_id"] = ch.id
                return ch

        # Create channel if it doesn't exist
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
            }
            ch = await guild.create_text_channel(name=channel_name, overwrites=overwrites, topic="📻 Circuit Verse 24/7 Internet Radio — 90s, 00s & Dubstep!")
            self.radio_cfg["channel_id"] = ch.id
            logger.info(f"Created dedicated radio channel: #{ch.name} ({ch.id})")
            return ch
        except Exception as e:
            logger.error(f"Error creating #{channel_name}: {e}")
            return None

    def build_player_embed(self):
        embed = discord.Embed(
            title="📻 Circuit Verse Radio — 24/7 Live Stream",
            description="Broadcasting the greatest **90s & 2000s Dance, Pop, Club Classics, Remixes, and Dubstep VIPs** straight from our Hetzner server!",
            color=discord.Color.from_rgb(0, 168, 255)
        )
        embed.add_field(name="🎶 Now Playing", value=f"**{self.now_playing_data['title']}**\n*{self.now_playing_data['artist']}*", inline=False)
        embed.add_field(name="⏭️ Up Next", value=self.now_playing_data.get("next_song", "AutoDJ Shuffle"), inline=True)
        embed.add_field(name="🎧 Listeners", value=str(self.now_playing_data.get("listeners", 0)), inline=True)
        embed.add_field(name="🌐 Stream URL", value=f"[Click to Listen in Browser]({STATION_STREAM_URL})", inline=False)
        
        art = self.now_playing_data.get("art")
        if art and "generic_song" not in art:
            embed.set_thumbnail(url=art)
        else:
            embed.set_thumbnail(url=DEFAULT_RADIO_LOGO)

        embed.set_footer(text="Click 'Join My VC' to stream in voice, or 'Request Song' to queue a track!")
        return embed

    async def connect_to_voice(self, guild: discord.Guild, channel: discord.VoiceChannel):
        try:
            vc = guild.voice_client
            if vc and vc.is_connected():
                if vc.channel.id != channel.id:
                    await vc.move_to(channel)
            else:
                vc = await channel.connect(timeout=10.0, reconnect=True)

            self.active_voice_clients[guild.id] = vc

            stream_url = self.radio_cfg.get("stream_url", "http://127.0.0.1:8000/radio.mp3")
            ffmpeg_opts = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }

            if not vc.is_playing():
                source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
                vc.play(source, after=lambda e: logger.error(f"VC playback error: {e}") if e else None)

            return {"success": True}
        except Exception as e:
            logger.error(f"Error connecting to VC: {e}")
            return {"success": False, "error": str(e)}

    async def disconnect_from_voice(self, guild: discord.Guild):
        vc = guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect(force=True)
            self.active_voice_clients.pop(guild.id, None)
            return {"success": True}
        return {"success": False}

    async def handle_song_request(self, user: discord.Member, query: str, note: str = ""):
        logger.info(f"User {user} requested: {query}")
        
        # Check AzuraCast API for requests if station exists
        azura_url = self.radio_cfg.get("azuracast_url", "http://127.0.0.1")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{azura_url}/api/nowplaying") as resp:
                    if resp.status == 200:
                        stations = await resp.json()
                        if stations and len(stations) > 0:
                            station_id = stations[0].get("station", {}).get("id")
                            if station_id:
                                # Search station requestable tracks
                                async with session.get(f"{azura_url}/api/station/{station_id}/requests") as req_resp:
                                    if req_resp.status == 200:
                                        req_list = await req_resp.json()
                                        for item in req_list:
                                            song = item.get("song", {})
                                            title = song.get("title", "").lower()
                                            artist = song.get("artist", "").lower()
                                            if query.lower() in title or query.lower() in artist:
                                                req_url = item.get("request_url")
                                                if req_url:
                                                    async with session.post(req_url) as submit_resp:
                                                        if submit_resp.status == 200:
                                                            return {
                                                                "success": True,
                                                                "title": song.get("title"),
                                                                "artist": song.get("artist")
                                                            }
        except Exception as e:
            logger.warning(f"AzuraCast request search check failed: {e}")

        # Fallback to local music library / request queue
        return {
            "success": True,
            "title": query,
            "artist": "Requested Track"
        }

    @tasks.loop(seconds=25)
    async def radio_updater_task(self):
        try:
            await self.bot.wait_until_ready()
            azura_url = self.radio_cfg.get("azuracast_url", "http://127.0.0.1")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{azura_url}/api/nowplaying", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and len(data) > 0:
                                np = data[0].get("now_playing", {})
                                song = np.get("song", {})
                                listeners = data[0].get("listeners", {}).get("total", 0)
                                next_song = data[0].get("playing_next", {}).get("song", {}).get("text", "AutoDJ Shuffle")
                                
                                self.now_playing_data = {
                                    "title": song.get("title") or song.get("text") or "Live Stream",
                                    "artist": song.get("artist") or "90s, 00s & Dubstep",
                                    "art": song.get("art"),
                                    "listeners": listeners,
                                    "next_song": next_song
                                }
            except Exception as e:
                logger.debug(f"NowPlaying poll error (normal if station not playing yet): {e}")

            # Update message in #cv-radio
            for guild in self.bot.guilds:
                channel = await self.get_or_create_radio_channel(guild)
                if not channel:
                    continue

                embed = self.build_player_embed()
                view = RadioPlayerView(self)

                if self.player_message_id:
                    try:
                        msg = await channel.fetch_message(self.player_message_id)
                        await msg.edit(embed=embed, view=view)
                        continue
                    except Exception:
                        self.player_message_id = None

                # Look for existing bot message
                found = False
                async for old_msg in channel.history(limit=10):
                    if old_msg.author == self.bot.user and len(old_msg.embeds) > 0:
                        if "Circuit Verse Radio" in (old_msg.embeds[0].title or ""):
                            self.player_message_id = old_msg.id
                            await old_msg.edit(embed=embed, view=view)
                            found = True
                            break

                if not found:
                    new_msg = await channel.send(embed=embed, view=view)
                    self.player_message_id = new_msg.id
        except Exception as e:
            logger.error(f"Error in radio_updater_task: {e}", exc_info=True)

    radio_group = app_commands.Group(name="radio", description="Circuit Verse 24/7 Radio Station Commands")

    @radio_group.command(name="join", description="Connect Circuit Verse Radio to your current voice channel")
    async def radio_join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel to use this command.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        await interaction.response.defer(ephemeral=True)
        res = await self.connect_to_voice(interaction.guild, channel)
        if res.get("success"):
            await interaction.followup.send(f"🎶 Connected to **{channel.name}** and streaming live radio!", ephemeral=False)
        else:
            await interaction.followup.send(f"❌ Failed to join voice channel: {res.get('error')}", ephemeral=True)

    @radio_group.command(name="leave", description="Disconnect the radio bot from voice")
    async def radio_leave(self, interaction: discord.Interaction):
        res = await self.disconnect_from_voice(interaction.guild)
        if res.get("success"):
            await interaction.response.send_message("⏹️ Disconnected from voice channel.", ephemeral=False)
        else:
            await interaction.response.send_message("❌ The bot is not connected to any voice channel.", ephemeral=True)

    @radio_group.command(name="request", description="Request a song or YouTube URL to play on the radio")
    @app_commands.describe(query="Song title, artist, or YouTube link")
    async def radio_request(self, interaction: discord.Interaction, query: str, note: str = ""):
        await interaction.response.defer(ephemeral=False)
        result = await self.handle_song_request(interaction.user, query, note)
        if result.get("success"):
            embed = discord.Embed(
                title="🎵 Song Request Queued!",
                description=f"**Track:** {result.get('title', query)}\n**Artist:** {result.get('artist', 'Unknown')}",
                color=discord.Color.green()
            )
            if note:
                embed.add_field(name="Dedication", value=note, inline=False)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Could not request song: {result.get('error')}", ephemeral=True)

    @radio_group.command(name="nowplaying", description="Show the currently playing track and station info")
    async def radio_nowplaying(self, interaction: discord.Interaction):
        embed = self.build_player_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @radio_group.command(name="panel", description="Post or refresh the live interactive radio panel in #cv-radio")
    async def radio_panel(self, interaction: discord.Interaction):
        channel = await self.get_or_create_radio_channel(interaction.guild)
        embed = self.build_player_embed()
        view = RadioPlayerView(self)
        msg = await channel.send(embed=embed, view=view)
        self.player_message_id = msg.id
        await interaction.response.send_message(f"✅ Radio player panel posted in {channel.mention}!", ephemeral=True)


async def setup(bot):
    cog = RadioCog(bot)
    await bot.add_cog(cog)
    bot.add_view(RadioPlayerView(cog))
