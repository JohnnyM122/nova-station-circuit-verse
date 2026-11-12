import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

SCRIPT = """
with open('/opt/zomboid-panel/client/dist/assets/Login-7CbMDwkk.js') as f:
    text = f.read()

import re
for m in re.finditer(r'URLSearchParams', text):
    start = max(0, m.start() - 50)
    end = min(len(text), m.end() + 300)
    print('--- MATCH ---')
    print(text[start:end])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "python3 -"]
res = subprocess.run(cmd, input=SCRIPT.encode("utf-8"), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
