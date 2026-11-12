import urllib.request
import re

url = "https://restoremonarchy.com/plugins"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
html = urllib.request.urlopen(req).read().decode("utf-8")

# Parse blocks
blocks = re.findall(r'<div class="col-12 col-md-6 col-xl-4">(.*?)</div>\s*</div>\s*</div>\s*</div>', html, re.DOTALL)
free_plugins = []
for b in blocks:
    title_m = re.search(r'<h5[^>]*>(.*?)</h5>', b)
    title = re.sub('<[^<]+?>', '', title_m.group(1)).strip() if title_m else "Unknown"
    is_free = "Free" in b
    link_m = re.search(r'href=["\'](/plugins/[^"\']+)["\']', b)
    link = link_m.group(1) if link_m else ""
    if is_free:
        free_plugins.append((title, link))

print(f"FREE PLUGINS ({len(free_plugins)}):")
for t, l in free_plugins:
    print(f"- **{t}**: https://restoremonarchy.com{l}")
