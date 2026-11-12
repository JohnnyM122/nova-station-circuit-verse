import urllib.request
import re

try:
    req = urllib.request.Request("https://restoremonarchy.com/plugins", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req).read().decode("utf-8", errors="ignore")
    plugins = re.findall(r'<a[^>]+href=["\'](/plugins/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL)
    print(f"RestoreMonarchy plugins ({len(plugins)}):")
    for link, name in plugins[:30]:
        clean_name = re.sub('<[^<]+?>', '', name).strip()
        if clean_name:
            print(f"- {clean_name}: {link}")
except Exception as e:
    print(f"Error fetching RestoreMonarchy: {e}")
