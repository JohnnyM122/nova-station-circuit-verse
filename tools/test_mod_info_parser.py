import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import os, glob

base = "/home/pz/pz-server/steamapps/workshop/content/108600"
for wid in sorted(os.listdir(base)):
    wdir = os.path.join(base, wid)
    if not os.path.isdir(wdir): continue
    infos = glob.glob(os.path.join(wdir, "mods", "*", "mod.info"))
    if not infos:
        infos = glob.glob(os.path.join(wdir, "**", "mod.info"), recursive=True)
    print(f"=== Workshop {wid} ===")
    for info in infos:
        d = {}
        with open(info, errors="replace") as f:
            for l in f:
                if "=" in l:
                    k, v = l.strip().split("=", 1)
                    d[k.lower()] = v
        print("  name=" + str(d.get("name")) + " id=" + str(d.get("id")))
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
