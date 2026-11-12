import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
cid = "1566648730210406481"
mid = "1566649022591139892"
url = f"https://discord.com/api/v10/channels/{cid}/messages/{mid}"
req = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    },
)
with urllib.request.urlopen(req) as resp:
    msg = json.loads(resp.read().decode("utf-8"))

print("Embed:")
print(json.dumps(msg["embeds"], indent=2))
print("Components:")
print(json.dumps(msg["components"], indent=2))
