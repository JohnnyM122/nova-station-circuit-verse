import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "100.100.148.47"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username="SysAdmin", pkey=key, timeout=10)

try:
    cmd = """powershell -Command "
    New-Item -ItemType Directory -Force -Path 'E:\\Backups\\CircuitVerse_20261112'
    New-Item -ItemType Directory -Force -Path 'F:\\Backups\\CircuitVerse_20261112'
    New-Item -ItemType Directory -Force -Path 'G:\\Backups\\CircuitVerse_20261112'
    Get-Item 'E:\\Backups\\CircuitVerse_20261112', 'F:\\Backups\\CircuitVerse_20261112', 'G:\\Backups\\CircuitVerse_20261112'
    "
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print("STDOUT:\n", stdout.read().decode())
    print("STDERR:\n", stderr.read().decode())
finally:
    client.close()
