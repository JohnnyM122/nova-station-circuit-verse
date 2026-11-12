import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

with open("tools/remote_pz_cog.py", "rb") as f:
    content = f.read()

cmd = "cat > /home/ubuntu/CV-Nova-Helper/cogs/project_zomboid.py && sudo systemctl restart cv-nova-helper.service && sudo systemctl is-active cv-nova-helper.service"

res = subprocess.run(
    ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8", HOST, cmd],
    input=content,
    capture_output=True
)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
