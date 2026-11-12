Get-ScheduledTask | Where-Object { $_.TaskName -match 'Help Desk' } | ForEach-Object {
    Write-Output "NAME: $($_.TaskName)"
    Write-Output "STATE: $($_.State)"
    Write-Output "ACTIONS:"
    $_.Actions | ForEach-Object { Write-Output "  Exec: $($_.Execute)  Args: $($_.Arguments)" }
    Write-Output "TRIGGERS:"
    $_.Triggers | ForEach-Object { Write-Output "  $($_ | Out-String)" }
    $info = $_ | Get-ScheduledTaskInfo
    Write-Output "LAST RUN: $($info.LastRunTime) RESULT: $($info.LastTaskResult)"
    Write-Output "NEXT RUN: $($info.NextRunTime)"
    Write-Output "----------------------------------------"
}
