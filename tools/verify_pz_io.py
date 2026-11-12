import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """python3 -c "
import urllib.request, json
# Let's test reading the ini and sandbox directly as our function does
ini_path = '/home/pz/Zomboid/Server/CircuitVersePZ.ini'
sb_path = '/home/pz/Zomboid/Server/CircuitVersePZ_SandboxVars.lua'
with open(ini_path) as f:
    ini = f.read()
for line in ini.splitlines():
    if line.startswith('Mods=') or line.startswith('WorkshopItems='):
        print(line)
with open(sb_path) as f:
    sb = f.read()
print('SandboxVars lines:', len(sb.splitlines()))
"
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, f"sudo {cmd}"], capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
