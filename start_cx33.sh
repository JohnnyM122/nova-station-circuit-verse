#!/bin/bash
set -e
chown -R unturned:unturned /home/unturned/unturned-server
chmod +x /home/unturned/unturned-server/Unturned_Headless.x86_64 || true
chmod +x /home/unturned/unturned-server/ServerHelper.sh || true
cp /opt/unturned.service.bak /etc/systemd/system/unturned.service
systemctl daemon-reload
systemctl enable unturned
systemctl restart unturned
sleep 3
systemctl status unturned --no-pager
