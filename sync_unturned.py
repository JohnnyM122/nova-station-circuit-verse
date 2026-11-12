import subprocess
import os
import time

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'
UNTURNED_IP = '91.107.198.243'

def run_ssh(host, command, user='root', timeout=300):
    cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'{user}@{host}', command]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

print("1. Stopping Unturned on old cloud server...")
rc, out, err = run_ssh(UNTURNED_IP, 'systemctl stop unturned')
print(f"Stop result: rc={rc}")

print("2. Syncing /home/unturned from Unturned server to Dedicated server...")
sync_cmd = f"""
ssh -o StrictHostKeyChecking=accept-new root@{UNTURNED_IP} 'uptime' && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{UNTURNED_IP}:/home/unturned/ /home/unturned/
"""
rc, out, err = run_ssh(DED_IP, sync_cmd, timeout=300)
print(f"Rsync result: rc={rc}")

print("3. Fetching and copying Unturned systemd service...")
rc1, out1, err1 = run_ssh(UNTURNED_IP, 'cat /etc/systemd/system/unturned.service')

install_cmd = f"""
cat << 'EOF' > /etc/systemd/system/unturned.service
{out1}
EOF

chown -R unturned:unturned /home/unturned
systemctl daemon-reload
systemctl enable unturned
systemctl start unturned
"""
rc, out, err = run_ssh(DED_IP, install_cmd)
print(f"Service install/start result: rc={rc}")

print("4. Waiting 15s to check Unturned status on dedicated server...")
time.sleep(15)
rc, out, err = run_ssh(DED_IP, 'systemctl status unturned --no-pager; ss -tulpn | grep -i unturned')
print(f"Status:\n{out}")
