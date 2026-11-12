import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

check_script = """
import davey
print("davey contents:", dir(davey))
ds = davey.DaveSession(12345, 1) # user_id, group_id
print("ds methods:", dir(ds))
print("ds.ready:", getattr(ds, "ready", None))
print("ds.can_encrypt:", getattr(ds, "can_encrypt", None))
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=check_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
