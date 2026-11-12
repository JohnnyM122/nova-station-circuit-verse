import subprocess
import os
import time

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'
GEN_IP = '2.31.173.113'

def run_ssh(host, command, user='root', timeout=300):
    cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'{user}@{host}', command]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

print("1. Stopping AzuraCast and bots on old cloud server...")
run_ssh(GEN_IP, 'sudo systemctl stop cv-radio-helper cv-radio-tunnel && cd /var/azuracast && sudo docker compose down', user='ubuntu')

print("2. Syncing cloudflared, azuracast, and docker volumes...")
sync_cmd = f"""
ssh -o StrictHostKeyChecking=accept-new root@{GEN_IP} 'uptime' && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{GEN_IP}:/etc/cloudflared/ /etc/cloudflared/ && \
rsync -aHAXxv -e 'ssh -o StrictHostKeyChecking=accept-new' root@{GEN_IP}:/usr/local/bin/cloudflared /usr/local/bin/cloudflared && \
chmod +x /usr/local/bin/cloudflared && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{GEN_IP}:/var/azuracast/ /var/azuracast/ && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{GEN_IP}:/home/ubuntu/CV-Radio-Helper/ /home/ubuntu/CV-Radio-Helper/ && \
systemctl stop docker && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{GEN_IP}:/var/lib/docker/volumes/ /var/lib/docker/volumes/ && \
systemctl start docker
"""
rc, out, err = run_ssh(DED_IP, sync_cmd, timeout=900)
print(f"Rsync result: rc={rc}")

print("3. Copying systemd services and launching AzuraCast...")
rc1, out1, err1 = run_ssh(GEN_IP, 'sudo cat /etc/systemd/system/cv-radio-helper.service', user='ubuntu')
rc2, out2, err2 = run_ssh(GEN_IP, 'sudo cat /etc/systemd/system/cv-radio-tunnel.service', user='ubuntu')

install_cmd = f"""
cat << 'EOF' > /etc/systemd/system/cv-radio-helper.service
{out1}
EOF

cat << 'EOF' > /etc/systemd/system/cv-radio-tunnel.service
{out2}
EOF

chown -R ubuntu:ubuntu /home/ubuntu/CV-Radio-Helper
cd /var/azuracast && docker compose pull && docker compose up -d
systemctl daemon-reload
systemctl enable cv-radio-tunnel cv-radio-helper
systemctl start cv-radio-tunnel cv-radio-helper
"""
rc, out, err = run_ssh(DED_IP, install_cmd, timeout=300)
print(f"Launch result: rc={rc}")

print("4. Checking docker and radio status...")
time.sleep(15)
rc, out, err = run_ssh(DED_IP, 'docker ps; systemctl status cv-radio-tunnel cv-radio-helper --no-pager')
print(f"Status:\n{out}")
