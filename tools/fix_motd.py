import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

remote_script = """
set -e
sudo systemctl stop project-zomboid.service
sleep 2

sudo python3 -c '
new_motd = "ServerWelcomeMessage=<RGB:0.35,0.75,1.0> Welcome to Circuit Verse • Project Zomboid (Build 42)!<LINE><RGB:1.0,1.0,1.0> Join our Discord community for rules, updates, live support and voice:<LINE><RGB:0.34,0.85,0.95> https://discord.gg/M7R8EY28q6 <LINE><RGB:0.8,0.8,0.8> Enjoy smooth survival and fair play!\\n"

for p in ["/home/pz/Zomboid/Server/CircuitVersePZ.ini", "/home/pz/repo/server_config/CircuitVersePZ.ini"]:
    try:
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(p, "w", encoding="utf-8") as f:
            for l in lines:
                if l.startswith("ServerWelcomeMessage="):
                    f.write(new_motd)
                else:
                    f.write(l)
    except Exception as e:
        print("Error on", p, e)
'

echo "=== Verified Clean MOTD in CircuitVersePZ.ini ==="
sudo grep -n "ServerWelcomeMessage=" /home/pz/Zomboid/Server/CircuitVersePZ.ini

sudo systemctl start project-zomboid.service
sleep 5
sudo systemctl is-active project-zomboid.service
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, remote_script], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
