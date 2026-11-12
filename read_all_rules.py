import json
import urllib.request

with open('cv_panel_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

token = cfg['discord_bot_token']
ch_id = '1566600269649678467'

req = urllib.request.Request(
    f'https://discord.com/api/v10/channels/{ch_id}/messages?limit=15',
    headers={'Authorization': f'Bot {token}', 'User-Agent': 'CircuitVerseHelper/1.0'}
)

with urllib.request.urlopen(req) as resp:
    messages = json.loads(resp.read().decode('utf-8'))

for m in reversed(messages):
    print("=" * 60)
    print(f"MESSAGE ID: {m['id']}")
    print(m.get('content'))
