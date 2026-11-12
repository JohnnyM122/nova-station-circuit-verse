import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "100.100.148.47"

ps_remediate = """
$tasks = @(
    "Johnny Lyn Help Desk Auto Update",
    "Johnny Lyn Help Desk Deployment",
    "Johnny Lyn Help Desk Tunnel"
)

foreach ($t in $tasks) {
    Write-Output "Stopping task: $t"
    Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    Write-Output "Disabling task: $t"
    Disable-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
}

# Stop orphaned cloudflared process associated with the old tunnel
$cf = Get-Process -Name cloudflared -ErrorAction SilentlyContinue
if ($cf) {
    Write-Output "Stopping cloudflared process ID(s): $($cf.Id -join ', ')"
    Stop-Process -Id $cf.Id -Force -ErrorAction SilentlyContinue
}

Write-Output "=== CURRENT TASK STATUSES ==="
Get-ScheduledTask -TaskPath '\\' | Where-Object { $_.TaskName -match 'Johnny' } | Select-Object TaskName, State | Format-Table -AutoSize
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "powershell -NoProfile -ExecutionPolicy Bypass -Command -"], input=ps_remediate.encode(), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("ERR:", res.stderr.decode("utf-8", errors="replace"))
