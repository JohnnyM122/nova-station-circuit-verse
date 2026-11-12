import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    sftp = client.open_sftp()
    local_file = r"bot\cogs\radio.py"
    
    # 1. Upload to CV-Nova-Helper
    sftp.put(local_file, "/home/ubuntu/CV-Nova-Helper/cogs/radio.py")
    print("Uploaded to /home/ubuntu/CV-Nova-Helper/cogs/radio.py")
    
    # 2. Upload to CV-Radio-Helper
    sftp.put(local_file, "/home/ubuntu/CV-Radio-Helper/cogs/radio.py")
    print("Uploaded to /home/ubuntu/CV-Radio-Helper/cogs/radio.py")
    sftp.close()

    # Restart services
    cmd = "sudo systemctl restart cv-nova-helper.service cv-radio-helper.service && sleep 4 && systemctl is-active cv-nova-helper.service cv-radio-helper.service"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("Service Status:\n", stdout.read().decode())
    if stderr:
        print("STDERR:\n", stderr.read().decode())
finally:
    client.close()
