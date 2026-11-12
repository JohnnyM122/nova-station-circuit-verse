import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = "cat /home/ubuntu/CV-Nova-Helper/cogs/voice_channels.py"

res = subprocess.run(["ssh", "-n", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
if res.returncode == 0:
    with open("tools/remote_voice_channels.py", "wb") as f:
        f.write(res.stdout)
    print("Saved remote_voice_channels.py! Size:", len(res.stdout))
else:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
