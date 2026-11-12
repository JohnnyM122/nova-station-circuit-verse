import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"

CAT_GENERAL = "1564605316849733723"
CAT_GAMING = "1570017434260217917"

NEW_CHANNELS = [
    # Community General channels
    {
        "name": "😂・memes-and-media",
        "type": 0,
        "parent_id": CAT_GENERAL,
        "topic": "Share funny memes, viral clips, humor, and community entertainment!",
    },
    {
        "name": "🤖・tech-and-ai",
        "type": 0,
        "parent_id": CAT_GENERAL,
        "topic": "Discussions on software, PC hardware, programming, gadgets, and AI tech.",
    },
    {
        "name": "💡・community-ideas",
        "type": 0,
        "parent_id": CAT_GENERAL,
        "topic": "Share feedback, ideas, suggestions, and feature requests for Circuit Verse.",
    },
    # Community Gaming channels
    {
        "name": "🧟・survival-and-crafting",
        "type": 0,
        "parent_id": CAT_GAMING,
        "topic": "Discussion and co-op for survival, crafting, and sandbox titles (Rust, Terraria, Valheim, DayZ, Ark, etc.).",
    },
    {
        "name": "🕹️・indie-and-retro",
        "type": 0,
        "parent_id": CAT_GAMING,
        "topic": "Indie gems, retro classics, roguelikes, emulation, and passion projects.",
    },
    {
        "name": "🎁・game-deals-and-freebies",
        "type": 0,
        "parent_id": CAT_GAMING,
        "topic": "Share Steam sales, Epic Games weekly freebies, Humble Bundles, and game discounts.",
    },
]

# 1. Fetch existing channels
url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels"
req = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    },
)
with urllib.request.urlopen(req) as resp:
    existing = json.loads(resp.read().decode("utf-8"))

existing_names = {c["name"]: c["id"] for c in existing}

# 2. Create new channels if not existing
create_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels"
for ch in NEW_CHANNELS:
    if ch["name"] in existing_names:
        print(f"EXISTS: Channel '{ch['name']}' already exists (id: {existing_names[ch['name']]})")
        continue

    data = json.dumps(ch).encode("utf-8")
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
            created = json.loads(resp.read().decode("utf-8"))
            print(f"CREATED: '{created['name']}' (id: {created['id']}) in parent {ch['parent_id']}")
    except Exception as e:
        print(f"FAILED to create '{ch['name']}': {e}")
