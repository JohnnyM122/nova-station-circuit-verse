import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo cp /home/pz/Zomboid/Server/CircuitVersePZ.ini /home/pz/repo/server_config/CircuitVersePZ.ini && sudo chown -R pz:pz /home/pz/repo/server_config/"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
