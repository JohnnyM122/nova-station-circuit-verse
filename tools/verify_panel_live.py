import urllib.request

req = urllib.request.Request("https://panel.circuitverse.online/", headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print("Status:", resp.status)
        print("Has pz-tab-mods:", "pz-tab-mods" in html)
        print("Has Mod Manager & Configurator:", "Mod Manager &amp; Configurator" in html or "Mod Manager & Configurator" in html)
        print("Has pz-ini-editor:", "pz-ini-editor" in html)
        print("Has pz-sandbox-editor:", "pz-sandbox-editor" in html)
except Exception as e:
    print("Error:", e)
