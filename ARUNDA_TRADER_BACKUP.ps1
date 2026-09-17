# ================================================================
# ARUNDA TRADER — BACKUP SCRIPT
# ================================================================

$ErrorActionPreference = "Stop"

$ProjectPath = "C:\Users\ASUS\ArundaTrader"

if (-not (Test-Path $ProjectPath)) {
    Write-Host "ERROR: Project directory not found." -ForegroundColor Red
    exit 1
}

$ParentPath = Split-Path $ProjectPath -Parent
$ProjectName = Split-Path $ProjectPath -Leaf

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$BackupRoot = Join-Path $ParentPath "ARUNDA_TRADER_BACKUPS"

if (-not (Test-Path $BackupRoot)) {
    New-Item `
        -ItemType Directory `
        -Path $BackupRoot `
        -Force | Out-Null
}

$BackupPath = Join-Path `
    $BackupRoot `
    "${ProjectName}_BACKUP_${Timestamp}"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ARUNDA TRADER BACKUP" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "SOURCE:" -ForegroundColor Yellow
Write-Host $ProjectPath

Write-Host ""
Write-Host "DESTINATION:" -ForegroundColor Yellow
Write-Host $BackupPath

Write-Host ""
Write-Host "Creating backup..." -ForegroundColor Yellow

New-Item `
    -ItemType Directory `
    -Path $BackupPath `
    -Force | Out-Null

# ------------------------------------------------
# Copy the complete project.
# Production files are READ ONLY during backup.
# ------------------------------------------------

$RobocopyArgs = @(
    $ProjectPath
    $BackupPath
    "/E"
    "/COPY:DAT"
    "/DCOPY:DAT"
    "/R:2"
    "/W:2"
    "/XJ"
    "/NFL"
    "/NDL"
    "/NP"
)

$RobocopyProcess = Start-Process `
    -FilePath "robocopy.exe" `
    -ArgumentList $RobocopyArgs `
    -Wait `
    -PassThru `
    -NoNewWindow

# Robocopy exit codes 0-7 are normally successful/non-fatal.
if ($RobocopyProcess.ExitCode -gt 7) {
    Write-Host ""
    Write-Host "BACKUP FAILED." -ForegroundColor Red
    Write-Host "Robocopy exit code: $($RobocopyProcess.ExitCode)"
    exit $RobocopyProcess.ExitCode
}

# ------------------------------------------------
# Create backup manifest.
# ------------------------------------------------

$ManifestPath = Join-Path $BackupPath "BACKUP_MANIFEST.txt"

$Files = Get-ChildItem `
    -Path $BackupPath `
    -File `
    -Recurse

$TotalFiles = $Files.Count

$TotalBytes = (
    $Files |
    Measure-Object -Property Length -Sum
).Sum

$Manifest = @"
ARUNDA TRADER BACKUP MANIFEST
============================================================

Created:
$(Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")

Source:
$ProjectPath

Backup:
$BackupPath

Files:
$TotalFiles

Bytes:
$TotalBytes

Database:
$(if (Test-Path (Join-Path $BackupPath "arunda.db")) { "PRESENT" } else { "NOT FOUND" })

Checkpoint:
$(if (Test-Path (Join-Path $BackupPath "ARUNDA_TRADER_PROJECT_CHECKPOINT_v0.1.md")) { "PRESENT" } else { "NOT FOUND" })

Backup script:
$(if (Test-Path (Join-Path $BackupPath "ARUNDA_TRADER_BACKUP.ps1")) { "PRESENT" } else { "NOT FOUND" })

============================================================
Production source was not modified by this backup process.
============================================================
"@

Set-Content `
    -Path $ManifestPath `
    -Value $Manifest `
    -Encoding UTF8

# ------------------------------------------------
# SHA256 hashes for critical files.
# ------------------------------------------------

$HashPath = Join-Path $BackupPath "CRITICAL_FILE_HASHES.txt"

$CriticalFiles = @(
    "arunda.db",
    "fusion_engine.py",
    "ARUNDA_TRADER_PROJECT_CHECKPOINT_v0.1.md",
    "ARUNDA_TRADER_BACKUP.ps1"
)

$HashLines = @(
    "ARUNDA TRADER CRITICAL FILE SHA256"
    "============================================================"
    ""
)

foreach ($RelativeFile in $CriticalFiles) {

    $FullPath = Join-Path $BackupPath $RelativeFile

    if (Test-Path $FullPath) {

        $Hash = Get-FileHash `
            -Path $FullPath `
            -Algorithm SHA256

        $HashLines += "$RelativeFile"
        $HashLines += "SHA256: $($Hash.Hash)"
        $HashLines += ""
    }
    else {

        $HashLines += "$RelativeFile"
        $HashLines += "STATUS: NOT FOUND"
        $HashLines += ""
    }
}

Set-Content `
    -Path $HashPath `
    -Value $HashLines `
    -Encoding UTF8

# ------------------------------------------------
# Final verification.
# ------------------------------------------------

$DbExists = Test-Path `
    (Join-Path $BackupPath "arunda.db")

$CheckpointExists = Test-Path `
    (Join-Path $BackupPath "ARUNDA_TRADER_PROJECT_CHECKPOINT_v0.1.md")

$BackupScriptExists = Test-Path `
    (Join-Path $BackupPath "ARUNDA_TRADER_BACKUP.ps1")

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " BACKUP COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

Write-Host ""
Write-Host "Backup directory:" -ForegroundColor Cyan
Write-Host $BackupPath

Write-Host ""
Write-Host "Files copied : $TotalFiles"
Write-Host "Database     : $DbExists"
Write-Host "Checkpoint   : $CheckpointExists"
Write-Host "Backup script: $BackupScriptExists"

if ($DbExists -and $CheckpointExists -and $BackupScriptExists) {

    Write-Host ""
    Write-Host "BACKUP VERIFICATION = VERIFIED" -ForegroundColor Green
    Write-Host ""

}
else {

    Write-Host ""
    Write-Host "BACKUP VERIFICATION = FAILED" -ForegroundColor Red
    Write-Host ""

    exit 2
}
