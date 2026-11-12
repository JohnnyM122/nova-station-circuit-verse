import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import json, urllib.request

with open("/etc/cv-panel/config.json") as f:
    cfg = json.load(f)

token = cfg["discord_bot_token"]
guild_id = cfg["guild_id"]

req = urllib.request.Request(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers={
    "Authorization": f"Bot {token}",
    "User-Agent": "DiscordBot (CircuitVerse, 1.0)"
})

with urllib.request.urlopen(req) as resp:
    channels = json.load(resp)

cats = {c["id"]: c["name"] for c in channels if c.get("type") == 4}
for ch in channels:
    name = ch.get("name", "")
    pname = cats.get(ch.get("parent_id"), "")
    if any(k in name.lower() or k in pname.lower() for k in ["zomboid", "pz", "staff"]):
        print(f"[{pname or \"TOP\"}] #{name} (ID: {ch[\"id\"]}, type: {ch.get(\"type\")})")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
