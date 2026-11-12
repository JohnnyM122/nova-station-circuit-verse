import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import zipfile

with zipfile.ZipFile("/home/pz/pz-server/java/projectzomboid.jar", "r") as z:
    raw = z.read("zombie/network/DiscordBot.class")

# Print all string constants in raw class bytes
import re
strings = re.findall(b"[\\x20-\\x7e]{3,}", raw)
for s in strings:
    s_dec = s.decode(errors=\"ignore\")
    if any(k in s_dec.lower() for k in [\"channel\", \"chat\", \"log\", \"command\", \"discord\", \"error\", \"warning\", \"token\"]):
        print(s_dec)
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
