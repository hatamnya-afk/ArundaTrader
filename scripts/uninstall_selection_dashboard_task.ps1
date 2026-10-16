# Removes only the optional read-only dashboard logon task.
$ErrorActionPreference = "Stop"
$taskName = "ArundaTrader-Selection-Quality-Dashboard"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task not installed: $taskName"
    exit 0
}
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "Removed task: $taskName"
Write-Host "No repository files or trading data were deleted."
