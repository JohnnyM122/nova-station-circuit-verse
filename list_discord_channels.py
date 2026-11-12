import json, urllib.request

with open("c:\\Users\\SysAdmin\\Documents\\nova-station-circuit-verse-main\\cv_panel_config.json") as f:
    cfg = json.load(f)
token = cfg["discord_bot_token"]

req = urllib.request.Request("https://discord.com/api/v10/guilds/1564605314752585797/channels")
req.add_header("Authorization", f"Bot {token}")
req.add_header("User-Agent", "DiscordBot (CircuitVerse, 1.0)")

with urllib.request.urlopen(req) as resp:
    channels = json.load(resp)

print(f"Total channels: {len(channels)}")
for ch in sorted(channels, key=lambda x: (x.get('parent_id') or '', x.get('position', 0))):
    name = ch.get('name')
    cid = ch.get('id')
    ctype = ch.get('type')
    parent = ch.get('parent_id')
    print(f"Type {ctype}: #{name} (ID: {cid}, Parent: {parent})")
