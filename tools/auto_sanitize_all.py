import re
import os

token_patterns = [
    re.compile(r'gh[pous]_[a-zA-Z0-9]{36}'),
    re.compile(r'cfat_[a-zA-Z0-9_\-]{40,}'),
    re.compile(r'MTU[a-zA-Z0-9_\-\.]{50,}')
]

import subprocess
files = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()

for fpath in files:
    if not os.path.exists(fpath):
        continue
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        orig = content
        
        # Replace tokens
        for pat in token_patterns:
            if fpath.endswith('.json'):
                content = pat.sub('REDACTED_SECRET_ENV', content)
            else:
                content = pat.sub('os.environ.get("API_SECRET_TOKEN", "REDACTED")', content)
                
        if content != orig:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Sanitized: {fpath}")
    except Exception as e:
        print(f"Error {fpath}: {e}")
