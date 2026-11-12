import subprocess
import os

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DEDICATED_IP = '62.238.81.224'

def run_cmd(command, timeout=120):
    cmd = [
        'ssh', '-i', SSH_KEY,
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        f'root@{DEDICATED_IP}',
        command
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

print("1. Adding i386 architecture and installing base packages...")
script = """
dpkg --add-architecture i386
apt-get update
apt-get install -y \
  openjdk-21-jre-headless \
  docker.io docker-compose-v2 \
  mariadb-server \
  python3 python3-pip python3-venv \
  libc6:i386 libstdc++6:i386 libgcc-s1:i386 zlib1g:i386 libsdl2-2.0-0:i386 \
  screen tmux rsync curl git jq htop net-tools

# Ensure users exist
id -u minecraft &>/dev/null || useradd -r -m -U -d /opt/minecraft -s /bin/bash minecraft
id -u pz &>/dev/null || useradd -m -U -s /bin/bash pz
id -u unturned &>/dev/null || useradd -m -U -s /bin/bash unturned
id -u ubuntu &>/dev/null || useradd -m -U -s /bin/bash ubuntu
usermod -aG sudo ubuntu
usermod -aG docker ubuntu
usermod -aG docker root

# Ensure .ssh dir on users
for u in root pz unturned ubuntu minecraft; do
  h=$(eval echo ~$u)
  mkdir -p $h/.ssh
  chmod 700 $h/.ssh
  cat /root/.ssh/id_ed25519.pub >> $h/.ssh/authorized_keys 2>/dev/null || true
  cat ~/.ssh/authorized_keys >> $h/.ssh/authorized_keys 2>/dev/null || true
  sort -u $h/.ssh/authorized_keys -o $h/.ssh/authorized_keys
  chown -R $u:$u $h/.ssh
done
"""

rc, out, err = run_cmd(script, timeout=300)
print(f"Base setup return code: {rc}")
if err:
    print(f"STDERR (last 500 chars):\n{err[-500:]}")
print(f"STDOUT (last 500 chars):\n{out[-500:]}")
