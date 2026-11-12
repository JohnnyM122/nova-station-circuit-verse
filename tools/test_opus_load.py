import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

check_script = """
import discord.opus
import ctypes.util

print("find_library opus:", ctypes.util.find_library("opus"))
try:
    discord.opus._load_default()
    print("Opus loaded successfully! is_loaded:", discord.opus.is_loaded())
except Exception as e:
    print("Error loading default opus:", e)

# Test davey
import davey
print("Davey import successful! version:", getattr(davey, "__version__", "ok"))
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "/home/ubuntu/CV-Nova-Helper/venv/bin/python3 -"]
res = subprocess.run(cmd, input=check_script.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
