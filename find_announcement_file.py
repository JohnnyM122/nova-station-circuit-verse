import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    "grep -rn 'this is an announcement' /home/unturned/unturned-server/Servers/CircuitVerse/Rocket/ 2>/dev/null || grep -rn 'this is something' /home/unturned/unturned-server/Servers/CircuitVerse/Rocket/ 2>/dev/null"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Grep output:\n", res.stdout)
