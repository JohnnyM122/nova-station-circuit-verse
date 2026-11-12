import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

check_script = """
import urllib.request, subprocess

stream_url = "http://127.0.0.1/listen/circuit_verse_radio/radio.mp3"
print(f"Testing stream URL: {stream_url}")

try:
    with urllib.request.urlopen(stream_url, timeout=5) as resp:
        print("HTTP status:", resp.status)
        print("Content-Type:", resp.headers.get("Content-Type"))
        chunk = resp.read(1024 * 64)
        print(f"Read {len(chunk)} bytes from stream!")
except Exception as e:
    print(f"Error fetching from 127.0.0.1: {e}")

# Also test ffmpeg probing the stream
cmd = ["ffmpeg", "-t", "2", "-i", stream_url, "-f", "null", "-"]
p = subprocess.run(cmd, capture_output=True, text=True)
print("=== FFMPEG PROBE ===")
for line in p.stderr.splitlines():
    if "Stream #" in line or "Audio:" in line or "Duration:" in line or "Output #" in line:
        print(line)
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=check_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
