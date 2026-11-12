import subprocess, os

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'

def run_ssh(host, command):
    cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'root@{host}', command]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return res.stdout.strip()

check_script = """
echo "=== SYSTEM RESOURCES ==="
uptime
free -h
echo ""
echo "=== ACTIVE GAME & WEB SERVICES ==="
systemctl is-active \
  minecraft.service \
  mc-staff-logger.service \
  project-zomboid.service \
  zomboid-panel.service \
  unturned.service \
  docker.service \
  cv-radio-tunnel.service \
  cv-radio-helper.service \
  mariadb.service \
  novastation.service \
  cv-nova-helper.service
echo ""
echo "=== LISTENING GAME & APP PORTS ==="
ss -tulpn | grep -E "25565|16261|3001|3443|27015|27016|27115|80|443|8088|7777|3306"
echo ""
echo "=== AZURACAST DOCKER STATUS ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
"""

out = run_ssh(DED_IP, check_script)
print(out)
