cat << 'EOF' > /tmp/setup_unturned_cx33.sh
#!/bin/bash
set -e

NEW_IP="91.107.198.243"
SSH="ssh -i /etc/cv-panel/id_ed25519 -o StrictHostKeyChecking=no root@$NEW_IP"
SCP="scp -i /etc/cv-panel/id_ed25519 -o StrictHostKeyChecking=no"

echo "=== 1. System packages & Swap on $NEW_IP ==="
$SSH "bash -s" << 'REMOTE_INIT'
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y lib32gcc-s1 lib32stdc++6 libssl-dev libc6-dev curl tar screen ufw git rsync

# Swapfile
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Firewall
ufw allow 22/tcp
ufw allow 27015/udp
ufw allow 27016/udp
ufw allow 27115/tcp
ufw --force enable

# User
if ! id -u unturned >/dev/null 2>&1; then
    useradd -m -s /bin/bash unturned
fi
REMOTE_INIT

echo "=== 2. SteamCMD & Unturned App 1110390 ==="
$SSH "bash -s" << 'REMOTE_STEAM'
set -e
su - unturned -c '
mkdir -p /home/unturned/steamcmd /home/unturned/unturned-server
cd /home/unturned/steamcmd
if [ ! -f steamcmd.sh ]; then
    curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -
fi
./steamcmd.sh +@sSteamCmdForcePlatformType linux +force_install_dir /home/unturned/unturned-server +login anonymous +app_update 1110390 validate +quit
'
REMOTE_STEAM

echo "=== 3. Enable RocketMod Module ==="
$SSH "bash -s" << 'REMOTE_ROCKET'
set -e
mkdir -p /home/unturned/unturned-server/Modules
cp -r /home/unturned/unturned-server/Extras/Rocket.Unturned /home/unturned/unturned-server/Modules/Rocket.Unturned
mkdir -p /home/unturned/unturned-server/Servers
REMOTE_ROCKET

echo "=== 4. Restore CircuitVerse Configuration & State ==="
$SCP /opt/CircuitVerse_backup.tar.gz root@$NEW_IP:/tmp/CircuitVerse_backup.tar.gz
$SCP /opt/unturned.service.bak root@$NEW_IP:/etc/systemd/system/unturned.service

$SSH "bash -s" << 'REMOTE_RESTORE'
set -e
tar -xzf /tmp/CircuitVerse_backup.tar.gz -C /home/unturned/unturned-server/Servers/
rm -f /tmp/CircuitVerse_backup.tar.gz
chown -R unturned:unturned /home/unturned/unturned-server
chmod +x /home/unturned/unturned-server/ServerHelper.sh /home/unturned/unturned-server/Unturned_Headless.x86_64

systemctl daemon-reload
systemctl enable unturned.service
systemctl restart unturned.service
sleep 5
systemctl status unturned.service --no-pager
REMOTE_RESTORE

echo "=== MIGRATION TO CX33 (€9.99/mo) COMPLETE ==="
EOF
bash /tmp/setup_unturned_cx33.sh
