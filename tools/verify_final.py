import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c "
import urllib.request, json
# Let's inspect the files on disk and check that the server is listening
import os
print('Server files exist:', os.path.exists('/home/pz/pz-server/steamapps/workshop/content/108600/3745718141'))
os.system('pgrep -f ProjectZomboid64')
"
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
