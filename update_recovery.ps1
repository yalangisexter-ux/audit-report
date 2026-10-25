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

function Remove-DirectorySafely([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }

    try {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        if (-not (Test-Path -LiteralPath $Path)) { return }
    } catch {}

    try {
        Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
            try { $_.Attributes = 'Normal' } catch {}
        }
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        if (-not (Test-Path -LiteralPath $Path)) { return }
    } catch {}

    try {
        & cmd.exe /c "rmdir /s /q `"$Path`"" | Out-Null
    } catch {}

    if (Test-Path -LiteralPath $Path) {
        Start-Sleep -Milliseconds 300
        try {
            $junkPath = Join-Path ([System.IO.Path]::GetTempPath()) ('RSC-orphan-' + [guid]::NewGuid().ToString('N'))
            Move-Item -LiteralPath $Path -Destination $junkPath -Force -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $junkPath -Recurse -Force -ErrorAction SilentlyContinue
        } catch {}
    }

    if (Test-Path -LiteralPath $Path) {
        throw "Could not remove directory: $Path"
    }
}

function Stop-RunningAppProcesses {
    Get-Process -Name 'RawStrengthEmployeeAuditManager' -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $_.Kill()
            $_.WaitForExit(3000)
        } catch {}
    }
}

function Cleanup-StaleDirectories {
    param(
        [string]$InstallDir,
        [string]$BackupDir,
        [switch]$CleanBackupDir
    )

    if ($CleanBackupDir -and (Test-Path -LiteralPath $BackupDir)) {
        Remove-DirectorySafely -Path $BackupDir
    }

    $parentDir = Split-Path -Parent $InstallDir
    if (-not $parentDir -or -not (Test-Path -LiteralPath $parentDir)) { return }

    $installLeaf = Split-Path -Leaf $InstallDir
    $patterns = @(
        "$installLeaf.rollback.new-*",
        "$installLeaf.rollback.old-*",
        "$installLeaf.failed-*",
        "$installLeaf.restore-*"
    )
    foreach ($pat in $patterns) {
        Get-ChildItem -LiteralPath $parentDir -Filter $pat -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-DirectorySafely -Path $_.FullName
        }
    }
}

function Copy-VerifiedTree([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Source directory is missing: $Source"
    }
    if (Test-Path -LiteralPath $Destination) {
        Remove-DirectorySafely -Path $Destination
    }

    $null = New-Item -ItemType Directory -Path $Destination -Force
    & robocopy.exe $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /NFL /NDL /NJH /NJS /NP | Out-Null
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
            Stop-RunningAppProcesses
            Cleanup-StaleDirectories -InstallDir $InstallDir -BackupDir $BackupDir -CleanBackupDir
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
            Stop-RunningAppProcesses
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
                    Move-Item -LiteralPath $InstallDir -Destination $failedDir -Force
                    $movedCurrent = $true
                }
                Move-Item -LiteralPath $restoreDir -Destination $InstallDir -Force
            }
            catch {
                if ($movedCurrent -and -not (Test-Path -LiteralPath $InstallDir) -and (Test-Path -LiteralPath $failedDir)) {
                    Move-Item -LiteralPath $failedDir -Destination $InstallDir -Force -ErrorAction SilentlyContinue
                }
                throw
            }
            finally {
                if ($movedCurrent -and (Test-Path -LiteralPath $failedDir)) {
                    Remove-DirectorySafely -Path $failedDir
                }
                if (Test-Path -LiteralPath $restoreDir) {
                    Remove-DirectorySafely -Path $restoreDir
                }
            }

            Remove-DirectorySafely -Path $BackupDir
        }

        'promote' {
            if (-not (Test-Path -LiteralPath (Join-Path $BackupDir $exeName) -PathType Leaf)) {
                Cleanup-StaleDirectories -InstallDir $InstallDir -BackupDir $BackupDir -CleanBackupDir
                return
            }

            Cleanup-StaleDirectories -InstallDir $InstallDir -BackupDir $BackupDir

            $oldStable = $StableBackupDir + '.old-' + [guid]::NewGuid().ToString('N')
            $movedOld = $false
            try {
                if (Test-Path -LiteralPath $StableBackupDir) {
                    Move-Item -LiteralPath $StableBackupDir -Destination $oldStable -Force
                    $movedOld = $true
                }
                Move-Item -LiteralPath $BackupDir -Destination $StableBackupDir -Force
            }
            catch {
                try {
                    if (-not (Test-Path -LiteralPath $StableBackupDir)) {
                        $null = New-Item -ItemType Directory -Path $StableBackupDir -Force
                    }
                    & robocopy.exe $BackupDir $StableBackupDir /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /XJ /NFL /NDL /NJH /NJS /NP | Out-Null
                }
                catch {
                    if ($movedOld -and -not (Test-Path -LiteralPath $StableBackupDir) -and (Test-Path -LiteralPath $oldStable)) {
                        Move-Item -LiteralPath $oldStable -Destination $StableBackupDir -Force -ErrorAction SilentlyContinue
                    }
                    throw
                }
            }
            finally {
                if ($movedOld -and (Test-Path -LiteralPath $oldStable)) {
                    Remove-DirectorySafely -Path $oldStable
                }
                if (Test-Path -LiteralPath $BackupDir) {
                    Remove-DirectorySafely -Path $BackupDir
                }
            }
        }

        'remove-new' {
            Stop-RunningAppProcesses
            if (Test-Path -LiteralPath $InstallDir) {
                $failedDir = $InstallDir + '.failed-' + [guid]::NewGuid().ToString('N')
                Move-Item -LiteralPath $InstallDir -Destination $failedDir -Force -ErrorAction SilentlyContinue
                Remove-DirectorySafely -Path $failedDir
                if (Test-Path -LiteralPath $InstallDir) {
                    Remove-DirectorySafely -Path $InstallDir
                }
            }
        }
    }

    exit 0
}
catch {
    $msg = $_.Exception.Message
    [Console]::Error.WriteLine($msg)
    try {
        $logFile = Join-Path ([System.IO.Path]::GetTempPath()) 'update_recovery.log'
        Add-Content -LiteralPath $logFile -Value ("[{0}] [Mode={1}] ERROR: {2}" -f (Get-Date -Format 's'), $Mode, $msg) -ErrorAction SilentlyContinue
    } catch {}
    exit 1
}
