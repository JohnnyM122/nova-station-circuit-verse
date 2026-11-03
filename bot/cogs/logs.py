import discord
from discord.ext import commands, tasks
import logging
import mysql.connector
import asyncio
import os
import glob

logger = logging.getLogger("CVNovaHelper.logs")

class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.last_admin_log_id = None
        self.runtime_file_pos = 0
        self.current_runtime_file = None
        self.poll_admin_logs.start()
        self.poll_server_logs.start()

    def cog_unload(self):
        self.poll_admin_logs.cancel()
        self.poll_server_logs.cancel()

    def get_db_connection(self):
        db_conf = self.config.get("database", {})
        return mysql.connector.connect(
            host=db_conf.get("host", "localhost"),
            user=db_conf.get("user", "root"),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", "paradise_gamedb")
        )

    @tasks.loop(seconds=5.0)
    async def poll_admin_logs(self):
        admin_channel_id = self.config["channels"].get("admin_logs")
        if not admin_channel_id:
            return

        channel = self.bot.get_channel(admin_channel_id)
        if not channel:
            return

        try:
            conn = await asyncio.to_thread(self.get_db_connection)
            cursor = conn.cursor(dictionary=True)

            if self.last_admin_log_id is None:
                # Initialize to current highest ID so we don't spam ancient logs
                cursor.execute("SELECT MAX(id) AS max_id FROM admin_log")
                row = cursor.fetchone()
                self.last_admin_log_id = row["max_id"] if row and row["max_id"] else 0
                cursor.close()
                conn.close()
                return

            cursor.execute("""
                SELECT id, datetime, adminckey, log
                FROM admin_log
                WHERE id > %s
                ORDER BY id ASC LIMIT 25
            """, (self.last_admin_log_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            for row in rows:
                self.last_admin_log_id = max(self.last_admin_log_id, row["id"])
                admin = row.get("adminckey", "Unknown")
                log_text = row.get("log", "")
                dt = str(row.get("datetime", ""))

                embed = discord.Embed(
                    title=f"🛡️ Admin Log: {admin}",
                    description=f"```\n{log_text[:1900]}\n```",
                    color=discord.Color.dark_blue()
                )
                embed.set_footer(text=f"Log #{row['id']} • {dt}")
                await channel.send(embed=embed)
        except Exception as e:
            logger.debug(f"Admin log polling error: {e}")

    def find_latest_runtime_file(self):
        base_dir = "/home/ubuntu/NovaStation/data/logs"
        pattern = f"{base_dir}/**/**/**/runtime.log"
        files = glob.glob(pattern, recursive=True)
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    @tasks.loop(seconds=10.0)
    async def poll_server_logs(self):
        server_channel_id = self.config["channels"].get("server_logs")
        if not server_channel_id:
            return

        channel = self.bot.get_channel(server_channel_id)
        if not channel:
            return

        try:
            latest_file = await asyncio.to_thread(self.find_latest_runtime_file)
            if not latest_file or not os.path.exists(latest_file):
                return

            if latest_file != self.current_runtime_file:
                self.current_runtime_file = latest_file
                self.runtime_file_pos = os.path.getsize(latest_file)
                return

            current_size = os.path.getsize(latest_file)
            if current_size > self.runtime_file_pos:
                with open(latest_file, "r", encoding="latin1", errors="replace") as f:
                    f.seek(self.runtime_file_pos)
                    new_content = f.read()
                    self.runtime_file_pos = f.tell()

                if new_content.strip():
                    lines = new_content.strip().splitlines()
                    chunk = "\n".join(lines[:25])
                    embed = discord.Embed(
                        title="⚠️ Server Runtime / Error Detected",
                        description=f"```\n{chunk[:1900]}\n```",
                        color=discord.Color.orange()
                    )
                    embed.set_footer(text=f"File: {os.path.basename(os.path.dirname(latest_file))}/runtime.log")
                    await channel.send(embed=embed)
        except Exception as e:
            logger.debug(f"Server log polling error: {e}")

async def setup(bot):
    await bot.add_cog(LogsCog(bot))
