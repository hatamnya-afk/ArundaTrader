# Installs a per-user Windows logon task for the read-only selection dashboard.
# Does not install, start, or enable the trading runtime.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$supervisor = Join-Path $repoRoot "scripts\run_selection_dashboard_supervisor.ps1"
if (-not (Test-Path -LiteralPath $supervisor)) { throw "Supervisor missing: $supervisor" }
$taskName = "ArundaTrader-Selection-Quality-Dashboard"
$powershell = (Get-Command powershell.exe -ErrorAction SilentlyContinue)
if (-not $powershell) { throw "Windows PowerShell was not found." }
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$supervisor`""
$action = New-ScheduledTaskAction -Execute $powershell.Source -Argument $arguments -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Local read-only ArundaTrader selection-quality dashboard. Does not enable trading." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "Installed and started: $taskName"
Write-Host "Dashboard: http://127.0.0.1:8765"
Write-Host "Supervisor log: $env:LOCALAPPDATA\ArundaTrader\logs\selection-dashboard-supervisor.log"
Write-Host "This task supervises the dashboard only, not the trading pipeline."
