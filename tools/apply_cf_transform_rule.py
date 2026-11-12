import urllib.request
import urllib.error
import json

import os
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ZONE_ID = "4eebb417a420327c172f337afd14b988"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "rules": [
        {
            "expression": '(http.host eq "zcp.circuitverse.online")',
            "description": "Allow embedding ZCP in Circuit Verse Panel",
            "action": "rewrite",
            "action_parameters": {
                "headers": {
                    "X-Frame-Options": {
                        "operation": "remove"
                    },
                    "Content-Security-Policy": {
                        "operation": "set",
                        "value": "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob: ws: wss:; frame-ancestors 'self' https://panel.circuitverse.online https://circuitverse.online;"
                    }
                }
            }
        }
    ]
}

url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/rulesets/phases/http_response_headers_transform/entrypoint"
req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")

try:
    with urllib.request.urlopen(req) as resp:
        result = json.load(resp)
        print("SUCCESS:", json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode())
