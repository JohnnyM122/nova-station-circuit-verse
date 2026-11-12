import subprocess
import base64

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

patch_script = r'''
import re

cog_path = "/home/ubuntu/CV-Nova-Helper/cogs/project_zomboid.py"
with open(cog_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Ensure timedelta is imported
if "from datetime import datetime, timezone" in code and "timedelta" not in code:
    code = code.replace("from datetime import datetime, timezone", "from datetime import datetime, timezone, timedelta")

# 2. Add delete_after=300 to send_status_channel_alert
code = re.sub(
    r"await ch\.send\(embed=embed\)",
    "await ch.send(embed=embed, delete_after=300)",
    code
)

# 3. Add on_message listener if not present
if "async def on_message(self, message: discord.Message):" not in code:
    listener_code = """
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
"""
    code = code.replace("    @tasks.loop(seconds=60)\n    async def status_loop(self):", listener_code + "\n    @tasks.loop(seconds=60)\n    async def status_loop(self):")

# 4. Add channel pruning logic inside status_loop
prune_code = """
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
"""

if "Auto-prune PZ server logs" not in code:
    target = 'await msg.edit(embed=embed)'
    if target in code:
        code = code.replace(target, target + "\n" + prune_code)
    else:
        code = code.replace("        embed.set_footer(text=", prune_code + "\n        embed.set_footer(text=")

with open(cog_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Project Zomboid Cog patched successfully!")
'''

b64 = base64.b64encode(patch_script.encode("utf-8")).decode("ascii")
cmd = f"echo {b64} | base64 -d | sudo python3 && sudo systemctl restart cv-nova-helper.service && sudo systemctl is-active cv-nova-helper.service"

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
