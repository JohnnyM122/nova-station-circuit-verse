import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
req = urllib.request.Request(
    "https://discord.com/api/v10/guilds/1564605314752585797/channels",
    headers={"Authorization": f"Bot {TOKEN}", "User-Agent": "DiscordBot (CircuitVerse, 1.0)"}
)
with urllib.request.urlopen(req) as resp:
    channels = json.load(resp)

for c in channels:
    if "ticket" in c["name"].lower() or "support" in c["name"].lower():
        print(f"{c['name']} (ID: {c['id']}, Type: {c['type']}, Parent: {c.get('parent_id')})")
