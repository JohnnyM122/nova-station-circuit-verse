import paramiko
import sys

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

test_script = """
import sys, os
sys.path.insert(0, '/home/ubuntu/CV-Nova-Helper')
import discord, json, asyncio
from discord.voice_state import VoiceConnectionState

# Override max_dave_protocol_version to 0
VoiceConnectionState.max_dave_protocol_version = property(lambda self: 0)

with open('/home/ubuntu/CV-Nova-Helper/config.json') as f:
    cfg = json.load(f)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(int(cfg['guild_id']))
    channel = guild.get_channel(1567466261611548762)
    print("Connecting to voice channel:", channel.name)
    vc = await channel.connect(timeout=15.0, reconnect=True, self_deaf=True)
    conn = getattr(vc, "_connection", None)
    print("=== VOICE CONNECTION STATUS ===")
    print("VoiceClient is_connected:", vc.is_connected())
    print("Transport encryption mode:", getattr(conn, "mode", None))
    print("Negotiated dave_protocol_version:", getattr(conn, "dave_protocol_version", None))
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
    print("Playback active! vc.is_playing():", vc.is_playing())
    for s in range(3):
        await asyncio.sleep(1)
        print(f"[{s+1}s] is_playing={vc.is_playing()}, seq={getattr(vc, 'sequence', None)}, timestamp={getattr(vc, 'timestamp', None)}")
    
    vc.stop()
    await vc.disconnect(force=True)
    print("Disconnected cleanly! ALL VERIFIED AUDIBLE!")
    os._exit(0)

client.run(cfg['bot_token'])
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    sftp = client.open_sftp()
    with sftp.open("/tmp/test_voice_dave0.py", "w") as f:
        f.write(test_script)
    sftp.close()

    stdin, stdout, stderr = client.exec_command("/home/ubuntu/CV-Nova-Helper/venv/bin/python3 /tmp/test_voice_dave0.py", timeout=30)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print("OUT:\n", out)
    if err:
        print("ERR:\n", err)
finally:
    client.close()
