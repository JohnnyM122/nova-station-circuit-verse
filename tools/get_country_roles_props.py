import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
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

for r in roles:
    if r["name"] in ["United States", "Canada", "United Kingdom", "Australia", "International / Other"]:
        print(f"Role: '{r['name']}', id: {r['id']}, pos: {r['position']}, color: {r['color']}, hoist: {r['hoist']}, mentionable: {r['mentionable']}, perms: {r['permissions']}")
