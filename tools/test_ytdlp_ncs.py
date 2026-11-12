import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

check_script = """
import subprocess, json

# Test yt-dlp extracting titles from an official NCS playlist without downloading
cmd = [
    "yt-dlp",
    "--flat-playlist",
    "--dump-single-json",
    "https://www.youtube.com/@NoCopyrightSounds/videos"
]
print("Running yt-dlp flat-playlist on @NoCopyrightSounds/videos (first 10)...")
p = subprocess.run(["yt-dlp", "--flat-playlist", "-I", "1:10", "--print", "%(title)s - %(id)s", "https://www.youtube.com/@NoCopyrightSounds/videos"], capture_output=True, text=True)
print("OUT:\\n", p.stdout[:500])
if p.stderr:
    print("ERR:\\n", p.stderr[:300])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=check_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
