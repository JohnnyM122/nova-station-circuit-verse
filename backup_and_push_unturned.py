import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
backup_dir = r"E:\CircuitVerse_Backups_20261107\circuit-verse-unturned"

# Download current Commands.dat and Config.txt
res1 = subprocess.run([
    "scp", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243:/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat",
    f"{backup_dir}/Server/Commands.dat"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Commands.dat backup:", res1.returncode)

res2 = subprocess.run([
    "scp", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243:/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt",
    f"{backup_dir}/Config.txt"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Config.txt backup:", res2.returncode)

res3 = subprocess.run([
    "scp", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243:/home/unturned/unturned-server/Servers/CircuitVerse/Rocket/Plugins/RichMessageAnnouncer/RichMessageAnnouncer.configuration.xml",
    f"{backup_dir}/Rocket/Plugins/RichMessageAnnouncer/RichMessageAnnouncer.configuration.xml"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("RichMessageAnnouncer backup:", res3.returncode)

# Git commit and push in backup_dir
cmd = f"cd /d {backup_dir} && git add . && git commit -m 'Update MOTD, hiring notice, BattlEye secure setting & whitelist notices' && git push"
res4 = subprocess.run(["cmd.exe", "/c", cmd], capture_output=True, text=True)
print("Git stdout:", res4.stdout)
print("Git stderr:", res4.stderr)
