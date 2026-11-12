import urllib.request
import re

try:
    req = urllib.request.Request("https://iceplugins.github.io/", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req).read().decode("utf-8", errors="ignore")
    links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
    gh_links = [l for l in set(links) if "github.com" in l]
    print(f"IcePlugins links ({len(gh_links)}):")
    for l in sorted(gh_links):
        print(l)
except Exception as e:
    print(f"Error fetching IcePlugins: {e}")
