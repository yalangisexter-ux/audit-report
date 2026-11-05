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



def test_resolver_finds_database_in_custom_local_appdata_from_profile_registry(tmp_path):
    import uuid
    import winreg

    script = Path(__file__).resolve().parents[1] / "resolve_customer_data_dir.ps1"
    profiles = tmp_path / "Users"
    profiles.mkdir()
    profile = tmp_path / "CustomerProfile"
    profile.mkdir()
    custom_local = tmp_path / "RedirectedLocalData"
    data_dir = custom_local / "EmployeeAuditManager"
    data_dir.mkdir(parents=True)
    (data_dir / "employee_audit.db").write_bytes(b"custom local appdata database")
    output = tmp_path / "resolved.txt"

    sid = "S-1-5-21-111-222-333-1001"
    registry_root = "Software\\RSCResolverTests\\" + uuid.uuid4().hex
    profile_key = registry_root + "\\ProfileList\\" + sid
    hive_key = registry_root + "\\Hives\\" + sid + "\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders"

    def delete_registry_tree(path):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                    except OSError:
                        break
                    delete_registry_tree(path + "\\" + child)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, profile_key) as key:
            winreg.SetValueEx(key, "ProfileImagePath", 0, winreg.REG_EXPAND_SZ, str(profile))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, hive_key) as key:
            winreg.SetValueEx(key, "Local AppData", 0, winreg.REG_SZ, str(custom_local))

        proc = subprocess.run(
            [
                POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-File", str(script), "-OutputFile", str(output), "-ProfilesRoot", str(profiles),
                "-InteractiveProfilePath", str(profile),
                "-ProfileListRoot", "HKCU:\\" + registry_root + "\\ProfileList",
                "-UserHivesRoot", "Registry::HKEY_CURRENT_USER\\" + registry_root + "\\Hives",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert output.read_text(encoding="utf-8-sig") == str(data_dir)
    finally:
        delete_registry_tree(registry_root)
