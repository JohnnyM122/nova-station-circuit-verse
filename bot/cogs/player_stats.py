import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import mysql.connector
import datetime

logger = logging.getLogger("CVNovaHelper.player_stats")

class PlayerStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.byond = bot.byond
        self.config = bot.config

    def get_db_connection(self):
        db_conf = self.config.get("database", {})
        return mysql.connector.connect(
            host=db_conf.get("host", "127.0.0.1"),
            user=db_conf.get("user", "nova_station_app"),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", "paradise_gamedb")
        )

    def is_staff(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return True
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            tier = staff_cog.get_staff_tier(member)
            return tier in ("FOUNDER", "ADMIN", "MODERATOR", "MENTOR")
        return False

    @app_commands.command(name="player_info", description="Look up a player's in-game record, connection stats, and history")
    @app_commands.describe(ckey="The BYOND ckey of the player to look up")
    async def cmd_player_info(self, interaction: discord.Interaction, ckey: str):
        clean_ckey = ckey.strip().lower().replace(" ", "")
        await interaction.response.defer()

        def fetch_data():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM player WHERE LOWER(ckey) = %s", (clean_ckey,))
            player_row = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) AS total_conns, MAX(datetime) AS last_conn FROM connection_log WHERE LOWER(ckey) = %s", (clean_ckey,))
            conn_row = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) AS ban_count FROM ban WHERE LOWER(ckey) = %s AND (unbanned IS NULL OR unbanned = 0)", (clean_ckey,))
            ban_row = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) AS note_count FROM notes WHERE LOWER(ckey) = %s AND (deleted IS NULL OR deleted = 0)", (clean_ckey,))
            notes_row = cursor.fetchone()

            cursor.execute("SELECT discord_id, linked_at FROM discord_links WHERE LOWER(ckey) = %s", (clean_ckey,))
            link_row = cursor.fetchone()

            cursor.execute("SELECT a.display_rank, r.name AS rank_name FROM admin a LEFT JOIN admin_ranks r ON a.permissions_rank = r.id WHERE LOWER(a.ckey) = %s", (clean_ckey,))
            admin_row = cursor.fetchone()

            cursor.close()
            conn.close()
            return player_row, conn_row, ban_row, notes_row, link_row, admin_row

        try:
            player_row, conn_row, ban_row, notes_row, link_row, admin_row = await asyncio.to_thread(fetch_data)
        except Exception as e:
            await interaction.followup.send(f"❌ Database error: `{e}`")
            return

        if not player_row:
            await interaction.followup.send(f"❌ No player record found in database for ckey **`{clean_ckey}`**.")
            return

        embed = discord.Embed(
            title=f"📋 Station Personnel Record: {clean_ckey}",
            color=discord.Color.from_rgb(0, 225, 255)
        )

        first_seen = player_row.get("firstseen")
        first_seen_str = first_seen.strftime("%Y-%m-%d %H:%M") if isinstance(first_seen, datetime.datetime) else str(first_seen or "Unknown")
        last_seen = player_row.get("lastseen")
        last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M") if isinstance(last_seen, datetime.datetime) else str(last_seen or "Unknown")

        embed.add_field(name="📅 First Registered", value=first_seen_str, inline=True)
        embed.add_field(name="🕒 Last Active", value=last_seen_str, inline=True)
        embed.add_field(name="🔌 Total Connections", value=str(conn_row["total_conns"] if conn_row else 0), inline=True)

        if admin_row:
            staff_rank = admin_row.get("display_rank") or admin_row.get("rank_name") or "Staff"
            embed.add_field(name="🛡️ Staff Position", value=f"**{staff_rank}**", inline=True)

        if link_row:
            discord_user = f"<@{link_row['discord_id']}>"
            embed.add_field(name="🔗 Discord Account", value=discord_user, inline=True)

        # Only reveal notes and bans summary if requester is staff
        if self.is_staff(interaction.user):
            bans = ban_row["ban_count"] if ban_row else 0
            notes = notes_row["note_count"] if notes_row else 0
            embed.add_field(name="⚠️ Active Bans", value=str(bans), inline=True)
            embed.add_field(name="📝 Admin Notes", value=str(notes), inline=True)

        embed.set_footer(text="Nova Station 13 Personnel Database • Circuit Verse", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        await interaction.followup.send(embed=embed)

    @commands.hybrid_command(name="who", description="View all players and crew members currently active in the game")
    async def cmd_who(self, ctx: commands.Context):
        await ctx.defer()

        # Query manifest and status simultaneously
        manifest_task = asyncio.create_task(self.byond.get_manifest())
        status_task = asyncio.create_task(self.byond.get_status())
        manifest, status = await asyncio.gather(manifest_task, status_task, return_exceptions=True)

        if not status or not isinstance(status, dict):
            await ctx.send("🔴 **Nova Station 13 is currently offline or unreachable.**")
            return

        total_players = status.get("players", 0)
        round_id = status.get("round_id", "N/A")
        map_name = status.get("map_name", "Unknown")

        embed = discord.Embed(
            title=f"👥 Station Roster — Round #{round_id} ({total_players} Online)",
            description=f"Map: **{map_name}** • Mode: **{status.get('mode', 'Unknown').capitalize()}** • Duration: `{status.get('roundtime', '00:00:00')}`",
            color=discord.Color.teal()
        )

        dept_emojis = {
            "heads": "🎖️ Command",
            "sec": "🛡️ Security",
            "eng": "🔧 Engineering",
            "med": "⚕️ Medical",
            "sci": "🔬 Science",
            "car": "📦 Supply / Cargo",
            "srv": "🍸 Service",
            "ast": "🎒 Assistants",
            "bot": "🤖 Silicons"
        }

        has_crew = False
        if isinstance(manifest, dict):
            for dept_key, dept_name in dept_emojis.items():
                members = manifest.get(dept_key)
                if members and isinstance(members, dict):
                    has_crew = True
                    lines = [f"• `{rank}` **{name}**" for name, rank in list(members.items())[:8]]
                    count_str = f"({len(members)})"
                    embed.add_field(name=f"{dept_name} {count_str}", value="\n".join(lines), inline=False)

        if not has_crew:
            embed.description += "\n\n*No crew members registered in the current station manifest (round may be starting).* "

        guild_icon = ctx.guild.icon.url if (ctx.guild and ctx.guild.icon) else None
        embed.set_footer(text="Nova Station 13 Live Crew Manifest • Circuit Verse", icon_url=guild_icon)
        await ctx.send(embed=embed)

    @app_commands.command(name="deaths", description="View recent casualties and final words from the station")
    @app_commands.describe(round_id="The Round ID to check casualties for (defaults to current or latest round)")
    async def cmd_deaths(self, interaction: discord.Interaction, round_id: int = None):
        await interaction.response.defer()

        def fetch_deaths():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            target_rid = round_id
            if not target_rid:
                cursor.execute("SELECT MAX(id) AS latest_round FROM round")
                latest = cursor.fetchone()
                target_rid = latest["latest_round"] if latest else None

            if not target_rid:
                cursor.close()
                conn.close()
                return None, []

            cursor.execute("""
                SELECT name, byondkey, job, last_words, tod, bruteloss, fireloss, brainloss, oxyloss
                FROM death
                WHERE death_rid = %s
                ORDER BY id DESC
                LIMIT 10
            """, (target_rid,))
            deaths = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) AS total_deaths FROM death WHERE death_rid = %s", (target_rid,))
            total_row = cursor.fetchone()
            total_count = total_row["total_deaths"] if total_row else len(deaths)

            cursor.close()
            conn.close()
            return target_rid, total_count, deaths

        try:
            target_rid, total_count, deaths = await asyncio.to_thread(fetch_deaths)
        except Exception as e:
            await interaction.followup.send(f"❌ Database error: `{e}`")
            return

        if not target_rid:
            await interaction.followup.send("❌ No round records found in the database.")
            return

        if not deaths:
            await interaction.followup.send(f"🕊️ **Zero recorded casualties for Round #{target_rid}!** All crew members survived or data has not synced yet.")
            return

        embed = discord.Embed(
            title=f"💀 Round #{target_rid} Casualties Report ({total_count} Total)",
            description=f"Showing the **{len(deaths)}** most recent crew casualties logged in the medical database:",
            color=discord.Color.dark_red()
        )

        for d in deaths:
            name = d.get("name", "Unknown")
            job = d.get("job", "Crew")
            ckey = d.get("byondkey", "unknown")
            last_words = d.get("last_words")
            last_words_str = f'*"{last_words}"*' if last_words else "*None recorded*"

            damage_types = []
            if d.get("bruteloss", 0) > 0:
                damage_types.append(f"Brute: {d['bruteloss']}")
            if d.get("fireloss", 0) > 0:
                damage_types.append(f"Burn: {d['fireloss']}")
            if d.get("oxyloss", 0) > 0:
                damage_types.append(f"Oxy: {d['oxyloss']}")
            if d.get("brainloss", 0) > 0:
                damage_types.append(f"Brain: {d['brainloss']}")
            damage_str = ", ".join(damage_types) if damage_types else "Unknown causes"

            embed.add_field(
                name=f"⚰️ {name} ({job}) — `{ckey}`",
                value=f"**Last Words:** {last_words_str}\n**Damage:** {damage_str}",
                inline=False
            )

        embed.set_footer(text=f"Nova Station 13 Morgue Log • Round #{target_rid}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="round_info", description="View detailed summary and statistics for any station round")
    @app_commands.describe(round_id="The round number to view (defaults to latest)")
    async def cmd_round_info(self, interaction: discord.Interaction, round_id: int = None):
        await interaction.response.defer()

        def fetch_round():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if round_id:
                cursor.execute("SELECT * FROM round WHERE id = %s", (round_id,))
            else:
                cursor.execute("SELECT * FROM round ORDER BY id DESC LIMIT 1")
            r_data = cursor.fetchone()

            if not r_data:
                cursor.close()
                conn.close()
                return None, 0

            rid = r_data["id"]
            cursor.execute("SELECT COUNT(*) AS casualties FROM death WHERE death_rid = %s", (rid,))
            death_row = cursor.fetchone()
            casualties = death_row["casualties"] if death_row else 0

            cursor.close()
            conn.close()
            return r_data, casualties

        try:
            r_data, casualties = await asyncio.to_thread(fetch_round)
        except Exception as e:
            await interaction.followup.send(f"❌ Database error: `{e}`")
            return

        if not r_data:
            await interaction.followup.send(f"❌ No round record found with ID `{round_id}`.")
            return

        rid = r_data["id"]
        embed = discord.Embed(
            title=f"🪐 Round #{rid} Archives",
            description=f"**Station:** {r_data.get('station_name', 'Nova Station 13')}",
            color=discord.Color.purple()
        )

        embed.add_field(name="🗺️ Map", value=r_data.get("map_name", "Unknown"), inline=True)
        embed.add_field(name="🎲 Game Mode", value=str(r_data.get("game_mode", "Unknown")).capitalize(), inline=True)
        embed.add_field(name="🏁 Result", value=r_data.get("game_mode_result") or r_data.get("end_state") or "In Progress", inline=True)

        start = r_data.get("start_datetime") or r_data.get("initialize_datetime")
        end = r_data.get("end_datetime") or r_data.get("shutdown_datetime")
        start_str = start.strftime("%Y-%m-%d %H:%M") if isinstance(start, datetime.datetime) else str(start or "N/A")
        end_str = end.strftime("%Y-%m-%d %H:%M") if isinstance(end, datetime.datetime) else (str(end) if end else "Active / Ongoing")

        embed.add_field(name="🚀 Round Started", value=start_str, inline=True)
        embed.add_field(name="🏁 Round Concluded", value=end_str, inline=True)
        embed.add_field(name="💀 Total Casualties", value=str(casualties), inline=True)

        embed.set_footer(text="Nova Station 13 Archives • Circuit Verse")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="View top crew members by total server connections and veteran status")
    @app_commands.describe(metric="Choose metric to rank players by")
    @app_commands.choices(metric=[
        app_commands.Choice(name="Total Connections (Most active)", value="connections"),
        app_commands.Choice(name="Veterans (Earliest registered)", value="veterans")
    ])
    async def cmd_leaderboard(self, interaction: discord.Interaction, metric: app_commands.Choice[str]):
        await interaction.response.defer()

        def fetch_lb():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if metric.value == "connections":
                cursor.execute("""
                    SELECT ckey, COUNT(*) AS count_val, MAX(datetime) AS last_seen
                    FROM connection_log
                    GROUP BY ckey
                    ORDER BY count_val DESC
                    LIMIT 10
                """)
            else:
                cursor.execute("""
                    SELECT ckey, firstseen AS count_val, lastseen
                    FROM player
                    WHERE firstseen IS NOT NULL
                    ORDER BY firstseen ASC
                    LIMIT 10
                """)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows

        try:
            rows = await asyncio.to_thread(fetch_lb)
        except Exception as e:
            await interaction.followup.send(f"❌ Database error: `{e}`")
            return

        title_str = "🔌 Most Active Crew (Total Connections)" if metric.value == "connections" else "🎖️ Oldest Crew Veterans"
        embed = discord.Embed(title=f"🏆 Station Leaderboard: {title_str}", color=discord.Color.gold())

        lines = []
        for i, row in enumerate(rows, 1):
            ckey = row["ckey"]
            val = row["count_val"]
            if isinstance(val, datetime.datetime):
                val_str = val.strftime("%Y-%m-%d")
            else:
                val_str = f"{val:,} connections"

            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"`#{i:2d}`"))
            lines.append(f"{medal} **`{ckey}`** — {val_str}")

        embed.description = "\n".join(lines) if lines else "No data available."
        embed.set_footer(text="Nova Station 13 Hall of Fame • Circuit Verse")
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------
    # Admin Notes & Watchlist Management Commands
    # -------------------------------------------------------------

    @app_commands.command(name="note_add", description="Add an official administrative note or warning to a player's record")
    @app_commands.describe(ckey="Player BYOND ckey", note="The note or warning text")
    async def cmd_note_add(self, interaction: discord.Interaction, ckey: str, note: str):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("🚫 **Access Denied**: Staff permissions required.", ephemeral=True)
            return

        clean_ckey = ckey.strip().lower().replace(" ", "")

        def insert_note():
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (ckey, notetext, timestamp, adminckey, server, automated, deleted, public)
                VALUES (%s, %s, NOW(), %s, %s, 0, 0, 0)
            """, (clean_ckey, note, interaction.user.name, "Nova Station 13"))
            conn.commit()
            cursor.close()
            conn.close()

        try:
            await asyncio.to_thread(insert_note)
            embed = discord.Embed(title="📝 Admin Note Recorded", color=discord.Color.blue())
            embed.add_field(name="Target CKey", value=f"`{clean_ckey}`", inline=True)
            embed.add_field(name="Staff Member", value=interaction.user.mention, inline=True)
            embed.add_field(name="Note Text", value=note, inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to record note: `{e}`", ephemeral=True)

    @app_commands.command(name="note_list", description="View administrative notes and warnings for a player")
    @app_commands.describe(ckey="Player BYOND ckey")
    async def cmd_note_list(self, interaction: discord.Interaction, ckey: str):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("🚫 **Access Denied**: Staff permissions required.", ephemeral=True)
            return

        clean_ckey = ckey.strip().lower().replace(" ", "")

        def fetch_notes():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, notetext, timestamp, adminckey
                FROM notes
                WHERE LOWER(ckey) = %s AND (deleted IS NULL OR deleted = 0)
                ORDER BY timestamp DESC
                LIMIT 10
            """, (clean_ckey,))
            notes = cursor.fetchall()
            cursor.close()
            conn.close()
            return notes

        try:
            notes = await asyncio.to_thread(fetch_notes)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error fetching notes: `{e}`", ephemeral=True)
            return

        if not notes:
            await interaction.response.send_message(f"ℹ️ No active notes found for **`{clean_ckey}`**.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📝 Staff Notes for `{clean_ckey}` ({len(notes)})", color=discord.Color.blue())
        for n in notes:
            ts = n["timestamp"].strftime("%Y-%m-%d") if isinstance(n["timestamp"], datetime.datetime) else str(n["timestamp"])
            embed.add_field(
                name=f"Note #{n['id']} • By {n.get('adminckey', 'Staff')} on {ts}",
                value=n["notetext"][:300],
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="watch_add", description="Place a player on the station administrative watchlist")
    @app_commands.describe(ckey="Player BYOND ckey", reason="Reason for watching this player")
    async def cmd_watch_add(self, interaction: discord.Interaction, ckey: str, reason: str):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("🚫 **Access Denied**: Staff permissions required.", ephemeral=True)
            return

        clean_ckey = ckey.strip().lower().replace(" ", "")

        def insert_watch():
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO watch (ckey, reason, timestamp, adminckey)
                VALUES (%s, %s, NOW(), %s)
                ON DUPLICATE KEY UPDATE reason = %s, timestamp = NOW(), adminckey = %s
            """, (clean_ckey, reason, interaction.user.name, reason, interaction.user.name))
            conn.commit()
            cursor.close()
            conn.close()

        try:
            await asyncio.to_thread(insert_watch)
            embed = discord.Embed(title="👁️ Player Added to Watchlist", color=discord.Color.gold())
            embed.add_field(name="Target CKey", value=f"`{clean_ckey}`", inline=True)
            embed.add_field(name="Logged By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding to watchlist: `{e}`", ephemeral=True)

    @app_commands.command(name="watch_list", description="View players currently on the administrative watchlist")
    async def cmd_watch_list(self, interaction: discord.Interaction):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("🚫 **Access Denied**: Staff permissions required.", ephemeral=True)
            return

        def fetch_watch():
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT ckey, reason, timestamp, adminckey FROM watch ORDER BY timestamp DESC LIMIT 20")
            watched = cursor.fetchall()
            cursor.close()
            conn.close()
            return watched

        try:
            watched = await asyncio.to_thread(fetch_watch)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error fetching watchlist: `{e}`", ephemeral=True)
            return

        if not watched:
            await interaction.response.send_message("ℹ️ Watchlist is currently empty.", ephemeral=True)
            return

        embed = discord.Embed(title=f"👁️ Administrative Watchlist ({len(watched)} Listed)", color=discord.Color.gold())
        for w in watched:
            ts = w["timestamp"].strftime("%Y-%m-%d") if isinstance(w["timestamp"], datetime.datetime) else str(w["timestamp"])
            embed.add_field(
                name=f"⚠️ `{w['ckey']}` (by {w.get('adminckey', 'Staff')} on {ts})",
                value=f"**Reason:** {w['reason'][:250]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="watch_remove", description="Remove a player from the administrative watchlist")
    @app_commands.describe(ckey="Player BYOND ckey to remove")
    async def cmd_watch_remove(self, interaction: discord.Interaction, ckey: str):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("🚫 **Access Denied**: Staff permissions required.", ephemeral=True)
            return

        clean_ckey = ckey.strip().lower().replace(" ", "")

        def del_watch():
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watch WHERE LOWER(ckey) = %s", (clean_ckey,))
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return deleted

        try:
            deleted = await asyncio.to_thread(del_watch)
            if deleted > 0:
                await interaction.response.send_message(f"✅ Removed **`{clean_ckey}`** from the administrative watchlist.")
            else:
                await interaction.response.send_message(f"ℹ️ **`{clean_ckey}`** was not found on the watchlist.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing from watchlist: `{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PlayerStatsCog(bot))
