import urllib.request
import json
import time

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
GUILD_ID = "1564605314752585797"

# Desired order from top to bottom:
DESIRED_ORDER = [
    "United States",
    "Canada",
    "United Kingdom",
    "Australia",
    "New Zealand",
    "Germany",
    "France",
    "Netherlands",
    "Nordics / Scandinavia",
    "Europe (Other)",
    "Latin America",
    "Asia / Pacific",
    "International / Other",
]

# 1. Fetch current roles
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

roles_by_name = {r["name"]: r for r in roles}

# Find reference boundaries:
# 'Web Admin' was above 'United States'
# 'CV-Radio-Helper' was below 'International / Other'
web_admin = roles_by_name.get("Web Admin")
radio_helper = roles_by_name.get("CV-Radio-Helper")

print(f"Web Admin pos: {web_admin['position'] if web_admin else 'None'}")
print(f"CV-Radio-Helper pos: {radio_helper['position'] if radio_helper else 'None'}")

for name in DESIRED_ORDER:
    r = roles_by_name.get(name)
    if r:
        print(f"  {r['name']} ({r['id']}) pos: {r['position']}")
