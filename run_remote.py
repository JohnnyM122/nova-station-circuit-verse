import subprocess
import sys

def run_remote(ip, cmd, user="ubuntu", key=r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"):
    ssh_cmd = [
        "ssh", "-i", key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{user}@{ip}",
        cmd
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    print("STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("STDERR:")
        print(res.stderr)
    return res.returncode

if __name__ == "__main__":
    ip = sys.argv[1]
    cmd = " ".join(sys.argv[2:])
    sys.exit(run_remote(ip, cmd))
