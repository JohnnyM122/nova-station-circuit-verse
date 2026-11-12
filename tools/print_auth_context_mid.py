import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

SCRIPT = """
with open('/opt/zomboid-panel/client/dist/assets/AuthContext-BV3pKPH6.js') as f:
    text = f.read()

print(text[1500:4500])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "python3 -"]
res = subprocess.run(cmd, input=SCRIPT.encode("utf-8"), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
