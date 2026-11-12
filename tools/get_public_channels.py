import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"
url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels"
req = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    },
)
with urllib.request.urlopen(req) as resp:
    channels = json.loads(resp.read().decode("utf-8"))

categories = {c["id"]: c["name"] for c in channels if c["type"] == 4}

staff_cats = [
    "Community Staff Area",
    "NS13 Staff",
    "Minecraft Staff",
    "Zomboid Staff",
    "Unturned Staff",
    "CSRP Staff",
    "Staff Tickets",
    "Incident Managment",
    "Restricted",
    "Community Tickets",
]

public_channels = []
for c in channels:
    if c["type"] not in [0, 5]:  # Only standard text (0) or announcement (5) channels
        continue
    parent_name = categories.get(c.get("parent_id"), "ROOT")

    if any(s.lower() in parent_name.lower() for s in staff_cats):
        continue

    cname = c["name"]
    if any(
        s in cname.lower()
        for s in [
            "staff",
            "admin",
            "ticket",
            "logs",
            "audit",
            "status",
            "mentorhelp",
            "adminhelp",
        ]
    ):
        continue

    # Skip the 6 newly created channels since we just seeded them
    if c["id"] in [
        "1570200515000664304",
        "1570200516598829076",
        "1570200518217965748",
        "1570200520520499300",
        "1570200522185506846",
        "1570200523842519100",
    ]:
        continue

    public_channels.append(
        {
            "id": c["id"],
            "name": cname,
            "parent": parent_name,
            "topic": c.get("topic", ""),
        }
    )

print(f"Total public text channels needing pinned description: {len(public_channels)}")
for pc in public_channels:
    print(f"{pc['id']} | [{pc['parent']}] #{pc['name']}")
