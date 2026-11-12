import urllib.request
import json
import time

token = "yUFP5O7QAVWuH242p3GODbr4OlXDPj0GbGfSWGxIqgsxsiFBk38bVgcaLX4NDC3W"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
server_id = 175065653

def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"https://api.hetzner.cloud/v1{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        return json.loads(content) if content else {}

print(f"1. Deleting expensive cpx32 server ({server_id})...")
try:
    api("DELETE", f"/servers/{server_id}")
    print("Delete requested successfully.")
except Exception as e:
    print("Delete error:", e)

# Wait 5 seconds for core limits to clear
time.sleep(5)

print("2. Deploying cx33 server (4 vCPUs, 8 GB RAM, 80 GB NVMe, EUR 9.99/mo)...")
payload = {
    "name": "circuit-verse-unturned",
    "server_type": "cx33",
    "image": "ubuntu-22.04",
    "location": "fsn1",
    "ssh_keys": [132337475],
    "start_after_create": True
}

for attempt in range(5):
    try:
        res = api("POST", "/servers", payload)
        srv = res["server"]
        ip = srv["public_net"]["ipv4"]["ip"]
        print(f"DEPLOYED CX33 SUCCESS! ID={srv['id']} Name={srv['name']} IP={ip} Type={srv['server_type']['name']} Status={srv['status']}")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(4)
