# Raw Strength Calisthenics — Employee Audit Manager

## Build a Windows release with GitHub Actions

1. Extract this ZIP and upload the contents of this folder to the root of a GitHub repository.
2. Open **Actions** and select **Build Raw Strength Employee Audit Manager (Windows)**.
3. Select **Run workflow** or push to `main` / `master`.
4. Pushes to `main` / `master` publish a versioned GitHub Release. The Actions artifact `RawStrengthEmployeeAuditManager-Windows-Release` is also available for 14 days.
5. Extract the artifact and run `RawStrengthEmployeeAuditManager-Setup.exe`. Setup installs the required Visual C++ runtime before launching the app.

## In-app updates

- Select **Update application** on the Home page to check the latest GitHub Release.
- New installers are downloaded in the background over HTTPS from the public GitHub release.
- Confirming the update closes the app and opens the installer. Windows may request administrator approval; the existing database and backups stay in Local AppData.
- The built-in updater requires the GitHub repository to be public and releases to include the setup installer (`RawStrengthEmployeeAuditManager-Setup.exe`).

## Public download

Latest Windows installer: [GitHub Releases](https://github.com/yalangisexter-ux/audit-report/releases/latest)

Anyone with the link can download the installer without a GitHub account.

The target Windows PC does not need Python installed. Use the setup installer for first installs and updates; it installs the Visual C++ runtime prerequisite and places the application DLLs in the installed app folder.

## UI updates

- Main navigation stays horizontal above the page content, with the existing feature pages and controls retained.
- The Home page opens first with signed-in session details and concise instructions and examples for each section.
- The interface follows the supplied purple dashboard and blue project-management references, with Raw Strength branding and the bundled DejaVu Sans font.
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

The GitHub Actions workflow builds an onedir application bundle and an Inno Setup installer. The installer creates Start Menu and optional Desktop shortcuts. The SQLite database and backups remain in the current user's Local AppData and are not stored in the install directory; the installer script intentionally does not remove them during uninstall. Always create a database backup before replacing a production build.
