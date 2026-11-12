import subprocess
import json

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

BASH_SCRIPT = r"""
echo '=== 1. SYSTEM UPTIME AND LOAD AVERAGE ==='
uptime
echo ''
echo '=== 2. CPU UTILIZATION AND SPECS ==='
lscpu | grep -E "Model name|Socket|Thread|NUMA|CPU\(s\):"
echo ''
top -bn1 | head -n 5
echo ''
echo '=== 3. MEMORY (RAM AND SWAP) USAGE ==='
free -h
echo ''
echo '=== 4. DISK STORAGE AND FILESYSTEM USAGE ==='
df -h -x tmpfs -x devtmpfs -x squashfs
echo ''
echo '=== 5. GAME SERVERS AND CRITICAL DAEMONS STATUS ==='
services=(
    "novastation.service"
    "minecraft.service"
    "project-zomboid.service"
    "unturned.service"
    "cv-panel.service"
    "cv-nova-helper.service"
    "cv-radio-helper.service"
    "zomboid-panel.service"
    "mariadb.service"
    "nginx.service"
    "docker.service"
)
for s in "${services[@]}"; do
    state=$(systemctl is-active "$s" 2>/dev/null || echo "inactive")
    sub=$(systemctl show -p SubState --value "$s" 2>/dev/null || echo "unknown")
    printf "%-28s : %-10s (%s)\n" "$s" "$state" "$sub"
done
echo ''
echo '=== 6. DOCKER CONTAINERS (AZURACAST) ==='
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ''
echo '=== 7. TOP 10 PROCESSES BY RAM AND CPU ==='
ps aux --sort=-%mem | head -n 12
"""

cmd = [
    "ssh", "-i", KEY,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    HOST,
    "bash -s"
]

clean_script = BASH_SCRIPT.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
res = subprocess.run(cmd, input=clean_script, capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:", res.stderr.decode("utf-8", errors="replace"))
