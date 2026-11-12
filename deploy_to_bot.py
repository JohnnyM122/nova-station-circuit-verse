import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"

files_to_copy = [
    ("local_unturned_cog.py", "/home/ubuntu/CV-Nova-Helper/cogs/unturned.py"),
    ("local_support_tickets.py", "/home/ubuntu/CV-Nova-Helper/cogs/support_tickets.py"),
    ("local_pz_cog.py", "/home/ubuntu/CV-Nova-Helper/cogs/project_zomboid.py"),
    ("local_bot_config.json", "/home/ubuntu/CV-Nova-Helper/config.json"),
]

for src, dst in files_to_copy:
    print(f"Uploading {src} to {dst}...")
    res = subprocess.run([
        "scp", "-i", key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        src,
        f"ubuntu@87.99.133.221:{dst}"
    ], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        print(f"Error uploading {src}: {res.stderr}")
    else:
        print(f"Uploaded {src} successfully.")

print("Restarting cv-nova-helper.service...")
res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "ubuntu@87.99.133.221",
    "sudo systemctl restart cv-nova-helper.service && sudo systemctl is-active cv-nova-helper.service"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Restart output:\n", res.stdout)
if res.stderr:
    print("Restart stderr:\n", res.stderr)
