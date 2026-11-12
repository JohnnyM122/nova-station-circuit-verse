import urllib.request
import json
import time

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"

# Category color codes
COL_GENERAL = 0x38BDF8  # Light Blue / Cyan
COL_GAMING = 0x8B5CF6   # Purple
COL_SS13 = 0x06B6D4     # Teal
COL_MC = 0x10B981       # Emerald Green
COL_PZ = 0xEF4444       # Red / Blood
COL_UNTURNED = 0x15803D # Forest Green
COL_RADIO = 0xF59E0B    # Amber

DESCRIPTIONS = [
    # --- Community General ---
    {
        "channel_id": "1566635359641669652",
        "name": "general-chat",
        "embed": {
            "title": "💬 Welcome to #general-chat!",
            "description": "The central gathering hub for Circuit Verse members! Talk about your day, catch up with friends, discuss anything under the sun, and hang out.\n\n• Be friendly and welcoming to newcomers\n• Adhere to community guidelines in <#1566600269649678467>\n• Keep all conversations PG-13 and safe for work.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1567013381104345152",
        "name": "ask-circuit-verse",
        "embed": {
            "title": "❓ Welcome to #ask-circuit-verse!",
            "description": "Got questions about the community, server connection info, roles, or events? Ask here!\n\nBoth staff and veteran members are always happy to help you get started.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1570021758826709054",
        "name": "hobbies-and-interests",
        "embed": {
            "title": "🎨 Welcome to #hobbies-and-interests!",
            "description": "Share your passions outside of gaming! Artwork, photography, cooking, 3D printing, fitness, writing, instruments, model kits, and crafts.\n\nWe love seeing what our members build and create.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1570021763109097532",
        "name": "irl-pictures",
        "embed": {
            "title": "📷 Welcome to #irl-pictures!",
            "description": "Share real-life snapshots, travel pictures, pets, scenery, food, and daily life.\n\n• Please do not post sensitive personal data (addresses, school/work badges, IDs)\n• Always respect everyone's privacy and comfort.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1570021768322752644",
        "name": "battlestations-rigs",
        "embed": {
            "title": "🖥️ Welcome to #battlestations-rigs!",
            "description": "Show off your desk setup, PC builds, keyboard collections, monitors, cable management, and gaming battlestations!\n\nFeel free to ask for part recommendations and setup critiques.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1570021772416253962",
        "name": "movies-tv-anime",
        "embed": {
            "title": "🍿 Welcome to #movies-tv-anime!",
            "description": "Discuss blockbusters, series, anime, cartoons, and cinematic classics!\n\n• Please use `||spoiler tags||` for newly released episodes and movies\n• Share recommendations and watchlist reviews.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1570021776002388008",
        "name": "music-lounge",
        "embed": {
            "title": "🎵 Welcome to #music-lounge!",
            "description": "Share what you're currently listening to! Post Spotify playlists, favorite tracks, YouTube music videos, artist discoveries, and genre discussions.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },
    {
        "channel_id": "1570124053698576575",
        "name": "community-partnerships-chat",
        "embed": {
            "title": "🤝 Welcome to #community-partnerships-chat!",
            "description": "Collaboration lounge for verified community partners, affiliates, and representatives to connect, organize joint events, and coordinate cross-community projects.",
            "color": COL_GENERAL,
            "footer": {"text": "Circuit Verse • Community General Hub"},
        },
    },

    # --- Community Gaming ---
    {
        "channel_id": "1570017440522575922",
        "name": "gaming-lounge",
        "embed": {
            "title": "🎮 Welcome to #gaming-lounge!",
            "description": "The general gaming parlor! Chat about new releases, gaming news, patches, favorite franchises, and what you're playing today.",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570017444444250163",
        "name": "looking-for-group",
        "embed": {
            "title": "👥 Welcome to #looking-for-group!",
            "description": "Looking for teammates, co-op partners, or a full squad? Post your game, platform/region, and how many players you need!\n\nJump into the Voice Channels (<#1564605316849733724>) once you assemble your group.",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570017448227246153",
        "name": "clips-and-screenshots",
        "embed": {
            "title": "📸 Welcome to #clips-and-screenshots!",
            "description": "Post your epic plays, clutch moments, hilarious glitches, cinematic screenshots, and victory clips across any game!",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570021779957747783",
        "name": "fps-and-shooters",
        "embed": {
            "title": "🎯 Welcome to #fps-and-shooters!",
            "description": "Dedicated to first-person and tactical shooters (Valorant, CS2, Rainbow Six Siege, Apex Legends, Overwatch, Call of Duty, Battlefield, Team Fortress 2, etc.).",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570021784286265396",
        "name": "strategy-and-rts",
        "embed": {
            "title": "⚔️ Welcome to #strategy-and-rts!",
            "description": "For grand strategy, RTS, 4X, and turn-based commanders (Civ, Hearts of Iron, Crusader Kings, Stellaris, Total War, Age of Empires, StarCraft, XCOM, etc.).",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570021789164380200",
        "name": "rpg-and-mmo",
        "embed": {
            "title": "🏹 Welcome to #rpg-and-mmo!",
            "description": "For roleplayers and questers (World of Warcraft, Final Fantasy XIV, OSRS/RuneScape, Elden Ring, Baldur's Gate 3, Monster Hunter, Skyrim, Destiny 2, etc.).",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570021792922472548",
        "name": "sim-and-racing",
        "embed": {
            "title": "🏎️ Welcome to #sim-and-racing!",
            "description": "For simulation and racing enthusiasts (Forza, Assetto Corsa, F1, iRacing, Gran Turismo, MS Flight Sim, Euro Truck Simulator, BeamNG.drive, etc.).",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },
    {
        "channel_id": "1570021796462203024",
        "name": "action-and-fighting",
        "embed": {
            "title": "🥊 Welcome to #action-and-fighting!",
            "description": "For fighting games and high-octane action titles (Street Fighter, Tekken, Guilty Gear, Smash Bros, Mortal Kombat, Devil May Cry, Sekiro, etc.).",
            "color": COL_GAMING,
            "footer": {"text": "Circuit Verse • Community Gaming Lounge"},
        },
    },

    # --- Game Server Public Channels ---
    {
        "channel_id": "1566678879882711152",
        "name": "ns13-ooc-chat",
        "embed": {
            "title": "🚀 Welcome to #ns13-ooc-chat!",
            "description": "Out-of-Character discussion for Nova Station 13 crew members!\n\n• Debrief after rounds, discuss station events, and ask mechanics questions\n• No meta-communication (do not reveal antagonists or round secrets while a shift is live)!\n• Join server via `game.circuitverse.online:7777`",
            "color": COL_SS13,
            "footer": {"text": "Circuit Verse • Nova Station 13"},
        },
    },
    {
        "channel_id": "1567426752697860216",
        "name": "mc-general-chat",
        "embed": {
            "title": "⛏️ Welcome to #mc-general-chat!",
            "description": "General chat for Circuit Verse Minecraft players! Talk about survival projects, coordinate town builds, trade items, and team up in-game.\n\n• Connect Address: `play.circuitverse.online` (Port 25565)\n• Proximity Voice: Press `[V]` in-game",
            "color": COL_MC,
            "footer": {"text": "Circuit Verse • Minecraft Server"},
        },
    },
    {
        "channel_id": "1567507620099530752",
        "name": "mc-suggestions",
        "embed": {
            "title": "💡 Welcome to #mc-suggestions!",
            "description": "Have ideas for the Minecraft server? Suggest new plugins, datapacks, gameplay balances, shop items, spawn features, or event ideas here!",
            "color": COL_MC,
            "footer": {"text": "Circuit Verse • Minecraft Server"},
        },
    },
    {
        "channel_id": "1567507814270767115",
        "name": "mc-media",
        "embed": {
            "title": "🖼️ Welcome to #mc-media!",
            "description": "Show off your Minecraft builds, redstone contraptions, shader screenshots, survival bases, and memorable moments!",
            "color": COL_MC,
            "footer": {"text": "Circuit Verse • Minecraft Server"},
        },
    },
    {
        "channel_id": "1567507926669594654",
        "name": "mc-events",
        "embed": {
            "title": "🎉 Welcome to #mc-events!",
            "description": "Announcements, sign-ups, and discussions for community Minecraft events, building contests, tournaments, and seasonal specials!",
            "color": COL_MC,
            "footer": {"text": "Circuit Verse • Minecraft Server"},
        },
    },
    {
        "channel_id": "1567702354638274640",
        "name": "pz-general-chat",
        "embed": {
            "title": "🧟 Welcome to #pz-general-chat!",
            "description": "General survivor chat for Circuit Verse Project Zomboid (Build 42)!\n\nDiscuss safehouses, coordinate supply runs, trade loot, and plan horde defenses.\n• Connect Address: `pz.circuitverse.online` (Port 16261 UDP)",
            "color": COL_PZ,
            "footer": {"text": "Circuit Verse • Project Zomboid"},
        },
    },
    {
        "channel_id": "1567702359050817656",
        "name": "pz-suggestions",
        "embed": {
            "title": "💡 Welcome to #pz-suggestions!",
            "description": "Suggest server settings, mod additions, spawn changes, or sandbox tweaks for our Project Zomboid survival world!",
            "color": COL_PZ,
            "footer": {"text": "Circuit Verse • Project Zomboid"},
        },
    },
    {
        "channel_id": "1567702365275164692",
        "name": "pz-media",
        "embed": {
            "title": "🖼️ Welcome to #pz-media!",
            "description": "Post screenshots of your Project Zomboid safehouses, vehicle fleets, survivor outfits, and close-call zombie encounters!",
            "color": COL_PZ,
            "footer": {"text": "Circuit Verse • Project Zomboid"},
        },
    },
    {
        "channel_id": "1567702362456465428",
        "name": "pz-events",
        "embed": {
            "title": "🎉 Welcome to #pz-events!",
            "description": "Discussion and scheduling for server-wide helicopter events, mega-horde incursions, community clearing expeditions, and extraction challenges.",
            "color": COL_PZ,
            "footer": {"text": "Circuit Verse • Project Zomboid"},
        },
    },
    {
        "channel_id": "1568805623108476948",
        "name": "unturned-chat",
        "embed": {
            "title": "🌲 Welcome to #unturned-chat!",
            "description": "Survivor chat for Circuit Verse Unturned Dedicated!\n\nCoordinate base construction, discuss map loot hotspots, trade weapons/kits, and team up.\n• Connect: `unturned.circuitverse.online` (Port 27015 UDP)",
            "color": COL_UNTURNED,
            "footer": {"text": "Circuit Verse • Unturned Dedicated"},
        },
    },
    {
        "channel_id": "1567345945077616782",
        "name": "radio-chat",
        "embed": {
            "title": "🎵 Welcome to #radio-chat!",
            "description": "Live listener chat for Circuit Verse Radio!\n\nReact to the current track, chat with fellow listeners, and discuss music requests.\n• Web Player: https://radio.circuitverse.online",
            "color": COL_RADIO,
            "footer": {"text": "Circuit Verse • 24/7 Community Radio"},
        },
    },
]

# Newly created channels from previous turn that need pinning:
NEW_PINS = [
    "1570200515000664304",
    "1570200516598829076",
    "1570200518217965748",
    "1570200520520499300",
    "1570200522185506846",
    "1570200523842519100",
]

def pin_message(cid, mid):
    pin_url = f"https://discord.com/api/v10/channels/{cid}/pins/{mid}"
    req = urllib.request.Request(
        pin_url,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status

print("1. Pinning messages in the 6 newly created channels...")
for cid in NEW_PINS:
    try:
        url = f"https://discord.com/api/v10/channels/{cid}/messages?limit=2"
        req = urllib.request.Request(url, headers={"Authorization": f"Bot {TOKEN}", "User-Agent": "DiscordBot (CircuitVerse, 1.0)"})
        with urllib.request.urlopen(req) as resp:
            msgs = json.loads(resp.read().decode("utf-8"))
            if msgs:
                st = pin_message(cid, msgs[0]["id"])
                print(f"Pinned message in {cid}: {st}")
    except Exception as e:
        print(f"Error pinning in {cid}: {e}")
    time.sleep(0.8)

print("\n2. Posting and pinning descriptions in all public community & game channels...")
for item in DESCRIPTIONS:
    cid = item["channel_id"]
    name = item["name"]
    payload = {"embeds": [item["embed"]]}
    data = json.dumps(payload).encode("utf-8")
    post_url = f"https://discord.com/api/v10/channels/{cid}/messages"
    req = urllib.request.Request(
        post_url,
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
            msg = json.loads(resp.read().decode("utf-8"))
            mid = msg["id"]
            print(f"Posted to #{name} ({cid}) -> msg {mid}")
            time.sleep(0.5)
            pin_st = pin_message(cid, mid)
            print(f"Pinned in #{name} -> status {pin_st}")
    except Exception as e:
        print(f"FAILED for #{name} ({cid}): {e}")
    time.sleep(0.8)

print("\nAll channel descriptions posted and pinned successfully!")
