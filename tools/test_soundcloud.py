import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    cmd = '/home/ubuntu/CV-Nova-Helper/venv/bin/yt-dlp --flat-playlist --dump-single-json "https://soundcloud.com/nocopyrightsounds/tracks" | head -n 30'
    stdin, stdout, stderr = client.exec_command(cmd)
    print("STDOUT preview:\n", stdout.read().decode()[:500])
    print("STDERR:\n", stderr.read().decode())
finally:
    client.close()
