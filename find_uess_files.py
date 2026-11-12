import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    "grep -rni 'this is something' /home/unturned/ 2>/dev/null; find /home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins/uEssentials/ -type f"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Search results:\n", res.stdout)
