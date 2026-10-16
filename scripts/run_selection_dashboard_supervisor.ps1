# ArundaTrader selection-quality dashboard supervisor.
# This supervises the read-only UI only; it does not start the trading pipeline.
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python was not found on PATH. Install Python 3.12+ and reopen the terminal." }
$script = Join-Path $repoRoot "arunda_selection_quality_dashboard_v0_1.py"
if (-not (Test-Path -LiteralPath $script)) { throw "Dashboard script missing: $script" }
$logDir = Join-Path $env:LOCALAPPDATA "ArundaTrader\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir "selection-dashboard-supervisor.log"
while ($true) {
    $started = Get-Date
    "[$($started.ToString('o'))] Starting read-only selection dashboard." | Add-Content -LiteralPath $log
    try {
        & $python.Source $script --host 127.0.0.1 --port 8765 2>&1 |
            ForEach-Object { "$($_)" | Add-Content -LiteralPath $log }
        $exitCode = $LASTEXITCODE
        "[$((Get-Date).ToString('o'))] Dashboard exited with code $exitCode." | Add-Content -LiteralPath $log
    } catch {
        "[$((Get-Date).ToString('o'))] Dashboard launch error: $($_.Exception.Message)" | Add-Content -LiteralPath $log
    }
    Start-Sleep -Seconds 10
}
