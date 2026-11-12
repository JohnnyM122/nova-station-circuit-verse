import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import json

with open("/etc/cv-panel/config.json") as f:
    cfg = json.load(f)

token = cfg["discord_bot_token"]

ini_path = "/home/pz/Zomboid/Server/CircuitVersePZ.ini"
with open(ini_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith("DiscordEnable="):
        new_lines.append("DiscordEnable=true\\n")
    elif stripped.startswith("DiscordToken="):
        new_lines.append(f"DiscordToken={token}\\n")
    elif stripped.startswith("DiscordChatChannel="):
        new_lines.append("DiscordChatChannel=💬・pz-in-game-chat\\n")
    elif stripped.startswith("DiscordLogChannel="):
        new_lines.append("DiscordLogChannel=🖥️・pz-server-logs\\n")
    elif stripped.startswith("DiscordCommandChannel="):
        new_lines.append("DiscordCommandChannel=💻・pz-staff-commands\\n")
    else:
        new_lines.append(line)

with open(ini_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# Also sync to repo
import shutil
shutil.copy2(ini_path, "/home/pz/repo/server_config/CircuitVersePZ.ini")
print("Updated CircuitVersePZ.ini with Discord settings!")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
