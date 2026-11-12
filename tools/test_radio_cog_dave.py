import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

test_script = """
import sys
sys.path.insert(0, '/home/ubuntu/CV-Nova-Helper')
import discord, json, asyncio, logging
logging.basicConfig(level=logging.INFO)
import cogs.radio # loads monkey patches

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
    ds = getattr(conn, "dave_session", None)
    print("DAVE session object:", ds)
    print("DAVE protocol version:", getattr(conn, "dave_protocol_version", None))
    for i in range(5):
        await asyncio.sleep(1)
        print(f"[{i+1}s] conn.can_encrypt: {getattr(conn, 'can_encrypt', None)}, ds.ready: {getattr(ds, 'ready', None)}, ds.can_encrypt: {getattr(ds, 'can_encrypt', None)}, ds.status: {getattr(ds, 'status', None)}")
    await vc.disconnect(force=True)
    await client.close()

client.run(cfg['bot_token'])
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=test_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:\n", res.stderr.decode("utf-8", errors="replace"))
