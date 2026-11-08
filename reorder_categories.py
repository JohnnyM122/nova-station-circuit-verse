import json
import urllib.request
import urllib.error

CONFIG_PATH = "/home/ubuntu/CV-Nova-Helper/config.json"
with open(CONFIG_PATH, "r") as f:
    cfg = json.load(f)

token = cfg.get("bot_token")
guild_id = "1564605314752585797"

desired_category_order = [
    # Community
    1566679559481462864, # 📊・Community Dashboard
    1564605316849733723, # 💬・Community General
    1564605316849733724, # 🔊・Voice Channels
    1567345837510758430, # 📻・CV Radio Station
    1567435050331537468, # 🎫・Community Support Area
    1568819739847823360, # 🎫・Community Tickets
    1566680487504650330, # 🛡️・Community Staff Area

    # NS13
    1566607420275564638, # 🚀・Circuit Verse - SS13
    1566608607829692696, # 🚀・NS13 Staff Area
    1568819763059359754, # 🎫・NS13 Staff Tickets

    # Minecraft
    1567426382664040459, # ⛏️・CircuitVerse-Minecraft
    1567464236177817620, # ⛏️・Minecraft Staff Area
    1568819751315185785, # 🎫・MC Staff Tickets
    1567537293357486261, # 🚨Incident Managment Tickets

    # Project Zomboid
    1567692616202719405, # 🧟・CircuitVerse-Zomboid
    1567692617112756407, # 🧟・Zomboid Staff Area
    1568819774803283988, # 🎫・PZ Staff Tickets

    # Unturned
    1568805615164334171, # 🌲・CircuitVerse-Unturned
    1568805616443596880, # 🌲・Unturned Staff Area
    1568819786228432978, # 🎫・Unturned Staff Tickets
]

payload = [{"id": str(cat_id), "position": idx} for idx, cat_id in enumerate(desired_category_order)]

req = urllib.request.Request(
    f"https://discord.com/api/v10/guilds/{guild_id}/channels",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "CircuitVerseBot/1.0"
    },
    method="PATCH"
)

try:
    with urllib.request.urlopen(req) as resp:
        print(f"SUCCESS: Categories reordered atomically! HTTP {resp.status}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
