import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

try:
    code = """
import sys, json, os, subprocess, requests

print("=== 1. CHECK STREAM URL & CODEC ===")
stream_url = "http://127.0.0.1/listen/circuit_verse_radio/radio.mp3"
r = requests.get(stream_url, stream=True, timeout=5)
print(f"Stream HTTP Status: {r.status_code}")
print(f"Stream Headers: {r.headers}")
chunk = next(r.iter_content(chunk_size=4096))
print(f"Received chunk of size {len(chunk)} bytes from stream.")
r.close()

print("\\n=== 2. PROBE WITH FFPROBE ===")
p = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels",
    "-of", "default=noprint_wrappers=1", stream_url
], capture_output=True, text=True, timeout=10)
print("ffprobe stdout:", p.stdout.strip())
if p.stderr:
    print("ffprobe stderr:", p.stderr.strip())

print("\\n=== 3. TEST FFMPEG CONVERSION TO S16LE 48000Hz 2CH ===")
ff_cmd = [
    "ffmpeg", "-y", "-i", stream_url,
    "-t", "2", "-vn", "-ar", "48000", "-ac", "2", "-f", "s16le",
    "/tmp/test_stream_audio.raw"
]
ff = subprocess.run(ff_cmd, capture_output=True, text=True, timeout=10)
if os.path.exists("/tmp/test_stream_audio.raw"):
    size = os.path.getsize("/tmp/test_stream_audio.raw")
    print(f"Generated 2s s16le raw audio: {size} bytes (Expected ~384,000 bytes)")
else:
    print("Failed to generate raw audio")
    print("ffmpeg stderr:", ff.stderr)

print("\\n=== 4. TEST OPUS ENCODING IN DISCORD.PY ===")
import discord
from discord import opus
if not opus.is_loaded():
    opus._load_default()
print("Opus loaded:", opus.is_loaded())
encoder = opus.Encoder()
sample_bytes = b'\\x00' * 3840 # 20ms of silence
enc = encoder.encode(sample_bytes, 960)
print(f"Encoded 3840 bytes of PCM -> {len(enc)} bytes of Opus packet")

print("\\n=== 5. CHECK AUDIO LEVELS / SILENCE DETECTION ===")
# Check if the stream actually has non-zero sound
with open("/tmp/test_stream_audio.raw", "rb") as f:
    raw_data = f.read()
non_zero = sum(1 for b in raw_data if b != 0)
print(f"Raw data total bytes: {len(raw_data)}, non-zero bytes: {non_zero} ({non_zero/len(raw_data)*100:.1f}%)")

"""
    sftp = client.open_sftp()
    with sftp.open("/tmp/diagnose_audio_pipeline.py", "w") as f:
        f.write(code)
    sftp.close()

    stdin, stdout, stderr = client.exec_command("/home/ubuntu/CV-Radio-Helper/venv/bin/python3 /tmp/diagnose_audio_pipeline.py")
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("ERR:", err)
finally:
    client.close()
