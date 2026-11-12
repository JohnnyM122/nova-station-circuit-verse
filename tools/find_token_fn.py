import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

SCRIPT = """
with open('/opt/zomboid-panel/client/dist/assets/errorMessage-DV5sBvRy.js') as f:
    text = f.read()

import re
idx = text.find('at as b')
print(text[idx-200:idx+300])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "python3 -"]
res = subprocess.run(cmd, input=SCRIPT.encode("utf-8"), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
