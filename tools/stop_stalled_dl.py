import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    cmd = 'sudo pkill -9 -f download_ncs_batch; sudo pkill -9 -f yt-dlp; sleep 1; ps aux | grep download_ncs | grep -v grep || echo "Downloader stopped"'
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode())
finally:
    client.close()
