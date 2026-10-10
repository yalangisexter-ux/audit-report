# Raw Strength Calisthenics — Employee Audit Manager

## What's in this package
- `app.py`: desktop application with embedded historical audit seed data.
- `assets/raw_strength_brand.png`: Raw Strength branding artwork.
- `assets/raw_strength_athlete.png`: athlete visual used in the dashboard header.
- `assets/DejaVuSans.ttf` and `assets/DejaVuSans-Bold.ttf`: bundled Unicode-capable PDF fonts for reliable glyph rendering and alignment.
- `.github/workflows/build-windows.yml`: builds a standalone Windows executable on GitHub Actions.
- `requirements.txt`: packages for local development; the workflow installs the build dependencies directly.

## Build a Windows EXE with GitHub Actions
1. Create a GitHub repository and upload the contents of this folder to its root.
2. Push to `main`/`master`, or open **Actions** and manually run **Build Raw Strength Employee Audit Manager (Windows)**.
3. When the run completes, open the run summary and download the `RawStrengthEmployeeAuditManager-Windows-EXE` artifact.
4. Extract the artifact and run `RawStrengthEmployeeAuditManager.exe` on Windows.

## PDF report layout update
PDF exports use a consistent embedded DejaVu Sans font, controlled page margins, aligned report title/date/scope, bullet-point employee and task sections, clickable-looking plain-text proof URLs, and page-number footers. PDF reports are intentionally **not rendered as tables**. The report types remain Employee Attendance, Employee Details, and Audit/EOD, with consolidated or individual scope and PDF/Word/CSV formats. Archived historical PDFs can be selected in Print Center for viewing/exporting/printing.

## Data and security notes
- The application stores records in a local SQLite database under the current user's local application-data directory.
- The historical source audit dated 09 October 2026 is embedded in `app.py`.
- Back up the database regularly. A database restore replaces current data with the selected backup.
- Test first-run account setup, all report formats, printing, and backup/restore on the intended Windows machine before production use.
- The GitHub Actions workflow has not been run from this environment, and a Windows `.exe` has not been built or verified here.
