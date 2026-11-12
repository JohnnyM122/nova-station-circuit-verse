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
    
    files_to_clean = [
        "/home/ubuntu/CV-Radio-Helper/main.py",
        "/home/ubuntu/CV-Radio-Helper/cogs/radio.py",
        "/home/ubuntu/CV-Nova-Helper/main.py",
        "/home/ubuntu/CV-Nova-Helper/cogs/radio.py",
    ]
    
    for fpath in files_to_clean:
        try:
            with sftp.open(fpath, "r") as f:
                content = f.read().decode("utf-8")
            
            orig = content
            # Remove max_dave_protocol_version monkey patches
            lines = content.splitlines(keepends=True)
            new_lines = []
            for line in lines:
                if "max_dave_protocol_version" in line:
                    continue
                new_lines.append(line)
            content = "".join(new_lines)
            
            if content != orig:
                with sftp.open(fpath, "w") as f:
                    f.write(content)
                print(f"Cleaned max_dave_protocol_version from {fpath}")
            else:
                print(f"No monkey patch found in {fpath}")
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
            
    sftp.close()

    # Restart both bots
    cmd = "sudo systemctl restart cv-radio-helper.service cv-nova-helper.service && sleep 3 && systemctl is-active cv-radio-helper.service cv-nova-helper.service"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("Services status:\n", stdout.read().decode())
    if stderr:
        print("STDERR:\n", stderr.read().decode())

finally:
    client.close()
