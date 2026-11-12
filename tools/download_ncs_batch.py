import os
import sys
import time
import subprocess
import glob
import re

MEDIA_DIR = '/var/lib/docker/volumes/azuracast_station_data/_data/circuit_verse_radio/media'
CANDIDATES_FILE = '/tmp/ncs_candidates.txt'
TARGET_TOTAL = 1525
MAX_STORAGE_GB = 120.0  # Strict safety ceiling below the 125 GB limit

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
    cleaned = re.sub(r'\[.*?Release.*?\]', '', title, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[.*?Official.*?\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\(.*?NCS.*?\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\\/:*?"<>|]', '', cleaned)
    return cleaned.strip()

def main():
    print(f"=== Starting NCS Library Expansion (Target: {TARGET_TOTAL} songs, Limit: {MAX_STORAGE_GB} GB) ===")
    if not os.path.exists(CANDIDATES_FILE):
        print(f"Error: {CANDIDATES_FILE} not found!")
        sys.exit(1)

    with open(CANDIDATES_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if '\t' in l]

    existing_files = os.listdir(MEDIA_DIR)
    existing_mp3s = [f for f in existing_files if f.endswith('.mp3')]
    current_count = len(existing_mp3s)
    current_size = get_dir_size_gb(MEDIA_DIR)

    print(f"Current library: {current_count} tracks, {current_size:.2f} GB")

    if current_count >= TARGET_TOTAL:
        print(f"Target {TARGET_TOTAL} already reached!")
        return

    existing_lower = set(f.lower().replace('.mp3', '') for f in existing_mp3s)

    needed = TARGET_TOTAL - current_count
    print(f"Need to download {needed} new non-copyrighted NCS tracks.")

    downloaded = 0
    for idx, line in enumerate(lines):
        if current_count + downloaded >= TARGET_TOTAL:
            print(f"Reached target of {TARGET_TOTAL} songs!")
            break

        current_size = get_dir_size_gb(MEDIA_DIR)
        if current_size >= MAX_STORAGE_GB:
            print(f"WARNING: Approaching storage limit ({current_size:.2f} GB). Halting downloads.")
            break

        parts = line.split('\t', 1)
        vid_id = parts[0].strip()
        raw_title = parts[1].strip()
        clean_title = sanitize_title(raw_title)

        if any(vid_id in f for f in existing_mp3s) or clean_title.lower() in existing_lower:
            continue

        url = f"https://www.youtube.com/watch?v={vid_id}"
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
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=60)
            if res.returncode == 0:
                downloaded += 1
                if downloaded % 25 == 0 or downloaded == 1:
                    total_now = current_count + downloaded
                    sz = get_dir_size_gb(MEDIA_DIR)
                    print(f"[{downloaded}/{needed}] Progress: {total_now} tracks total ({sz:.2f} GB)")
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

    final_count = len([f for f in os.listdir(MEDIA_DIR) if f.endswith('.mp3')])
    final_size = get_dir_size_gb(MEDIA_DIR)
    print(f"=== Download Finished: {final_count} songs ({final_size:.2f} GB) ===")

    print("Updating AzuraCast ownership...")
    subprocess.run(["chown", "-R", "1000:1000", MEDIA_DIR], check=False)
    subprocess.run(["docker", "exec", "azuracast", "chown", "-R", "azuracast:azuracast", "/var/azuracast/stations/circuit_verse_radio/media"], check=False)

    print("Syncing AzuraCast media database...")
    subprocess.run(["docker", "exec", "azuracast", "azuracast_cli", "azuracast:media:sync", "circuit_verse_radio"], check=False)

    print("Populating playlist 1 (station_playlist_media)...")
    sql = "INSERT IGNORE INTO station_playlist_media (playlist_id, media_id, weight, last_played, is_queued) SELECT 1, id, 0, 0, 0 FROM station_media;"
    subprocess.run(["docker", "exec", "azuracast", "gosu", "azuracast", "php", "/var/azuracast/www/backend/bin/console", "dbal:run-sql", sql], check=False)

    print("=== AzuraCast Sync Complete! ===")

if __name__ == '__main__':
    main()
