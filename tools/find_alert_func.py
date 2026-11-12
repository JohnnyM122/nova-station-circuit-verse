import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
with open("/home/ubuntu/CV-Nova-Helper/cogs/project_zomboid.py", "r", errors="ignore") as f:
    for i, line in enumerate(f, 1):
        if "send_status_channel_alert" in line:
            print(f"{i}: {line.strip()[:120]}")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
