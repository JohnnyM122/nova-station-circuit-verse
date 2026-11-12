import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """
sudo systemctl start project-zomboid.service
sleep 8
sudo systemctl is-active project-zomboid.service
sudo python3 -c '
with open("/home/pz/Zomboid/server-console.txt", "r", errors="ignore") as f:
    for line in f:
        if "version=" in line.lower():
            print("PZ SERVER VERSION:", line.strip())
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
