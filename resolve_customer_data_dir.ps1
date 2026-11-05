param(
    [Parameter(Mandatory = $true)][string]$OutputFile,
    [string]$ProfilesRoot = (Join-Path $env:SystemDrive "Users"),
    [string]$InteractiveProfilePath = "",
    [switch]$DisableInteractiveLookup
)

$ErrorActionPreference = "Stop"

function Write-ResolvedDirectory([string]$Directory) {
    [System.IO.File]::WriteAllText($OutputFile, $Directory, [System.Text.Encoding]::UTF8)
}

function Get-ProfileLocalAppData([string]$ProfilePath, [string]$Sid) {
    $localAppData = Join-Path $ProfilePath "AppData\Local"
    if (-not [string]::IsNullOrWhiteSpace($Sid)) {
        $userShellFolders = "Registry::HKEY_USERS\" + $Sid + "\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        if (Test-Path -LiteralPath $userShellFolders) {
            $shellFolders = Get-ItemProperty -LiteralPath $userShellFolders -ErrorAction SilentlyContinue
            $configuredPath = [string]$shellFolders."Local AppData"
            if (-not [string]::IsNullOrWhiteSpace($configuredPath)) {
                $configuredPath = $configuredPath.Replace("%USERPROFILE%", $ProfilePath)
                $configuredPath = [Environment]::ExpandEnvironmentVariables($configuredPath)
                if ([System.IO.Path]::IsPathRooted($configuredPath)) { $localAppData = $configuredPath }
            }
        }
    }
    return $localAppData
}

try {
    $interactiveUser = ""
    $interactiveSid = ""
    $profilePath = $InteractiveProfilePath
    if ([string]::IsNullOrWhiteSpace($profilePath) -and -not $DisableInteractiveLookup) {
        try {
            $interactiveUser = [string](Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop).UserName
        } catch {}
        if ([string]::IsNullOrWhiteSpace($interactiveUser)) {
            try {
                $explorer = Get-CimInstance -ClassName Win32_Process -Filter "Name = 'explorer.exe'" -ErrorAction Stop |
                    Select-Object -First 1
                if ($explorer) {
                    $owner = Invoke-CimMethod -InputObject $explorer -MethodName GetOwner -ErrorAction Stop
                    if ($owner.ReturnValue -eq 0 -and $owner.User) {
                        $interactiveUser = if ($owner.Domain) { "$($owner.Domain)\$($owner.User)" } else { $owner.User }
                    }
                }
            } catch {}
        }
    }

    if ([string]::IsNullOrWhiteSpace($profilePath) -and -not [string]::IsNullOrWhiteSpace($interactiveUser)) {
        try {
            $account = [System.Security.Principal.NTAccount]::new($interactiveUser)
            $interactiveSid = $account.Translate([System.Security.Principal.SecurityIdentifier]).Value
            $profileKey = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\" + $interactiveSid
            $profile = Get-ItemProperty -LiteralPath $profileKey -ErrorAction Stop
            $profilePath = [Environment]::ExpandEnvironmentVariables([string]$profile.ProfileImagePath)
        } catch { $profilePath = "" }
    }

    $interactiveDataDirectory = ""
    if (-not [string]::IsNullOrWhiteSpace($profilePath) -and (Test-Path -LiteralPath $profilePath -PathType Container)) {
        $localAppData = Get-ProfileLocalAppData -ProfilePath $profilePath -Sid $interactiveSid
        $interactiveDataDirectory = Join-Path $localAppData "EmployeeAuditManager"
    }

    # Recover customer data even when the old EXE was removed or another admin
    # account launched Setup. Never guess between multiple customer databases.
    $candidates = @()
    if (Test-Path -LiteralPath $ProfilesRoot -PathType Container) {
        Get-ChildItem -LiteralPath $ProfilesRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $candidate = Join-Path $_.FullName "AppData\Local\EmployeeAuditManager"
            if (Test-Path -LiteralPath (Join-Path $candidate "employee_audit.db") -PathType Leaf) {
                $candidates += $candidate
            }
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($interactiveDataDirectory) -and
        (Test-Path -LiteralPath (Join-Path $interactiveDataDirectory "employee_audit.db") -PathType Leaf)) {
        Write-ResolvedDirectory $interactiveDataDirectory
        exit 0
    }
    if ($candidates.Count -eq 1) {
        Write-ResolvedDirectory $candidates[0]
        exit 0
    }
    if ($candidates.Count -gt 1) {
        throw "More than one Windows profile contains an EmployeeAuditManager database. Refusing to guess which customer database to use."
    }
    if (-not [string]::IsNullOrWhiteSpace($interactiveDataDirectory)) {
        Write-ResolvedDirectory $interactiveDataDirectory
        exit 0
    }

    Write-ResolvedDirectory "__RSC_NO_EXISTING_PROFILE__"
    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
