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
        return json.loads(resp.read().decode())

print("1. Powering off server...")
api("POST", f"/servers/{server_id}/actions/poweroff")

for _ in range(30):
    time.sleep(2)
    s = api("GET", f"/servers/{server_id}")["server"]
    print(f"Status: {s['status']}")
    if s["status"] == "off":
        break

print("2. Changing server_type to cx33 (EUR 9.99/mo)...")
try:
    action = api("POST", f"/servers/{server_id}/actions/change_type", {"server_type": "cx33", "upgrade_disk": False})
    print("Change type action initiated:", action["action"]["status"])
except Exception as e:
    print("Change type error:", e)
    if hasattr(e, "read"):
        print(e.read().decode())
    exit(1)

for _ in range(30):
    time.sleep(2)
    s = api("GET", f"/servers/{server_id}")["server"]
    print(f"Server Type: {s['server_type']['name']} | Status: {s['status']}")
    if s["server_type"]["name"] == "cx33":
        break

print("3. Powering on server...")
api("POST", f"/servers/{server_id}/actions/poweron")

for _ in range(30):
    time.sleep(2)
    s = api("GET", f"/servers/{server_id}")["server"]
    print(f"Status: {s['status']}")
    if s["status"] == "running":
        print(f"SUCCESS! Server {server_id} is now running on {s['server_type']['name']} (4 vCPUs, 8 GB RAM, EUR 9.99/mo) with IP {s['public_net']['ipv4']['ip']}!")
        break
