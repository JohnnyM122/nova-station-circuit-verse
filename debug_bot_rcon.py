import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
code = """
import sys
sys.path.append('/home/ubuntu/CV-Nova-Helper')
import json, asyncio
from cogs.unturned import unturned_rcon_sync, load_config

cfg = load_config()
u = cfg.get("unturned_server", {})
print("CONFIG U:", u)
host = u.get("host", "2.31.169.227")
port = int(u.get("rcon_port", 27115))
password = u.get("rcon_password", "CircuitVerseUnturned2026!")

try:
    res = unturned_rcon_sync(host, port, password, "p")
    print("SUCCESS:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
"""
res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "ubuntu@87.99.133.221",
    f"/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -c {subprocess.list2cmdline([code])}"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)

print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
