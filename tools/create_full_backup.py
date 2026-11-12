import paramiko
import time

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

backup_script = """#!/bin/bash
set -e

BACKUP_ROOT="/home/ubuntu/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEST="$BACKUP_ROOT/$TIMESTAMP"
mkdir -p "$DEST"
mkdir -p "$BACKUP_ROOT/latest"

echo "=== 1. Backing up Discord Bots & Configs ==="
tar --exclude='*/venv/*' --exclude='*/__pycache__/*' -czf "$DEST/discord_bots_and_data.tar.gz" \
    /home/ubuntu/CV-Nova-Helper /home/ubuntu/CV-Radio-Helper
echo "Discord backup done: $(ls -lh $DEST/discord_bots_and_data.tar.gz | awk '{print $5}')"

echo "=== 2. Backing up Minecraft Server ==="
tar --exclude='*/cache/*' -czf "$DEST/minecraft_server.tar.gz" /opt/minecraft/server
echo "Minecraft backup done: $(ls -lh $DEST/minecraft_server.tar.gz | awk '{print $5}')"

echo "=== 3. Backing up Nova Station 13 ==="
tar --exclude='*/.git/*' -czf "$DEST/novastation13.tar.gz" /home/ubuntu/NovaStation
echo "Nova Station backup done: $(ls -lh $DEST/novastation13.tar.gz | awk '{print $5}')"

echo "=== 4. Backing up Unturned Server ==="
tar -czf "$DEST/unturned_server.tar.gz" /home/unturned
echo "Unturned backup done: $(ls -lh $DEST/unturned_server.tar.gz | awk '{print $5}')"

echo "=== 5. Backing up Project Zomboid & Panel ==="
tar --exclude='*/venv/*' -czf "$DEST/project_zomboid.tar.gz" /home/pz /opt/zomboid-panel
echo "Project Zomboid backup done: $(ls -lh $DEST/project_zomboid.tar.gz | awk '{print $5}')"

echo "=== 6. Backing up CV Control Panel & Systemd Services ==="
tar --exclude='*/venv/*' -czf "$DEST/cv_panel_and_services.tar.gz" \
    /opt/cv-panel /etc/systemd/system/cv*.service /etc/systemd/system/minecraft.service \
    /etc/systemd/system/novastation.service /etc/systemd/system/unturned.service \
    /etc/systemd/system/zomboid-panel.service 2>/dev/null || true
echo "CV Panel & Services backup done: $(ls -lh $DEST/cv_panel_and_services.tar.gz | awk '{print $5}')"

echo "=== 7. Backing up AzuraCast Database & Configuration ==="
docker exec azuracast gosu azuracast mysqldump -u root azuracast > "$DEST/azuracast_database.sql" 2>/dev/null || true
tar -czf "$DEST/azuracast_station_config.tar.gz" -C "$DEST" azuracast_database.sql 2>/dev/null || true
rm -f "$DEST/azuracast_database.sql"
echo "AzuraCast backup done: $(ls -lh $DEST/azuracast_station_config.tar.gz | awk '{print $5}')"

# Copy to latest
cp -f "$DEST"/* "$BACKUP_ROOT/latest/"

echo "=== ALL BACKUPS COMPLETED SUCCESSFULLY IN $DEST ==="
ls -lh "$DEST"
"""

try:
    sftp = client.open_sftp()
    with sftp.open("/home/ubuntu/run_full_backup.sh", "w") as f:
        f.write(backup_script)
    sftp.close()

    print("Created /home/ubuntu/run_full_backup.sh. Making executable and running...")
    stdin, stdout, stderr = client.exec_command("chmod +x /home/ubuntu/run_full_backup.sh && sudo /home/ubuntu/run_full_backup.sh")
    
    while not stdout.channel.exit_status_ready():
        line = stdout.readline()
        if line:
            print(line.strip())
        time.sleep(0.5)
    for line in stdout.readlines():
        print(line.strip())
    
    err = stderr.read().decode()
    if err:
        print("ERRORS/WARNINGS:\n", err)

finally:
    client.close()
