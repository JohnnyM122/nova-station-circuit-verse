import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    cmd = '/home/ubuntu/CV-Nova-Helper/venv/bin/yt-dlp -x --audio-format mp3 --audio-quality 192K -o "/tmp/test_sc.%(ext)s" "https://soundcloud.com/nocopyrightsounds/1aevne-baby-murcielaga-i-just"'
    stdin, stdout, stderr = client.exec_command(cmd)
    print("STDOUT:\n", stdout.read().decode())
    print("STDERR:\n", stderr.read().decode())
finally:
    client.close()
