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
import logging
logging.basicConfig(level=logging.DEBUG)
import discord
from discord.voice_state import VoiceConnectionState

VoiceConnectionState.max_dave_protocol_version = property(lambda self: 0)

import json, asyncio, os

with open('/home/ubuntu/CV-Radio-Helper/config.json') as f:
    cfg = json.load(f)

client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    print(">>> ON READY CALLED <<<", flush=True)
    guild = client.get_guild(int(cfg['guild_id']))
    channel = guild.get_channel(1564605316849733726)
    print(">>> CALLING channel.connect <<<", flush=True)
    try:
        vc = await asyncio.wait_for(channel.connect(timeout=10.0, reconnect=False), timeout=12.0)
        print(">>> CONNECTED TO VC SUCCESSFULLY! <<<", flush=True)
        print("is_connected:", vc.is_connected(), flush=True)
        await asyncio.sleep(2)
        await vc.disconnect(force=True)
    except Exception as e:
        print(f">>> EXCEPTION IN CONNECT: {type(e)} {e} <<<", flush=True)
    await client.close()
    os._exit(0)

client.run(cfg['bot_token'])
"""
    sftp = client.open_sftp()
    with sftp.open("/tmp/debug_vc.py", "w") as f:
        f.write(code)
    sftp.close()

    stdin, stdout, stderr = client.exec_command("/home/ubuntu/CV-Radio-Helper/venv/bin/python3 /tmp/debug_vc.py", timeout=30)
    print("STDOUT:\n", stdout.read().decode())
    print("STDERR:\n", stderr.read().decode())
finally:
    client.close()
