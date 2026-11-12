import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "sudo find /home /opt /root /var -name '*CircuitVersePZ*' -o -name '*servertest*' 2>/dev/null"]
res = subprocess.run(cmd, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
