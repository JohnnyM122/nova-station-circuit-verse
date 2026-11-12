import subprocess
import os

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_tailscale')
DED_IP = '62.238.81.224'

def run_ssh(cmd_str, timeout=60):
    cmd = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', f'root@{DED_IP}', cmd_str]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

print("1. Deploying Kernel Anti-DDoS sysctl settings...")
sysctl_conf = """
# === CIRCUIT VERSE KERNEL ANTI-DDOS & HARDENING ===
# SYN Flood Protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_syn_retries = 2
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_max_syn_backlog = 8192

# Socket Exhaustion & Connection Reaping
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 100000
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.ip_local_port_range = 1024 65535

# Reverse Path Filtering & Anti-Spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP Broadcasts & Bogus Errors (Anti-Smurf)
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Disable ICMP Redirect Acceptance & Transmission
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Disable IP Source Routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Buffer Sizes for high throughput & game packet bursts
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.udp_rmem_min = 16384
net.ipv4.udp_wmem_min = 16384
"""

code, out, err = run_ssh(f"cat << 'EOF' > /etc/sysctl.d/99-anti-ddos-security.conf\n{sysctl_conf}\nEOF\nsysctl --system | grep -E '(syncookies|somaxconn|rp_filter|max_syn_backlog)'")
print("Sysctl status:", code)
print(out)

print("\n2. Installing fail2ban and iptables-persistent...")
code, out, err = run_ssh("DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban iptables-persistent", timeout=120)
print("Packages install status:", code)

print("\n3. Hardening SSH configuration...")
ssh_harden = """
PasswordAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 30
"""
run_ssh(f"cat << 'EOF' > /etc/ssh/sshd_config.d/99-hardened.conf\n{ssh_harden}\nEOF\nsystemctl reload ssh || systemctl restart ssh")

print("\n4. Configuring Fail2Ban jail...")
fail2ban_jail = """
[DEFAULT]
bantime  = 24h
findtime = 10m
maxretry = 3
banaction = iptables-multiport

[sshd]
enabled = true
port    = 22
mode    = aggressive
maxretry = 3
"""
run_ssh(f"cat << 'EOF' > /etc/fail2ban/jail.local\n{fail2ban_jail}\nEOF\nsystemctl restart fail2ban && systemctl enable fail2ban")
code, out, err = run_ssh("fail2ban-client status && fail2ban-client status sshd")
print(out)
