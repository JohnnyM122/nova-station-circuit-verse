import urllib.request

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "User-Agent": "DiscordBot (CircuitVerse, 1.0)"
}

to_delete = [
    ("1567702337961594883", "1568821092238491710"),
    ("1567702337961594883", "1568820819772178612"),
    ("1567702337961594883", "1567704327206736013"),
    ("1568805619522343095", "1568828760248160367"),
    ("1567516535159787700", "1567530336953442386"),
]

for ch_id, msg_id in to_delete:
    url = f"https://discord.com/api/v10/channels/{ch_id}/messages/{msg_id}"
    req = urllib.request.Request(url, headers=HEADERS, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Deleted message {msg_id} in channel {ch_id}: status {resp.status}")
    except Exception as e:
        print(f"Failed to delete {msg_id} in {ch_id}: {e}")
