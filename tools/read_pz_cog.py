import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = "cat /home/ubuntu/CV-Nova-Helper/cogs/project_zomboid.py"

res = subprocess.run(["ssh", "-n", "-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
if res.returncode == 0:
    with open("tools/remote_pz_cog.py", "wb") as f:
        f.write(res.stdout)
    print("Successfully saved remote_pz_cog.py! Length:", len(res.stdout))
else:
    print("EXIT CODE:", res.returncode)
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
