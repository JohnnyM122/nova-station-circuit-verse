import urllib.request
import json

import os
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ZONE_ID = "4eebb417a420327c172f337afd14b988"
DED_IP = "62.238.81.224"
TUNNEL_CNAME = "7d957cd1-b462-458c-a073-20aed739b74d.cfargotunnel.com"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Fetch existing DNS records
req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records", headers=headers)
with urllib.request.urlopen(req) as resp:
    records = json.load(resp)["result"]

rec_by_name = {r["name"]: r for r in records}

# Updates to make:
# Game subdomains: A record -> DED_IP (proxied: False, because raw UDP/TCP game traffic cannot go through free Cloudflare HTTP proxy)
# Web panels: CNAME -> TUNNEL_CNAME (proxied: True, for full Cloudflare SSL and WAF proxy)

targets = {
    "game.circuitverse.online": {"type": "A", "content": DED_IP, "proxied": False},
    "mc.circuitverse.online": {"type": "A", "content": DED_IP, "proxied": False},
    "play.circuitverse.online": {"type": "A", "content": DED_IP, "proxied": False},
    "pz.circuitverse.online": {"type": "A", "content": DED_IP, "proxied": False},
    "unturned.circuitverse.online": {"type": "A", "content": DED_IP, "proxied": False},
    "general.circuitverse.online": {"type": "A", "content": DED_IP, "proxied": False},
    "panel.circuitverse.online": {"type": "CNAME", "content": TUNNEL_CNAME, "proxied": True},
    "zcp.circuitverse.online": {"type": "CNAME", "content": TUNNEL_CNAME, "proxied": True},
}

for name, spec in targets.items():
    if name in rec_by_name:
        rec = rec_by_name[name]
        rid = rec["id"]
        # Update existing record
        url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{rid}"
        data = {
            "type": spec["type"],
            "name": name,
            "content": spec["content"],
            "proxied": spec["proxied"],
            "ttl": 1 # auto
        }
        # If type changed from A to CNAME, delete and recreate or PUT
        req_put = urllib.request.Request(url, method="PUT", data=json.dumps(data).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req_put) as resp_put:
                res = json.load(resp_put)
                print(f"Updated {name} -> {spec['type']} {spec['content']} (proxied: {spec['proxied']}): success={res.get('success')}")
        except Exception as e:
            print(f"Error updating {name}: {e}")
            # Try DELETE and POST if type conflict
            try:
                req_del = urllib.request.Request(url, method="DELETE", headers=headers)
                urllib.request.urlopen(req_del)
                req_post = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records", method="POST", data=json.dumps(data).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req_post) as resp_post:
                    res = json.load(resp_post)
                    print(f"Recreated {name} -> {spec['type']} {spec['content']} (proxied: {spec['proxied']}): success={res.get('success')}")
            except Exception as e2:
                print(f"Fallback error for {name}: {e2}")
    else:
        # Create record
        data = {
            "type": spec["type"],
            "name": name,
            "content": spec["content"],
            "proxied": spec["proxied"],
            "ttl": 1
        }
        req_post = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records", method="POST", data=json.dumps(data).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req_post) as resp_post:
                res = json.load(resp_post)
                print(f"Created {name} -> {spec['type']} {spec['content']}: success={res.get('success')}")
        except Exception as e:
            print(f"Error creating {name}: {e}")
