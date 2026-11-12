import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"

# 1. Update Commands.dat on 91.107.198.243
unturned_ip = "91.107.198.243"
py_cmds = """
path = '/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = [l for l in lines if l.strip().lower() != 'whitelisted']
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Removed Whitelisted from Commands.dat!')
"""

res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    f"root@{unturned_ip}",
    f"python3 -c {subprocess.list2cmdline([py_cmds])}"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Commands.dat update:", res.stdout)

# 2. Update Config.txt on 91.107.198.243
py_cfg = """
path = '/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
for i, l in enumerate(lines):
    if l.strip().startswith('Desc_Hint'):
        lines[i] = '\\tDesc_Hint Official Unturned Server | Discord: https://discord.gg/M7R8EY28q6'
    elif l.strip().startswith('Desc_Full'):
        lines[i] = '\\tDesc_Full Welcome to Circuit Verse - Official Unturned Server!\\nSurvival, Base Building, Custom Airdrops, Kits, and Dynamic Economy.\\n\\n🌐 Open to Community - No Whitelist Required!\\nJoin our community Discord: https://discord.gg/M7R8EY28q6 for starter kits & perks.\\n\\n📢 WE ARE HIRING SERVER & COMMUNITY STAFF!\\nInquire within Discord or make a support ticket in #open-a-ticket!'
    elif l.strip().startswith('Desc_Server_List'):
        lines[i] = '\\tDesc_Server_List Circuit Verse Official | Open to All | Discord: https://discord.gg/M7R8EY28q6'

with open(path, 'w', encoding='utf-8') as f:
    f.write('\\n'.join(lines) + '\\n')

print('Updated Config.txt descriptions!')
"""

res2 = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    f"root@{unturned_ip}",
    f"python3 -c {subprocess.list2cmdline([py_cfg])}"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Config.txt update:", res2.stdout)

# 3. Restart Unturned Server
print("Restarting unturned.service...")
res3 = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    f"root@{unturned_ip}",
    "systemctl restart unturned.service"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Restart Unturned status:", res3.returncode)
