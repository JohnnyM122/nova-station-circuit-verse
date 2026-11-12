import urllib.request
import json

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
GUILD_ID = "1564605314752585797"

url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles"
req = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    },
)
with urllib.request.urlopen(req) as resp:
    roles = json.loads(resp.read().decode("utf-8"))

roles.sort(key=lambda x: x["position"], reverse=True)
for r in roles:
    if 0 <= r["position"] <= 35:
        print(f"pos {r['position']:3d} | id {r['id']} | '{r['name']}'")
