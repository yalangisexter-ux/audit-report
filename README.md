# Raw Strength Calisthenics — Employee Audit Manager & Operations OS

## Modern React SPA + FastAPI REST API Interface (v1.3.81)

A React web interface built with **React 18**, **Tailwind CSS**, and **Lucide icons**, powered by a **FastAPI REST API** backend and the shared SQLite data model. Existing PBKDF2 account hashes and installation-scoped sync behavior are preserved. Desktop-to-web feature parity is tracked screen by screen and is not yet complete.

### Quick Start
To launch the modern web application and automatically open it in your browser:
```powershell
python run_web.py
```
- **Web App URL:** `http://127.0.0.1:8000`
- **Interactive REST API Docs (Swagger):** `http://127.0.0.1:8000/docs`
- **Alternative Dev Server (Vite HMR):** `cd frontend; npm run dev` (runs on `http://localhost:5173`)

### Key Features
- **Modern Cyberpunk/Executive Glassmorphism:** Deep navy gradients, glowing card HUDs, dynamic telemetry clocks, and sleek neon scrollbars.
- **Dynamic Custom Task Tracking:** The web Task Manager now exposes arbitrary key-value tracking fields (e.g., `Tracked By`, `Equipment`, `Inspection Result`) in create/edit forms, alongside target/actual quantities, extended statuses, evidence links, selective bulk editing and role-checked deletion.
- **Editable Department:** Free-text editable department field with auto-completion from existing organizational units.
- **Responsive Dialog Modals:** Center-anchored with max-height limits and internal scrolling to prevent modals from hiding under taskbars or screen edges.
- **Silent Background Sync HUD:** Real-time green auto-sync badge without disruptive loading screens or UI blocking.
- **Web account management:** Admin/Developer accounts can create active users, approve registrations, change roles, activate/deactivate accounts and reset passwords with the desktop PBKDF2 hash format and session invalidation.
- **Web Print Center:** Dedicated React workspace supports four report types, consolidated/individual/excluded employee scope, report-specific field toggles, preview, and PDF/DOCX/CSV export APIs. Side-by-side document layout and field verification remain in progress.
- **Compatibility and regression:** The web and Windows apps use the same SQLite data model and preserve existing PBKDF2 account hashes; run #1099 passed 270 regression tests plus React, Worker, EXE, installer, legacy-upgrade and customer-database-preservation checks. The daily employee target/report correction added after #1099 is awaiting the next CI run. Full feature parity remains in progress.

---

## Build a Windows release with GitHub Actions

1. Extract this ZIP and upload the contents of this folder to the root of a GitHub repository.
2. Open **Actions** and select **Master Build and Test**.
3. Select **Run workflow** or push to `main`.
4. Pushes to `main` publish a versioned GitHub Release. The Actions artifact `RawStrengthEmployeeAuditManager-Windows-Release` is also available for 14 days.
5. Extract the artifact and run `RawStrengthEmployeeAuditManager-Setup.exe`. Setup installs the required Visual C++ runtime before launching the app.

## Live Chat (Cloudflare)

- The Windows app supports private employee conversations and authorized groups. The current web screen supports general-channel messaging only; private/group chat, unread state, and reconnect parity remain open.
- A responsive browser/mobile client is served from the Cloudflare Worker. The chat backend is separate from the local audit database.
- Deploy the service using the instructions in [Cloudflare Live Chat setup](cloudflare-chat/README.md). Configure a real D1 database ID and Cloudflare secrets before deploying; source-control changes alone do not deploy the service.
- Chat accounts are provisioned by the chat administrator and use separate credentials from the existing local Audit Manager login.

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

- Web navigation uses a collapsible left sidebar. The Windows EXE retains its native navigation and controls; the parity ledger records missing web actions.
- The Home page opens first with signed-in session details and concise instructions and examples for each section.
- The interface follows the supplied purple dashboard and blue project-management references, with Raw Strength branding and the bundled DejaVu Sans font.
- Forms use readable controls; report scope/options and PDF/DOCX/CSV exports are implemented, while side-by-side document layout and field parity remain under verification.
- The first run against a fresh database requires creating an Admin username, password, and recovery question/answer before login. No default password is provided.

## Reports

- **Audit / EOD:** reference-style employee-by-employee bullet points; status only, no task progress percentages, productivity scores, or attendance details. Optional sections are controlled by checkboxes.
- **Employee Productivity:** separate report for productivity score, calculation explanation, and task progress percentages.
- **Employee Attendance:** separate attendance report.
- **Employee Details:** separate employee register.
- **Daily target/status:** Task Manager loads and saves the selected employee's target and target status by work date, matching the desktop Task Dialog and Audit / EOD report data model.
- The Windows EXE and web Print Center both support Consolidated and Individual scopes, employee exclusions, selected sections, and PDF/Word/CSV exports. Remaining work is document-layout/field-by-field comparison and browser verification against the EXE.
- Missing Employee ID, Department, or Role is shown as `N/A`.

## Data and existing installations

The database is stored in the current Windows user's Local AppData under `EmployeeAuditManager`; rebuilding/upgrading the EXE does not intentionally erase it. Back up the database before changing versions. If an older installation already has an Admin account but you do not know its password, the first-run setup will not reappear just because the EXE was rebuilt; use the recovery flow or a data-preserving account-recovery procedure.

## Build notes

The GitHub Actions workflow installs dependencies and packages `assets/` into the executable. Test the built EXE, initial account setup, report previews/exports, printing, and database backup/restore on the target Windows machine before production use.


## Installer and data safety

The GitHub Actions workflow builds an onedir application bundle and an Inno Setup installer. The installer creates Start Menu and optional Desktop shortcuts. The SQLite database and backups remain in the current user's Local AppData and are not stored in the install directory; the installer script intentionally does not remove them during uninstall. Always create a database backup before replacing a production build.
