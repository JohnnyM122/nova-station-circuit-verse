import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo -u pz /home/pz/steamcmd/steamcmd.sh +login anonymous +app_info_update 1 +app_info_print 380870 +quit"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
out = res.stdout.decode("utf-8", errors="replace")

# Print branches section
import re
m = re.search(r'"branches".*?}\s*}', out, re.DOTALL)
if m:
    print(m.group(0))
else:
    print("No branches found, length of output:", len(out))
    print(out[-1000:])
