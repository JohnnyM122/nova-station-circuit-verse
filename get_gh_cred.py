import subprocess

p = subprocess.Popen(["git", "credential", "fill"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = p.communicate(input="protocol=https\nhost=github.com\n\n")
print("Credential fill result:")
for line in stdout.splitlines():
    if line.startswith("username=") or line.startswith("password="):
        key, val = line.split("=", 1)
        print(f"{key}={val[:4]}...{val[-4:] if len(val) > 8 else ''}")
