import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import os, glob, re

matches = set()
for path in ["/etc/cv-panel", "/opt/cv-panel", "/home/ubuntu", "/home/pz"]:
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith((".json", ".py", ".html", ".ini", ".txt")):
                fp = os.path.join(root, f)
                try:
                    with open(fp, "r", errors="ignore") as fl:
                        txt = fl.read()
                        invs = re.findall(r"discord\.(?:gg|com/invite)/[A-Za-z0-9]+", txt)
                        for inv in invs:
                            matches.add(inv)
                except Exception:
                    pass

for m in sorted(matches):
    print("Found invite:", m)
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
