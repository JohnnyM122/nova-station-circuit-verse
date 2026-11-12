import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import subprocess
print("=== SS LISTENING PORTS ===")
p = subprocess.run(["ss", "-tulpn"], capture_output=True, text=True)
for line in p.stdout.splitlines():
    if any(port in line for port in ["16261", "16262", "27015"]):
        print(line)

print("=== SERVER CONSOLE TAIL ===")
with open("/home/pz/Zomboid/server-console.txt", "r", errors="ignore") as f:
    lines = f.readlines()
for line in lines[-20:]:
    print(line.strip())
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
