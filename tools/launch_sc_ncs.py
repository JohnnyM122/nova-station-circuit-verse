import paramiko

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "62.238.81.224"
USER = "ubuntu"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)
client.connect(hostname=HOST, port=22, username=USER, pkey=key, timeout=15)

script_content = """import os
import sys
import time
import subprocess
import re

MEDIA_DIR = '/var/lib/docker/volumes/azuracast_station_data/_data/circuit_verse_radio/media'
TRACKS_FILE = '/tmp/sc_ncs_tracks.txt'
TARGET_TOTAL = 1525
MAX_STORAGE_GB = 120.0

def get_dir_size_gb(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except Exception:
                pass
    return total / (1024 ** 3)

def sanitize_title(title):
    cleaned = re.sub(r'\\[.*?(?:Release|Official).*?\\]', '', title, flags=re.IGNORECASE)
    cleaned = re.sub(r'\\(.*?NCS.*?\\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\\\\/:*?"<>|]', '', cleaned)
    cleaned = re.sub(r'\\s+', ' ', cleaned)
    return cleaned.strip()

def main():
    print(f"=== Starting Fast SoundCloud NCS Expansion (Target: {TARGET_TOTAL} songs, Limit: {MAX_STORAGE_GB} GB) ===", flush=True)
    if not os.path.exists(TRACKS_FILE):
        print(f"Error: {TRACKS_FILE} not found!", flush=True)
        sys.exit(1)

    with open(TRACKS_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if '\\t' in l]

    existing_files = os.listdir(MEDIA_DIR)
    existing_mp3s = [f for f in existing_files if f.endswith('.mp3')]
    current_count = len(existing_mp3s)
    current_size = get_dir_size_gb(MEDIA_DIR)

    print(f"Current library: {current_count} tracks, {current_size:.2f} GB", flush=True)

    if current_count >= TARGET_TOTAL:
        print(f"Target {TARGET_TOTAL} already reached!", flush=True)
        return

    # Normalize existing names for deduplication
    existing_lower = set(re.sub(r'[^a-z0-9]', '', f.lower().replace('.mp3', '')) for f in existing_mp3s)

    needed = TARGET_TOTAL - current_count
    print(f"Need to download {needed} new non-copyrighted NCS tracks.", flush=True)

    downloaded = 0
    for idx, line in enumerate(lines):
        if current_count + downloaded >= TARGET_TOTAL:
            print(f"Target of {TARGET_TOTAL} songs reached! ({downloaded} newly downloaded)", flush=True)
            break

        current_size = get_dir_size_gb(MEDIA_DIR)
        if current_size >= MAX_STORAGE_GB:
            print(f"WARNING: Approaching storage limit ({current_size:.2f} GB). Halting.", flush=True)
            break

        parts = line.split('\\t', 1)
        url = parts[0].strip()
        raw_title = parts[1].strip()
        clean_title = sanitize_title(raw_title)

        norm = re.sub(r'[^a-z0-9]', '', clean_title.lower())
        if norm in existing_lower or len(norm) < 4:
            continue

        out_template = os.path.join(MEDIA_DIR, f"{clean_title}.%(ext)s")

        cmd = [
            "/home/ubuntu/CV-Nova-Helper/venv/bin/yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "192K",
            "--no-playlist",
            "--max-filesize", "50M",
            "--output", out_template,
            url
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=45)
            if res.returncode == 0:
                downloaded += 1
                existing_lower.add(norm)
                if downloaded % 25 == 0 or downloaded == 1:
                    total_now = current_count + downloaded
                    sz = get_dir_size_gb(MEDIA_DIR)
                    print(f"[{downloaded}/{needed}] Progress: {total_now} total songs ({sz:.2f} GB)", flush=True)
            else:
                pass
        except Exception as e:
            pass

    print(f"Finished downloads! Total newly downloaded: {downloaded}.", flush=True)
    print("Syncing AzuraCast station library...", flush=True)
    subprocess.run(["docker", "exec", "azuracast", "chown", "-R", "azuracast:azuracast", "/var/azuracast/stations/circuit_verse_radio/media"])
    subprocess.run(["docker", "exec", "azuracast", "azuracast_cli", "azuracast:media:sync", "circuit_verse_radio"])
    sql = "INSERT IGNORE INTO station_playlist_media (playlist_id, media_id, weight, last_played, is_queued) SELECT 1, id, 0, 0, 0 FROM station_media;"
    subprocess.run(["docker", "exec", "azuracast", "gosu", "azuracast", "php", "/var/azuracast/www/backend/bin/console", "dbal:run-sql", sql])
    print("AzuraCast sync and playlist integration complete!", flush=True)

if __name__ == '__main__':
    main()
"""

try:
    sftp = client.open_sftp()
    with sftp.open("/home/ubuntu/download_ncs_soundcloud.py", "w") as f:
        f.write(script_content)
    sftp.close()

    # Launch in background with nohup
    launch_cmd = "sudo nohup /home/ubuntu/CV-Nova-Helper/venv/bin/python3 -u /home/ubuntu/download_ncs_soundcloud.py > /home/ubuntu/ncs_sc_download.log 2>&1 &"
    client.exec_command(launch_cmd)
    print("SoundCloud NCS downloader launched!")

finally:
    client.close()
