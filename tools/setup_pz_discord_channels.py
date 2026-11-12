import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import json, urllib.request

with open("/etc/cv-panel/config.json") as f:
    cfg = json.load(f)

token = cfg["discord_bot_token"]
guild_id = cfg["guild_id"]

headers = {
    "Authorization": f"Bot {token}",
    "Content-Type": "application/json",
    "User-Agent": "DiscordBot (CircuitVerse, 1.0)"
}

# Fetch categories to copy permission overwrites
def get_cat(cid):
    req = urllib.request.Request(f"https://discord.com/api/v10/channels/{cid}", headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

pz_cat = get_cat("1567692616202719405")
staff_cat = get_cat("1567692617112756407")

# Check if channels already exist
req_guild = urllib.request.Request(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers)
with urllib.request.urlopen(req_guild) as resp:
    existing_channels = {c["name"]: c for c in json.load(resp)}

def create_or_get_channel(name, parent_cat, topic, pos):
    if name in existing_channels:
        print(f"Channel #{name} already exists (ID: {existing_channels[name][\"id\"]})")
        return existing_channels[name]
    
    payload = {
        "name": name,
        "type": 0,
        "parent_id": parent_cat["id"],
        "topic": topic,
        "position": pos,
        "permission_overwrites": parent_cat.get("permission_overwrites", [])
    }
    req = urllib.request.Request(f"https://discord.com/api/v10/guilds/{guild_id}/channels", 
                                 data=json.dumps(payload).encode("utf-8"), 
                                 headers=headers, 
                                 method="POST")
    with urllib.request.urlopen(req) as resp:
        ch = json.load(resp)
        print(f"Created #{name} (ID: {ch[\"id\"]})")
        return ch

ch_chat = create_or_get_channel("💬・pz-in-game-chat", pz_cat, "Project Zomboid In-Game Chat Bridge • Live 2-way chat between Knox County survivors and Discord.", 95)
ch_logs = create_or_get_channel("🖥️・pz-server-logs", staff_cat, "Project Zomboid Server Event Stream • Live server connection logs, combat, deaths, and admin events.", 104)

# Function to post and pin embed
def post_and_pin(ch_id, title, desc, color):
    embed = {
        "title": title,
        "description": desc,
        "color": color,
        "footer": {"text": "Circuit Verse • Project Zomboid Dedicated Network"}
    }
    msg_req = urllib.request.Request(f"https://discord.com/api/v10/channels/{ch_id}/messages",
                                     data=json.dumps({"embeds": [embed]}).encode("utf-8"),
                                     headers=headers,
                                     method="POST")
    with urllib.request.urlopen(msg_req) as resp:
        msg = json.load(resp)
        mid = msg["id"]
        # Pin message
        pin_req = urllib.request.Request(f"https://discord.com/api/v10/channels/{ch_id}/pins/{mid}",
                                         headers=headers,
                                         method="PUT")
        urllib.request.urlopen(pin_req)
        print(f"Posted and pinned embed in {ch_id}")

chat_desc = (
    "### 🧟 Welcome to the Project Zomboid In-Game Chat Bridge!\\n\\n"
    "This channel provides real-time, bi-directional communication between our dedicated Build 42 Knox County server and Discord.\\n\\n"
    "**How It Works:**\\n"
    "• Messages typed here will instantly appear in-game in the **[Global]** chat channel for all active survivors.\\n"
    "• In-game global chat messages from players will be transmitted directly to this channel in real-time.\\n\\n"
    "**Channel Guidelines:**\\n"
    "1. Keep discussion civil and adhere to server rules (#📜・pz-rules).\\n"
    "2. No spamming, advertising, or toxic behavior.\\n"
    "3. Roleplay and survivor distress calls are welcomed!"
)
post_and_pin(ch_chat["id"], "💬 Project Zomboid In-Game Chat Bridge", chat_desc, 0x10b981)

logs_desc = (
    "### 🖥️ Project Zomboid Server Console & Event Logs\\n\\n"
    "This restricted staff channel receives automated real-time event feeds directly from the Project Zomboid dedicated server daemon.\\n\\n"
    "**Streamed Events:**\\n"
    "• Survivor connections, disconnects, and Steam authentication validations.\\n"
    "• Survivor deaths, infected casualties, and PvP encounters.\\n"
    "• Administrative commands, server reloads, and safety sentinel warnings.\\n\\n"
    "*(Staff Only • Restricted Access)*"
)
post_and_pin(ch_logs["id"], "🖥️ Project Zomboid Server Event Stream", logs_desc, 0x3b82f6)
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
