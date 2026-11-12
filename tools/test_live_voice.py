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
import sys, json, discord, asyncio, os
from discord.voice_state import VoiceConnectionState

# Disable DAVE protocol
VoiceConnectionState.max_dave_protocol_version = property(lambda self: 0)

with open('/home/ubuntu/CV-Radio-Helper/config.json') as f:
    cfg = json.load(f)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name} ({client.user.id})")
    guild = client.get_guild(int(cfg['guild_id']))
    channel = guild.get_channel(1564605316849733726) # General VC 1
    print(f"Joining {channel.name}...")
    
    vc = await channel.connect(timeout=15.0, reconnect=True, self_deaf=False)
    conn = getattr(vc, "_connection", None)
    print("Voice connected!")
    print("Mode:", getattr(conn, "mode", None))
    print("DAVE version:", getattr(conn, "dave_protocol_version", None))
    print("can_encrypt:", getattr(conn, "can_encrypt", None))
    
    stream_url = "http://127.0.0.1/listen/circuit_verse_radio/radio.mp3"
    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            stream_url,
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            options='-vn -ar 48000 -ac 2 -f s16le'
        ),
        volume=0.8
    )
    vc.play(source)
    print("Playback initiated, vc.is_playing():", vc.is_playing())
    
    for sec in range(5):
        await asyncio.sleep(1)
        seq = getattr(vc, "sequence", None)
        ts = getattr(vc, "timestamp", None)
        print(f"Sec {sec+1}: playing={vc.is_playing()}, seq={seq}, ts={ts}")
    
    print("Voice test successful! Stopping playback and disconnecting...")
    vc.stop()
    await vc.disconnect(force=True)
    await client.close()

client.run(cfg['bot_token'])
"""
    sftp = client.open_sftp()
    with sftp.open("/tmp/test_vc_stream.py", "w") as f:
        f.write(code)
    sftp.close()

    # Note: stop cv-radio-helper temporarily so client tokens don't conflict
    cmd = """
    sudo systemctl stop cv-radio-helper
    /home/ubuntu/CV-Radio-Helper/venv/bin/python3 /tmp/test_vc_stream.py
    sudo systemctl start cv-radio-helper
    """
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERR:", err)
finally:
    client.close()
