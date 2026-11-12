import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import zipfile

with zipfile.ZipFile("/home/pz/pz-server/java/projectzomboid.jar", "r") as z:
    raw = z.read("zombie/network/DiscordBot.class")

# Let us disassemble the method using a python disassembler or just analyze constant pool references
idx = 0
import struct

# Simple class file parser to find methods
magic, minor, major = struct.unpack(">IHH", raw[:8])
cp_count = struct.unpack(">H", raw[8:10])[0]
print(f"Major: {major}, Minor: {minor}, CP Count: {cp_count}")

# Print any string or utf8 entries in constant pool
pos = 10
cp = [None] * cp_count
i = 1
while i < cp_count:
    tag = raw[pos]
    pos += 1
    if tag == 1: # Utf8
        length = struct.unpack(">H", raw[pos:pos+2])[0]
        pos += 2
        val = raw[pos:pos+length].decode(errors="ignore")
        pos += length
        cp[i] = val
    elif tag in (3, 4): # Integer, Float
        pos += 4
    elif tag in (5, 6): # Long, Double
        pos += 8
        i += 1 # takes two slots
    elif tag in (7, 8): # Class, String
        val = struct.unpack(">H", raw[pos:pos+2])[0]
        pos += 2
        cp[i] = (tag, val)
    elif tag in (9, 10, 11, 12): # Ref
        pos += 4
    elif tag in (15, 16, 18):
        pos += 3 if tag == 15 else 4
    elif tag in (19, 20):
        pos += 2
    i += 1

print("Filtered strings from CP:")
for idx, entry in enumerate(cp):
    if isinstance(entry, str) and any(k in entry.lower() for k in ["channel", "discord", "bot", "token", "error"]):
        print(f"  [{idx}] {entry}")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
