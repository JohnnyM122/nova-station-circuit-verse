import urllib.request
import json
import time

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
GUILD_ID = "1564605314752585797"

# New country roles to add
NEW_COUNTRY_ROLES = [
    {"name": "New Zealand", "color": 1089901, "emoji": "🇳🇿"},
    {"name": "Germany", "color": 15582234, "emoji": "🇩🇪"},
    {"name": "France", "color": 3447003, "emoji": "🇫🇷"},
    {"name": "Netherlands", "color": 16744448, "emoji": "🇳🇱"},
    {"name": "Nordics / Scandinavia", "color": 3385790, "emoji": "🇸🇪"},
    {"name": "Europe (Other)", "color": 2123412, "emoji": "🇪🇺"},
    {"name": "Latin America", "color": 3066993, "emoji": "🌎"},
    {"name": "Asia / Pacific", "color": 15105570, "emoji": "🌏"},
]

EXISTING_COUNTRY_ROLES = [
    {"name": "United States", "id": "1568627267783888997", "emoji": "🇺🇸"},
    {"name": "Canada", "id": "1568627268765360241", "emoji": "🇨🇦"},
    {"name": "United Kingdom", "id": "1568627270199812258", "emoji": "🇬🇧"},
    {"name": "Australia", "id": "1568627272913522849", "emoji": "🇦🇺"},
    {"name": "International / Other", "id": "1568627273999851570", "emoji": "🌐"},
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

existing_by_name = {r["name"]: r for r in roles}

created_roles = {}
create_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles"

for cr in NEW_COUNTRY_ROLES:
    name = cr["name"]
    if name in existing_by_name:
        print(f"Role '{name}' already exists (id: {existing_by_name[name]['id']})")
        created_roles[name] = existing_by_name[name]["id"]
        continue

    payload = {
        "name": name,
        "color": cr["color"],
        "hoist": False,
        "mentionable": False,
        "permissions": "673972814728768",
    }
    data = json.dumps(payload).encode("utf-8")
    creq = urllib.request.Request(
        create_url,
        data=data,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(creq) as resp:
            new_r = json.loads(resp.read().decode("utf-8"))
            print(f"Created role '{name}' -> id: {new_r['id']}")
            created_roles[name] = new_r["id"]
    except Exception as e:
        print(f"Error creating role '{name}': {e}")
    time.sleep(0.5)

print("\nAll new country roles ensured.")
