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
logging.basicConfig(level=logging.INFO)
import discord
# DO NOT OVERRIDE max_dave_protocol_version! Let native davey handle it!
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
        conn = getattr(vc, "_connection", None)
        print("dave_protocol_version:", getattr(conn, "dave_protocol_version", None), flush=True)
        print("can_encrypt:", getattr(conn, "can_encrypt", None), flush=True)
        print("dave_session:", getattr(conn, "dave_session", None), flush=True)
        
        # Test playing audio
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
        print(">>> PLAYING STREAM! <<<", flush=True)
        for i in range(5):
            await asyncio.sleep(1)
            print(f"[{i+1}s] is_playing: {vc.is_playing()}, can_encrypt: {getattr(conn, 'can_encrypt', None)}", flush=True)
            
        await vc.disconnect(force=True)
        print(">>> DISCONNECTED CLEANLY <<<", flush=True)
    except Exception as e:
        print(f">>> EXCEPTION: {type(e)} {e} <<<", flush=True)
        import traceback
        traceback.print_exc()
    await client.close()
    os._exit(0)

client.run(cfg['bot_token'])
"""
    sftp = client.open_sftp()
    with sftp.open("/tmp/test_native_davey.py", "w") as f:
        f.write(code)
    sftp.close()

    stdin, stdout, stderr = client.exec_command("/home/ubuntu/CV-Radio-Helper/venv/bin/python3 /tmp/test_native_davey.py", timeout=30)
    print("STDOUT:\n", stdout.read().decode())
    print("STDERR:\n", stderr.read().decode())
finally:
    client.close()
