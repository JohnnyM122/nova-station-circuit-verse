import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    "ls -la /home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins/"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Plugins:\n", res.stdout)
