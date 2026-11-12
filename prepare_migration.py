import subprocess
import os
import json
import time

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DEDICATED_IP = '62.238.81.224'

def run_ssh(host, command, user='root', timeout=20):
    cmd = [
        'ssh',
        '-i', SSH_KEY,
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        f'{user}@{host}',
        command
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, '', str(e)

print("Checking connection to dedicated server...")
rc, out, err = run_ssh(DEDICATED_IP, "test -f /root/.ssh/id_ed25519 || ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519; cat /root/.ssh/id_ed25519.pub")
print(f"Dedicated SSH key result ({rc}):\n{out}\n{err}")
pubkey = out.strip().split('\n')[-1] if out else ''
print(f"Dedicated server pubkey: {pubkey}")

# Now check each old server status and push pubkey to authorized_keys
with open('hetzner_servers.json', 'r') as f:
    config = json.load(f)

for name, sdata in config['servers'].items():
    ip = sdata['ip']
    user = 'ubuntu' if name in ['nova-station-13', 'circuit-verse-general'] else 'root'
    print(f"\nTesting connection to {name} ({user}@{ip})...")
    rc, out, err = run_ssh(ip, "uptime", user=user)
    print(f"{name} uptime: {out} (rc={rc})")
    if rc == 0 and pubkey:
        # Append pubkey to user authorized_keys and root authorized_keys
        add_key_cmd = f"echo '{pubkey}' | sudo tee -a /root/.ssh/authorized_keys > /dev/null && echo '{pubkey}' >> ~/.ssh/authorized_keys"
        rc_k, out_k, err_k = run_ssh(ip, add_key_cmd, user=user)
        print(f"Authorized key added to {name}: rc={rc_k}")
