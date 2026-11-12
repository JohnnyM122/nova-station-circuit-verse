import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """
sudo ln -sf /home/ubuntu/CV-Nova-Helper/venv/bin/yt-dlp /usr/local/bin/yt-dlp
which yt-dlp
yt-dlp --version
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
