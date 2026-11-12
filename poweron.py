import urllib.request
import json

token = "yUFP5O7QAVWuH242p3GODbr4OlXDPj0GbGfSWGxIqgsxsiFBk38bVgcaLX4NDC3W"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
server_id = 175065653

req = urllib.request.Request(f"https://api.hetzner.cloud/v1/servers/{server_id}/actions/poweron", headers=headers, method="POST")
with urllib.request.urlopen(req) as resp:
    print("Powering server back on:", resp.status)
