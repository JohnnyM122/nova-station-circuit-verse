import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"
PARENT_ID = "1566679559481462864"

ORDERED_CHANNEL_IDS = [
    "1567427447811739698",  # announcements-and-news (pos 0)
    "1567434275928809544",  # community-info (pos 1)
    "1566600269649678467",  # discord-rules (pos 2)
    "1564605316849733725",  # welcome (pos 3)
    "1566648730210406481",  # auto-roles (pos 4)
    "1570213601430732873",  # staff-intro (pos 5)
    "1570213618757144780",  # member-intro (pos 6)
    "1567730987821957180",  # partnerships (pos 7)
    "1570071721703116864",  # affiliates (pos 8)
]

payload = [
    {"id": cid, "position": idx}
    for idx, cid in enumerate(ORDERED_CHANNEL_IDS)
]

patch_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels"
req = urllib.request.Request(
    patch_url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    },
    method="PATCH",
)

with urllib.request.urlopen(req) as resp:
    print(f"Successfully positioned Community Dashboard channels! status: {resp.status}")
