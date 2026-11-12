import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

test_script = """
import discord, json, asyncio, logging
logging.basicConfig(level=logging.INFO)

with open('/home/ubuntu/CV-Nova-Helper/config.json') as f:
    cfg = json.load(f)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(int(cfg['guild_id']))
    # Test channel: General VC 3 (empty)
    channel = guild.get_channel(1567466261611548762)
    print(f"Connecting to test channel: {channel.name}...")
    try:
        vc = await channel.connect(timeout=15.0, reconnect=True, self_deaf=True)
        print("Connected to voice successfully!")
        print("VoiceClient is_connected:", vc.is_connected())
        
        conn = getattr(vc, "_connection", None)
        print("DAVE protocol version:", getattr(conn, "dave_protocol_version", None))
        print("can_encrypt:", getattr(conn, "can_encrypt", None))
        
        # Stream URL
        stream_url = "http://127.0.0.1/listen/circuit_verse_radio/radio.mp3"
        print("Creating FFmpegPCMAudio source...")
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                stream_url,
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options='-vn'
            ),
            volume=0.8
        )
        
        print("Starting playback...")
        vc.play(source)
        print("vc.is_playing():", vc.is_playing())
        
        for i in range(5):
            await asyncio.sleep(1)
            print(f"Playing check {i+1}s: is_playing={vc.is_playing()}, can_encrypt={getattr(conn, 'can_encrypt', None)}")
        
        vc.stop()
        await vc.disconnect(force=True)
        print("Disconnected cleanly after successful test!")
    except Exception as e:
        print("Voice test failed with exception:", type(e), e)
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

client.run(cfg['bot_token'])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=test_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
