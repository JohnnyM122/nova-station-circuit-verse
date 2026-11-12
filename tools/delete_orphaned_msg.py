import urllib.request

TOKEN = "os.environ.get("API_SECRET_TOKEN", "REDACTED")"
cid = "1568805619522343095"
mid = "1570197021900415071"

url = f"https://discord.com/api/v10/channels/{cid}/messages/{mid}"
req = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    },
    method="DELETE",
)
try:
    with urllib.request.urlopen(req) as resp:
        print(f"Deleted orphaned offline message {mid}: status {resp.status}")
except Exception as e:
    print(f"Error: {e}")
