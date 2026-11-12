import urllib.request
import json

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
req = urllib.request.Request(
    "https://discord.com/api/v10/channels/1566986370910654517/messages?limit=10",
    headers={"Authorization": f"Bot {TOKEN}", "User-Agent": "DiscordBot (CircuitVerse, 1.0)"}
)
try:
    with urllib.request.urlopen(req) as resp:
        msgs = json.loads(resp.read().decode())
        for m in msgs:
            author = m.get("author", {}).get("username")
            ts = m.get("timestamp")
            content = m.get("content")
            print(f"{ts} | {author}: {content}")
            for e in m.get("embeds", []):
                print(f"   Embed: {e.get('title')} | {e.get('description')}")
except Exception as e:
    print("Error:", e)
