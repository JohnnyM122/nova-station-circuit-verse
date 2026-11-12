import json

for fname in ["bot_config.json", "config_vps.json", "local_bot_config.json"]:
    with open(fname, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "mc_server" in data:
        data["mc_server"]["host"] = "127.0.0.1"
        data["mc_server"]["ssh_host"] = "127.0.0.1"

    if "pz_server" in data:
        data["pz_server"]["host"] = "127.0.0.1"

    if "unturned_server" in data:
        data["unturned_server"]["host"] = "127.0.0.1"
        data["unturned_server"]["ssh_host"] = "127.0.0.1"

    with open(fname, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Updated {fname} with 127.0.0.1 hosts.")
