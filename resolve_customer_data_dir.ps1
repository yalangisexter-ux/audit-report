param([Parameter(Mandatory = $true)][string]$OutputFile)

$ErrorActionPreference = "Stop"

try {
    # Resolve the interactive desktop user, not the elevated administrator account.
    $interactiveUser = [string](Get-CimInstance -ClassName Win32_ComputerSystem).UserName
    if ([string]::IsNullOrWhiteSpace($interactiveUser)) { throw "No interactive Windows user could be identified." }

    $account = [System.Security.Principal.NTAccount]::new($interactiveUser)
    $sid = $account.Translate([System.Security.Principal.SecurityIdentifier]).Value
    $profileKey = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\" + $sid
    $profile = Get-ItemProperty -LiteralPath $profileKey
    $profilePath = [Environment]::ExpandEnvironmentVariables([string]$profile.ProfileImagePath)
    if ([string]::IsNullOrWhiteSpace($profilePath) -or -not (Test-Path -LiteralPath $profilePath -PathType Container)) { throw "The interactive user profile could not be resolved." }

    $localAppData = Join-Path $profilePath "AppData\Local"
    $userShellFolders = "Registry::HKEY_USERS\" + $sid + "\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
    if (Test-Path -LiteralPath $userShellFolders) {
        $shellFolders = Get-ItemProperty -LiteralPath $userShellFolders -ErrorAction SilentlyContinue
        $configuredPath = [string]$shellFolders."Local AppData"
        if (-not [string]::IsNullOrWhiteSpace($configuredPath)) {
            $configuredPath = $configuredPath.Replace("%USERPROFILE%", $profilePath)
            $configuredPath = [Environment]::ExpandEnvironmentVariables($configuredPath)
            if ([System.IO.Path]::IsPathRooted($configuredPath)) { $localAppData = $configuredPath }
        }
    }

    $dataDirectory = Join-Path $localAppData "EmployeeAuditManager"
    [System.IO.File]::WriteAllText($OutputFile, $dataDirectory, [System.Text.Encoding]::UTF8)
    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
