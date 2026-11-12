import subprocess

def ssh_cmd(host, cmd, user="ubuntu"):
    key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
    res = subprocess.run([
        "ssh", "-i", key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{user}@{host}",
        cmd
    ], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return res.stdout

for fn in ["status.py", "support_tickets.py", "tickets.py"]:
    out = ssh_cmd("87.99.133.221", f"cat /home/ubuntu/CV-Nova-Helper/cogs/{fn}")
    with open(f"local_{fn}", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Downloaded local_{fn}")
