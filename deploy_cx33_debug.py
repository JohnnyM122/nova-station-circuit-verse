import urllib.request
import json

token = "yUFP5O7QAVWuH242p3GODbr4OlXDPj0GbGfSWGxIqgsxsiFBk38bVgcaLX4NDC3W"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payload = {
    "name": "circuit-verse-unturned-prod",
    "server_type": "cx33",
    "image": "ubuntu-22.04",
    "location": "fsn1",
    "ssh_keys": [132337475],
    "start_after_create": True
}

req = urllib.request.Request("https://api.hetzner.cloud/v1/servers", data=json.dumps(payload).encode(), headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    print("Error:", e.code, e.read().decode())
