import urllib.request
import urllib.parse
import json

query = 'albert einstein'
url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
req = urllib.request.Request(url, headers={'User-Agent': 'NovaStation13Bot/1.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("Abstract:", data.get('Abstract')[:200])
        print("Source:", data.get('AbstractURL'))
except Exception as e:
    print("Error:", e)
