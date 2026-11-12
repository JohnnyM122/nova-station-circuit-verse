import paramiko
import os

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    sftp = client.open_sftp()
    local_file = r"tools\download_ncs_batch.py"
    remote_file = "/home/ubuntu/download_ncs_batch.py"
    sftp.put(local_file, remote_file)
    sftp.chmod(remote_file, 0o755)
    print("Uploaded download_ncs_batch.py successfully!")
    sftp.close()

    # Launch in background with nohup and redirect output to /home/ubuntu/ncs_download.log
    cmd = "sudo nohup /home/ubuntu/CV-Nova-Helper/venv/bin/python3 /home/ubuntu/download_ncs_batch.py > /home/ubuntu/ncs_download.log 2>&1 &"
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout.channel.recv_exit_status()
    print("Started background download process!")

    # Check that it is running
    stdin, stdout, stderr = client.exec_command("ps aux | grep download_ncs_batch | grep -v grep; head -n 5 /home/ubuntu/ncs_download.log")
    print(stdout.read().decode())
finally:
    client.close()
