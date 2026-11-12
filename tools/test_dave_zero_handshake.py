import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

test_script = """
import sys
sys.path.insert(0, '/home/ubuntu/CV-Nova-Helper')
import discord, json, asyncio
from discord.voice_state import VoiceConnectionState
from discord.gateway import DiscordVoiceWebSocket

session_desc_data = {}
orig_poll_event = DiscordVoiceWebSocket.poll_event

async def _tracked_poll_event(self):
    msg = await orig_poll_event(self)
    if self._connection.dave_protocol_version is not None:
        session_desc_data['dave_protocol_version'] = self._connection.dave_protocol_version
        session_desc_data['mode'] = self._connection.mode
    return msg

DiscordVoiceWebSocket.poll_event = _tracked_poll_event

# Set max_dave_protocol_version to 0
VoiceConnectionState.max_dave_protocol_version = property(lambda self: 0)

with open('/home/ubuntu/CV-Nova-Helper/config.json') as f:
    cfg = json.load(f)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(int(cfg['guild_id']))
    channel = guild.get_channel(1567466261611548762)
    print("Connecting with max_dave = 0...")
    vc = await channel.connect(timeout=10.0, reconnect=True, self_deaf=True)
    conn = vc._connection
    print("Connected!")
    print("  Negotiated dave_protocol_version:", conn.dave_protocol_version)
    print("  Mode:", conn.mode)
    print("  has_nacl:", discord.voice_client.has_nacl)
    print("  is_connected:", vc.is_connected())
    
    await asyncio.sleep(1)
    await vc.disconnect(force=True)
    print("Disconnected cleanly!")
    import os
    os._exit(0)

client.run(cfg['bot_token'])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=test_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:\n", res.stderr.decode("utf-8", errors="replace"))
