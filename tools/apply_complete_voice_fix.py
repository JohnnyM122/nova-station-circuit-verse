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
    
    # 1. Update CV-Radio-Helper main.py
    with sftp.open("/home/ubuntu/CV-Radio-Helper/main.py", "r") as f:
        radio_main = f.read().decode("utf-8")
    
    if "max_dave_protocol_version" not in radio_main:
        idx = radio_main.find("import discord")
        inject = "import discord\nfrom discord.voice_state import VoiceConnectionState\nVoiceConnectionState.max_dave_protocol_version = property(lambda self: 0)\n"
        radio_main = radio_main.replace("import discord\n", inject, 1)
        with sftp.open("/home/ubuntu/CV-Radio-Helper/main.py", "w") as f:
            f.write(radio_main)
        print("Patched CV-Radio-Helper/main.py with max_dave_protocol_version=0")

    # 2. Update CV-Nova-Helper main.py
    with sftp.open("/home/ubuntu/CV-Nova-Helper/main.py", "r") as f:
        nova_main = f.read().decode("utf-8")
    
    if "max_dave_protocol_version" not in nova_main:
        idx = nova_main.find("import discord")
        inject = "import discord\nfrom discord.voice_state import VoiceConnectionState\nVoiceConnectionState.max_dave_protocol_version = property(lambda self: 0)\n"
        nova_main = nova_main.replace("import discord\n", inject, 1)
        with sftp.open("/home/ubuntu/CV-Nova-Helper/main.py", "w") as f:
            f.write(nova_main)
        print("Patched CV-Nova-Helper/main.py with max_dave_protocol_version=0")

    # 3. Update CV-Radio-Helper config.json
    with sftp.open("/home/ubuntu/CV-Radio-Helper/config.json", "r") as f:
        import json
        cfg = json.loads(f.read().decode("utf-8"))
    
    cfg["discord"]["voice_channel_id"] = 1564605316849733726
    cfg["radio"]["voice_channel_id"] = 1564605316849733726
    with sftp.open("/home/ubuntu/CV-Radio-Helper/config.json", "w") as f:
        f.write(json.dumps(cfg, indent=2))
    print("Updated CV-Radio-Helper config.json voice_channel_id to General VC 1 (1564605316849733726)")

    sftp.close()

    # Restart both services
    cmd = "sudo systemctl restart cv-radio-helper.service cv-nova-helper.service && sleep 4 && systemctl is-active cv-radio-helper.service cv-nova-helper.service"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("Restart result:\n", stdout.read().decode())
    if stderr:
        print("STDERR:\n", stderr.read().decode())

finally:
    client.close()
