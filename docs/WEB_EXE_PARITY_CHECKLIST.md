# Web / Windows EXE feature-parity tracker

Last inspected: 2026-11-06 IST. Repository target: `main`. This is an evidence ledger, not a completion claim.

## Verification baseline

- Latest successful full regression + Windows installer verification: [Master Build and Test run #1156](https://github.com/yalangisexter-ux/audit-report/actions/runs/42152945307), tested code commit `6da2a434d5e3462b552cabc0c237877b2b9f0cc9`, passed **318 regression tests** in 450.26s. React production build/publication, Cloudflare chat and isolated database-sync Worker validation, Python compilation, PyInstaller EXE build, Inno Setup installer, legacy v1.1.74 in-place upgrade, uninstall/reinstall database hash + SQLite integrity + sentinel preservation, and 8-second packaged-process smoke all passed. Artifact `13473287981` is a private Actions artifact (75,041,864 bytes; expires after 14 days). Public release publication was skipped because version remains v1.3.81.
- Latest published desktop release is [v1.3.81](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.81). Run #1102 rebuilt the installer from commit `8c61bb9becbd7dbbb4a38a42bfebf5d25207670d`, uploaded it to the public release and verified exactly one non-draft/non-prerelease installer asset. Direct installer: [RawStrengthEmployeeAuditManager-Setup.exe](https://github.com/yalangisexter-ux/audit-report/releases/download/v1.3.81/RawStrengthEmployeeAuditManager-Setup.exe). Verified release asset SHA-256: `231b73d3476dd338d98e83a6874618b8b300890652c8c21a03de261cbe9ece1c`.
- The application source tested in run #1156 is commit `6da2a434d5e3462b552cabc0c237877b2b9f0cc9`. Subsequent `main` commits have added only installation-scoped encrypted snapshots under `customer-data/` and parity-documentation updates; no application source changed. The latest published frontend bundle contains the authenticated render-error recovery boundary and archived-report Print Center actions.
- Latest published desktop release is [v1.3.81](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.81). Version metadata is consistently v1.3.81 across `build_info.py`, `installer.iss`, `version_info.txt`, `.github/workflows/master.yml`, and `frontend/package.json`. Do not bump for minor web-only parity corrections (daily employee target/report sync, Store Directory workbook/region/export work, and read-API security).
- Follow-ups are committed directly to `main`; generated encrypted customer snapshot files are preserved and no feature branches or PRs are used.
- Cloudflare DB-sync Worker version **809**, deployment `7750fd42-8700-454c-87cf-930c9c468a02`, is at **100%** traffic (latest deployment 2026-11-05 07:48 UTC; Worker commit annotation `f64f344bb42acd1881a5fe92fc269e7ad83fde5f`). Existing Durable Object namespace and binding types remain present. Run #1099 passed the isolated Worker validation/test step.
- Cloudflare Live Chat Worker `raw-strength-employee-chat` version **630** is deployed at **100%** traffic (deployment `4540ccc5-3c68-4892-a951-2373712c91b1`, 2026-10-31 05:30 UTC). The Worker script source last changed 2026-10-16 and the browser client assets last changed 2026-10-29, so the active deployment postdates both. Its `ASSETS`, D1, and `ChatRoom` Durable Object bindings are present; secret values were not read. The React iframe integration uses this existing deployment and does not require a Worker code or binding change.
- Last confirmed Render deployment remains application commit `8d01e178f265e303855273f17ba35e637669cdb4`, deployment `dep-dbm5r6jbc2fs73apuko0`, at 2026-11-05 10:44 UTC; it reported Live and `HEAD /` returned HTTP 200. Source commits `11fdb130`, `1095b982`, and `6da2a434` are now in `main`; repository `render.yaml` builds the React app from `frontend/src`, includes `api_server.py` in the build filter, uses `checksPass`, and defines `/api/health`. The live service's adoption/deployment result still cannot be verified until the user explicitly selects Yalangis's Render workspace; no Render resource was changed.
- The last recorded live-dashboard inspection found the Render service on Free, without a persistent disk or health-check path, using older build/start commands and auto-deploying every commit. Repository `render.yaml` describes `checksPass`, build filters and `/api/health`, but adoption is not revalidated in this run. Free filesystem durability and write-to-snapshot recovery remain blockers; no paid plan or storage change was made.
- The web migration is **not complete**. The screen-by-screen rows below remain Partial or In progress until every desktop action, field, permission and workflow has been browser-verified against the EXE using representative customer data, and production sync/health checks pass.

## Screen-by-screen parity ledger

| Desktop screen / workflow | Web implementation inspected | Status | Remaining verification / gaps |
|---|---|---|---|
| Login, registration, password recovery, account management | React login, pending registration, recovery question/reset, Admin-created active accounts, role changes, activation/deactivation and Admin password reset; root-level `AppErrorBoundary` now renders a readable recovery panel instead of leaving only the wallpaper after a React render exception | CI verified in run #1156; browser parity pending | The `clockModeBusy` render crash was removed and guarded by tests. Run #1156 includes the new error-boundary regression. Verify exact-case Admin/admin login, every role/permission edge and recovery behavior in a browser using representative customer accounts.
| Home workspace | Distinct React Home page with signed-in session/version strip, Update Center and previous-version navigation, quick theme/wallpaper/custom-image controls, the 11-card desktop Workspace Guide, and live Business Tracking metrics (products, low stock, orders, active members, activities and sales) from an authenticated read API | CI verified in run #1139; browser parity pending | Run #1139 passed 307 regression tests, React production build/publication, Worker validation/tests, Python compilation, Windows EXE and Inno Setup installer builds, legacy v1.1.74 in-place upgrade, uninstall/reinstall database hash + SQLite integrity + sentinel preservation, and packaged launch smoke. Browser navigation, responsive layout, appearance persistence and live business counts still require side-by-side verification against the EXE. |
| Dashboard | Five clickable desktop KPI cards, Operations Command banner, five quick actions, recent active employees, 12-row task/progress table, attendance gauge/roster, productivity bars and score summary; API calculates active-roster counts and desktop-compatible productivity in batched queries | CI verified; browser parity pending | Run #1129 passed the dashboard calculation regressions and installer-preservation pipeline. The React Dashboard remains separate from Home after this correction. Browser side-by-side checks, role-specific navigation and live production data verification remain. |
| Employees | Create/list/edit/status and soft/permanent delete with safety backup; employee code, name, section/department, designation, phone, email, joining date and notes; employee-group create/rename/delete/order and custom employee ordering/move-to-group APIs | CI verified; browser parity pending | Existing API regressions passed in run #1129. Browser-verify every field, group action, inactive-employee flow and role matrix against the EXE using representative customer data. |
| Task Manager | Dedicated React UI/API cover assignment, date, department, details, due time, target/actual, per-employee/per-date target and target-status read/write, progress, priority, status (including Not selected), proof URL/note, next action, report-link exposure, dynamic custom fields, filters, search, selection, full desktop bulk-edit fields, evidence opening and Admin/Developer-only delete | CI verified; browser parity pending | Run #1129 passed the full current task/API regression suite and Windows installer-preservation pipeline. Browser functional verification against the EXE and production sync/storage checks remain. |
| Employee Tracker | Dedicated React Task Manager in Tracker mode with employee/date selectors, task KPIs, filtered task list, add/edit/delete, proof opening and shared Task Manager API/model | CI verified; browser parity pending | Existing tracker regressions and the full suite passed in run #1129. Direct browser side-by-side testing against the desktop EXE and representative customer data, plus production sync/storage verification, remain. |
| Attendance & Working Calendar | Daily roster, selected date, status marking, time/remarks editing, employee filter, multi-selection, selective bulk edit, net hours, monthly totals and holiday declaration/removal | CI validation pending; browser parity pending | Windows inline editor date-change flushing remains covered by run #1129. Web now saves every pending row draft against the currently selected date before loading a new date; saving one row preserves other pending rows, and a Save all action is available. New frontend regression guards are included in this change. Direct browser side-by-side verification on a representative customer database, role restrictions and legacy attendance detail display remain. |
| Print Center / Reports | Dedicated React Print Center with four report types, consolidated/individual/excluded employee scope, date and report-specific field toggles, preview, PDF/DOCX/CSV export, always-visible business product/service catalog options, historical archived-PDF selector, archived view/print/export-copy actions and navigation to the shared archive | CI verified in run #1156; document/browser parity pending | Run #1156 passed archive-selection/API-default regressions, PDF font/logo coverage and the full installer-preservation pipeline. EOD attendance is now excluded by default, matching the Windows option set. Compare generated PDF content/layout field-by-field against the EXE and verify archive selection, preview, print and downloads in a browser.
| Historical EOD Archive | Multi-PDF upload, employee/date/notes association, searchable selection, inline view, export, refresh, Admin/Developer delete; Print Center can now select archived PDFs and reuse the same authenticated view/download endpoints | CI verified in run #1156; browser parity pending | Run #1156 passed the new Print Center archive-action regressions and existing archive authentication/role/metadata coverage. Direct browser side-by-side verification and production storage/sync checks remain.
| Business Tracking | Dedicated React workspace with Dashboard, Products & Inventory, stock movement ledger, Orders, Services & Members, and Employee Activities | CI verified; browser parity pending | Run #1129 passed the current Business Tracking API/UI regression coverage. Direct browser/EXE side-by-side verification, permission checks and production sync/storage verification remain. |
| Store Directory / Scraping | Evidence-backed public merchant scraping, create/edit/delete APIs, branch-aware dedupe, address/email/website/Maps fields, Admin/Developer edit/delete permissions, encrypted-sync callback on scrape commits, stable keyset API pagination, 100-row React paging, workbook import/merge, regional benchmark import, filtered CSV/XLSX exports, regional summary and print previews | CI verified; browser/production parity pending | Run #1129 passed the current Store Directory regressions, including scraper sync callback and keyset pagination. Browser-verify filters/exclusions, map links, print workflows, real merchant source accuracy and dedupe against representative customer data. Confirm the 5,003-row production dataset has no gaps or duplicates. |
| Live Chat | Main React Live Chat tab now embeds the existing Worker-served client for private/group conversations, authorized membership, reconnect, WebRTC audio/video and screen sharing; it also offers reload/open-in-new-tab. The prior general-channel history and send action remain available as a second tab using the existing authenticated web API. | Partial | The integration and separate-auth boundary passed source/API regression coverage in run #1129. Browser-verify embed storage, camera/microphone/display-capture permissions, private/group membership, reconnect and general-channel send/history against the desktop workflow. The desktop support-chat mode and chat identity are not yet fully unified with the main Audit Manager login. |
| Settings & Backup | Web account activation and self-service Change password; working-week configuration; authenticated DB health/counts, encrypted sync status/manual sync, backup download and validated restore; employee CSV export including inactive staff; global proof-link exposure; explicit Google Sheets master-workbook pull with exact lowercase `admin` developer-password gate; four themes, 17 wallpaper styles, custom wallpaper upload, and browser-local Digital/Analog clock mode | CI verified; browser and production verification pending | Run #1129 passed the account/password, settings, Google Sheets authorization, CSV, proof-link, appearance and earlier clock API tests. The new browser-local clock preference correction awaits CI. Live workbook pull, browser permission/UX behavior, clock reload persistence, wallpaper reload/reset, and production encrypted-sync checks remain. |
| Cloud sync / customer data | Web standalone encrypted snapshot bootstrap/polling; installation-scoped database sync | Partial | Verify multi-device conflict behavior, identity/password hash preservation, rollback/recovery and production health under real customer data. |
| Updater / rollback | Authenticated web Update Center reports the current and latest stable versions, validates the official Windows installer asset metadata, links the latest installer, and lists previous stable installers only after Admin/Developer password re-authentication | CI verified; browser and Windows rollback verification pending | Run #1129 passed the Update Center API/RBAC/asset-filtering regressions. Browser-test current/update/offline states, role/password denial, release metadata filtering and actual downloads. A browser cannot execute an EXE; actual rollback still requires a Windows test after a verified database backup, including older-build compatibility and customer DB preservation. |

## Attendance milestone added in this change

- The web attendance roster now exposes the desktop's core daily fields: status, check-in, check-out, net hours and remarks.
- Added employee filtering, multi-selection, field-selective bulk edit, holiday banner/lockout and monthly workday/present/absent/leave/holiday/total-present summary.
- Added authenticated attendance read/write/summary endpoints, server-side time/status/holiday validation, and atomic bulk persistence.
- Added regression coverage for desktop-compatible summary counting, bulk-edit preservation/clearing, invalid time inputs and attendance API persistence. Run #958 passed all 201 tests, Windows EXE packaging, installer creation, legacy v1.1.74 database-preservation upgrade, and launch smoke test.
- The attendance milestone is released as v1.3.75; v1.3.76 is configured for the next verified release build.

## EOD Archive web milestone — CI verified in run #1129; browser parity pending

- Replaced the single-file upload control with multi-PDF upload matching the desktop workflow; employee association, optional report date and notes are applied to each selected PDF.
- Added searchable archive rows with employee, report date, upload time, notes and file size; users can select a document, view it inline, export it, refresh the list, and delete the selected document when authorized.
- Added an authenticated inline-view endpoint. Archive listing and downloads now require a valid session; PDF responses use private no-store caching and X-Content-Type-Options: nosniff.
- Kept permanent deletion restricted to Admin/Developer on the server; the web UI disables the action for other roles. Existing archive records and the archived_documents schema are unchanged.
- Added regression coverage for unauthenticated access, Staff read/view/export, Admin-only deletion, PDF metadata association, and invalid PDF rejection.
- Run #1129 passed the React build, Python regression suite, Windows EXE/installer and legacy database-preservation upgrade. Production deployment, direct browser side-by-side verification and production persistence checks must pass before marking it Complete.

## User account management milestone — CI verified in run #1129; browser verification pending

- Added Admin/Developer-only account creation from Settings, including username, display name, role, initial password and recovery question/answer. New accounts are active immediately, matching the Windows Manage User Accounts workflow; public self-registration remains pending until an Admin activates it.
- Added role changes for Staff, HR, Admin and Developer accounts. The last active Admin cannot be demoted. Developer accounts and Developer-role assignment remain restricted to Developer callers to preserve the web application's existing developer-account isolation.
- Added Admin password reset using the same desktop_app.hash_pin PBKDF2 scheme as the EXE. Password plaintext is never logged or returned.
- Account deactivation, role changes and password resets invalidate the target's in-memory and persistent web sessions. Account actions are recorded in audit_log; existing usernames, IDs, password hashes and recovery hashes are not rewritten by role changes.
- Added seven regression tests covering account creation and case-insensitive duplicate rejection, role updates without hash changes, last-Admin protection, password hashing/session invalidation, Staff denial, Developer isolation, and standalone persistent-session invalidation.
- This major account-management milestone was configured as v1.3.79 across build_info.py, installer.iss, version_info.txt, and .github/workflows/master.yml. Run #1129 passed the current account-management regressions and Windows packaging/legacy-upgrade checks. No new release was published; production deployment and browser role verification remain.

## Daily employee target / Print Center parity correction — CI verified

- The Windows Task Dialog stores an employee target and target status by employee/date in `employee_targets`; Audit / EOD Print Center reports read that table.
- The web Task Manager already exposed target and actual quantity fields, but the API only persisted them in `tasks`. A web-created or edited task could therefore leave the daily target/status record stale and make the web report show `N/A` even when the desktop had a saved value.
- This correction adds an authenticated read endpoint, loads the saved values when employee/date changes, and upserts the target/status in the same task transaction. It only changes `employee_targets` when the client actually supplied one of the quantity fields, preserving the record for older clients that omit them.
- Regression coverage checks read, create, edit, report preview, and preservation of both task quantities and the daily target record when older clients omit those fields. Run #1100 failed before Python tests at Vite parsing (`TaskManager.jsx:103`) because the hook insertion dropped a closing bracket; this follow-up restores the state declaration and adds the legacy task-field assertion. Run #1101 passed all 271 regression tests, React/Worker validation, Windows EXE/installer build, legacy upgrade, uninstall/reinstall database hash + integrity/sentinel checks, and launch smoke test. No version bump is required.

## Attendance inline editor date-change persistence correction — CI verified in run #1102

- The Attendance roster renders inline check-in, check-out and remarks editors. Changing the selected date rebuilds the table; an editor that has not yet emitted `editingFinished` could be destroyed before its latest text reached SQLite.
- The follow-up captures pending editor values using the date shown in the old row, validates HH:MM and check-out/check-in consistency, commits them in a SQLite savepoint before the date change, and schedules the existing encrypted sync callback. Invalid values keep the previous date selected instead of silently discarding text.
- Toolbar and bulk status writes mark their visible values as acknowledged so stale editor contents cannot overwrite an intentional Absent/Leave/Unmarked update.
- New regression tests cover saving uncommitted check-in/check-out/remarks across a date change, reopening SQLite to verify persistence, blocking navigation when a pending time is invalid, and preventing a stale editor from undoing a toolbar Absent status. Run #1102 passed all of them as part of 274 tests, along with the v1.3.81 Windows installer, legacy upgrade, uninstall/reinstall DB-preservation and launch smoke checks. This is a maintenance correction; no version bump is required.

## Main React Live Chat integration — CI verified in run #1129; browser integration remains partial

- Added the existing Worker-hosted private/group chat client to the main React tab using the same `chat-web/` assets served by Cloudflare. The React workspace now exposes the desktop's private/group conversation workflow, member-only authorization, reconnect, audio/video and screen-share controls.
- Preserved the pre-existing web general-channel history and send action as a separate tab instead of removing it during the integration. The general channel continues to use the authenticated `/api/chat/messages` API.
- Added a responsive in-app frame, explicit reload and open-in-new-tab actions, and camera/microphone/display-capture/fullscreen permission delegation so the existing audio/video and screen-share flows can run inside the web workspace.
- The component resolves `VITE_CHAT_WORKER_URL` only as an HTTPS origin and falls back to the same public Worker origin used by the desktop chat module. No chat password or Audit Manager bearer token is copied into the frame.
- Kept the separate chat-service sign-in and member-only authorization boundary explicit; this change does not claim single sign-on or identity unification.
- Added `tests/test_web_live_chat_integration.py` to guard the React navigation, Worker asset origin, iframe permissions, safe new-tab relationship, separate-auth boundary, and preservation of general-channel history/send. Run #1129 passed the current source/API regression suite and full EXE/installer preservation pipeline. The frontend bundle contains both private/group and general-channel modes. Browser functional comparison of embed storage, media permissions, membership, reconnect and message send/history, plus production deployment checks, remain open. Chat identity is still separate from the main Audit Manager login. No version bump is appropriate for this web-only integration.

## GitHub Actions frontend bundle publication race — fix implemented; verification pending

- Runs #1108 and #1109 failed after the React/Vite build, specifically in the step that publishes generated `frontend/dist` files to `main`. Concurrent workflow runs produced different hashed asset filenames and attempted to rebase over one another; Git reported a rename/rename conflict for the generated JavaScript asset and a content conflict in `frontend/dist/index.html`.
- Replaced the rebase-based publisher with a latest-main reconciliation loop: it saves the freshly built bundle outside the checkout, fetches `origin/main`, verifies that the build commit is still an ancestor, skips a bundle if newer frontend source/assets exist, resets to the latest main commit, restores and stages only `frontend/dist`, and pushes with a normal non-force update. If another run already published the same bundle, the step exits successfully instead of treating that race as a failure.
- Added `test_frontend_bundle_publisher_skips_stale_builds_and_avoids_rebase_races` to `tests/test_render_configuration.py`.
- Run #1129 completed successfully after the publisher change: React production build and latest-main frontend publication, Worker validation/tests, Python compilation and the full 303-test regression suite all passed. The publisher uses latest-main reconciliation and a normal non-force push; no rebase-based asset race occurred in this run.
- No version bump is required; this is CI reliability and generated-asset publication maintenance.

## Web Update Center parity — CI verified; browser and Windows rollback verification pending

- Added an authenticated read-only release catalog endpoint. It selects only published stable GitHub releases with the expected Raw Strength installer asset, official repository download URL, a plausible installer size and valid SHA-256 metadata when present. Release results are cached for five minutes; a cached catalog is retained if GitHub is temporarily unavailable.
- Added an Update Center to Settings for all signed-in roles. It reports the current/latest application version, whether a newer stable Windows installer exists, release notes, publication time and direct installer download.
- Added a separate Admin/Developer-only previous-installer list. The caller must re-enter the exact active account password (or the same developer authorization accepted by the desktop rollback flow). Exact-case username + account ID lookup preserves the distinction between customer `Admin` and developer `admin`. Authorization attempts are audited without storing the password or changing account hashes.
- The browser cannot execute an EXE. The web flow deliberately downloads a previous installer rather than pretending to perform a silent rollback. The customer must run the installer on Windows after creating and verifying a database backup.
- Added regression coverage for stable-release selection, invalid/untrusted asset filtering, latest-version detection, login requirements, Admin/Developer authorization, Staff denial, audit records, exact-case account credential preservation and browser-safe UI behavior.
- Run #1127 built and published the React frontend, validated both Cloudflare Workers, and compiled all Python modules. Pytest reported 300 passed and one stale static UI assertion failed; the component behavior was correct. The assertion was corrected, and run #1129 subsequently passed all 303 tests including Update Center release filtering, authentication and rollback authorization. Browser download verification and Windows rollback compatibility verification remain pending.

## Home / Dashboard parity — CI verified in run #1129; browser verification pending

- Replaced the four-card web summary with the desktop's five clickable KPIs, Operations Command status banner, five quick actions, recent active employees, today's task table with progress bars, attendance gauge and roster, and employee productivity visualization.
- Reworked `GET /api/dashboard` to use the same active employee roster and ordering as `Database.employees(False)`, the same task ordering and first-12 display, and the same attendance classification as `refresh_dashboard`.
- Added batched history queries for productivity instead of per-employee queries. Tracking start uses joining date, then first task/attendance record, then today. Productivity follows the desktop 70% task / 30% attendance weighting, unknown task statuses contribute zero while remaining in the task denominator, leave days are excluded from eligible attendance days, holidays are excluded, and Sunday remains a working day.
- Added regression coverage for active/inactive roster handling, Submitted/Completed/cancelled/unselected task semantics, Sunday inclusion, holiday and leave exclusion, attendance summaries, and the combined productivity score.
- This is a web-only parity correction; application version remains v1.3.81. Windows EXE source, customer database schema, account identities/password hashes, encrypted snapshot behavior and updater code are unchanged. Run #1129 passed the 303-test suite and installer-preservation pipeline; browser and production verification remain pending.

## Completion gate

A row can move to **Complete** only after:
1. every desktop field and action has a corresponding web UI and API operation;
2. tests cover create/read/update/delete, permissions, edge cases and migration preservation;
3. functional verification is performed against the same representative customer database in web and EXE;
4. production deployment and health are verified;
5. the matching Windows build/release and web build pass.

No 100% parity claim is permitted while any row above remains Partial or In progress.

## Employee Directory milestone — CI verified in run #1129; browser parity pending

- Web create/edit exposes employee code, full name, department/section, designation, phone, email, joining date, notes and active status.
- Web directory adds full-field search, department/group filter, Serial Number / ID, Department / Group, Name (A-Z), and Custom Order sorting.
- Added Manage Sections with add, rename, delete and ordering; employee Move Up/Move Down and Move to Section actions; selected-row editing and activate/deactivate controls.
- Server-side permission checks enforce HR/Admin/Developer for add/edit/activate and Admin/Developer for permanent deletion, section management and reordering. The legacy DELETE endpoint retains its soft-toggle contract for older clients.
- Permanent deletion creates a SQLite safety backup first, then removes tasks, attendance and linked business activities; employee targets cascade and archived documents retain their content with a null employee link.
- Added API regression tests for complete employee fields, section rename propagation to tasks, section and employee ordering, role restrictions, and backup-before-permanent-delete.
- Run #1129 passed the full regression suite, EXE/installer build and legacy database-preservation checks. Render deployment and side-by-side browser verification against a representative customer database remain pending. Do not mark this row Complete until all gates pass.

## Task Manager milestone — CI and release verified; functional parity still in progress

- Replaced the limited web task form with a dedicated responsive Task Manager matching the desktop TaskDialog's assignment, department, target/actual quantity, progress, priority, extended status, proof URL, expose-link, next-action and dynamic custom key/value fields. Optional details, due time and proof notes are also editable without dropping existing values.
- Added desktop-style date/employee filtering, status/priority/department filters, search, selection, Select All, bulk editing, proof-link opening, task KPI cards and Admin/Developer-only deletion controls.
- Added authenticated task list/create/update/bulk-edit/delete API dependencies. Task deletion enforces Admin/Developer; bulk edit updates only selected fields and runs transactionally.
- API writes now preserve the first submitted/completed timestamp, set it on the first Submitted/Completed transition, keep target/actual and custom values intact, and return 404 for missing tasks. Task date and due-time inputs are validated.
- Added regression tests for the full task-field round trip, custom key/value persistence, filter behavior, submitted timestamp preservation, selective bulk updates and deletion permissions.
- Runs #961 and #962 each passed 206 tests, React build, Python compilation, EXE/installer, legacy v1.1.74 upgrade with unchanged customer DB hash/records, launch smoke test and v1.3.77 release asset verification. Render deployed the frontend bundle and reports the service live. The task manager is still not Complete until the remaining bulk fields/status behavior are covered, the browser is functionally exercised against the EXE and same customer data, and production database sync/storage durability is verified.

## Employee Tracker milestone — CI verified in run #1129; browser parity pending

- Added the employee/date selectors, task summary/progress KPIs, task list, add/edit/delete/open-proof actions and filters by reusing the shared Task Manager component and API.
- Regression coverage and CI/EXE release gates passed in runs #966 and #967. Direct browser side-by-side verification against the desktop EXE and a representative customer database remains open.
- Preserve the shared Task Manager permission and evidence-link behavior; do not create a second task data model.


## Print Center web milestone — CI verified in run #1129; document layout and browser parity pending

- Added a dedicated responsive React Print Center with the Windows report types: Audit / EOD, Employee Attendance, Employee Details, and Employee Productivity.
- Added consolidated and individual employee scope, report-only employee exclusion, date selection, and Word/PDF/CSV output selection.
- Added report-specific include/exclude controls for identity, contact, attendance fields, productivity metrics, task fields, proof links, remarks, employee notes, and optional product/service catalogs.
- Added authenticated /api/reports/preview and /api/reports/export operations. Preview and export share the same report filters/options. Exclusion is a query filter only and never modifies employee records.
- DOCX and PDF exports retain exposed evidence URLs as clickable links; CSV exports preserve the report's sections and fields as section/field/value rows.
- Added regression tests for employee exclusion, hidden private notes, and PDF/DOCX/CSV response formats.
- Corrected the web product-list API and Print Center catalog to call the shared desktop `business_tracking.available_stock()` calculation; the regression fixture covers dispatched, free, returned, damaged, expired and quarantined quantities and verifies available stock of 111.
- Run #976 passed 213 regression tests, React production build, Cloudflare Worker checks, Python compilation, Windows EXE compilation, installer generation, legacy v1.1.74 in-place upgrade with unchanged customer database hash and sentinel records, application launch smoke test, and v1.3.77 release asset verification.
- Remaining: compare generated DOCX/PDF layout and CSV columns/values against the EXE for each report type; verify evidence-link exposure and every report field against the same customer database; test report permissions in production. Do not mark Print Center Complete until these checks pass.


## Business Tracking web milestone — CI verified in run #1129; browser parity pending

- Replaced the previous three basic inline forms with a dedicated Business Tracking workspace matching the desktop sub-tabs: Dashboard, Products & Inventory, Orders, Services & Members, and Employee Activities.
- Product creation now exposes the desktop database fields for SKU, category, brand, package type, unit, opening/received/reserved/dispatched/free/returned/damaged/expired/quarantined quantities, purchase/selling prices, reorder level, batch, expiry and storage location.
- Added a stock movement ledger API and UI for receive, reserve, release, dispatch, free/promotional, return, damage, expiry, quarantine and unquarantine movements. Each movement updates the aggregate product quantity and ledger record in one SQLite transaction; outbound movements are rejected when they exceed available stock.
- Order entry now exposes customer/contact, channel, payment mode, status, discount, order value, invoice, shipment, assigned employee and remarks. Order status updates use the existing status endpoint.
- Service and membership forms now expose training mode, service unit, duration, sessions, validity, price, member registration/start/expiry dates, purchased/completed sessions, assigned trainer, membership/payment status, invoice and remarks. Membership session/status updates are persisted through authenticated PATCH operations.
- Employee activities now expose employee, related order/service/product, task type, quantity/unit, start/completion time, status, proof reference and remarks; activity status updates preserve timestamps and automatically set start/completion time when transitioning to In Progress/Completed.
- Business overview now calculates low-stock counts using the same stock ledger formula as the desktop and correctly reads the bt_orders.order_status column.
- Business read APIs now require an authenticated session. New regression tests cover unauthenticated denial, full-field persistence, stock movement atomicity/overdraw protection, order lifecycle, membership sessions, activity status and overview counts.
- The additive implementation uses the existing bt_* tables; no customer table replacement, account/password migration, encryption-key change or updater contract change is included. Run #1129 passed the current regression suite and Windows EXE/installer plus legacy database-preservation checks. Production deployment and direct browser side-by-side verification remain pending. Do not mark this module Complete until those gates pass.


## Settings / database backup milestone — implementation added; verification pending

- Registered the existing standalone web database export/import routes with the FastAPI application; previously the route module was present but not imported, so the frontend's database backup controls could not reach it.
- Added authenticated `/api/system/db-info` with safe database size, integrity, table counts, backup count, app version and encrypted-sync status. It does not expose the absolute database path or account usernames.
- Added authenticated `/api/system/sync-now`, delegating to the existing `WebDatabaseSync.sync_now` manager without changing the Worker URL, installation ID, encryption secret, key derivation or snapshot path.
- Exposed database backup download in the web Settings page. Database restore is restricted to Admin/Developer, validates the uploaded SQLite database, retains a pre-import backup, and clears web sessions while preserving the imported account identities and password hashes.
- Added API regression tests for authentication, safe DB metadata, manual sync delegation, backup download, and Staff-versus-Admin restore permissions.
- [Run #981](https://github.com/yalangisexter-ux/audit-report/actions/runs/41954082587) passed 218 regression tests and the full Windows EXE, installer, legacy v1.1.74 database-preservation upgrade, launch smoke test and v1.3.77 release verification. Render loaded 80 API routes and the deployment reached live. A valid backup/restore round-trip with account-hash assertions is included in the next regression update. Render currently has no persistent disk mounted, so production restore must not be treated as durable until service storage is corrected.


## Encrypted snapshot Worker production reconciliation — 2026-11-05

- Compared the Worker currently deployed in Cloudflare with `audit-db-sync/src/index.js` on `main`. The deployed version 808 was stale: it fell back to the latest customer's snapshot when an exact installation pull returned 404, and its GitHub snapshot commit message omitted Render's `[skip render]` phrase. The first behavior could expose a different installation's encrypted snapshot to a client with a missing snapshot; the second caused every snapshot commit to redeploy the Render service.
- Uploaded the current `main` Worker source from commit `f64f344bb42acd1881a5fe92fc269e7ad83fde5f` as Worker version 809 and deployed it at 100% traffic. The exact-installation pull now returns 404 when that installation has no snapshot; latest-snapshot discovery is only used when explicitly requested. Snapshot writes include `[skip render]`.
- Preserved the existing `DEVICE_REGISTRY` Durable Object namespace and the `GITHUB_OWNER`, `GITHUB_REPO`, `JWT_SECRET`, and `RELEASE_TOKEN_2` bindings. Secret values were not read or changed.
- The Worker test suite in #1042 passed all four tests. It verifies that installation B cannot pull installation A's snapshot when B has no snapshot and that snapshot commit messages include `[skip render]`.
- Render history shows the earlier snapshot commits caused successive deploys. No natural post-v809 snapshot commit has yet been observed, so the Render skip behavior is test-backed but still awaiting production event confirmation. No artificial customer snapshot was written for testing.

## Render Free-tier configuration reconciliation — 2026-11-05

- Updated `render.yaml` to describe the actual Free service: one instance, no paid disk, `autoDeployTrigger: checksPass`, build filters excluding `customer-data/`, and `/api/health` health check. Removed the unused `AUDIT_DATA_DIR=/var/data` setting so the working copy uses the service's normal `web-data` directory and encrypted snapshot bootstrap.
- Rewrote `RENDER_DEPLOY.md` to describe the architecture accurately: web and EXE use separate local SQLite working copies that converge through installation-scoped encrypted snapshots; `WEB_STANDALONE=1` does not disable web-specific snapshot sync.
- Created a no-cost adoption plan for the existing service: [Render Blueprint sync plan](https://dashboard.render.com/blueprint/exs-dbm5sot9fdbs73bug7r0/sync/exe-dbm5sp59fdbs73bug8bg). It proposes the React production build command, the credential-heal startup import, build filters, `checksPass` auto-deploy, `/api/health`, and explicit `WEB_PURGE_SEED_DATA=0` / `WEB_PURGE_DEMO_ROSTER=0`. The plan proposes no plan upgrade, disk, or manual environment values. It has not been approved or applied.
- Before approval, verify that any existing `WEB_CUSTOMER_ADMIN_PASSWORD` and `WEB_DEVELOPER_ADMIN_PASSWORD` secrets are the intended values: the startup helper preserves account IDs and existing hashes when credentials already match, but rotates a hash if a configured secret differs.
- The live service still uses the older build/start commands, commit-triggered auto-deploy, and no health-check path. The Free filesystem is not durable; a write not uploaded before process stop can be lost. This remains a production data-durability blocker until write-through and restart recovery are functionally verified.



## Case-sensitive customer/developer account sync milestone — v1.3.81

- Found a data-integrity defect in both desktop snapshot merge paths: `merge_remote_json_snapshot` and `merge_remote_database_snapshot` normalized usernames to lowercase, so exact-case `Admin` and `admin` could resolve to the same local account and overwrite the other account's role or password hash.
- Corrected both merge paths to key accounts by exact username. Password recovery and Change Password now resolve exact-case usernames first and allow a case-insensitive fallback only when there is exactly one active match; ambiguous mixed-case input is rejected.
- Added regression tests for SQLite snapshot merge, JSON snapshot merge, preservation of separate account roles/salts/hashes, exact-case recovery lookup, and unambiguous legacy casing.
- Added a Render build-filter regression and changed the CI-generated `frontend/dist` commit to use `[skip render]`, so generated assets do not restart the Free service.
- Version metadata is advanced consistently to v1.3.81 for this cross-device account-identity integrity milestone. Run #1129 passed the Windows installer build, legacy upgrade, offscreen launch smoke check and account/hash regression tests. Production deployment and live account/sync round-trip remain pending.



## v1.3.81 transaction, account and deployment follow-up — 2026-11-05

- Run #1047 failed with 2 failures / 243 passes. Both failures were nested-transaction errors in the JSON and SQLite snapshot merge functions (`cannot start a transaction within a transaction`). Main commit `2bfd005` changed those merges to savepoints; run #1048 is revalidating the fix.
- This follow-up preserves the `SyncableSQLiteConnection.commit()` callback when a merge owns the transaction, while leaving a caller's existing transaction open. Regression tests cover nested success, merge-local rollback on failure, and commit-callback delivery for both snapshot formats.
- Web account registration and Admin-managed account creation now use exact-case (`COLLATE BINARY`) duplicate checks, matching the migrated desktop schema. Tests cover `Admin` and `admin` creation, exact-case login, PBKDF2 hash preservation, pending registration/activation, and same-case duplicate rejection.
- Render logs after the successful 2bfd005 deployment showed `HEAD /` returning 405 even though `GET /` returned 200 and Uvicorn started. A no-body `HEAD /` route is added for the service's current default probe; `GET /api/health` remains covered by the API health test. The live Render dashboard still has no explicit `/api/health` health-check path, which remains a dashboard/Blueprint reconciliation item.
- The Cloudflare Live Chat manual deploy workflow now rejects non-main refs, and its README no longer instructs selecting a feature branch.
- Version metadata remains consistently at v1.3.81. No new version bump is made for these corrective fixes. Release/installer verification remains gated on the next full CI run.


## Web working-week / Sunday parity correction — implementation in this change

- The desktop `Database.working_weekdays()` always includes Sunday, including for older databases whose saved setting is Monday–Friday. The web attendance-summary route previously parsed the saved value independently and did not force Sunday, so the same customer DB could show different working-day, present and total-present counts in the browser.
- The web summary now uses the same Sunday-required rule. Admin/Developer users receive a responsive Working week settings panel and authenticated GET/PUT endpoints for the remaining weekdays; Sunday is visible, selected and disabled. The generic `/api/settings` read/write endpoints are now Admin/Developer-only because they expose and mutate the complete settings table.
- Added regression coverage for legacy Monday–Friday settings, Sunday attendance summary counts, Admin/Developer-only weekday configuration, invalid weekday values, and authorization of the generic settings API. Run #1129 passed the current regression suite; production deployment and live browser verification remain pending.

## Store Directory web milestone — CI verified; browser parity pending

- Expanded the web form and record table to cover business name/category, Store/Gym kind, state/UT, city, area, contact person, phone, email, full postal address, official website, Google Maps URL, follow-up date, call time, connection, verification, response, notes and source status.
- Added state, kind, website-presence and verification filters; expanded search across contact, address, website and Maps fields; rendered external website and Google Maps links safely in a new tab.
- Added authenticated list/summary endpoints, full-field create persistence through the existing branch-aware `persist_prospect_records` dedupe/enrichment helper, generated Google Maps search URLs when a real address is supplied, and duplicate feedback without synthetic contact details.
- Regression coverage includes unauthenticated list/summary rejection, location/address/website/Maps persistence, duplicate enrichment and frontend field/filter/link presence. [Run #1054](https://github.com/yalangisexter-ux/audit-report/actions/runs/42011338778) passed 257 tests; React build, Worker validation/tests and Python compilation passed. The installer was correctly skipped for this non-release change.
- The screen remains Partial until the web form and permissions are compared in-browser with the desktop read-only explorer/scraper/export workflow. Edit-time dedupe-key recomputation and Staff action visibility are the next Store Directory correction.

## Protected operational read APIs — CI verified; production route probe pending

- The parity/security audit found four data-bearing GET routes callable without a session while `WEB_REQUIRE_LOGIN=1`: dashboard KPIs, employee directory, chat messages, and Print Center summary.
- Added the shared `get_current_user` dependency to all four routes. Public health, login, registration/recovery, static assets, and release-check endpoints remain public by design.
- Added a regression test proving each route returns HTTP 401 without a session and HTTP 200 with a valid in-memory Admin session. [Run #1055](https://github.com/yalangisexter-ux/audit-report/actions/runs/42012951770) passed all 258 tests; React build, Worker validation/tests, and Python compilation passed.
- The code was deployed by Render deployment `dep-dbm5r6jbc2fs73apuko0`; startup and root HEAD probe succeeded. A direct production request asserting 401/200 for these four endpoints remains to be performed.
- No customer rows, auth identities, PBKDF2 salts/hashes, sync callbacks, installation IDs, encryption settings, schema, or version metadata were changed.

### Store Directory edit/permission correction — CI verified; production browser verification pending

- Fixed the web editor's discriminator collision: a prospect's business kind (Store/Gym) no longer overwrites the UI edit-type marker, so the edit modal loads prospect fields and submits PATCH to the correct endpoint.
- Restricted prospect edit and delete actions to Admin/Developer in both UI and API. Staff no longer see controls that would fail with HTTP 403.
- Prospect edits now recompute the canonical name/state/city dedupe key, reject collisions with another branch using HTTP 409, persist the Store/Gym kind, and generate a Maps search URL from a real address when the direct Maps field is cleared.
- [Run #1056](https://github.com/yalangisexter-ux/audit-report/actions/runs/42015428311) passed 259 tests, including these Store Directory regressions; React build, Worker validation/tests, and Python compilation also passed. The installer was correctly skipped for this web-only correction.
- Production browser verification against a representative customer account remains outstanding.

### Store Directory scraper encrypted-sync callback — CI verified in run #1129; production verification pending

- Found that the background scraper opened a raw SQLite connection, bypassing `SyncableSQLiteConnection` and its encrypted snapshot commit callback. Scraped records could therefore be saved locally without being marked pending for cloud sync.
- Changed the scraper to use the shared `api.get_db()` connection and close its dependency generator reliably. Empty scrape results do not create a needless sync write.
- Added a regression test that stubs the crawler, verifies a prospect is inserted, and asserts that the encrypted-sync manager receives exactly one pending notification.
- Commit: [dfd7a2f](https://github.com/yalangisexter-ux/audit-report/commit/dfd7a2f09093ce8ac96f8fc8dcf824b0459c4d96). [Run #1129 passed the scraper callback regression as part of 303 tests. The earlier Render deployment evidence is historical; current production deployment and live encrypted-sync behavior still need verification.

### Administrator credential hash preservation — CI verified in run #1129; live Render verification pending

- The Render startup helper previously replaced an existing Admin/admin password hash when the configured deployment secret did not match it. That could silently change customer credentials during Blueprint adoption.
- The helper now preserves existing exact-case account IDs, display names, password salts and hashes. It only heals role/active metadata, refuses to auto-reset an existing account with a missing hash, and uses deployment secrets only when creating a genuinely missing account.
- Updated regression coverage verifies that a later deployment with different secrets cannot rotate either existing account hash, while a missing Developer account can still be provisioned.
- Commit: [a6abc0e](https://github.com/yalangisexter-ux/audit-report/commit/a6abc0eb87308bcc9af059660edb695becef1051). [Run #1129](https://github.com/yalangisexter-ux/audit-report/actions/runs/42122417618) passed the credential-hash preservation regression. The helper is not confirmed active in the live Render start command until the Blueprint plan is approved and the deployment is verified.

## Production deployment and data-visibility findings — 5 November 2026

- Live Render service inspection shows the current build command is `pip install -r requirements.txt`; it does not build the React app. The live service also has no health-check path and deploys on every commit. Therefore source-level React changes are not reliably reaching production.
- Repository `render.yaml` defines a React production build, a frontend/backend build filter, `checksPass` auto-deploy, `/api/health`, and a Free plan. The live service has not adopted that Blueprint.
- Render deployment for commit `dfd7a2f` succeeded. Logs show `Application startup complete`, Uvicorn listening on port 10000, `HEAD /` 200 and `GET /` 200.
- Blueprint plan `exe-dbm6b1ec6qcc73846pug` is prepared. It proposes the build command, start command, build filter, health check, and no-cost Free-tier settings; it requests no manual secret values and no paid disk/plan. It has not been approved or applied. Review it at [Render Blueprint plan](https://dashboard.render.com/blueprint/exs-dbm5sot9fdbs73bug7r0/sync/exe-dbm6b1ec6qcc73846pug).
- Render snapshot-restore logs report 5,003 customer prospects restored. The web list API defaults to `limit=200` and currently has no offset parameter; the React app makes one request. This is a confirmed data-visibility gap, not evidence of lost customer rows. Add API offset support and a paged table before declaring Store Directory parity.
- Render Free currently has no persistent disk. Encrypted installation-scoped snapshots are the recovery path; verify a full post-write snapshot round-trip and restart recovery. Do not change hosting cost or storage plan without explicit approval.

### Next Store Directory milestone

- API keyset pagination is already implemented in `/api/customers/prospects` (`limit` up to 1,000 plus descending `before_id` cursor). React `fetchAllProspects()` walks every page and the UI renders a 100-row client-side page; filtering covers business/contact/address/website/Maps fields, state, record kind, website presence and verification state.
- Regression test `test_customer_prospect_api_keyset_pagination_returns_every_row_once` inserts 2,505 records and verifies every ID is returned exactly once in descending order. The 5,003-row production restore still needs a direct authenticated browser/API count and no-gap/no-duplicate check.
- Workbook import/merge, regional benchmark import, filtered CSV/XLSX exports, regional summary and print-preview paths are now implemented and covered by run #1099. Remaining: browser comparison of filters, exclusions, map links, print workflows and permissions against the EXE; validate scraper source accuracy and dedupe with real customer data. Retain the 5,003-record keyset-pagination performance check in production.
- Verify one-tap scraping updates the same customer dataset and triggers encrypted snapshot sync.
- Complete browser-side comparison with the EXE before marking the screen complete.
## Print Center PDF font regression diagnosis — CI verified in run #1129

- GitHub Actions runs #1084 through #1088 repeatedly failed at the same single assertion in `test_web_print_center_exports_pdf_docx_and_csv`; the other 265 tests in #1088 passed.
- The generated PDF was valid, branded, included the Raw Strength logo and metadata, but ReportLab did not serialize the registration alias `RawStrengthSans` into the PDF. TrueType fonts are embedded under the font face's internal DejaVu name, often with a subset prefix.
- The regression assertion is corrected to verify the embedded `DejaVuSans` face name and `/FontFile2` font program rather than the Python-side registration alias. This tests the actual embedded font and avoids a false negative.
- Run #1129 passed the corrected PDF font assertion as part of 303 regression tests; no version bump is appropriate for this test-only fix.

## Store Directory pagination re-inspection — 2026-11-05

- Re-inspection of current `main` confirms keyset pagination is present in `web_ops_routes.py`: `limit` is capped at 1,000 and `before_id` advances a descending ID cursor. The React `fetchAllProspects()` requests every page, then `prospectRows` applies the current search/filter set and displays 100 rows at a time.
- `test_customer_prospect_api_keyset_pagination_returns_every_row_once` verifies a 2,505-record fixture returns all IDs exactly once. This is source/test evidence, not production proof that all 5,003 restored records are visible to a real authenticated browser session.
- The earlier statement that pagination had not landed was incorrect and is superseded by this evidence. The current main also includes workbook import/merge, regional benchmark import, filtered CSV/XLSX exports, regional summary and print-preview code with regression coverage; Store Directory remains In progress until browser/production verification is complete.


## Web self-service password change — CI verified in run #1129; browser verification pending

- Added the Windows login dialog's Change password workflow to the web sign-in screen: username, current password, new password and confirmation.
- Added an unauthenticated /api/auth/change-password endpoint protected by the current password. It uses the same PBKDF2 hash_pin and strength rules as the EXE; it does not recreate accounts, change usernames, roles, account IDs, or the other case-distinct account's salt/hash.
- Username lookup is exact-case first, with a case-insensitive fallback only when exactly one active account matches. This prevents Admin and admin from being confused.
- Successful changes invalidate that account's in-memory and persistent web sessions, create an audit-log entry, and commit through the existing syncable database connection so the encrypted snapshot callback remains active.
- Added API regressions for successful exact-case change, wrong current password, weak new password, ambiguous mixed-case usernames, session invalidation, unchanged other-account credentials, audit logging and the React sign-in form. Run #1129 passed the password-change regressions as part of 303 tests; no version bump is appropriate for this web-only parity correction.


## Live Chat regression assertion correction — CI failure isolated

- Runs #1113 and #1114 reached the Python regression step and each failed on one stale source assertion (277 passed, 1 failed): the test expected a prop-less <LiveChat/> even though the integration passes messages, user identity and the authenticated general-channel send callback.
- The React production build, frontend publisher, Worker checks and database-sync Worker tests passed before the regression step.
- Updated the test to assert that the chat tab renders LiveChat with its required props; the implementation and separate chat authentication boundary are unchanged. Run #1129 subsequently passed all 303 regression tests, including this corrected assertion.


## Settings parity — employee CSV export and global proof-link exposure — CI verified in run #1129; browser verification pending

- Added the desktop-compatible employee CSV export endpoint and Settings action. It exports all employee records, including inactive staff, in the same ten-column order and labels as the Windows EXE; CSV quoting and UTF-8 BOM preserve commas, quotes, newlines and non-ASCII text.
- The export requires an authenticated session, returns an attachment with no-store and nosniff headers, and does not expose account hashes or other authentication fields.
- Added the desktop "Expose all proof links" action. After explicit confirmation, the authenticated endpoint marks every task `expose_link=1`, sets `global_expose_link` and `report_opt_expose_link`, writes the matching audit event, and commits through the normal database connection so the existing encrypted-sync callback is retained. The action remains available to Staff as it is in the Windows Settings screen.
- Added API regressions for exact CSV headers/ordering, inactive employee inclusion, special-character escaping, authentication, Staff access, all-task updates, both settings values, audit logging and commit invocation; a React source regression checks that both Settings actions are rendered.
- This is a web-only parity correction; application version remains v1.3.81. Run #1129 passed the employee CSV/proof-link regressions as part of 303 tests and completed the React build plus EXE/installer preservation checks. Production browser behavior and Render deployment remain pending.

## Google Sheets sync scope and security notes

- The new web action intentionally mirrors the desktop `sync_from_live_google_sheet` pull path. It does not upload local web changes to Google Sheets and is not the continuous EXE↔web database sync mechanism; that remains the encrypted snapshot/Worker path.
- The customer username `Admin` can run the pull without a developer password. The exact lowercase developer username `admin` must provide the existing per-request developer authorization. Staff/HR are denied. The password is never stored by the web UI or API.
- Regression tests cover customer account-hash preservation, developer password gating, Staff denial, offline/no-change behavior and the UI action. Run #1129 passed all 303 tests and the full EXE installer/database-preservation pipeline, including the Google Sheets authorization tests. The live workbook pull and browser permission/UX behaviour still require production-side verification.
- The repository still contains legacy fallback encryption credentials in source/mobile client code and default account-password literals in test fixtures. They were not changed because rotating encryption material without a coordinated migration could make existing encrypted snapshots or older mobile clients unreadable, while changing test fixtures must not alter the provisioned customer accounts. Verify the production `DB_SYNC_ENCRYPTION_SECRET` configuration and plan coordinated secret/default-credential rotation before claiming encryption-secret hygiene.

## Appearance and wallpaper parity — CI verified; browser verification pending

- Added the Windows desktop's four color themes (Day, Night, Ocean, Sunset) to the web Settings screen and compact desktop-width header selectors.
- Added all 17 AnimatedBackground.STYLES choices, with bundled photographic assets for Galaxy, Milky Way, Ocean Waves, Lord Shiva and Love & Couples; remaining styles use CSS-generated animated backgrounds without remote requests.
- Added custom PNG/JPG/WEBP/BMP wallpaper upload (15 MB maximum), validation, browser-local IndexedDB persistence, and Reset wallpaper. Theme and wallpaper preferences use browser-local storage; they are deliberately not written to the shared SQLite settings table, customer records, authentication rows or encrypted database snapshots.
- Added source regressions comparing the web theme and wallpaper option lists directly with app.py, checking local-only storage and verifying the controls and contrast styling.
- Commits: [df8013f](https://github.com/yalangisexter-ux/audit-report/commit/df8013f1a5efda22b0e4222c669b4a2cca235af8), [a2ba355](https://github.com/yalangisexter-ux/audit-report/commit/a2ba355d7f53296d20a62da62ca8129a484996ec), [edea583](https://github.com/yalangisexter-ux/audit-report/commit/edea583a6d5439bdf273d1c8f0be975e48a58079). The CI frontend publisher also committed bundle [7050957](https://github.com/yalangisexter-ux/audit-report/commit/7050957e435458fd37bc88acb5bcbf898387c212).
- [Run #1125](https://github.com/yalangisexter-ux/audit-report/actions/runs/42098957726) completed successfully: React production build and latest-main frontend publication passed, Cloudflare Worker validation and isolated database-sync Worker tests passed, Python compilation passed, and **293 regression tests passed**. Windows installer-impacting changes were not detected, so EXE/installer/upgrade/reinstall steps were correctly skipped. The latest full installer/database-preservation baseline remains run #1121.
- Run #1131 passed the browser-local clock preference regression as part of 304 tests and completed the React build/publication, Worker checks, Python compilation, EXE/installer build, legacy v1.1.74 upgrade, uninstall/reinstall database-preservation checks and packaged launch smoke test. Browser verification of all four themes, all wallpaper styles, custom upload/reload/reset, responsive header controls, text contrast and clock reload behavior remains pending.
- No application version bump is appropriate for this web-only appearance milestone.


## Digital / Analog clock parity — local preference scope correction CI-verified in run #1131; browser verification pending

- Added the Windows desktop's Digital/Analog clock selector to web Settings and a clickable live clock in the application header. Digital mode displays the local date and 12-hour time with seconds; Analog mode renders a live SVG clock face with hour, minute and second hands, refreshed every second.
- Retained authenticated GET/PUT `/api/settings/clock-mode` routes for older web bundles; the current React UI no longer calls them. The compatibility endpoints still validate Digital/Analog values and require an authenticated session.
- The Windows EXE stores `clock_mode` in its local SQLite settings. Encrypted snapshots intentionally strip local settings other than the business-calendar key, so a server-side clock setting would not reliably follow the desktop across devices and would instead be shared by every web user. The React UI now stores `rsc_web_clock_mode` in browser `localStorage`, matching the desktop's per-installation preference without changing the shared customer database or encrypted snapshots.
- The legacy API endpoints retain regression coverage for authenticated Staff access, persistence, validation and unauthenticated rejection. The React source regression checks localStorage initialization/write and confirms the current UI does not call the server endpoint. Run #1131 passed all 304 regressions and the full EXE/installer preservation pipeline; browser verification of reload persistence, the header toggle, one-second analog hand movement and responsive layout remains pending.
- No application version bump is appropriate for this web-only preference-scope correction. Browser verification of reload persistence, the header toggle, one-second analog hand movement and responsive layout remains pending.


## Full regression and installer re-verification — 2026-11-06

- Run #1129 supersedes earlier notes that marked the dashboard, Update Center, password change, account management, CSV/proof-link settings, Google Sheets authorization and appearance regressions as pending. It also passed the then-current server-side clock API tests. The full suite passed **303 tests**; React build/publication, Worker checks, Python compilation, EXE/installer build and legacy database-preservation scenarios also passed. The newer browser-local clock preference correction is not included in that run.
- The installer upgrade test used a synthetic v1.1.74 customer database and verified the file hash, SQLite integrity and sentinel record through upgrade, uninstall and reinstall. This is strong regression evidence, but not a test against the customer's live database.
- The packaged EXE launch check used the offscreen Qt platform and only verified that the process remained alive for eight seconds. A visible interactive Windows launch and customer login/attendance workflow remain to be tested.
- The installer artifact is private to GitHub Actions and expires 2026-11-19. Run #1129 skipped public release publication; the public v1.3.81 release asset remains unchanged.
- Browser-side functional comparison and Render production deployment/health remain outstanding. The Render connector lists one workspace (Yalangis's workspace), but no explicit workspace selection was authorized in this run, so no service or deployment was changed.


## Digital / Analog preference scope correction — CI verified in run #1131

- Inspection found that `create_encrypted_database_snapshot()` intentionally removes every `settings` row except `working_weekdays`. Therefore the earlier React clock API wrote to the server's local settings table but did not make the preference part of the encrypted desktop/web snapshot. It also made one web user's clock choice global to all web users, unlike the desktop's per-installation setting.
- The React UI now initializes and saves `rsc_web_clock_mode` in browser `localStorage`, like the other appearance preferences. The legacy authenticated clock API routes remain available for older cached bundles, but the current UI no longer calls them.
- The change does not alter the SQLite schema, existing customer rows, account IDs/password hashes, encryption keys, snapshot allowlist, sync callback or updater contract. Version remains v1.3.81.
- Added a regression assertion for browser-local initialization/write and absence of a server clock API call. Run #1131 passed this regression as part of 304 tests; browser reload, analog hand movement and responsive clock behavior remain to be exercised.


## Distinct Home workspace parity — CI verified in run #1139; browser verification pending

- Inspection of the Windows MainWindow confirmed that Home and Dashboard are separate tabs. The Home screen contains a signed-in session/version strip, Update and Roll back actions, theme and wallpaper selectors with custom-image browsing, an 11-section Workspace Guide, and a Business Tracking live snapshot. The web app previously rendered the Dashboard component for both Home and Dashboard, so those Home-specific workflows were missing.
- Added frontend/src/HomeWorkspace.jsx and changed App.jsx so Home and Dashboard render independently. The web Home now exposes all 11 workspace-guide destinations, local appearance controls, Update Center navigation, Admin/Developer previous-version navigation, and the Business Tracking snapshot cards.
- Added authenticated read-only GET /api/home/business-snapshot. It mirrors the desktop counters: all catalog products, products whose computed available stock is at/below a positive reorder threshold, all sales orders and their total value, active memberships, and employee business activities. It returns the application version for the session strip. It performs no writes.
- Added tests/test_web_home_parity.py for desktop-equivalent inventory/order/member/activity counts, authentication, separate Home/Dashboard rendering, the 11 guide destinations, and Home appearance/update controls.
- Commits: [b4bb8fa](https://github.com/yalangisexter-ux/audit-report/commit/b4bb8faa871d1a00c7ac0a225fd67a5df786eec9) (Home component), [88d37ae](https://github.com/yalangisexter-ux/audit-report/commit/88d37ae91bef24b9c51edc5681dd1006a4a4c9d1) (business snapshot API), [8b3d8ff](https://github.com/yalangisexter-ux/audit-report/commit/8b3d8ffd878d5791577084dcec6456034431349c) (separate React Home route), [6ccfbd8](https://github.com/yalangisexter-ux/audit-report/commit/6ccfbd8eb667e022db45cd0348d85f20aa43ad6f) (regression tests).
- No database schema, employee/customer rows, account identities, password hashes, encrypted snapshot logic, sync callbacks, updater code, installer configuration or version metadata changed. Application version remains v1.3.81.
- [Run #1139](https://github.com/yalangisexter-ux/audit-report/actions/runs/42137300677) completed successfully: 307 tests passed; React build/publication, Worker checks, Python compilation, EXE/installer build, legacy upgrade, uninstall/reinstall DB hash/integrity/sentinel preservation, and packaged launch smoke all passed. The installer remains a private Actions artifact, not a new public release. Browser verification and Render production adoption remain open.


## GitHub Actions Node 24 and main-only policy — implementation committed; latest validation pending

- Upgraded all eight repository workflows to Node 24-compatible action majors: checkout/setup-node/setup-python/upload-artifact v7 where applicable. The setup-node action disables automatic package-manager caching explicitly; the application toolchain remains Node 22 and Python 3.12.
- Removed the main build's pull-request trigger and the Live Chat check's old feature/cloudflare-live-chat and pull-request triggers. The standalone chat check is now restricted to main and only chat-related paths: cloudflare-chat/**, chat-web/**, cloudflare_chat.py, and tests/*chat*.py.
- Added explicit main-ref guards to every manually dispatchable workflow, including the master build, chat checks, Cloudflare deployment, one-shot apply workflows and restore workflow. No feature branch, PR or parallel release-branch workflow is used.
- Added tests/test_workflow_policy.py to prevent regressions in action majors, chat path filters, pull-request/feature-branch triggers and manual-dispatch guards.
- Implementation commits include [59d0f3d](https://github.com/yalangisexter-ux/audit-report/commit/59d0f3dde1a9dd836bfee47150b9ac32ecdf8dfc), [112feff](https://github.com/yalangisexter-ux/audit-report/commit/112feff5c846a1237f1a85fd367b0a7ae2df12d3), [8071b5d](https://github.com/yalangisexter-ux/audit-report/commit/8071b5d33accf71f6f010475308f25cdaa93f2c2), [cb1bf55](https://github.com/yalangisexter-ux/audit-report/commit/cb1bf55c3c35fa5c747206414a0483bc1a26c41b), [b048dc8](https://github.com/yalangisexter-ux/audit-report/commit/b048dc8a4326c01d8cad6e2efcde0fcf05728b3c), [615cef4](https://github.com/yalangisexter-ux/audit-report/commit/615cef46a660198b7582c1c8b020795f2e90f52b), and the workflow-policy tests in [eee5744](https://github.com/yalangisexter-ux/audit-report/commit/eee5744f8e663da1418c6cf38902b62f724cec8f).
- Static inspection confirms no Node 20 action references, no PR triggers, no feature-branch references, and every manual workflow has a main-only guard. The full master regression run for this workflow-policy change is still pending; do not mark it CI-verified until it completes.


## Frontend recovery and Print Center report parity — CI verified in run #1156

- The blank authenticated screen was traced to the undefined `clockModeBusy` reference in `frontend/src/App.jsx`. Commit [f8cad1b](https://github.com/yalangisexter-ux/audit-report/commit/f8cad1b81c56bb3f8b60ddfc87ce6ca79fb303bc) removed the reference; [1cb0da4](https://github.com/yalangisexter-ux/audit-report/commit/1cb0da408663dcddf06d34f2dd8df41096e755b8) added the initial render/login guards. Commit [11fdb13](https://github.com/yalangisexter-ux/audit-report/commit/11fdb130c3c10529af3805f26fcb2b1979429b22) added a root React error boundary with an accessible, high-contrast reload panel so future render exceptions do not leave the wallpaper as the only visible screen.
- The Windows Print Center exposes historical archived PDFs, disables generated-report controls while an archive item is selected, opens the selected PDF for view/print, exports an archived copy, and provides a browser-equivalent route to the saved reports archive. The React component now receives the same archive records used by the Archive screen. Commit [1095b98](https://github.com/yalangisexter-ux/audit-report/commit/1095b982643318912726f1501ac739bda1f01d92).
- The desktop business product/service catalog options are a separate always-visible group, not part of the Audit / EOD-only option list. The web UI was aligned to that layout. The non-desktop Audit / EOD attendance toggle was removed, and the web API default changed from including attendance to excluding it, matching the desktop report option set. Commit [6da2a43](https://github.com/yalangisexter-ux/audit-report/commit/6da2a434d5e3462b552cabc0c237877b2b9f0cc9).
- Added regression coverage for the root error boundary, archived report selector/view/download/browse actions, the business catalog option group, and an in-memory SQLite EOD report containing a Present attendance row to prove that attendance is not emitted by default.
- [Run #1154](https://github.com/yalangisexter-ux/audit-report/actions/runs/42152302296) passed 314 tests and the full EXE/installer, legacy upgrade, uninstall/reinstall database-preservation and launch smoke pipeline. [Run #1155](https://github.com/yalangisexter-ux/audit-report/actions/runs/42152612311) completed successfully with 317 tests in 749.59s and the same full installer/upgrade/preservation/smoke checks. [Run #1156](https://github.com/yalangisexter-ux/audit-report/actions/runs/42152945307) is the latest superset and passed **318 tests in 450.26s**, React build/publication, Cloudflare Worker checks, Python compilation, EXE/installer build, legacy v1.1.74 upgrade with unchanged customer DB hash, uninstall/reinstall with unchanged hash/integrity/sentinel, and packaged launch smoke. Private installer artifacts: #1155 `13473409701`; #1156 `13473287981`.
- No application version bump was made: these are corrective web parity changes, not a major feature milestone. Version remains v1.3.81 across build, installer, updater/release workflow and frontend metadata. No customer database, account identity/password hash, encryption format, sync callback or updater contract was changed.
- Browser-side mobile/desktop verification and Render production deployment/health remain outstanding. The CI build publishes the frontend bundle to `main`; that does not prove the live Render service has deployed or is healthy.


## Web attendance draft persistence across date navigation — CI validation pending

- The web Attendance screen previously cleared all unsaved row drafts immediately after fetching a newly selected date. Saving one row also used the shared generic POST helper, which cleared every other employee's pending draft.
- Date navigation now flushes every pending employee row against the old selected work date before requesting the next date. If any write or the next-date read fails, the old date remains selected and the draft state is retained for retry.
- Individual Save now removes only the saved employee's draft; other employees' unsaved edits remain intact. A Save all action is provided, and overlapping save/date-change operations are disabled.
- Added regression guards for write-before-read ordering, per-row draft preservation, Save all visibility and busy-state protection. CI validation is pending; browser verification against the Windows EXE and representative customer data remains open.
