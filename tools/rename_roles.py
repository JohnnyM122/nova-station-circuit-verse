import urllib.request
import json

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
GUILD_ID = "1564605314752585797"

ROLE_UPDATES = {
    "1567475024892272741": "Community Senior Admin",
    "1567474474243072070": "Community Admin",
    "1567653677324304575": "Community Jr.Admin",
    "1567653679820054539": "Community Head Mod",
    "1567653682537828484": "Community Senior Mod",
    "1567653685620768990": "Community Mod",
    "1567653688628084787": "Community Jr.Mod",
}

for role_id, new_name in ROLE_UPDATES.items():
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles/{role_id}"
    data = json.dumps({"name": new_name}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"SUCCESS: Role {role_id} renamed to '{res['name']}'")
    except Exception as e:
        print(f"FAILED for role {role_id} ({new_name}): {e}")
