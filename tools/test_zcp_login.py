import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

SCRIPT = """
import urllib.request
import json

data = json.dumps({'username': 'cv_admin', 'password': 'CvZcpAdmin!24c4cae4a15d11b801b487c8', 'rememberMe': True}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:3001/api/auth/login', data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as resp:
        print('STATUS:', resp.status)
        print('BODY:', resp.read().decode())
        print('COOKIES:', resp.headers.get_all('Set-Cookie'))
except Exception as e:
    print('ERROR:', e)
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "python3 -"]
res = subprocess.run(cmd, input=SCRIPT.encode("utf-8"), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:", res.stderr.decode("utf-8", errors="replace"))
