import subprocess
import json

def ssh_cmd(host, cmd, user="ubuntu"):
    key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
    res = subprocess.run([
        "ssh", "-i", key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{user}@{host}",
        cmd
    ], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return res.stdout, res.stderr

out, err = ssh_cmd("87.99.133.221", "cat /home/ubuntu/CV-Nova-Helper/cogs/unturned.py")
with open("local_unturned_cog.py", "w", encoding="utf-8") as f:
    f.write(out)

out2, err2 = ssh_cmd("87.99.133.221", "cat /home/ubuntu/CV-Nova-Helper/config.json")
with open("local_bot_config.json", "w", encoding="utf-8") as f:
    f.write(out2)

print("Downloaded local_unturned_cog.py and local_bot_config.json")
