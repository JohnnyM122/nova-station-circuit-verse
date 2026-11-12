import subprocess
import os
import time

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'
NS13_IP = '87.99.133.221'

def run_ssh(host, command, user='root', timeout=300):
    cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'{user}@{host}', command]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

print("1. Stopping NS13 services and dumping MariaDB databases...")
dump_cmd = """
sudo systemctl stop novastation.service cv-nova-helper.service
sudo mysqldump --all-databases --routines --triggers > /tmp/ns13_all_dbs.sql
"""
rc, out, err = run_ssh(NS13_IP, dump_cmd, user='ubuntu')
print(f"Dump result: rc={rc}")

print("2. Syncing MariaDB dump and BYOND/SS13 files to Dedicated server...")
sync_cmd = f"""
ssh -o StrictHostKeyChecking=accept-new root@{NS13_IP} 'uptime' && \
rsync -aHAXxv -e 'ssh -o StrictHostKeyChecking=accept-new' root@{NS13_IP}:/tmp/ns13_all_dbs.sql /tmp/ns13_all_dbs.sql && \
mariadb < /tmp/ns13_all_dbs.sql && \
mariadb -e "FLUSH PRIVILEGES;" && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{NS13_IP}:/home/ubuntu/BYOND/ /home/ubuntu/BYOND/ && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{NS13_IP}:/home/ubuntu/NovaStation/ /home/ubuntu/NovaStation/ && \
rsync -aHAXxv --delete -e 'ssh -o StrictHostKeyChecking=accept-new' root@{NS13_IP}:/home/ubuntu/CV-Nova-Helper/ /home/ubuntu/CV-Nova-Helper/ && \
rsync -aHAXxv -e 'ssh -o StrictHostKeyChecking=accept-new' root@{NS13_IP}:/home/ubuntu/*.py /home/ubuntu/ 2>/dev/null || true
"""
rc, out, err = run_ssh(DED_IP, sync_cmd, timeout=600)
print(f"Rsync & DB import result: rc={rc}")

print("3. Fetching and copying NS13 systemd services...")
rc1, out1, err1 = run_ssh(NS13_IP, 'sudo cat /etc/systemd/system/novastation.service', user='ubuntu')
rc2, out2, err2 = run_ssh(NS13_IP, 'sudo cat /etc/systemd/system/cv-nova-helper.service', user='ubuntu')

install_cmd = f"""
cat << 'EOF' > /etc/systemd/system/novastation.service
{out1}
EOF

cat << 'EOF' > /etc/systemd/system/cv-nova-helper.service
{out2}
EOF

chown -R ubuntu:ubuntu /home/ubuntu
python3 -m venv --clear /home/ubuntu/CV-Nova-Helper/venv
/home/ubuntu/CV-Nova-Helper/venv/bin/pip install discord.py aiohttp python-dotenv requests mysql-connector-python pymysql
chown -R ubuntu:ubuntu /home/ubuntu/CV-Nova-Helper
systemctl daemon-reload
systemctl enable mariadb novastation.service cv-nova-helper.service
systemctl restart mariadb
systemctl start novastation.service cv-nova-helper.service
"""
rc, out, err = run_ssh(DED_IP, install_cmd, timeout=300)
print(f"Service install/start result: rc={rc}")

print("4. Waiting 15s to check NS13 status on dedicated server...")
time.sleep(15)
rc, out, err = run_ssh(DED_IP, 'systemctl status novastation.service cv-nova-helper.service --no-pager; ss -tulpn | grep 7777')
print(f"Status:\n{out}")
