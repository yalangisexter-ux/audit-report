param(
    [Parameter(Mandatory = $true)][string]$OutputFile,
    [string]$ProfilesRoot = (Join-Path $env:SystemDrive "Users"),
    [string]$InteractiveProfilePath = "",
    [string]$ProfileListRoot = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList",
    [string]$UserHivesRoot = "Registry::HKEY_USERS",
    [switch]$DisableInteractiveLookup
)

$ErrorActionPreference = "Stop"

function Write-ResolvedDirectory([string]$Directory) {
    [System.IO.File]::WriteAllText($OutputFile, $Directory, [System.Text.Encoding]::UTF8)
}

function Get-ProfileLocalAppData([string]$ProfilePath, [string]$Sid, [string]$UserHivesRoot = "Registry::HKEY_USERS") {
    $localAppData = Join-Path $ProfilePath "AppData\Local"
    if (-not [string]::IsNullOrWhiteSpace($Sid)) {
        $userShellFolders = $UserHivesRoot + "\" + $Sid + "\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
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

function Get-RegisteredProfileDataDirectories {
    $directories = @()
    $profileList = $ProfileListRoot
    if (-not (Test-Path -LiteralPath $profileList)) { return $directories }

    foreach ($entry in (Get-ChildItem -LiteralPath $profileList -ErrorAction SilentlyContinue)) {
        $sid = $entry.PSChildName
        if ($sid -notmatch '^S-1-5-21-(?:[0-9]+-){3}[0-9]+$') { continue }

        $mountedHive = $false
        try {
            $profile = Get-ItemProperty -LiteralPath $entry.PSPath -ErrorAction Stop
            $profilePath = [Environment]::ExpandEnvironmentVariables([string]$profile.ProfileImagePath)
            if ([string]::IsNullOrWhiteSpace($profilePath) -or -not (Test-Path -LiteralPath $profilePath -PathType Container)) { continue }

            $hivePath = $UserHivesRoot + "\" + $sid
            if (-not (Test-Path -LiteralPath $hivePath)) {
                $ntUserFile = Join-Path $profilePath "NTUSER.DAT"
                if (Test-Path -LiteralPath $ntUserFile -PathType Leaf) {
                    & "$env:SystemRoot\System32\reg.exe" load "HKU\$sid" "$ntUserFile" 2>$null | Out-Null
                    $mountedHive = ($LASTEXITCODE -eq 0)
                }
            }

            try {
                $localAppData = Get-ProfileLocalAppData -ProfilePath $profilePath -Sid $sid -UserHivesRoot $UserHivesRoot
                $dataDirectory = Join-Path $localAppData "EmployeeAuditManager"
                if (Test-Path -LiteralPath (Join-Path $dataDirectory "employee_audit.db") -PathType Leaf) {
                    $directories += $dataDirectory
                }
            }
            finally {
                if ($mountedHive) {
                    & "$env:SystemRoot\System32\reg.exe" unload "HKU\$sid" 2>$null | Out-Null
                }
            }
        }
        catch {
            if ($mountedHive) {
                & "$env:SystemRoot\System32\reg.exe" unload "HKU\$sid" 2>$null | Out-Null
            }
        }
    }

    return $directories
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
        $localAppData = Get-ProfileLocalAppData -ProfilePath $profilePath -Sid $interactiveSid -UserHivesRoot $UserHivesRoot
        $interactiveDataDirectory = Join-Path $localAppData "EmployeeAuditManager"
    }

    # Recover customer data even when the old EXE was removed or another admin
    # account launched Setup. Never guess between multiple customer databases.
    $candidates = @()
    if (-not $DisableInteractiveLookup) {
        $candidates += @(Get-RegisteredProfileDataDirectories)
    }
    if (Test-Path -LiteralPath $ProfilesRoot -PathType Container) {
        Get-ChildItem -LiteralPath $ProfilesRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $candidate = Join-Path $_.FullName "AppData\Local\EmployeeAuditManager"
            if (Test-Path -LiteralPath (Join-Path $candidate "employee_audit.db") -PathType Leaf) {
                $candidates += $candidate
            }
        }
    }
    $candidates = @($candidates | Sort-Object -Unique)

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
