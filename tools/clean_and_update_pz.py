import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

remote_script = """
set -e
echo "=== 1. Cleaning corrupted delta cache and normal.txt ==="
sudo rm -rf /home/pz/pz-server/steamapps/downloading/*
sudo rm -f /home/pz/pz-server/media/scripts/generated/items/normal.txt

echo "=== 2. Running steamcmd validation and update ==="
sudo -u pz /home/pz/steamcmd/steamcmd.sh +force_install_dir /home/pz/pz-server +login anonymous +app_update 380870 validate +quit

echo "=== 3. Checking updated buildid ==="
grep -E '(buildid|LastUpdated)' /home/pz/pz-server/steamapps/appmanifest_380870.acf
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, remote_script], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
