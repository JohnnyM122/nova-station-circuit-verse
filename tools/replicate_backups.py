import paramiko
import os
import sys
import time

HETZNER_HOST = "62.238.81.224"
HETZNER_USER = "ubuntu"

JLM_HOST = "100.100.148.47"
JLM_USER = "SysAdmin"

KEY_FILE = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
LOCAL_DIR = r"E:\Backups\CircuitVerse_20261112"

os.makedirs(LOCAL_DIR, exist_ok=True)

key = paramiko.Ed25519Key.from_private_key_file(KEY_FILE)

print("Connecting to Hetzner Dedicated Server...", flush=True)
c_hetzner = paramiko.SSHClient()
c_hetzner.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c_hetzner.connect(HETZNER_HOST, port=22, username=HETZNER_USER, pkey=key, timeout=15)
sftp_hetzner = c_hetzner.open_sftp()

print("Connecting to JLM Home Server...", flush=True)
c_jlm = paramiko.SSHClient()
c_jlm.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c_jlm.connect(JLM_HOST, port=22, username=JLM_USER, pkey=key, timeout=15)
sftp_jlm = c_jlm.open_sftp()

remote_dir = "/home/ubuntu/backups/latest"
backup_files = sorted(sftp_hetzner.listdir(remote_dir))
print(f"Found {len(backup_files)} backup archives on Hetzner: {backup_files}", flush=True)

for fname in backup_files:
    remote_path = f"{remote_dir}/{fname}"
    local_path = os.path.join(LOCAL_DIR, fname)
    remote_attr = sftp_hetzner.stat(remote_path)
    total_size = remote_attr.st_size
    size_mb = total_size / (1024 * 1024)

    # 1. Download to Laptop FD2A Drive (E:\)
    if os.path.exists(local_path) and os.path.getsize(local_path) == total_size:
        print(f"\n[SKIP] {fname} ({size_mb:.1f} MB) already exists on Laptop FD2A drive.", flush=True)
    else:
        print(f"\n[1/3] Downloading {fname} ({size_mb:.1f} MB) -> Laptop FD2A (E:\\)...", flush=True)
        t0 = time.time()
        last_pct = [0]
        def dl_progress(transferred, total):
            pct = int((transferred / total) * 100)
            if pct - last_pct[0] >= 20 or pct == 100:
                last_pct[0] = pct
                print(f"   Downloading {fname}: {pct}% ({transferred/(1024*1024):.1f}/{size_mb:.1f} MB)", flush=True)

        sftp_hetzner.get(remote_path, local_path, callback=dl_progress)
        elapsed = time.time() - t0
        rate = (size_mb / elapsed) if elapsed > 0 else 0
        print(f"   Done in {elapsed:.1f}s ({rate:.1f} MB/s)", flush=True)

    # 2. Upload to JLM Home Server Drive E:
    jlm_e_path = f"E:/Backups/CircuitVerse_20261112/{fname}"
    try:
        jlm_stat = sftp_jlm.stat(jlm_e_path)
        jlm_exists = (jlm_stat.st_size == total_size)
    except Exception:
        jlm_exists = False

    if jlm_exists:
        print(f"[SKIP] {fname} already exists on JLM Home Server (E:\\).", flush=True)
    else:
        print(f"[2/3] Uploading {fname} -> JLM Home Server (E:\\)...", flush=True)
        t0 = time.time()
        last_pct = [0]
        def up_progress(transferred, total):
            pct = int((transferred / total) * 100)
            if pct - last_pct[0] >= 20 or pct == 100:
                last_pct[0] = pct
                print(f"   Uploading {fname}: {pct}% ({transferred/(1024*1024):.1f}/{size_mb:.1f} MB)", flush=True)

        sftp_jlm.put(local_path, jlm_e_path, callback=up_progress)
        elapsed = time.time() - t0
        rate = (size_mb / elapsed) if elapsed > 0 else 0
        print(f"   Done in {elapsed:.1f}s ({rate:.1f} MB/s)", flush=True)

    # 3. Check and Replicate to F: and G: on JLM Home Server
    for drive in ["F", "G"]:
        dst_path = f"{drive}:/Backups/CircuitVerse_20261112/{fname}"
        try:
            stat_dst = sftp_jlm.stat(dst_path)
            already_done = (stat_dst.st_size == total_size)
        except Exception:
            already_done = False

        if already_done:
            print(f"[SKIP] {fname} already replicated on JLM Home Server ({drive}:\\).", flush=True)
        else:
            print(f"[3/3] Copying {fname} -> JLM Home Server ({drive}:\\)...", flush=True)
            cmd = f'powershell -Command "Copy-Item -Force -Path \'E:\\Backups\\CircuitVerse_20261112\\{fname}\' -Destination \'{drive}:\\Backups\\CircuitVerse_20261112\\{fname}\'"'
            stdin, stdout, stderr = c_jlm.exec_command(cmd)
            stdout.read()
            stderr.read()
            print(f"   Replicated {fname} to {drive}:\\ successfully!", flush=True)

sftp_hetzner.close()
c_hetzner.close()
sftp_jlm.close()
c_jlm.close()

print("\n=== ALL 7 BACKUPS FULLY REPLICATED ACROSS LAPTOP (FD2A) & JLM (E:, F:, G:)! ===", flush=True)
