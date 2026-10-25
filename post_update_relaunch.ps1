param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,
    [int]$MaxWaitSeconds = 300
)

$ErrorActionPreference = 'SilentlyContinue'
$exeName = 'RawStrengthEmployeeAuditManager'

# Wait until no installer process is running (UAC-elevated or silent)
$deadline = (Get-Date).AddSeconds($MaxWaitSeconds)
while ((Get-Date) -lt $deadline) {
    $setup = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $n = $_.ProcessName
        ($n -like 'RawStrengthEmployeeAuditManager-Setup*') -or
        ($n -like '*Setup*' -and $_.Path -and ($_.Path -like '*RawStrength*'))
    }
    if (-not $setup) { break }
    Start-Sleep -Seconds 2
}

# Brief settle time after installer exits
Start-Sleep -Seconds 2

# If the app is already running (installer [Run] launched it), do nothing
$running = Get-Process -Name $exeName -ErrorAction SilentlyContinue
if ($running) {
    exit 0
}

if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    $candidates = @(
        "${env:ProgramFiles}\Raw Strength Employee Audit Manager\RawStrengthEmployeeAuditManager.exe",
        "${env:ProgramFiles(x86)}\Raw Strength Employee Audit Manager\RawStrengthEmployeeAuditManager.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c -PathType Leaf) {
            $ExePath = $c
            break
        }
    }
}

if (Test-Path -LiteralPath $ExePath -PathType Leaf) {
    Start-Process -FilePath $ExePath
    exit 0
}

exit 1
