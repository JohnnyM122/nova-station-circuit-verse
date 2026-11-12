import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

check_script = """
import davey
kp = davey.generate_p256_keypair()
ds = davey.DaveSession(12345, 1, 67890, key_pair=kp)
print("ds methods:", [m for m in dir(ds) if not m.startswith("__")])
print("ds.ready:", getattr(ds, "ready", None))
print("ds.can_encrypt:", getattr(ds, "can_encrypt", None))
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=check_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
