#!/bin/bash
set -e
echo "=== 1. Running SteamCMD for Unturned Dedicated Server (1110390) ==="
su - unturned -c "/home/unturned/steamcmd/steamcmd.sh +@sSteamCmdForcePlatformType linux +force_install_dir /home/unturned/unturned-server +login anonymous +app_update 1110390 validate +quit"

echo "=== 2. Setting up RocketMod ==="
if [ -d "/home/unturned/unturned-server/Extras/Rocket.Unturned" ]; then
    mkdir -p /home/unturned/unturned-server/Modules
    cp -r /home/unturned/unturned-server/Extras/Rocket.Unturned /home/unturned/unturned-server/Modules/
    echo "RocketMod module copied to Modules/"
fi

echo "=== 3. Restoring CircuitVerse Configs & Permissions ==="
mkdir -p /home/unturned/unturned-server/Servers
cd /home/unturned/unturned-server/Servers
tar -zxvf /opt/CircuitVerse_backup.tar.gz

echo "=== 4. Setting Permissions and Ownership ==="
chown -R unturned:unturned /home/unturned/unturned-server
chmod +x /home/unturned/unturned-server/Unturned.x86_64
chmod +x /home/unturned/unturned-server/ServerHelper.sh

echo "=== 5. Enabling and Starting systemd Service ==="
cp /opt/unturned.service.bak /etc/systemd/system/unturned.service
systemctl daemon-reload
systemctl enable unturned
systemctl restart unturned

echo "=== 6. Status Check ==="
sleep 5
systemctl status unturned --no-pager
