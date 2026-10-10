# Raw Strength Calisthenics — Employee Audit Manager

## Build a standalone Windows EXE with GitHub Actions

1. Extract this ZIP and upload the contents of this folder to the root of a GitHub repository.
2. Open **Actions** and select **Build Raw Strength Employee Audit Manager (Windows)**.
3. Select **Run workflow** or push to `main` / `master`.
4. After the workflow succeeds, download `RawStrengthEmployeeAuditManager-Windows-Release`. Use `RawStrengthEmployeeAuditManager-Setup.exe` for installation, or the standalone EXE if preferred.
5. Extract the artifact and run `RawStrengthEmployeeAuditManager.exe`.

The target Windows PC does not need Python installed.

## UI updates

- Main navigation is displayed horizontally above the page content, not in a side panel.
- The dark navy/cyan theme, Raw Strength branding, and athlete image assets are retained.
- Forms use readable dropdowns and checkboxes where choices or multi-selection are appropriate; report scope and report options remain explicit.
- The first run against a fresh database requires creating an Admin username, password, and recovery question/answer before login. No default password is provided.

## Reports

- **Audit / EOD:** reference-style employee-by-employee bullet points; status only, no task progress percentages, productivity scores, or attendance details. Optional sections are controlled by checkboxes.
- **Employee Productivity:** separate report for productivity score, calculation explanation, and task progress percentages.
- **Employee Attendance:** separate attendance report.
- **Employee Details:** separate employee register.
- Consolidated and Individual scopes are supported. PDF, Word, and CSV exports are available where applicable.
- Missing Employee ID, Department, or Role is shown as `N/A`.

## Data and existing installations

The database is stored in the current Windows user's Local AppData under `EmployeeAuditManager`; rebuilding/upgrading the EXE does not intentionally erase it. Back up the database before changing versions. If an older installation already has an Admin account but you do not know its password, the first-run setup will not reappear just because the EXE was rebuilt; use the recovery flow or a data-preserving account-recovery procedure.

## Build notes

The GitHub Actions workflow installs dependencies and packages `assets/` into the executable. Test the built EXE, initial account setup, report previews/exports, printing, and database backup/restore on the target Windows machine before production use.


## Installer and data safety

The GitHub Actions workflow now builds both the standalone EXE and an Inno Setup installer. The installer creates Start Menu and optional Desktop shortcuts. The SQLite database and backups remain in the current user's Local AppData and are not stored in the install directory; the installer script intentionally does not remove them during uninstall. Always create a database backup before replacing a production build.
