import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import os
for root, dirs, files in os.walk("/home/pz/pz-server/media/lua/client"):
    for f in files:
        if "menu" in f.lower():
            print(os.path.join(root, f))
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
