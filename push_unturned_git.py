import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
repo_dir = r"C:\Users\SysAdmin\Documents\circuit-verse-unturned"

# Download current Commands.dat and Config.txt
res1 = subprocess.run([
    "scp", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243:/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat",
    f"{repo_dir}/CircuitVerse/Server/Commands.dat"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Commands.dat backup:", res1.returncode)

res2 = subprocess.run([
    "scp", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243:/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt",
    f"{repo_dir}/CircuitVerse/Config.txt"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Config.txt backup:", res2.returncode)

res3 = subprocess.run([
    "scp", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243:/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins/RichMessageAnnouncer/RichMessageAnnouncer.configuration.xml",
    f"{repo_dir}/CircuitVerse/Rocket/Plugins/RichMessageAnnouncer/RichMessageAnnouncer.configuration.xml"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("RichMessageAnnouncer backup:", res3.returncode)

# Git commit and push in repo_dir
res4 = subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, text=True)
res5 = subprocess.run(["git", "commit", "-m", "Update MOTD, hiring notice, BattlEye secure setting & whitelist notices"], cwd=repo_dir, capture_output=True, text=True)
print("Git commit:", res5.stdout)
res6 = subprocess.run(["git", "push"], cwd=repo_dir, capture_output=True, text=True)
print("Git push:", res6.stdout, res6.stderr)
