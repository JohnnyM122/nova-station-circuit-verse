import json, urllib.request, time

with open('bot_config.json', 'r') as bcf:
    bcfg = json.load(bcf)

targets = [
    ('nova-station-13', 174034628, bcfg['hetzner_api_token_ns13']),
    ('circuit-verse-mc', 174435350, 'kTMcuBEYA0T2sQrxxkfglRbcDthMF6tvghmAKKNUFehpjYOsEjygk4TnroXxKhwo')
]

for name, sid, token in targets:
    # 1. Disable protection
    prot_url = f'https://api.hetzner.cloud/v1/servers/{sid}/actions/change_protection'
    data = json.dumps({'delete': False, 'rebuild': False}).encode('utf-8')
    req = urllib.request.Request(prot_url, data=data, headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Disabled deletion protection on {name}")
    except Exception as e:
        print(f"Error changing protection on {name}: {e}")

time.sleep(2)

for name, sid, token in targets:
    # 2. Delete server
    del_url = f'https://api.hetzner.cloud/v1/servers/{sid}'
    req = urllib.request.Request(del_url, method='DELETE', headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"Terminated {name} (ID: {sid}): {data.get('action', {}).get('status')}")
    except Exception as e:
        print(f"Error deleting {name}: {e}")
