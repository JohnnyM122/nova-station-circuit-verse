import paramiko
import sys

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    code = sys.stdin.read()
    sftp = client.open_sftp()
    with sftp.open("/tmp/exec_temp.py", "w") as f:
        f.write(code)
    sftp.close()

    stdin, stdout, stderr = client.exec_command("sudo python3 /tmp/exec_temp.py")
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
finally:
    client.close()
