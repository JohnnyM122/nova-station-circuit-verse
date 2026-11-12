import subprocess, os

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'

# Fetch discord_audit_logger.py to local
cmd = ['scp', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'root@{DED_IP}:/home/ubuntu/CV-Nova-Helper/cogs/discord_audit_logger.py', 'c:\\Users\SysAdmin\\Documents\\nova-station-circuit-verse-main\\local_audit_logger.py']
res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
print("Fetch audit logger:", res.returncode)
