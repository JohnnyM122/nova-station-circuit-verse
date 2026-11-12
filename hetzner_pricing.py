import urllib.request
import json

token = "kTMcuBEYA0T2sQrxxkfglRbcDthMF6tvghmAKKNUFehpjYOsEjygk4TnroXxKhwo"
headers = {"Authorization": f"Bearer {token}"}

# 1. Servers
req = urllib.request.Request("https://api.hetzner.cloud/v1/servers", headers=headers)
with urllib.request.urlopen(req) as resp:
    servers = json.loads(resp.read().decode())["servers"]

print("=== CURRENT SERVERS ===")
for s in servers:
    st = s["server_type"]
    ip = s["public_net"]["ipv4"]["ip"]
    print(f"ID: {s['id']} | Name: {s['name']} | Type: {st['name']} ({st['cores']} vCPU, {st['memory']} GB RAM) | IP: {ip} | Status: {s['status']}")

# 2. Server Types & Pricing
req2 = urllib.request.Request("https://api.hetzner.cloud/v1/server_types", headers=headers)
with urllib.request.urlopen(req2) as resp:
    stypes = json.loads(resp.read().decode())["server_types"]

print("\n=== SERVER TYPES & PRICING (EUR / mo) ===")
for t in stypes:
    prices = t.get("prices", [])
    # fsn1 price or default
    p_eur = None
    for p in prices:
        if p.get("location") == "fsn1":
            p_eur = p.get("price_monthly", {}).get("gross")
            break
    if not p_eur and prices:
        p_eur = prices[0].get("price_monthly", {}).get("gross")
    print(f"{t['name']:<10} | {t['cores']} vCPUs | {t['memory']:>2} GB RAM | {t['disk']:>3} GB NVMe | Type: {t['cpu_type']:<6} | EUR/mo: {p_eur}")
