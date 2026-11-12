import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

print("Uploading app.py and index.html via scp...")
subprocess.run(["scp", "-i", KEY, "-o", "StrictHostKeyChecking=no", "cv_panel/app.py", f"{HOST}:/tmp/app.py"], check=True)
subprocess.run(["scp", "-i", KEY, "-o", "StrictHostKeyChecking=no", "cv_panel/index.html", f"{HOST}:/tmp/index.html"], check=True)

print("Moving to /opt/cv-panel/ and restarting cv-panel.service...")
cmd = "sudo mv /tmp/app.py /opt/cv-panel/app.py && sudo mv /tmp/index.html /opt/cv-panel/index.html && sudo chown root:root /opt/cv-panel/app.py /opt/cv-panel/index.html && sudo systemctl restart cv-panel.service && sleep 2 && sudo systemctl is-active cv-panel.service"
res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
