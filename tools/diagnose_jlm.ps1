Write-Output "=== PROCESSES ==="
Get-CimInstance Win32_Process | ForEach-Object {
    if ($_.Name -match 'powershell|cmd|python|node|wscript|cscript|conhost|pwsh') {
        [PSCustomObject]@{
            ProcessId = $_.ProcessId
            ParentId = $_.ParentProcessId
            Name = $_.Name
            CommandLine = $_.CommandLine
        }
    }
} | Format-Table -AutoSize

Write-Output "=== RECENT SCHEDULED TASKS (LAST 2 HOURS) ==="
Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' } | ForEach-Object {
    $info = $_ | Get-ScheduledTaskInfo -ErrorAction SilentlyContinue
    if ($info -and $info.LastRunTime -and $info.LastRunTime -gt (Get-Date).AddHours(-2)) {
        [PSCustomObject]@{
            TaskName = $_.TaskName
            TaskPath = $_.TaskPath
            LastRunTime = $info.LastRunTime
            NextRunTime = $info.NextRunTime
            LastResult = $info.LastTaskResult
        }
    }
} | Sort-Object LastRunTime -Descending | Format-Table -AutoSize

Write-Output "=== TASKS TRIGGERING POWERSHELL / CMD / BAT ==="
Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' } | ForEach-Object {
    $task = $_
    $task.Actions | ForEach-Object {
        if ($_.Execute -match 'powershell|cmd|bat|cmd\.exe|powershell\.exe|pwsh|vbs|wscript') {
            [PSCustomObject]@{
                TaskName = $task.TaskName
                TaskPath = $task.TaskPath
                Execute = $_.Execute
                Arguments = $_.Arguments
            }
        }
    }
} | Format-Table -AutoSize

Write-Output "=== STARTUP ITEMS (REGISTRY & FOLDERS) ==="
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User | Format-Table -AutoSize
