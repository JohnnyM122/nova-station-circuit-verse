import urllib.request
import re

url = "https://ldm-community.github.io/pluginlist/"
html = urllib.request.urlopen(url).read().decode("utf-8")

# Extract cards
cards = re.findall(r'<div class="col[^"]*plugin-col[^"]*">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
print(f"Found {len(cards)} plugin cards:")

for c in cards:
    title_m = re.search(r'<h5[^>]*class="card-title[^"]*"[^>]*>(.*?)</h5>', c)
    desc_m = re.search(r'<p[^>]*class="card-text[^"]*"[^>]*>(.*?)</p>', c)
    link_m = re.search(r'href=["\'](https?://[^"\']+)["\']', c)
    title = title_m.group(1).strip() if title_m else "Unknown"
    desc = re.sub('<[^<]+?>', '', desc_m.group(1)).strip() if desc_m else ""
    link = link_m.group(1).strip() if link_m else "No link"
    print(f"- **{title}**: {desc} ({link})")
