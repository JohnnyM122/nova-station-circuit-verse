import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
with open("/home/pz/Zomboid/Server/CircuitVersePZ.ini") as f:
    for i, line in enumerate(f, 1):
        if 169 <= i <= 189:
            # Mask token for security
            if "DiscordToken=" in line:
                val = line.split("=", 1)[1].strip()
                masked = val[:6] + "..." + val[-6:] if len(val) > 12 else "***"
                print(f"{i}: DiscordToken={masked}")
            else:
                print(f"{i}: {line.strip()}")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
