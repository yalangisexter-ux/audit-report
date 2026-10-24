param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('backup', 'launch-check', 'restore', 'promote', 'remove-new')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$InstallDir,

    [Parameter(Mandatory = $true)]
    [string]$BackupDir,

    [Parameter(Mandatory = $true)]
    [string]$StableBackupDir,

    [string]$ExpectedVersion = '',
    [string]$DataDir = ''
)

$ErrorActionPreference = 'Stop'
$exeName = 'RawStrengthEmployeeAuditManager.exe'
$exePath = Join-Path $InstallDir $exeName

function Copy-VerifiedTree([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Source directory is missing: $Source"
    }
    if (Test-Path -LiteralPath $Destination) {
        throw "Destination already exists: $Destination"
    }

    $null = New-Item -ItemType Directory -Path $Destination
    & robocopy.exe $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NFL /NDL /NJH /NJS /NP | Out-Null
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) {
        throw "File copy failed with Robocopy exit code $copyCode."
    }

    $sourceRoot = $Source.TrimEnd('\', '/')
    $sourceFiles = @(Get-ChildItem -LiteralPath $sourceRoot -File -Recurse -Force)
    $destinationFiles = @(Get-ChildItem -LiteralPath $Destination -File -Recurse -Force)
    if ($sourceFiles.Count -ne $destinationFiles.Count) {
        throw "Copy verification failed: file counts differ ($($sourceFiles.Count) vs $($destinationFiles.Count))."
    }

    $destinationMap = @{}
    foreach ($file in $destinationFiles) {
        $relativePath = $file.FullName.Substring($Destination.TrimEnd('\', '/').Length).TrimStart([char[]]'\/')
        $destinationMap[$relativePath] = $file.Length
    }
    foreach ($file in $sourceFiles) {
        $relativePath = $file.FullName.Substring($sourceRoot.Length).TrimStart([char[]]'\/')
        if (-not $destinationMap.ContainsKey($relativePath) -or $destinationMap[$relativePath] -ne $file.Length) {
            throw "Copy verification failed for file: $relativePath"
        }
    }
}

function Get-ProductVersion([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Application executable is missing: $Path"
    }
    return (Get-Item -LiteralPath $Path).VersionInfo.ProductVersion
}

try {
    switch ($Mode) {
        'backup' {
            Copy-VerifiedTree -Source $InstallDir -Destination $BackupDir
            if (-not (Test-Path -LiteralPath (Join-Path $BackupDir $exeName) -PathType Leaf)) {
                throw 'The backup does not contain the application executable.'
            }
        }

        'launch-check' {
            $productVersion = Get-ProductVersion -Path $exePath
            if ($ExpectedVersion -and $productVersion -notmatch ('^' + [regex]::Escape($ExpectedVersion) + '(\.|$)')) {
                throw "Installed executable version '$productVersion' does not match expected version '$ExpectedVersion'."
            }

            $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
            $smokeLocalAppData = Join-Path $tempRoot ('RSC-update-check-' + [guid]::NewGuid().ToString('N'))
            $originalLocalAppData = $env:LOCALAPPDATA
            $originalQtPlatform = $env:QT_QPA_PLATFORM

            try {
                $env:LOCALAPPDATA = $smokeLocalAppData
                $env:QT_QPA_PLATFORM = 'offscreen'
                $smokeDataDir = Join-Path $smokeLocalAppData 'EmployeeAuditManager'
                $null = New-Item -ItemType Directory -Path $smokeDataDir -Force
                if ($DataDir -and (Test-Path -LiteralPath (Join-Path $DataDir 'employee_audit.db') -PathType Leaf)) {
                    foreach ($dataFile in @('employee_audit.db', 'employee_audit.db-wal', 'employee_audit.db-shm')) {
                        $sourceFile = Join-Path $DataDir $dataFile
                        if (Test-Path -LiteralPath $sourceFile -PathType Leaf) {
                            Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $smokeDataDir $dataFile)
                        }
                    }
                }
                $process = Start-Process -FilePath $exePath -PassThru -WindowStyle Hidden
                Start-Sleep -Seconds 8
                $process.Refresh()
                if ($process.HasExited) {
                    throw "The updated app exited or crashed during startup check (exit code $($process.ExitCode))."
                }
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
            finally {
                $env:LOCALAPPDATA = $originalLocalAppData
                $env:QT_QPA_PLATFORM = $originalQtPlatform
                $resolvedSmokePath = [System.IO.Path]::GetFullPath($smokeLocalAppData)
                if ($resolvedSmokePath.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
                    (Split-Path -Leaf $resolvedSmokePath).StartsWith('RSC-update-check-', [System.StringComparison]::OrdinalIgnoreCase) -and
                    (Test-Path -LiteralPath $resolvedSmokePath)) {
                    Remove-Item -LiteralPath $resolvedSmokePath -Recurse -Force -ErrorAction SilentlyContinue
                }
            }
        }

        'restore' {
            if (-not (Test-Path -LiteralPath (Join-Path $BackupDir $exeName) -PathType Leaf)) {
                throw "The previous-version backup is missing or incomplete: $BackupDir"
            }

            $restoreDir = $InstallDir + '.restore-' + [guid]::NewGuid().ToString('N')
            $failedDir = $InstallDir + '.failed-' + [guid]::NewGuid().ToString('N')
            Copy-VerifiedTree -Source $BackupDir -Destination $restoreDir
            $restoredExe = Join-Path $restoreDir $exeName
            if ((Get-ProductVersion -Path $restoredExe) -ne (Get-ProductVersion -Path (Join-Path $BackupDir $exeName))) {
                throw 'The restored executable does not match the verified backup.'
            }

            $movedCurrent = $false
            try {
                if (Test-Path -LiteralPath $InstallDir) {
                    Move-Item -LiteralPath $InstallDir -Destination $failedDir
                    $movedCurrent = $true
                }
                Move-Item -LiteralPath $restoreDir -Destination $InstallDir
            }
            catch {
                if ($movedCurrent -and -not (Test-Path -LiteralPath $InstallDir) -and (Test-Path -LiteralPath $failedDir)) {
                    Move-Item -LiteralPath $failedDir -Destination $InstallDir -ErrorAction SilentlyContinue
                }
                throw
            }

            if ($movedCurrent -and (Test-Path -LiteralPath $failedDir)) {
                Remove-Item -LiteralPath $failedDir -Recurse -Force -ErrorAction SilentlyContinue
            }
            Remove-Item -LiteralPath $restoreDir -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $BackupDir -Recurse -Force -ErrorAction SilentlyContinue
        }

        'promote' {
            if (-not (Test-Path -LiteralPath (Join-Path $BackupDir $exeName) -PathType Leaf)) {
                throw "The verified previous-version backup is missing: $BackupDir"
            }

            $stableParent = Split-Path -Parent $StableBackupDir
            $stableName = Split-Path -Leaf $StableBackupDir
            $stableTemp = Join-Path $stableParent ($stableName + '.new-' + [guid]::NewGuid().ToString('N'))
            Copy-VerifiedTree -Source $BackupDir -Destination $stableTemp
            if (-not (Test-Path -LiteralPath (Join-Path $stableTemp $exeName) -PathType Leaf)) {
                throw 'The promoted previous-version backup failed verification.'
            }

            $oldStable = $StableBackupDir + '.old-' + [guid]::NewGuid().ToString('N')
            $movedOld = $false
            try {
                if (Test-Path -LiteralPath $StableBackupDir) {
                    Move-Item -LiteralPath $StableBackupDir -Destination $oldStable
                    $movedOld = $true
                }
                Move-Item -LiteralPath $stableTemp -Destination $StableBackupDir
            }
            catch {
                if ($movedOld -and -not (Test-Path -LiteralPath $StableBackupDir) -and (Test-Path -LiteralPath $oldStable)) {
                    Move-Item -LiteralPath $oldStable -Destination $StableBackupDir -ErrorAction SilentlyContinue
                }
                throw
            }

            if ($movedOld) {
                Remove-Item -LiteralPath $oldStable -Recurse -Force -ErrorAction SilentlyContinue
            }
            Remove-Item -LiteralPath $BackupDir -Recurse -Force -ErrorAction SilentlyContinue
        }

        'remove-new' {
            if (Test-Path -LiteralPath $InstallDir) {
                $failedDir = $InstallDir + '.failed-' + [guid]::NewGuid().ToString('N')
                Move-Item -LiteralPath $InstallDir -Destination $failedDir
                Remove-Item -LiteralPath $failedDir -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }

    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
