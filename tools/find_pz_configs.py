import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "find /home/pz -name '*.ini' 2>/dev/null; find /home/pz -name '*.lua' 2>/dev/null"]
res = subprocess.run(cmd, capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:", res.stderr.decode("utf-8", errors="replace"))
