import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import os
for root, dirs, files in os.walk("/home/ubuntu/CV-Nova-Helper"):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            with open(p, "r", errors="ignore") as fl:
                for i, line in enumerate(fl, 1):
                    if any(k in line.lower() for k in ["staff_logs_channel", "connected", "pz-server-logs", "server-logs"]):
                        print(f"{p}:{i}: {line.strip()[:100]}")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
