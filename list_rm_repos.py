import urllib.request
import json

req = urllib.request.Request(
    "https://api.github.com/users/RestoreMonarchy/repos?per_page=100",
    headers={"User-Agent": "CircuitVerse/1.0"}
)
try:
    with urllib.request.urlopen(req) as resp:
        repos = json.loads(resp.read().decode())
        print(f"Total RestoreMonarchy repos: {len(repos)}")
        for r in sorted(repos, key=lambda x: x["name"]):
            print(f"- {r['name']}: {r.get('description', '')}")
except Exception as e:
    print(f"Error: {e}")
