import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

script = """
import subprocess, json, time, os

t0 = time.time()
print("Extracting video list from @NoCopyrightSounds/videos...")
cmd = [
    "yt-dlp",
    "--flat-playlist",
    "-I", "1:1500",
    "--print", "%(id)s\\t%(title)s",
    "https://www.youtube.com/@NoCopyrightSounds/videos"
]
proc = subprocess.run(cmd, capture_output=True, text=True)
lines = [l.strip() for l in proc.stdout.splitlines() if "\\t" in l]
print(f"Extracted {len(lines)} videos in {time.time() - t0:.1f}s")
with open("/tmp/ncs_candidates.txt", "w", encoding="utf-8") as f:
    f.write("\\n".join(lines))
print("Saved to /tmp/ncs_candidates.txt")
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:\n", res.stderr.decode("utf-8", errors="replace"))
