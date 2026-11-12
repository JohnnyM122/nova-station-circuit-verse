import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import os, glob, re

items = set()
for sf in glob.glob("/home/pz/pz-server/media/scripts/**/*.txt", recursive=True):
    try:
        with open(sf, "r", errors="ignore") as f:
            for l in f:
                m = re.match(r"^\s*item\s+([A-Za-z0-9_]+)", l)
                if m:
                    name = m.group(1)
                    if any(x in name.lower() for x in ["water", "canned", "bottle", "chips", "crisps"]):
                        items.add(name)
    except Exception:
        pass

for name in sorted(items):
    if any(k in name.lower() for k in ["water", "beans", "canned", "bottle"]):
        print(name)
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
