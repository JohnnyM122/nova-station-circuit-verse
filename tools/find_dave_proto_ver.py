import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

check_script = """
import inspect
from discord import gateway

src = inspect.getsource(gateway)
lines = src.splitlines()
for i, l in enumerate(lines):
    if "dave_protocol_version" in l:
        print("\\n".join(lines[max(0, i-4):min(len(lines), i+12)]))
        print("="*40)
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=check_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:\n", res.stderr.decode("utf-8", errors="replace"))
