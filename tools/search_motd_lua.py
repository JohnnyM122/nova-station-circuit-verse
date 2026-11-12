import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import os, glob

# Search in media/lua
for root, dirs, files in os.walk("/home/pz/pz-server/media/lua"):
    for f in files:
        if "motd" in f.lower():
            print("Found lua file:", os.path.join(root, f))
        elif f.endswith(".lua"):
            fp = os.path.join(root, f)
            with open(fp, "r", errors="ignore") as fl:
                c = fl.read()
                if "motd" in c.lower() or "serverwelcomemessage" in c.lower():
                    print("Found in lua:", fp)
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
