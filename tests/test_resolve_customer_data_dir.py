import shutil
import subprocess
from pathlib import Path

import pytest


POWERSHELL = shutil.which("powershell.exe")


def run_resolver(script: Path, output: Path, profiles: Path, *extra: str):
    return subprocess.run(
        [
            POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-OutputFile", str(output), "-ProfilesRoot", str(profiles),
            "-DisableInteractiveLookup", *extra,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


pytestmark = pytest.mark.skipif(not POWERSHELL, reason="Windows PowerShell is required")


def test_resolver_finds_unique_customer_database_after_exe_uninstall(tmp_path):
    script = Path(__file__).resolve().parents[1] / "resolve_customer_data_dir.ps1"
    profiles = tmp_path / "Users"
    data_dir = profiles / "Customer" / "AppData" / "Local" / "EmployeeAuditManager"
    data_dir.mkdir(parents=True)
    (data_dir / "employee_audit.db").write_bytes(b"customer database sentinel")
    output = tmp_path / "resolved.txt"

    proc = run_resolver(script, output, profiles)

    assert proc.returncode == 0, proc.stderr
    assert output.read_text(encoding="utf-8-sig") == str(data_dir)


def test_resolver_refuses_to_guess_between_multiple_customer_databases(tmp_path):
    script = Path(__file__).resolve().parents[1] / "resolve_customer_data_dir.ps1"
    profiles = tmp_path / "Users"
    for username in ("CustomerA", "CustomerB"):
        data_dir = profiles / username / "AppData" / "Local" / "EmployeeAuditManager"
        data_dir.mkdir(parents=True)
        (data_dir / "employee_audit.db").write_bytes(username.encode())
    output = tmp_path / "resolved.txt"

    proc = run_resolver(script, output, profiles)

    assert proc.returncode != 0
    assert "Refusing to guess" in proc.stderr
    assert not output.exists()


def test_resolver_allows_new_install_without_using_elevated_profile(tmp_path):
    script = Path(__file__).resolve().parents[1] / "resolve_customer_data_dir.ps1"
    profiles = tmp_path / "Users"
    profiles.mkdir()
    output = tmp_path / "resolved.txt"

    proc = run_resolver(script, output, profiles)

    assert proc.returncode == 0, proc.stderr
    assert output.read_text(encoding="utf-8-sig") == "__RSC_NO_EXISTING_PROFILE__"


def test_resolver_uses_interactive_profile_when_database_not_created_yet(tmp_path):
    script = Path(__file__).resolve().parents[1] / "resolve_customer_data_dir.ps1"
    profile = tmp_path / "Users" / "Customer"
    profile.mkdir(parents=True)
    profiles = tmp_path / "Users"
    output = tmp_path / "resolved.txt"

    proc = run_resolver(script, output, profiles, "-InteractiveProfilePath", str(profile))

    assert proc.returncode == 0, proc.stderr
    assert output.read_text(encoding="utf-8-sig") == str(profile / "AppData" / "Local" / "EmployeeAuditManager")
