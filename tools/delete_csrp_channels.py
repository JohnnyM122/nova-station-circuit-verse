import urllib.request
import urllib.error
import json
import time

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
GUILD_ID = "1564605314752585797"
HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "User-Agent": "DiscordBot (CircuitVerse, 1.0)",
    "Content-Type": "application/json",
}

def get_channels():
    req = urllib.request.Request(f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels", headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def delete_channel(cid, name):
    url = f"https://discord.com/api/v10/channels/{cid}"
    while True:
        try:
            req = urllib.request.Request(url, headers=HEADERS, method="DELETE")
            with urllib.request.urlopen(req) as resp:
                print(f"[DELETED] #{name} ({cid}) - HTTP {resp.status}")
                return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = float(e.headers.get("Retry-After", 1))
                print(f"[RATE LIMITED] Waiting {retry_after}s...")
                time.sleep(retry_after + 0.1)
                continue
            elif e.code == 404:
                print(f"[NOT FOUND] #{name} ({cid}) already deleted.")
                return True
            else:
                print(f"[ERROR] Failed to delete #{name} ({cid}): {e}")
                return False
        except Exception as e:
            print(f"[EXCEPTION] #{name} ({cid}): {e}")
            return False

def main():
    channels = get_channels()
    csrp_channels = [c for c in channels if "csrp" in c.get("name", "").lower()]
    print(f"Total CSRP channels found: {len(csrp_channels)}")
    
    deleted_count = 0
    for c in csrp_channels:
        cid = c["id"]
        cname = c["name"]
        if delete_channel(cid, cname):
            deleted_count += 1
        time.sleep(0.5)

    print(f"\nFinished: Deleted {deleted_count}/{len(csrp_channels)} channels.")

if __name__ == "__main__":
    main()
