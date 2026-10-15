[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ServiceIdentity,

    [string]$JournalPath = 'C:\ProgramData\ArundaTrader\security\standing_mandate_lifecycle.jsonl'
)

$ErrorActionPreference = 'Stop'

$principal = [Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this configuration from an elevated PowerShell session.'
}

if (-not [IO.Path]::IsPathRooted($JournalPath)) {
    throw 'JournalPath must be an absolute path.'
}
$JournalPath = [IO.Path]::GetFullPath($JournalPath)
$directory = Split-Path -Parent $JournalPath
if (-not $directory) { throw 'JournalPath must have a parent directory.' }

# Never create, truncate, seed, or repair the journal here.
# A management-authorized ACTIVATE event must be persisted separately.
if ($PSCmdlet.ShouldProcess($directory, 'Create protected journal directory and set ACL')) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    & icacls.exe $directory /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'BUILTIN\Administrators:(OI)(CI)F' "\${ServiceIdentity}:(OI)(CI)M"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to apply journal directory ACL (icacls exit $LASTEXITCODE)."
    }
}

if ($PSCmdlet.ShouldProcess('Machine environment', "Set ARUNDA_MANDATE_LIFECYCLE_PATH=$JournalPath")) {
    [Environment]::SetEnvironmentVariable(
        'ARUNDA_MANDATE_LIFECYCLE_PATH',
        $JournalPath,
        [EnvironmentVariableTarget]::Machine
    )
}

Write-Output "CONFIGURED_PATH=$JournalPath"
Write-Output "SERVICE_IDENTITY=$ServiceIdentity"
Write-Output 'JOURNAL_CREATED_OR_MODIFIED=false'
Write-Output 'NEXT=Restart the actual service/process so it inherits the machine environment; then run the read-only Python preflight with the mandate ID from the validated management decision.'
