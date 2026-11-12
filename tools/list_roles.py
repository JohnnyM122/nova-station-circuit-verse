import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"
url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bot {TOKEN}",
    "User-Agent": "DiscordBot (CircuitVerse, 1.0)"
})

try:
    with urllib.request.urlopen(req) as resp:
        roles = json.loads(resp.read().decode("utf-8"))
        print(f"Total roles in guild: {len(roles)}")
        # Sort by position descending
        roles.sort(key=lambda x: x["position"], reverse=True)
        for r in roles:
            name = r["name"]
            rid = r["id"]
            pos = r["position"]
            print(f"{rid} | pos {pos:3d} | '{name}'")
except Exception as e:
    print("Error:", e)
