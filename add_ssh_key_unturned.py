import urllib.request
import json

token = "yUFP5O7QAVWuH242p3GODbr4OlXDPj0GbGfSWGxIqgsxsiFBk38bVgcaLX4NDC3W"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payload = {
    "name": "nova-admin-desktop",
    "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHYRrA+gqjhuz4DAPiirnb3vMeWti9gVsGZX496Og4oG codex-tailscale-desktop"
}
req = urllib.request.Request("https://api.hetzner.cloud/v1/ssh_keys", data=json.dumps(payload).encode(), headers=headers, method="POST")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print("Added SSH key ID:", res["ssh_key"]["id"])
