import urllib.request
import urllib.parse
import json
import re

query = 'cloning'
url = f"https://www.paradisestation.org/wiki/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=1&format=json"
req = urllib.request.Request(url, headers={'User-Agent': 'NovaStation13Bot/1.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

print("Search results:", data)
if len(data) > 1 and data[1]:
    title = data[1][0]
    link = data[3][0]
    p_url = f"https://www.paradisestation.org/wiki/api.php?action=parse&page={urllib.parse.quote(title)}&redirects=1&prop=wikitext&format=json"
    p_req = urllib.request.Request(p_url, headers={'User-Agent': 'NovaStation13Bot/1.0'})
    with urllib.request.urlopen(p_req) as p_resp:
        p_data = json.loads(p_resp.read().decode('utf-8'))
        raw_wiki = p_data.get('parse', {}).get('wikitext', {}).get('*', '')

        # Clean wikitext
        clean = re.sub(r'\{\{[^\}]+\}\}', '', raw_wiki)
        clean = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean)
        clean = re.sub(r"'''?", '', clean)
        clean = re.sub(r'==+[^=]+==+', '', clean)
        clean = '\n'.join([line.strip() for line in clean.splitlines() if line.strip() and not line.startswith('|')])
        print(f"Parsed {title} ({link}):\n", clean[:350])
