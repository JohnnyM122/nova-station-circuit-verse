import urllib.request
import json

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

WELCOME_MESSAGES = [
    {
        "channel_id": "1570200515000664304",  # memes-and-media
        "embed": {
            "title": "😂 Welcome to #memes-and-media!",
            "description": "The official spot to drop your favorite memes, hilarious clips, gaming highlights, and lighthearted content.\n\nKeep it fun, respectful, and adhere to our community guidelines!",
            "color": 0x38BDF8,
            "footer": {"text": "Circuit Verse Community • Community General"},
        },
    },
    {
        "channel_id": "1570200516598829076",  # tech-and-ai
        "embed": {
            "title": "🤖 Welcome to #tech-and-ai!",
            "description": "Discuss the latest in hardware, PC builds, software development, scripting, Linux, self-hosting, and artificial intelligence innovations.\n\nFeel free to ask for tech support or showcase your latest setup!",
            "color": 0x6366F1,
            "footer": {"text": "Circuit Verse Community • Community General"},
        },
    },
    {
        "channel_id": "1570200518217965748",  # community-ideas
        "embed": {
            "title": "💡 Welcome to #community-ideas!",
            "description": "Have an idea or suggestion for Circuit Verse? Share your thoughts on events, server features, Discord improvements, and game expansions.\n\nCommunity input shapes everything we build!",
            "color": 0xFBBF24,
            "footer": {"text": "Circuit Verse Community • Community General"},
        },
    },
    {
        "channel_id": "1570200520520499300",  # survival-and-crafting
        "embed": {
            "title": "🧟 Welcome to #survival-and-crafting!",
            "description": "Dedicated to survival, open-world crafting, and base-building titles including Rust, Ark, Terraria, Valheim, DayZ, Sons of the Forest, and more.\n\nFind co-op buddies, share your bases, and discuss survival strategies!",
            "color": 0x10B981,
            "footer": {"text": "Circuit Verse Community • Community Gaming"},
        },
    },
    {
        "channel_id": "1570200522185506846",  # indie-and-retro
        "embed": {
            "title": "🕹️ Welcome to #indie-and-retro!",
            "description": "Celebrate indie masterpieces, roguelikes, vintage console classics, pixel art, and passion projects.\n\nShare hidden gems you're playing and retro nostalgia favorites!",
            "color": 0xEC4899,
            "footer": {"text": "Circuit Verse Community • Community Gaming"},
        },
    },
    {
        "channel_id": "1570200523842519100",  # game-deals-and-freebies
        "embed": {
            "title": "🎁 Welcome to #game-deals-and-freebies!",
            "description": "Never miss a great gaming deal! Post Steam sales, weekly Epic Games free releases, Humble Bundle alerts, GOG deals, and console discounts here.",
            "color": 0xA855F7,
            "footer": {"text": "Circuit Verse Community • Community Gaming"},
        },
    },
]

for item in WELCOME_MESSAGES:
    cid = item["channel_id"]
    payload = {"embeds": [item["embed"]]}
    data = json.dumps(payload).encode("utf-8")
    url = f"https://discord.com/api/v10/channels/{cid}/messages"
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Posted welcome embed to {cid}: status {resp.status}")
    except Exception as e:
        print(f"Failed to post to {cid}: {e}")
