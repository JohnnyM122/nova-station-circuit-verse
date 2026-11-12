import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    cmd = 'curl -s -X POST http://127.0.0.1:8088/voice/join -H "Content-Type: application/json" -d \'{"channel_id": 1564605316849733726}\''
    stdin, stdout, stderr = client.exec_command(cmd)
    print("Join response:\n", stdout.read().decode())
    
    # Check journalctl
    cmd2 = 'sudo journalctl -u cv-radio-helper -n 15 --no-pager'
    stdin, stdout, stderr = client.exec_command(cmd2)
    print("Bot logs:\n", stdout.read().decode())

finally:
    client.close()
