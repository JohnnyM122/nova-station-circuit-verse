import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
import os
import aiohttp
import subprocess
import json
import re

logger = logging.getLogger("CVNovaHelper.radio")

def clean_song_title(text: str) -> str:
    """Removes common YouTube video clutter like (Official 4K Video), [Lyrics], etc."""
    if not text:
        return ""
    # Strip bracketed / parenthesized video tags
    tag_pattern = r"(?i)\s*[\(\[](?:official\s*(?:4k|hd|music|lyric|audio)?\s*video|original\s*video.*?|video\s*with\s*subtitles|official\s*(?:audio|music\s*video|video)|lyric\s*video|lyrics|4k\s*video|hd\s*video|audio|music\s*video|4k|hd|ncs\s*release|ncs\s*official|free\s*download)[\)\]]"
    text = re.sub(tag_pattern, "", text)
    # Strip trailing delimiters like " | Official Video" or " - Official 4K Video" or " | Eurodance Classic" or " | NCS Release"
    text = re.sub(r"(?i)\s*[\|\-–—]\s*(?:official\s*(?:video|audio|music\s*video)|eurodance\s*classic|4k\s*video|hd\s*video|4k|hd|ncs\s*release).*$", "", text)
    # Strip standalone phrases
    text = re.sub(r"(?i)\b(?:official\s*4k\s*video|official\s*video|official\s*audio|official\s*music\s*video|ncs\s*release)\b", "", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# --- Discord DAVE E2EE protocol compatibility layer ---
from discord.voice_state import VoiceConnectionState
from discord.gateway import DiscordVoiceWebSocket
import struct

# 1. Allow encryption when either can_encrypt or ready is True on dave_session
def _patched_can_encrypt(self):
    if not getattr(self, "dave_session", None):
        return False
    return (
        getattr(self, "dave_protocol_version", 0) != 0
        and (getattr(self.dave_session, "can_encrypt", False) or getattr(self.dave_session, "ready", False))
    )

VoiceConnectionState.can_encrypt = property(_patched_can_encrypt)

# 2. Patch received_binary_message to handle transition_id == 0 properly
orig_received_binary_message = DiscordVoiceWebSocket.received_binary_message

async def _patched_received_binary_message(self, msg: bytes) -> None:
    op = msg[2]
    await orig_received_binary_message(self, msg)
    if op in (DiscordVoiceWebSocket.MLS_ANNOUNCE_COMMIT_TRANSITION, DiscordVoiceWebSocket.MLS_WELCOME):
        transition_id = struct.unpack_from('>H', msg, 3)[0]
        if transition_id == 0:
            state = self._connection
            if state and getattr(state, "dave_session", None):
                try:
                    state.dave_session.execute_transition(0)
                    logger.info("Executed DAVE transition 0 on dave_session")
                except Exception as e:
                    logger.debug(f"execute_transition(0) notice: {e}")
                try:
                    await self.send_transition_ready(0)
                    logger.info("Sent DAVE transition ready for id 0")
                except Exception as e:
                    logger.debug(f"send_transition_ready(0) notice: {e}")

DiscordVoiceWebSocket.received_binary_message = _patched_received_binary_message

# 3. Patch _execute_transition so dave_session executes transitions
orig_execute_transition = VoiceConnectionState._execute_transition

async def _patched_execute_transition(self, transition_id: int) -> None:
    if getattr(self, "dave_session", None):
        try:
            self.dave_session.execute_transition(transition_id)
            logger.info(f"Executed DAVE transition {transition_id} on dave_session")
        except Exception as e:
            logger.debug(f"dave_session.execute_transition({transition_id}) notice: {e}")
    await orig_execute_transition(self, transition_id)

VoiceConnectionState._execute_transition = _patched_execute_transition
# --- End of DAVE compatibility layer ---

class SongSelectMenu(discord.ui.Select):
    def __init__(self, cog, songs: list, user: discord.Member, note: str = ""):
        options = []
        for s in songs[:25]:
            display_title = s["title"][:95]
            display_artist = s["artist"][:95] if s.get("artist") else "Stream-Safe EDM"
            options.append(
                discord.SelectOption(
                    label=display_title,
                    description=display_artist,
                    value=s["request_id"],
                    emoji="🎵"
                )
            )
        super().__init__(
            placeholder="Click here to choose a song to play...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.cog = cog
        self.user = user
        self.note = note

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        req_id = self.values[0]
        res = await self.cog.submit_request_by_id(self.user, req_id, self.note)
        if res.get("success"):
            embed = discord.Embed(
                title="🎵 Song Request Queued!",
                description=f"**Track:** {res.get('title')}\n**Artist:** {res.get('artist')}",
                color=discord.Color.green()
            )
            if self.note:
                embed.add_field(name="Dedication", value=self.note, inline=False)
            embed.set_footer(text=f"Requested by {self.user.display_name}")
            
            if interaction.channel:
                await interaction.channel.send(embed=embed)
            await interaction.followup.send(f"✅ Queued **{res.get('title')}**!", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Could not queue song: {res.get('error')}", ephemeral=True)


class SongDropdownView(discord.ui.View):
    def __init__(self, cog, songs: list, user: discord.Member, note: str = ""):
        super().__init__(timeout=120)
        self.add_item(SongSelectMenu(cog, songs, user, note))


class SongRequestModal(discord.ui.Modal, title="Search & Request a Song"):
    song_input = discord.ui.TextInput(
        label="Song Title, Artist, or Keyword",
        placeholder="e.g. Funeral, Home, Alan, Witch, House, Synthwave...",
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

        matches = await self.cog.search_library(query)
        if matches:
            if len(matches) == 1:
                res = await self.cog.submit_request_by_id(interaction.user, matches[0]["request_id"], note)
                if res.get("success"):
                    embed = discord.Embed(
                        title="🎵 Song Request Queued!",
                        description=f"**Track:** {res.get('title')}\n**Artist:** {res.get('artist')}",
                        color=discord.Color.green()
                    )
                    if note:
                        embed.add_field(name="Dedication", value=note, inline=False)
                    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                    if interaction.channel:
                        await interaction.channel.send(embed=embed)
                    await interaction.followup.send(f"✅ Queued **{res.get('title')}**!", ephemeral=True)
                    return
                else:
                    await interaction.followup.send(f"❌ Could not queue track: {res.get('error')}", ephemeral=True)
                    return
            else:
                view = SongDropdownView(self.cog, matches[:25], interaction.user, note)
                await interaction.followup.send(
                    f"🔍 Found **{len(matches)}** matching songs for **\"{query}\"**!\n**Choose your track from the dropdown below:**",
                    view=view,
                    ephemeral=True
                )
                return

        all_songs = await self.cog.get_requestable_songs()
        if all_songs:
            import random
            sample = random.sample(all_songs, min(25, len(all_songs)))
            view = SongDropdownView(self.cog, sample, interaction.user, note)
            await interaction.followup.send(
                f"🔍 No exact match found for **\"{query}\"** in our {len(all_songs)}-song library.\n**Pick a track from the library below:**",
                view=view,
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ No matching tracks found for \"{query}\".", ephemeral=True)


def get_station_base_url():
    tunnel_file = "/tmp/radio_tunnel_url.txt"
    if os.path.exists(tunnel_file):
        try:
            with open(tunnel_file, "r") as f:
                url = f.read().strip()
                if url.startswith("https://") or url.startswith("http://"):
                    return url
        except Exception:
            pass
    return "https://radio.circuitverse.online"


class RadioPlayerView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        base_url = get_station_base_url()
        self.add_item(discord.ui.Button(
            label="Web Player",
            style=discord.ButtonStyle.link,
            emoji="🌐",
            url=f"{base_url}/public/circuit_verse_radio"
        ))

    @discord.ui.button(label="Search & Request", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="cv_radio_request_btn")
    async def request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SongRequestModal(self.cog))

    @discord.ui.button(label="Browse Songs", style=discord.ButtonStyle.success, emoji="📋", custom_id="cv_radio_browse_btn")
    async def browse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        all_songs = await self.cog.get_requestable_songs()
        if not all_songs:
            await interaction.followup.send("❌ Library is currently updating, please try again in a few seconds.", ephemeral=True)
            return
        import random
        sample = random.sample(all_songs, min(25, len(all_songs)))
        view = SongDropdownView(self.cog, sample, interaction.user)
        await interaction.followup.send(
            f"📻 **Circuit Verse Library ({len(all_songs)} songs available)**\nSelect a track from the dropdown menu to queue it:",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Join My VC", style=discord.ButtonStyle.secondary, emoji="🔊", custom_id="cv_radio_join_btn")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        vc_channel = interaction.user.voice.channel
        res = await self.cog.connect_to_voice(interaction.guild, vc_channel)
        if res.get("success"):
            await interaction.followup.send(f"🎶 Connected to **{vc_channel.name}** and streaming **Circuit Verse Radio**!", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Could not connect: {res.get('error')}", ephemeral=True)

    @discord.ui.button(label="Leave VC", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="cv_radio_leave_btn")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        res = await self.cog.disconnect_from_voice(interaction.guild)
        if res.get("success"):
            await interaction.followup.send("⏹️ Disconnected from voice channel.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Bot is not currently in any voice channel.", ephemeral=True)


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
            "title": "Stream-Safe 24/7",
            "artist": "Pretzel Rocks",
            "art": None,
            "listeners": 0,
            "next_song": "AutoDJ Rotation"
        }

        # Ensure Opus is loaded for high-performance audio encoding
        if not discord.opus.is_loaded():
            try:
                discord.opus._load_default()
                logger.info("Loaded discord Opus library successfully.")
            except Exception as e:
                logger.warning(f"Could not load discord Opus: {e}")

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
            ch = await guild.create_text_channel(name=channel_name, overwrites=overwrites, topic="📻 Circuit Verse 24/7 Internet Radio — Stream-Safe Beats powered by Pretzel Rocks!")
            self.radio_cfg["channel_id"] = ch.id
            logger.info(f"Created dedicated radio channel: #{ch.name} ({ch.id})")
            return ch
        except Exception as e:
            logger.error(f"Error creating #{channel_name}: {e}")
            return None

    def build_player_embed(self):
        base_url = get_station_base_url()
        stream_url = f"{base_url}/listen/circuit_verse_radio/radio.mp3"
        logo_url = f"{base_url}/static/img/circuit_verse_radio.jpg"

        embed = discord.Embed(
            title="📻 Circuit Verse Radio — 24/7 Live Stream",
            description="Broadcasting 24/7 stream-safe EDM, Synthwave, Lofi, and Electronic Beats for the Circuit Verse community.",
            color=discord.Color.from_rgb(0, 168, 255)
        )
        embed.add_field(
            name="🌐 Subdomain & Web Player",
            value="✨ **Now Hosted on Subdomain! [radio.circuitverse.online](https://radio.circuitverse.online)**\n"
                  f"🔗 **Web Player:** **[Open Web Player]({base_url}/public/circuit_verse_radio)**\n"
                  f"📻 **Direct Stream:** **[Listen to Stream]({stream_url})**\n"
                  "🌐 **Main Domain:** **[CircuitVerse.Online](https://circuitverse.online)**\n"
                  "⛏️ **Official Minecraft Server:** `play.circuitverse.online`",
            inline=False
        )
        embed.add_field(name="🎶 Now Playing", value=f"**{self.now_playing_data['title']}**\n*{self.now_playing_data['artist']}*", inline=False)
        embed.add_field(name="⏭️ Up Next", value=self.now_playing_data.get("next_song", "AutoDJ Shuffle"), inline=True)
        embed.add_field(name="🎧 Listeners", value=str(self.now_playing_data.get("listeners", 0)), inline=True)
        embed.add_field(
            name="🛡️ Music Provider & Licensing",
            value="Music provided by **[Pretzel Rocks](https://www.pretzel.rocks)**\n*100% Cleared for live streams & Discord voice broadcasts.*",
            inline=False
        )
        embed.add_field(
            name="⚙️ Station Software & Hosting",
            value="Powered by **[AzuraCast](https://www.azuracast.com/)** (Icecast & Liquidsoap)\nHosted on **[Hetzner Cloud](https://www.hetzner.com/cloud)** • Secured by **[Cloudflare](https://www.cloudflare.com/)**",
            inline=False
        )
        
        art = self.now_playing_data.get("art")
        if art and "generic_song" not in art:
            for host in ["87.99.133.221", "127.0.0.1", "localhost", "circuitverse.online"]:
                art = art.replace(f"https://{host}", base_url).replace(f"http://{host}", base_url)
            embed.set_thumbnail(url=art)
        else:
            embed.set_thumbnail(url=logo_url)

        embed.set_footer(text="Powered by AzuraCast • Hosted on Hetzner • Music courtesy of Pretzel Rocks")
        return embed

    async def connect_to_voice(self, guild: discord.Guild, channel: discord.VoiceChannel):
        try:
            if not discord.opus.is_loaded():
                try:
                    discord.opus._load_default()
                    logger.info("Loaded discord Opus library.")
                except Exception as e:
                    logger.warning(f"Could not load discord Opus: {e}")

            vc = guild.voice_client or self.active_voice_clients.get(guild.id)
            if vc and vc.is_connected():
                if vc.channel.id != channel.id:
                    await vc.move_to(channel)
            else:
                vc = await channel.connect(timeout=20.0, reconnect=True, self_deaf=True, self_mute=False)

            self.active_voice_clients[guild.id] = vc

            conn = getattr(vc, "_connection", None)
            dave_ver = getattr(conn, "dave_protocol_version", None) if conn else None
            can_enc = getattr(conn, "can_encrypt", None) if conn else None
            logger.info(f"Voice state immediately after connect: is_connected={vc.is_connected()}, dave_version={dave_ver}, can_encrypt={can_enc}")

            if conn and dave_ver and dave_ver > 0:
                for _ in range(15):
                    if conn.can_encrypt:
                        break
                    await asyncio.sleep(0.1)
                logger.info(f"Voice state after DAVE wait: can_encrypt={conn.can_encrypt}, session_ready={getattr(conn.dave_session, 'ready', False)}")

            stream_url = self.radio_cfg.get("stream_url", "http://127.0.0.1/listen/circuit_verse_radio/radio.mp3")
            logger.info(f"Connecting audio stream to #{channel.name} (Guild: {guild.name}) via {stream_url}")

            if vc.is_playing():
                vc.stop()

            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    stream_url,
                    before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    options='-vn'
                ),
                volume=0.8
            )
            vc.play(source, after=lambda e: logger.error(f"VC playback stopped with error: {e}") if e else logger.info("VC playback stopped cleanly."))
            logger.info("Started streaming radio to voice channel successfully.")

            async def monitor_dave_session():
                for sec in range(8):
                    await asyncio.sleep(1)
                    if conn and getattr(conn, "dave_session", None):
                        ds = conn.dave_session
                        logger.info(f"DAVE Stream Check [{sec+1}s]: status={ds.status}, ready={ds.ready}, ds.can_enc={ds.can_encrypt}, conn.can_enc={conn.can_encrypt}, epoch={ds.epoch}, seq={getattr(vc, 'sequence', None)}")
            asyncio.create_task(monitor_dave_session())

            return {"success": True}
        except Exception as e:
            logger.error(f"Error connecting to VC: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def disconnect_from_voice(self, guild: discord.Guild):
        vc = guild.voice_client or self.active_voice_clients.get(guild.id)
        if vc and vc.is_connected():
            try:
                if vc.is_playing():
                    vc.stop()
                await vc.disconnect(force=True)
            except Exception as e:
                logger.warning(f"Error while disconnecting: {e}")
            self.active_voice_clients.pop(guild.id, None)
            return {"success": True}
        return {"success": False}

    async def download_and_queue_youtube(self, query: str):
        target = query if (query.startswith("http://") or query.startswith("https://")) else f"ytsearch1:{query}"
        media_dir = "/var/lib/docker/volumes/azuracast_station_data/_data/circuit_verse_radio/media"
        
        try:
            cmd = [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=android",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--max-filesize", "50M",
                "--no-playlist",
                "-o", f"{media_dir}/%(title)s.%(ext)s",
                "--print", "title",
                target
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                downloaded_title = stdout.decode("utf-8").strip().splitlines()[0] if stdout else query
                clean_title = clean_song_title(downloaded_title)

                # Set permissions and sync AzuraCast
                await asyncio.create_subprocess_exec("docker", "exec", "azuracast", "chown", "-R", "azuracast:azuracast", "/var/azuracast/stations/circuit_verse_radio/media")
                sync_proc = await asyncio.create_subprocess_exec("docker", "exec", "azuracast", "azuracast_cli", "azuracast:media:sync", "circuit_verse_radio")
                await sync_proc.communicate()

                # Clean song title in station_media if YouTube title had video tags
                if clean_title != downloaded_title:
                    clean_esc = clean_title.replace("'", "''")
                    down_esc = downloaded_title.replace("'", "''")
                    clean_sql = f"UPDATE station_media SET title='{clean_esc}', text=CONCAT(COALESCE(artist, ''), ' - ', '{clean_esc}') WHERE title='{down_esc}' OR title LIKE '%{down_esc}%';"
                    await asyncio.create_subprocess_exec("docker", "exec", "azuracast", "gosu", "azuracast", "php", "/var/azuracast/www/backend/bin/console", "dbal:run-sql", clean_sql)

                # Insert into station playlist
                sql = "INSERT IGNORE INTO station_playlist_media (playlist_id, media_id, weight, last_played, is_queued) SELECT 1, id, 0, 0, 0 FROM station_media;"
                await asyncio.create_subprocess_exec("docker", "exec", "azuracast", "gosu", "azuracast", "php", "/var/azuracast/www/backend/bin/console", "dbal:run-sql", sql)

                # Submit request to play next
                azura_url = self.radio_cfg.get("azuracast_url", "http://127.0.0.1")
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    async with session.get(f"{azura_url}/api/station/1/requests") as req_resp:
                        if req_resp.status == 200:
                            req_list = await req_resp.json()
                            for item in req_list:
                                song_title = item.get("song", {}).get("title", "").lower()
                                song_text = item.get("song", {}).get("text", "").lower()
                                if clean_title.lower() in song_title or clean_title.lower() in song_text or downloaded_title.lower() in song_title or downloaded_title.lower() in song_text:
                                    req_url = item.get("request_url", "")
                                    if req_url.startswith("/"):
                                        req_url = f"{azura_url}{req_url}"
                                    await session.post(req_url)
                                    break
                
                return {
                    "success": True,
                    "title": clean_title,
                    "artist": "YouTube Request"
                }
            else:
                err_str = stderr.decode("utf-8", errors="ignore")
                logger.warning(f"yt-dlp error: {err_str}")
                return {
                    "success": False,
                    "error": "Track not found in station library. (For YouTube links, try an alternate upload or remix, or select an iconic 90s/00s hit!)."
                }
        except Exception as e:
            logger.error(f"Error downloading YouTube request: {e}")
            return {"success": False, "error": str(e)}

    async def get_requestable_songs(self, force=False) -> list:
        now = time.time()
        if not force and hasattr(self, "_cached_songs") and (now - getattr(self, "_last_songs_fetch", 0) < 120):
            return self._cached_songs

        azura_url = self.radio_cfg.get("azuracast_url", "http://127.0.0.1")
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.get(f"{azura_url}/api/station/1/requests", timeout=5) as resp:
                    if resp.status == 200:
                        raw = await resp.json()
                        songs = []
                        for item in raw:
                            s = item.get("song", {})
                            t = clean_song_title(s.get("title") or s.get("text") or "")
                            a = clean_song_title(s.get("artist") or "")
                            if " - " in t and (not a or a.lower() in ("ncs", "stream-safe", "pretzel rocks", "nocopyrightsounds")):
                                parts = t.split(" - ", 1)
                                a = parts[0].strip()
                                t = parts[1].strip()
                            elif not a:
                                a = "Stream-Safe EDM"
                            songs.append({
                                "request_id": item.get("request_id"),
                                "request_url": item.get("request_url"),
                                "title": t,
                                "artist": a,
                                "search_text": f"{t} {a}".lower()
                            })
                        self._cached_songs = songs
                        self._last_songs_fetch = now
                        return songs
        except Exception as e:
            logger.warning(f"Error fetching requestable songs: {e}")
        return getattr(self, "_cached_songs", [])

    async def search_library(self, query: str) -> list:
        if not query:
            return []
        songs = await self.get_requestable_songs()
        q = query.lower().strip()
        for s in songs:
            if s["request_id"] == q:
                return [s]

        matches = [s for s in songs if q in s["search_text"]]
        return matches

    async def submit_request_by_id(self, user: discord.Member, request_id: str, note: str = "") -> dict:
        azura_url = self.radio_cfg.get("azuracast_url", "http://127.0.0.1")
        songs = await self.get_requestable_songs()
        matched = next((s for s in songs if s["request_id"] == request_id), None)
        title = matched["title"] if matched else "Requested Track"
        artist = matched["artist"] if matched else "Circuit Verse Radio"

        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                url = f"{azura_url}/api/station/1/request/{request_id}"
                async with session.post(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success"):
                            logger.info(f"User {user} successfully queued {title} ({request_id})")
                            return {"success": True, "title": title, "artist": artist}
                        else:
                            return {"success": False, "error": data.get("message", "Request was rejected by station.")}
                    else:
                        return {"success": False, "error": f"Station returned HTTP {resp.status}"}
        except Exception as e:
            logger.error(f"Error submitting request {request_id}: {e}")
            return {"success": False, "error": str(e)}

    async def handle_song_request(self, user: discord.Member, query: str, note: str = ""):
        logger.info(f"User {user} requested: {query}")
        matches = await self.search_library(query)
        if matches:
            return await self.submit_request_by_id(user, matches[0]["request_id"], note)

        return await self.download_and_queue_youtube(query)

    @tasks.loop(seconds=25)
    async def radio_updater_task(self):
        try:
            await self.bot.wait_until_ready()
            azura_url = self.radio_cfg.get("azuracast_url", "http://127.0.0.1")

            try:
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    async with session.get(f"{azura_url}/api/nowplaying", timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and len(data) > 0:
                                np = data[0].get("now_playing") or {}
                                song = np.get("song") or {}
                                listeners = (data[0].get("listeners") or {}).get("total", 0)
                                
                                next_wrapper = data[0].get("playing_next") or {}
                                next_obj = next_wrapper.get("song") or {}
                                raw_next = clean_song_title(next_obj.get("title") or next_obj.get("text") or "AutoDJ Rotation")
                                if " - " in raw_next and raw_next.lower().startswith("ncs - "):
                                    parts = [p.strip() for p in raw_next.split(" - ") if p.strip()]
                                    if len(parts) >= 3:
                                        raw_next = f"{parts[-2]} - {parts[-1]}"
                                    elif len(parts) == 2:
                                        raw_next = parts[1]

                                raw_title = clean_song_title(song.get("title") or song.get("text") or "Stream-Safe Beats")
                                raw_artist = clean_song_title(song.get("artist") or "")
                                if " - " in raw_title and (not raw_artist or raw_artist.lower() in ("ncs", "stream-safe", "pretzel rocks", "nocopyrightsounds")):
                                    parts = raw_title.split(" - ", 1)
                                    raw_artist = parts[0].strip()
                                    raw_title = parts[1].strip()
                                elif not raw_artist:
                                    raw_artist = "Pretzel Rocks"

                                self.now_playing_data = {
                                    "title": raw_title,
                                    "artist": raw_artist,
                                    "art": song.get("art"),
                                    "listeners": listeners,
                                    "next_song": raw_next
                                }
            except Exception as e:
                logger.error(f"NowPlaying poll error: {e}", exc_info=True)

            # Update message in #cv-radio
            for guild in self.bot.guilds:
                channel = await self.get_or_create_radio_channel(guild)
                if not channel:
                    continue

                embed = self.build_player_embed()
                view = RadioPlayerView(self)

                # Purge any old/stale messages from the bot in #cv-radio to prevent duplicate/broken buttons
                old_messages = []
                async for old_msg in channel.history(limit=25):
                    if old_msg.author == self.bot.user and len(old_msg.embeds) > 0:
                        if "Circuit Verse Radio" in (old_msg.embeds[0].title or ""):
                            old_messages.append(old_msg)

                if old_messages:
                    primary_msg = old_messages[0]
                    self.player_message_id = primary_msg.id
                    await primary_msg.edit(embed=embed, view=view)
                    for extra_msg in old_messages[1:]:
                        try:
                            await extra_msg.delete()
                        except Exception:
                            pass
                else:
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

    @radio_group.command(name="request", description="Request a song from our 600-track library or a YouTube link")
    @app_commands.describe(query="Type to search song title or artist")
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

    @radio_request.autocomplete("query")
    async def song_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        matches = await self.search_library(current) if current else (await self.get_requestable_songs())[:25]
        choices = []
        for m in matches[:25]:
            display = f"{m['title']} - {m['artist']}" if m.get("artist") and m["artist"] != "Stream-Safe EDM" else m["title"]
            if len(display) > 100:
                display = display[:97] + "..."
            choices.append(app_commands.Choice(name=display, value=m["request_id"]))
        return choices

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
