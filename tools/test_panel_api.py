import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "curl -s http://127.0.0.1:8099/api/health"]
res = subprocess.run(cmd, capture_output=True)
print("HEALTH:\n", res.stdout.decode("utf-8", errors="replace"))
