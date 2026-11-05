import subprocess
import sys
from pathlib import Path
import pytest


def run_powershell(script_path: Path, args: list[str]) -> subprocess.CompletedProcess:
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def test_backup_succeeds_when_destination_already_exists(tmp_path):
    script_path = Path(__file__).resolve().parents[1] / "update_recovery.ps1"
    assert script_path.exists()

    install_dir = tmp_path / "AppDir"
    install_dir.mkdir()
    exe_file = install_dir / "RawStrengthEmployeeAuditManager.exe"
    exe_file.write_bytes(b"dummy executable content 1.3.43")
    (install_dir / "data.txt").write_text("current app data", encoding="utf-8")

    backup_dir = tmp_path / "AppDir.rollback-pending"
    backup_dir.mkdir()
    (backup_dir / "stale_old_file.txt").write_text("old stale data", encoding="utf-8")

    stable_dir = tmp_path / "AppDir.rollback"

    # Prior code threw "Destination already exists" here. Now it safely cleans and backs up.
    proc = run_powershell(
        script_path,
        [
            "-Mode", "backup",
            "-InstallDir", str(install_dir),
            "-BackupDir", str(backup_dir),
            "-StableBackupDir", str(stable_dir),
        ],
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert (backup_dir / "RawStrengthEmployeeAuditManager.exe").exists()
    assert (backup_dir / "data.txt").read_text(encoding="utf-8") == "current app data"
    assert not (backup_dir / "stale_old_file.txt").exists()


def test_backup_cleans_up_stale_transient_folders(tmp_path):
    script_path = Path(__file__).resolve().parents[1] / "update_recovery.ps1"

    install_dir = tmp_path / "AppDir"
    install_dir.mkdir()
    (install_dir / "RawStrengthEmployeeAuditManager.exe").write_bytes(b"binary")

    stale_new = tmp_path / "AppDir.rollback.new-12345"
    stale_new.mkdir()
    (stale_new / "orphan.txt").write_text("orphan", encoding="utf-8")

    backup_dir = tmp_path / "AppDir.rollback-pending"
    stable_dir = tmp_path / "AppDir.rollback"

    proc = run_powershell(
        script_path,
        [
            "-Mode", "backup",
            "-InstallDir", str(install_dir),
            "-BackupDir", str(backup_dir),
            "-StableBackupDir", str(stable_dir),
        ],
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert not stale_new.exists()


def test_promote_promotes_backup_to_stable_and_cleans_pending(tmp_path):
    script_path = Path(__file__).resolve().parents[1] / "update_recovery.ps1"

    install_dir = tmp_path / "AppDir"
    install_dir.mkdir()
    (install_dir / "RawStrengthEmployeeAuditManager.exe").write_bytes(b"installed binary")

    backup_dir = tmp_path / "AppDir.rollback-pending"
    backup_dir.mkdir()
    (backup_dir / "RawStrengthEmployeeAuditManager.exe").write_bytes(b"backed-up binary")
    (backup_dir / "backup_marker.txt").write_text("marker", encoding="utf-8")

    stable_dir = tmp_path / "AppDir.rollback"
    stable_dir.mkdir()
    (stable_dir / "RawStrengthEmployeeAuditManager.exe").write_bytes(b"old stable binary")

    proc = run_powershell(
        script_path,
        [
            "-Mode", "promote",
            "-InstallDir", str(install_dir),
            "-BackupDir", str(backup_dir),
            "-StableBackupDir", str(stable_dir),
        ],
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert not backup_dir.exists()
    assert (stable_dir / "RawStrengthEmployeeAuditManager.exe").read_bytes() == b"backed-up binary"
    assert (stable_dir / "backup_marker.txt").exists()



def test_update_startup_check_uses_real_windows_qt_platform():
    script_path = Path(__file__).resolve().parents[1] / "update_recovery.ps1"
    source = script_path.read_text(encoding="utf-8")
    # The app uses Qt/WebEngine. Forcing the offscreen platform during an installer
    # startup check can make a valid Windows GUI build exit before the customer sees it.
    assert "$env:QT_QPA_PLATFORM = 'offscreen'" not in source
    assert "$env:LOCALAPPDATA = $smokeLocalAppData" in source


def test_failed_fresh_install_cleanup_never_touches_customer_database(tmp_path):
    script_path = Path(__file__).resolve().parents[1] / "update_recovery.ps1"
    install_dir = tmp_path / "Program Files" / "Raw Strength Employee Audit Manager"
    install_dir.mkdir(parents=True)
    (install_dir / "RawStrengthEmployeeAuditManager.exe").write_bytes(b"new app")
    customer_data = tmp_path / "CustomerProfile" / "AppData" / "Local" / "EmployeeAuditManager"
    customer_data.mkdir(parents=True)
    database = customer_data / "employee_audit.db"
    database.write_bytes(b"customer sqlite bytes")
    wal = customer_data / "employee_audit.db-wal"
    wal.write_bytes(b"customer wal bytes")

    proc = run_powershell(
        script_path,
        [
            "-Mode", "remove-new",
            "-InstallDir", str(install_dir),
            "-BackupDir", str(customer_data / "pending-update-backup"),
            "-StableBackupDir", str(customer_data / "previous-version"),
            "-DataDir", str(customer_data),
        ],
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\\nSTDERR: {proc.stderr}"
    assert not install_dir.exists()
    assert database.read_bytes() == b"customer sqlite bytes"
    assert wal.read_bytes() == b"customer wal bytes"
