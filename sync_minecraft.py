import subprocess
import os
import time

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'
MC_IP = '2.31.101.63'

def run_ssh(host, command, user='root', timeout=180):
    cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'{user}@{host}', command]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

print("1. Stopping Minecraft on old cloud server to flush world saves...")
rc, out, err = run_ssh(MC_IP, 'systemctl stop minecraft mc-staff-logger')
print(f"Stop result: rc={rc}")

print("2. Syncing /opt/minecraft directly from MC server to Dedicated server...")
sync_cmd = f"""
ssh -o StrictHostKeyChecking=accept-new root@{MC_IP} 'uptime' && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{MC_IP}:/opt/minecraft/ /opt/minecraft/
"""
rc, out, err = run_ssh(DED_IP, sync_cmd, timeout=600)
print(f"Rsync result: rc={rc}")
if err:
    print(f"Rsync STDERR:\n{err[-500:]}")

print("3. Copying systemd service files...")
rc1, out1, err1 = run_ssh(MC_IP, 'cat /etc/systemd/system/minecraft.service')
rc2, out2, err2 = run_ssh(MC_IP, 'cat /etc/systemd/system/mc-staff-logger.service')

install_service_cmd = f"""
cat << 'EOF' > /etc/systemd/system/minecraft.service
{out1}
EOF

cat << 'EOF' > /etc/systemd/system/mc-staff-logger.service
{out2}
EOF

chown -R minecraft:minecraft /opt/minecraft
chmod +x /opt/minecraft/scripts/*.sh 2>/dev/null || true
systemctl daemon-reload
systemctl enable minecraft mc-staff-logger
systemctl start minecraft mc-staff-logger
"""
rc, out, err = run_ssh(DED_IP, install_service_cmd)
print(f"Service install/start result: rc={rc}")

print("4. Waiting 15s to check Minecraft status on dedicated server...")
time.sleep(15)
rc, out, err = run_ssh(DED_IP, 'systemctl status minecraft mc-staff-logger --no-pager; ss -tulpn | grep 25565')
print(f"Status:\n{out}")
