import json, urllib.request

with open('hetzner_servers.json', 'r') as f:
    config = json.load(f)

with open('bot_config.json', 'r') as bcf:
    bcfg = json.load(bcf)

token_map = {
    'nova-station-13': bcfg.get('hetzner_api_token_ns13', bcfg.get('hetzner_api_token')),
    'circuit-verse-mc': 'kTMcuBEYA0T2sQrxxkfglRbcDthMF6tvghmAKKNUFehpjYOsEjygk4TnroXxKhwo',
    'circuit-verse-pz': 'vVzUe2o1iZ3WSmPgymFTCMnIT0cD4DpzeW0HGj2ZV8EYWVwC6gbUMYiGFPEMX4mW',
    'circuit-verse-unturned': 'yUFP5O7QAVWuH242p3GODbr4OlXDPj0GbGfSWGxIqgsxsiFBk38bVgcaLX4NDC3W',
    'circuit-verse-general': 'eC2dXFl7pE7up7mnlG05srpm2lYbuKcRhdFQUrk6ziv9zT3tcRRczb4nqOVhwUc6'
}

for name, sdata in config['old_cloud_servers'].items():
    sid = sdata['id']
    token = token_map.get(name)
    url = f'https://api.hetzner.cloud/v1/servers/{sid}'
    req = urllib.request.Request(url, method='DELETE', headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            status = data.get('action', {}).get('status')
            print(f"Terminated {name} (ID: {sid}): {status}")
            sdata['status'] = 'terminated'
    except Exception as e:
        print(f"Error terminating {name}: {e}")

with open('hetzner_servers.json', 'w') as f:
    json.dump(config, f, indent=2)
print("Updated hetzner_servers.json")
