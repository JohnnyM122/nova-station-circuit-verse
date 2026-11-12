import urllib.request
import json
import time

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"
PARENT_ID = "1566679559481462864"  # Community Dashboard

EVERYONE_ID = "1564605314752585797"
COMM_STAFF_ID = "1567663377054957830"

# Channel definitions
CHANNELS_TO_CREATE = [
    {
        "name": "🛡️・staff-intro",
        "type": 0,
        "parent_id": PARENT_ID,
        "topic": "Meet the Circuit Verse Staff Team! Learn about our founders, directors, admins, mods, and devs.",
        "permission_overwrites": [
            {
                "id": EVERYONE_ID,
                "type": 0,
                "allow": "66624",    # View Channel (1024) + Read History (65536) + Add Reactions (64)
                "deny": "2048",      # Send Messages (2048)
            },
            {
                "id": COMM_STAFF_ID,
                "type": 0,
                "allow": "117760",   # View (1024) + Send Messages (2048) + Embed Links (16384) + Attach Files (32768) + Read History (65536)
                "deny": "0",
            },
        ],
        "embed": {
            "title": "🛡️ Circuit Verse — Official Staff Team Introductions",
            "description": (
                "Welcome to **#staff-intro**! This channel is dedicated to introducing the Circuit Verse leadership, "
                "administration, moderation, and development teams.\n\n"
                "Browse below to learn more about the staff members who keep our community and game servers safe, fun, and operational!\n\n"
                "### 📋 Staff Introduction Template (For Staff Members):\n"
                "```markdown\n"
                "• Name / Handle:\n"
                "• Staff Rank & Role:\n"
                "• Server Departments (NS13 / MC / PZ / Unturned / Community):\n"
                "• Timezone & Active Hours:\n"
                "• What I Do in Circuit Verse:\n"
                "• Favorite Games & Hobbies:\n"
                "• A Fun Fact About Me:\n"
                "• How to Best Contact Me:\n"
                "```\n"
                "📌 **Notice for Members**: Staff members will post their bios here. Feel free to leave reaction emojis on staff posts to say hello! "
                "For direct support or inquiries, please open a ticket in <#1567435050331537468>."
            ),
            "color": 0x4F46E5,  # Indigo / Staff Royal
            "footer": {
                "text": "Circuit Verse Leadership & Operations • Community Dashboard"
            },
        },
    },
    {
        "name": "👋・member-intro",
        "type": 0,
        "parent_id": PARENT_ID,
        "topic": "Introduce yourself to the Circuit Verse community! Tell us about your gaming interests, hobbies, and style.",
        "permission_overwrites": [
            {
                "id": EVERYONE_ID,
                "type": 0,
                "allow": "68672",    # View (1024) + Send (2048) + Read History (65536) + Add Reactions (64)
                "deny": "0",
            },
        ],
        "embed": {
            "title": "👋 Welcome to Circuit Verse — Member Introductions!",
            "description": (
                "Welcome to **#member-intro**! We are thrilled to have you here in Circuit Verse.\n\n"
                "Take a moment to introduce yourself to your fellow community members using the quick template below or in your own style!\n\n"
                "### 🎉 Member Introduction Template:\n"
                "```markdown\n"
                "• Name / Nickname:\n"
                "• Country / Timezone:\n"
                "• Favorite Games You Play:\n"
                "• Which Circuit Verse Servers You Plan to Play (NS13 / MC / PZ / Unturned / Other):\n"
                "• Hobbies Outside Gaming:\n"
                "• What Brought You Here:\n"
                "• Fun Fact / Quote:\n"
                "```\n"
                "💡 **Tip**: Don't forget to grab your self-assignable roles in <#1566648730210406481> (`#🎭・auto-roles`) "
                "to get server notifications, game roles, and your country flag!"
            ),
            "color": 0x10B981,  # Emerald Green
            "footer": {
                "text": "Circuit Verse Welcome & Community Hub • Community Dashboard"
            },
        },
    },
]

# 1. Fetch existing channels to avoid duplicates
url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels"
req = urllib.request.Request(url, headers={"Authorization": f"Bot {TOKEN}", "User-Agent": "DiscordBot (CircuitVerse, 1.0)"})
with urllib.request.urlopen(req) as resp:
    existing = json.loads(resp.read().decode("utf-8"))

existing_names = {c["name"]: c["id"] for c in existing}

create_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels"

for ch_def in CHANNELS_TO_CREATE:
    cname = ch_def["name"]
    cid = existing_names.get(cname)

    if not cid:
        payload = {
            "name": cname,
            "type": ch_def["type"],
            "parent_id": ch_def["parent_id"],
            "topic": ch_def["topic"],
            "permission_overwrites": ch_def["permission_overwrites"],
        }
        creq = urllib.request.Request(
            create_url,
            data=json.dumps(payload).encode("utf-8"),
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
                cid = created["id"]
                print(f"Created channel '{cname}' -> id: {cid}")
        except Exception as e:
            print(f"Error creating '{cname}': {e}")
            continue
        time.sleep(1.0)
    else:
        print(f"Channel '{cname}' already exists -> id: {cid}")

    # Post embed
    post_url = f"https://discord.com/api/v10/channels/{cid}/messages"
    msg_payload = {"embeds": [ch_def["embed"]]}
    mreq = urllib.request.Request(
        post_url,
        data=json.dumps(msg_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(mreq) as resp:
            msg = json.loads(resp.read().decode("utf-8"))
            mid = msg["id"]
            print(f"Posted intro embed to '{cname}' -> msg {mid}")

            # Pin message
            time.sleep(0.5)
            pin_url = f"https://discord.com/api/v10/channels/{cid}/pins/{mid}"
            preq = urllib.request.Request(
                pin_url,
                headers={"Authorization": f"Bot {TOKEN}", "User-Agent": "DiscordBot (CircuitVerse, 1.0)"},
                method="PUT",
            )
            with urllib.request.urlopen(preq) as presp:
                print(f"Pinned message {mid} in '{cname}': status {presp.status}")
    except Exception as e:
        print(f"Error posting/pinning in '{cname}': {e}")

    time.sleep(1.0)

print("\nDone creating, posting, and pinning intro channels!")
