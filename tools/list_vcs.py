import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    code = """
import sys, json, discord, asyncio

with open('/home/ubuntu/CV-Radio-Helper/config.json') as f:
    cfg = json.load(f)

client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    guild = client.get_guild(int(cfg['guild_id']))
    print(f"Connected to guild: {guild.name}")
    print("Voice channels:")
    for ch in guild.voice_channels:
        print(f" - {ch.name} (id: {ch.id})")
    await client.close()

client.run(cfg['bot_token'])
"""
    sftp = client.open_sftp()
    with sftp.open("/tmp/list_vcs.py", "w") as f:
        f.write(code)
    sftp.close()

    stdin, stdout, stderr = client.exec_command("/home/ubuntu/CV-Radio-Helper/venv/bin/python3 /tmp/list_vcs.py")
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERR:", err)
finally:
    client.close()
