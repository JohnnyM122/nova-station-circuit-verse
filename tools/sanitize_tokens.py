import re

files_to_clean = [
    "apply_cf_dns.py",
    "cv_panel_config.json",
    "tools/apply_cf_transform_rule.py",
    "tools/read_logs.py",
    "tools/create_and_order_country_roles.py",
    "tools/delete_csrp_channels.py",
    "tools/list_low_roles.py",
    "tools/position_country_roles.py",
    "tools/seed_new_channels.py"
]

# Patterns for Discord token and Cloudflare token
# Cloudflare tokens are 40 chars alphanumeric
# Discord tokens are MTU...

cf_pattern = re.compile(r'["\']([a-zA-Z0-9_\-]{40})["\']')
discord_pattern = re.compile(r'["\'](MTU[a-zA-Z0-9_\-\.]{50,})["\']')

for fpath in files_to_clean:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        orig = content
        if fpath.endswith(".json"):
            # in cv_panel_config.json
            content = re.sub(r'"api_token":\s*"[^"]+"', '"api_token": "CLOUDFLARE_API_TOKEN_ENV"', content)
        else:
            content = discord_pattern.sub('os.environ.get("DISCORD_BOT_TOKEN", "")', content)
            content = cf_pattern.sub('os.environ.get("CLOUDFLARE_API_TOKEN", "")', content)

        if content != orig:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Sanitized: {fpath}")
        else:
            print(f"No match in: {fpath}")
    except Exception as e:
        print(f"Error {fpath}: {e}")
