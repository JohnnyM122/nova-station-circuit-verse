import urllib.request
import re
import json

url = "https://ldm-community.github.io/pluginlist/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8", errors="ignore")

# Find all links and plugin items
items = re.findall(r'<tr[^>]*>.*?</tr>', html, re.DOTALL)
print(f"Found {len(items)} table rows.")
if not items:
    # Look for lists or cards
    items = re.findall(r'<li[^>]*>.*?</li>', html, re.DOTALL)
    print(f"Found {len(items)} list items.")

links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
print(f"Total links: {len(links)}")
gh_links = [l for l in set(links) if "github.com" in l]
for l in sorted(gh_links)[:50]:
    print(l)
