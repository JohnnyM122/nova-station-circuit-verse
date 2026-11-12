#!/bin/bash
set -e
echo "=== Installing MariaDB Server ==="
apt-get update -y
apt-get install -y mariadb-server
systemctl enable --now mariadb

echo "=== Creating unturned database and user ==="
mariadb -e "CREATE DATABASE IF NOT EXISTS unturned; CREATE USER IF NOT EXISTS 'unturned'@'localhost' IDENTIFIED BY 'CircuitVerseUnturned2026!'; GRANT ALL PRIVILEGES ON unturned.* TO 'unturned'@'localhost'; FLUSH PRIVILEGES;"
echo "=== MariaDB Ready ==="
