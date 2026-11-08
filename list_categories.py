import discord
import json

CONFIG_PATH = "/home/ubuntu/CV-Nova-Helper/config.json"
with open(CONFIG_PATH) as f:
    cfg = json.load(f)

token = cfg.get("bot_token")
client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    g = client.get_guild(1564605314752585797)
    cats = sorted(g.categories, key=lambda c: c.position)
    print("=== ALL CATEGORIES IN ORDER ===")
    for c in cats:
        print(f"Pos {c.position:2d} | {c.name} (ID: {c.id})")
    await client.close()

client.run(token)
