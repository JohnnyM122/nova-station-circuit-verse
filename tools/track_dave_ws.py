import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

test_script = """
import sys
sys.path.insert(0, '/home/ubuntu/CV-Nova-Helper')
import discord, json, asyncio, struct
from discord.gateway import DiscordVoiceWebSocket

ws_events = []
binary_frames = []

orig_received_binary_message = DiscordVoiceWebSocket.received_binary_message
async def track_binary(self, msg: bytes):
    op = msg[2] if len(msg) > 2 else -1
    binary_frames.append((len(msg), op, msg[:10]))
    print(f"--> WS BINARY FRAME: len={len(msg)}, op={op}")
    await orig_received_binary_message(self, msg)

DiscordVoiceWebSocket.received_binary_message = track_binary

with open('/home/ubuntu/CV-Nova-Helper/config.json') as f:
    cfg = json.load(f)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(int(cfg['guild_id']))
    channel = guild.get_channel(1567466261611548762)
    vc = await channel.connect(timeout=15.0, reconnect=True, self_deaf=True)
    conn = getattr(vc, "_connection", None)
    
    print("Voice connection state:")
    print("  mode:", conn.mode)
    print("  dave_ver:", conn.dave_protocol_version)
    print("  has_dave_session:", conn.dave_session is not None)
    
    # Wait up to 5 seconds to see incoming voice ws events
    for s in range(5):
        await asyncio.sleep(1)
        ds = conn.dave_session
        print(f"  [{s+1}s] binary_frames count={len(binary_frames)}, ds.status={getattr(ds, 'status', None)}, ds.can_enc={getattr(ds, 'can_encrypt', None)}, ds.ready={getattr(ds, 'ready', None)}")
    
    await vc.disconnect(force=True)
    await client.close()

client.run(cfg['bot_token'])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=test_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:\n", res.stderr.decode("utf-8", errors="replace"))
