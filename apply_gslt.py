import subprocess

key = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
token = "E61497C0F8576188E6917275A1484BC0"

# 1. Update Config.txt on 91.107.198.243
py_remote = f"""
path = '/home/unturned/unturned-server/Servers/CircuitVerse/Config.txt'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip().startswith('Login_Token'):
        new_lines.append(f'\\tLogin_Token {token}\\n')
    elif line.strip().startswith('BookmarkHost'):
        new_lines.append('\\tBookmarkHost unturned.circuitverse.online\\n')
    else:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Updated Config.txt with GSLT!')
"""

res = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    f"python3 -c {subprocess.list2cmdline([py_remote])}"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Config update STDOUT:", res.stdout)
print("Config update STDERR:", res.stderr)

# 2. Also check Commands.dat to see if GSLT is in it
commands_check = f"""
path = '/home/unturned/unturned-server/Servers/CircuitVerse/Server/Commands.dat'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

if 'GSLT' not in text:
    with open(path, 'a', encoding='utf-8') as f:
        f.write('\\nGSLT {token}\\n')
    print('Appended GSLT to Commands.dat')
else:
    print('GSLT already in Commands.dat')
"""

res2 = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    f"python3 -c {subprocess.list2cmdline([commands_check])}"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Commands update STDOUT:", res2.stdout)

# 3. Restart unturned.service
print("Restarting unturned.service...")
res3 = subprocess.run([
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    "root@91.107.198.243",
    "systemctl restart unturned.service"
], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("Restart returncode:", res3.returncode)
