import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"

# Desired list of roles in order from TOP to BOTTOM:
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

# 1. Fetch all current roles
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

roles.sort(key=lambda x: x["position"])

# Build current order excluding the country roles
country_names = set(DESIRED_ORDER)
non_country_roles = [r for r in roles if r["name"] not in country_names]
country_roles_map = {r["name"]: r for r in roles if r["name"] in country_names}

# Find the insertion point: below 'Web Admin' (or right above 'CV-Radio-Helper')
insert_idx = 0
for i, r in enumerate(non_country_roles):
    if r["name"] == "CV-Radio-Helper":
        insert_idx = i + 1
        break

print(f"Inserting country roles at index {insert_idx} (above {non_country_roles[insert_idx-1]['name']})")

# In non_country_roles (sorted by position ascending, 0 is @everyone):
# The order from bottom to top should be:
# non_country_roles[:insert_idx]
# DESIRED_ORDER reversed (so top item has highest position)
# non_country_roles[insert_idx:]

new_order = []
new_order.extend(non_country_roles[:insert_idx])
# Add country roles in ascending position order (bottom to top = reversed DESIRED_ORDER)
for name in reversed(DESIRED_ORDER):
    new_order.append(country_roles_map[name])
new_order.extend(non_country_roles[insert_idx:])

# Now compute position payload
payload = []
for pos, r in enumerate(new_order):
    if r["name"] in country_names:
        payload.append({"id": r["id"], "position": pos})

print(f"Generated position payload for {len(payload)} roles:")
for p in payload:
    # find role name
    rname = next(r["name"] for r in roles if r["id"] == p["id"])
    print(f"  {rname} -> pos {p['position']}")

# Send PATCH
patch_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles"
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

try:
    with urllib.request.urlopen(req) as resp:
        updated_roles = json.loads(resp.read().decode("utf-8"))
        print(f"Successfully reordered roles! Total roles: {len(updated_roles)}")
except Exception as e:
    print(f"Error reordering roles: {e}")
