import subprocess
import os

SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519_tailscale")
cmd = [
    "ssh",
    "-i",
    SSH_KEY,
    "-o",
    "BatchMode=yes",
    "root@62.238.81.224",
    """python3 -c "
import socket
for port in [25565, 25575, 27015, 27115]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect(('127.0.0.1', port))
        print(f'Port {port} TCP: OPEN on 127.0.0.1')
        s.close()
    except Exception as e:
        print(f'Port {port}: ERROR {e}')
" """,
]

res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
