import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import mysql.connector
import asyncio

logger = logging.getLogger("CVNovaHelper.bans")

def parse_duration(dur_str: str) -> int:
    """Parses a duration string into minutes. 0 indicates permanent."""
    s = dur_str.strip().lower()
    if s in ["0", "perm", "permanent", "perma", "never"]:
        return 0

    match = re.match(r"^(\d+)\s*([mhdwy]?)$", s)
    if not match:
        raise ValueError(f"Invalid duration format: '{dur_str}'. Use e.g. 30m, 2h, 1d, 7d, 14d, perm.")

    val, unit = int(match.group(1)), match.group(2)
    if unit in ["", "m"]:
        return val
    elif unit == "h":
        return val * 60
    elif unit == "d":
        return val * 1440
    elif unit == "w":
        return val * 10080
    elif unit == "y":
        return val * 525600
    return val

class BansCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.byond = bot.byond

    def get_db_connection(self):
        db_conf = self.config.get("database", {})
        return mysql.connector.connect(
            host=db_conf.get("host", "127.0.0.1"),
            user=db_conf.get("user", "nova_station_app"),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", "paradise_gamedb")
        )

    def check_staff_permission(self, member: discord.Member, is_perma: bool, duration_mins: int):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            allowed, reason = staff_cog.check_command_access(member, "ban")
            if not allowed:
                return False, reason
            tier = staff_cog.get_staff_tier(member)
        else:
            tier = "NONE"

        if member.guild_permissions.administrator or tier in ["FOUNDER", "ADMIN"]:
            return True, "ADMIN"

        if tier == "MODERATOR":
            if is_perma:
                return False, "Moderators and Chief Mentors cannot issue permanent bans. Maximum duration is 14 days (20160 minutes)."
            if duration_mins > 20160:
                return False, f"Maximum ban duration for your role is 14 days (20160 minutes). Requested: {duration_mins} minutes."
            return True, "MODERATOR"

        return True, tier

    @app_commands.command(name="ban", description="Ban a player from the server or a job")
    @app_commands.describe(
        ckey="BYOND key or ckey of the player",
        duration="Duration (e.g. 30m, 2h, 1d, 7d, 14d, perm)",
        reason="Reason for the ban",
        ban_type="Server Ban or Job Ban",
        job="Job name (required if Job Ban)"
    )
    @app_commands.choices(ban_type=[
        app_commands.Choice(name="Server Ban", value="SERVER"),
        app_commands.Choice(name="Job Ban", value="JOB")
    ])
    async def cmd_ban(
        self,
        interaction: discord.Interaction,
        ckey: str,
        duration: str,
        reason: str,
        ban_type: app_commands.Choice[str],
        job: str = None
    ):
        try:
            duration_mins = parse_duration(duration)
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        is_perma = (duration_mins == 0)

        # Enforce strict staff check
        allowed, perm_reason = self.check_staff_permission(interaction.user, is_perma, duration_mins)
        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {perm_reason}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        # Determine bantype string
        if ban_type.value == "JOB":
            if not job:
                await interaction.followup.send("❌ You must specify a `job` when issuing a Job Ban.", ephemeral=True)
                return
            target_bantype = "JOB_PERMABAN" if is_perma else "JOB_TEMPBAN"
        else:
            target_bantype = "PERMABAN" if is_perma else "TEMPBAN"

        sender_tag = f"{interaction.user.display_name} ({interaction.user.name})"

        res = await self.byond.issue_ban(
            ckey=ckey,
            bantype=target_bantype,
            duration=duration_mins,
            reason=reason,
            sender=sender_tag,
            job=job
        )

        if not res or not isinstance(res, dict) or not res.get("success"):
            await interaction.followup.send(f"❌ Failed to apply ban: {res}", ephemeral=True)
            return

        duration_desc = f"{duration_mins} minutes" if duration_mins > 0 else "Permanent"
        embed = discord.Embed(
            title="🔨 Ban Applied Successfully",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="Target CKey", value=f"`{ckey}`", inline=True)
        embed.add_field(name="Type", value=target_bantype, inline=True)
        embed.add_field(name="Duration", value=duration_desc, inline=True)
        if job:
            embed.add_field(name="Job", value=job, inline=True)
        embed.add_field(name="Admin", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Recorded in database and applied to live server")

        await interaction.followup.send(embed=embed)

        # Also post to admin logs channel
        admin_logs_channel_id = self.config["channels"].get("admin_logs")
        if admin_logs_channel_id:
            ch = self.bot.get_channel(admin_logs_channel_id)
            if ch and ch.id != interaction.channel.id:
                await ch.send(embed=embed)

    @app_commands.command(name="unban", description="Unban a player in the database")
    @app_commands.describe(ckey="BYOND key or ckey of the player to unban")
    async def cmd_unban(self, interaction: discord.Interaction, ckey: str):
        staff_cog = self.bot.get_cog("StaffManagementCog")
        if staff_cog:
            allowed, perm_reason = staff_cog.check_command_access(interaction.user, "unban")
        else:
            allowed, perm_reason = self.check_staff_permission(interaction.user, is_perma=True, duration_mins=0)

        if not allowed:
            await interaction.response.send_message(f"🚫 **Access Denied**: {perm_reason}", ephemeral=True)
            return

        await interaction.response.defer()
        target_ckey = ckey.strip().lower()

        try:
            conn = await asyncio.to_thread(self.get_db_connection)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ban
                SET unbanned = 1, unbanned_datetime = NOW(), unbanned_ckey = %s
                WHERE ckey = %s AND (unbanned IS NULL OR unbanned = 0)
            """, (interaction.user.name, target_ckey))
            rows_affected = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            if rows_affected > 0:
                await interaction.followup.send(f"✅ Successfully unbanned `{target_ckey}` ({rows_affected} active ban(s) lifted).")
            else:
                await interaction.followup.send(f"ℹ️ No active bans found for `{target_ckey}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Database error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BansCog(bot))
