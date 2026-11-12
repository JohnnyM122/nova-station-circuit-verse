import subprocess
import os

SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519_tailscale")
script = """
echo '=== SERVICE STATES ==='
for s in novastation minecraft project-zomboid unturned cv-radio-helper cv-radio-tunnel cv-panel mariadb cv-nova-helper; do
    printf '%-20s: %s\\n' "$s" "$(systemctl is-active $s)"
done

echo '=== LISTENING PORTS ==='
ss -tulnp | grep -E ':(7777|25565|24454|16261|27015|27016|27115|8099|3306)' | awk '{print $1, $5, $7}' | sort -u
"""

cmd = ["ssh", "-n", "-i", SSH_KEY, "-o", "BatchMode=yes", "root@62.238.81.224", script]
res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
