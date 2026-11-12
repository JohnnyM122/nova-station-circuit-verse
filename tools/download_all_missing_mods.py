import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo -u pz /home/pz/steamcmd/steamcmd.sh +force_install_dir /home/pz/pz-server +login anonymous +workshop_download_item 108600 3745718141 validate +workshop_download_item 108600 3811752923 validate +workshop_download_item 108600 3787266180 validate +workshop_download_item 108600 3817590841 validate +quit"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
