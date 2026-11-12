import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    # Test 1: android client
    cmd1 = '/home/ubuntu/CV-Nova-Helper/venv/bin/yt-dlp --extractor-args "youtube:player_client=android" -x --audio-format mp3 -o "/tmp/test_android.%(ext)s" "https://www.youtube.com/watch?v=BZKwsPIhVO8"'
    stdin, stdout, stderr = client.exec_command(cmd1)
    print("Test 1 Android client:\n", stdout.read().decode())
    print("Stderr 1:\n", stderr.read().decode())
finally:
    client.close()
