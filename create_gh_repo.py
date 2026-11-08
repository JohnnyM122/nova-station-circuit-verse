import subprocess
import urllib.request
import json

# 1. Get credentials
p = subprocess.Popen(["git", "credential", "fill"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, _ = p.communicate(input="protocol=https\nhost=github.com\n\n")
creds = {}
for line in stdout.splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        creds[k] = v

token = creds.get("password")
username = creds.get("username")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "CircuitVerseDeployer/1.0"
}

# 2. Check if repo exists or create it
repo_name = "circuit-verse-unturned"
check_req = urllib.request.Request(f"https://api.github.com/repos/{username}/{repo_name}", headers=headers)
try:
    with urllib.request.urlopen(check_req) as resp:
        print(f"Repo {username}/{repo_name} already exists!")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"Creating private repo {username}/{repo_name}...")
        payload = json.dumps({
            "name": repo_name,
            "private": True,
            "description": "Circuit Verse Unturned Dedicated Server (RocketMod 4.9.3) Configurations, Architecture, Ranks & Plugins",
            "auto_init": False
        }).encode("utf-8")
        create_req = urllib.request.Request("https://api.github.com/user/repos", data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(create_req) as resp:
            data = json.loads(resp.read().decode())
            print(f"SUCCESS: Created private repo {data['full_name']} (private={data['private']})! Clone URL: {data['clone_url']}")
    else:
        print("Error checking repo:", e)
