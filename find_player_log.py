import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    "find /home/ -name 'Player.log'"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Find Player.log:\n", res.stdout)
