# Web / Windows EXE feature-parity tracker

Last inspected: 2026-11-05. Repository target: `main`. This is an evidence ledger, not a completion claim.

## Verification baseline

- Latest verified application/code baseline: [Master Build and Test run #1016](https://github.com/yalangisexter-ux/audit-report/actions/runs/41969035786), commit `76dd53ffa55f8fdd74b765f36f127660a10fdfa3`, passed **226 regression tests** in 9m34s. The React production build and frontend publication, Cloudflare/browser chat checks, isolated database-sync Worker tests, Python compilation, Windows EXE packaging, installer generation, legacy v1.1.74 in-place upgrade, launch smoke test, and release asset verification all passed.
- The legacy upgrade gate explicitly confirmed that upgrading v1.1.74 to v1.3.78 preserved the original customer database hash and records. The packaged application remained running for the 8-second launch smoke test.
- Latest published desktop release: [v1.3.78](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.78); the verified `RawStrengthEmployeeAuditManager-Setup.exe` asset is published (75,496,281 bytes). The Actions installer artifact is also available from [run #1016](https://github.com/yalangisexter-ux/audit-report/actions/runs/41969035786).
- Version consistency was verified by the passing regression gate: `build_info.py`, `installer.iss`, `version_info.txt`, and `.github/workflows/master.yml` agree on v1.3.78. This is the latest major release milestone; do not bump for minor fixes.
- Current `main` head at inspection: `d24fa6bd3a48fde9c76abc49d026343c7887a419`. It is ahead of the verified run commit only by automated encrypted `customer-data/*.db.enc` snapshot commits (no application-source changes). Preserve these snapshots exactly; do not normalize, decrypt, re-encrypt, replace, or delete them during parity work.
- Render production health and the actual service's persistent-disk configuration were not revalidated in this pass because no Render workspace was selected for this session. The last recorded service inspection found a Free instance without the persistent disk expected by `render.yaml` (Starter, 10 GB at `/var/data`, health check `/api/health`). Treat durable production storage and live health as **unverified / blocking** until the actual Render service is inspected in the correct workspace.
- The web migration is **not complete**. The screen-by-screen rows below remain Partial or In progress until every desktop action, field, permission and workflow has been browser-verified against the EXE using representative customer data, and production deployment/storage checks pass.

## Screen-by-screen parity ledger

| Desktop screen / workflow | Web implementation inspected | Status | Remaining verification / gaps |
|---|---|---|---|
| Login, registration, password recovery | React login, pending registration, recovery question/reset; standalone sessions and case-sensitive account migration | Partial | Verify Admin/Developer/Staff role behavior against the EXE; web currently exposes account activation but not the full desktop role-change/password-admin workflow. |
| Home / Dashboard | KPI cards, today's tasks, quick actions | Partial | Desktop has richer dashboard cards, charts, attendance/task telemetry, clock, refresh behavior and role-aware shortcuts. Compare every chart/action and data calculation. |
| Employees | Create/list/edit/delete with name, employee code, department, designation, phone, email; API model also accepts joining date, notes and active | Partial | Web form does not expose all desktop fields, group management, custom ordering/reordering, target assignment and complete employee detail actions. |
| Task Manager | Dedicated React UI/API cover assignment, date, department, details, due time, target/actual, progress, priority, status (including Not selected), proof URL/note, next action, report-link exposure, dynamic custom fields, filters, search, selection, full desktop bulk-edit fields, evidence opening and Admin/Developer-only delete | In progress | CI #961/#962 passed 206 tests, EXE/installer, legacy database-preservation upgrade and smoke test; Render frontend is live. Still need browser functional verification against the EXE and same customer data, plus verify production encrypted sync and persistent storage. |
| Employee Tracker | Dedicated React Task Manager in Tracker mode with employee/date selectors, task KPIs, filtered task list, add/edit/delete, proof opening and shared Task Manager API/model | In progress | Runs #966/#967 verified the tracker UI/API and regression coverage. Still require direct browser side-by-side testing against the EXE using representative customer data, plus production sync/storage verification. |
| Attendance & Working Calendar | Daily roster, selected date, status marking, time/remarks editing, employee filter, multi-selection, selective bulk edit, net hours, monthly totals and holiday declaration/removal | In progress | API/desktop regression coverage passed in run #958 (201 tests). Still requires direct side-by-side functional verification on a representative customer database, including role restrictions and legacy attendance detail display. |
| Print Center / Reports | Dedicated React Print Center with four report types, consolidated/individual/excluded employee scope, date and report-specific field toggles, preview, PDF/DOCX/CSV export APIs and exposed evidence-link handling | In progress | Run #976 passed 213 regression tests including employee exclusion, hidden-field behavior, all three export formats and full stock-ledger calculation; React build, Python compilation, EXE/installer, legacy upgrade and launch smoke also passed. Still require document-layout/field-by-field comparison against the EXE and production permission checks. |
| Historical EOD Archive | Multi-PDF upload, employee/date/notes association, searchable selection, inline view, export, refresh, Admin/Developer delete | In progress | Automated auth/RBAC and metadata regression coverage added; direct browser side-by-side verification and production storage/sync checks remain. |
| Business Tracking | Dedicated React workspace with Dashboard, Products & Inventory, stock movement ledger, Orders, Services & Members, and Employee Activities | In progress | Automated API and UI regression coverage plus direct browser/EXE side-by-side verification, permission checks and production sync/storage verification are pending. |
| Store Directory / Scraping | Public merchant scraping, prospect create/edit/delete, archive and status endpoints | Partial | Verify all desktop prospect fields, scrape sources, filters, deduplication, multi-location evidence and export/report workflows. |
| Live Chat | General-channel message list/send in web | Partial | Desktop supports private conversations and authorized groups; web needs channel/user selection, unread state, reconnect and role/permission parity. |
| Settings & Backup | Web account activation; authenticated DB health/counts, encrypted sync status/manual sync, database backup download and Admin/Developer-only validated restore with pre-import safety copy | In progress | API/UI and 218-test Windows release pipeline verified; a valid backup/restore round-trip with account-hash assertions is being added. Still need password/recovery changes, employee CSV, expose-all-links, Google Sheets sync, working weekdays, theme/wallpaper, updater and rollback controls; production storage remains a blocker. |
| Cloud sync / customer data | Web standalone encrypted snapshot bootstrap/polling; installation-scoped database sync | Partial | Verify multi-device conflict behavior, identity/password hash preservation, rollback/recovery and production health under real customer data. |
| Updater / rollback | Web exposes update-check API; desktop has in-app update and rollback | Partial | Web browser update workflow and desktop rollback are not equivalent; retain the EXE updater contract and verify old-customer upgrade path on every release. |

## Attendance milestone added in this change

- The web attendance roster now exposes the desktop's core daily fields: status, check-in, check-out, net hours and remarks.
- Added employee filtering, multi-selection, field-selective bulk edit, holiday banner/lockout and monthly workday/present/absent/leave/holiday/total-present summary.
- Added authenticated attendance read/write/summary endpoints, server-side time/status/holiday validation, and atomic bulk persistence.
- Added regression coverage for desktop-compatible summary counting, bulk-edit preservation/clearing, invalid time inputs and attendance API persistence. Run #958 passed all 201 tests, Windows EXE packaging, installer creation, legacy v1.1.74 database-preservation upgrade, and launch smoke test.
- The attendance milestone is released as v1.3.75; v1.3.76 is configured for the next verified release build.

## EOD Archive web milestone — implementation added; verification pending

- Replaced the single-file upload control with multi-PDF upload matching the desktop workflow; employee association, optional report date and notes are applied to each selected PDF.
- Added searchable archive rows with employee, report date, upload time, notes and file size; users can select a document, view it inline, export it, refresh the list, and delete the selected document when authorized.
- Added an authenticated inline-view endpoint. Archive listing and downloads now require a valid session; PDF responses use private no-store caching and X-Content-Type-Options: nosniff.
- Kept permanent deletion restricted to Admin/Developer on the server; the web UI disables the action for other roles. Existing archive records and the archived_documents schema are unchanged.
- Added regression coverage for unauthenticated access, Staff read/view/export, Admin-only deletion, PDF metadata association, and invalid PDF rejection.
- React build, Python regression suite, Windows EXE/installer, legacy database-preservation upgrade and production deployment are pending for this milestone. Direct browser side-by-side verification and production persistence checks must pass before marking it Complete.

## Completion gate

A row can move to **Complete** only after:
1. every desktop field and action has a corresponding web UI and API operation;
2. tests cover create/read/update/delete, permissions, edge cases and migration preservation;
3. functional verification is performed against the same representative customer database in web and EXE;
4. production deployment and health are verified;
5. the matching Windows build/release and web build pass.

No 100% parity claim is permitted while any row above remains Partial or In progress.

## Employee Directory milestone — implementation added; verification pending

- Web create/edit exposes employee code, full name, department/section, designation, phone, email, joining date, notes and active status.
- Web directory adds full-field search, department/group filter, Serial Number / ID, Department / Group, Name (A-Z), and Custom Order sorting.
- Added Manage Sections with add, rename, delete and ordering; employee Move Up/Move Down and Move to Section actions; selected-row editing and activate/deactivate controls.
- Server-side permission checks enforce HR/Admin/Developer for add/edit/activate and Admin/Developer for permanent deletion, section management and reordering. The legacy DELETE endpoint retains its soft-toggle contract for older clients.
- Permanent deletion creates a SQLite safety backup first, then removes tasks, attendance and linked business activities; employee targets cascade and archived documents retain their content with a null employee link.
- Added API regression tests for complete employee fields, section rename propagation to tasks, section and employee ordering, role restrictions, and backup-before-permanent-delete.
- CI, EXE release, legacy upgrade, Render deployment and side-by-side verification against a representative customer database remain pending. Do not mark this row Complete until all gates pass.

## Task Manager milestone — CI and release verified; functional parity still in progress

- Replaced the limited web task form with a dedicated responsive Task Manager matching the desktop TaskDialog's assignment, department, target/actual quantity, progress, priority, extended status, proof URL, expose-link, next-action and dynamic custom key/value fields. Optional details, due time and proof notes are also editable without dropping existing values.
- Added desktop-style date/employee filtering, status/priority/department filters, search, selection, Select All, bulk editing, proof-link opening, task KPI cards and Admin/Developer-only deletion controls.
- Added authenticated task list/create/update/bulk-edit/delete API dependencies. Task deletion enforces Admin/Developer; bulk edit updates only selected fields and runs transactionally.
- API writes now preserve the first submitted/completed timestamp, set it on the first Submitted/Completed transition, keep target/actual and custom values intact, and return 404 for missing tasks. Task date and due-time inputs are validated.
- Added regression tests for the full task-field round trip, custom key/value persistence, filter behavior, submitted timestamp preservation, selective bulk updates and deletion permissions.
- Runs #961 and #962 each passed 206 tests, React build, Python compilation, EXE/installer, legacy v1.1.74 upgrade with unchanged customer DB hash/records, launch smoke test and v1.3.77 release asset verification. Render deployed the frontend bundle and reports the service live. The task manager is still not Complete until the remaining bulk fields/status behavior are covered, the browser is functionally exercised against the EXE and same customer data, and production database sync/storage durability is verified.

## Employee Tracker milestone — implementation added; functional parity verification pending

- Added the employee/date selectors, task summary/progress KPIs, task list, add/edit/delete/open-proof actions and filters by reusing the shared Task Manager component and API.
- Regression coverage and CI/EXE release gates passed in runs #966 and #967. Direct browser side-by-side verification against the desktop EXE and a representative customer database remains open.
- Preserve the shared Task Manager permission and evidence-link behavior; do not create a second task data model.


## Print Center web milestone — core UI/API and exports implemented; side-by-side parity verification pending

- Added a dedicated responsive React Print Center with the Windows report types: Audit / EOD, Employee Attendance, Employee Details, and Employee Productivity.
- Added consolidated and individual employee scope, report-only employee exclusion, date selection, and Word/PDF/CSV output selection.
- Added report-specific include/exclude controls for identity, contact, attendance fields, productivity metrics, task fields, proof links, remarks, employee notes, and optional product/service catalogs.
- Added authenticated /api/reports/preview and /api/reports/export operations. Preview and export share the same report filters/options. Exclusion is a query filter only and never modifies employee records.
- DOCX and PDF exports retain exposed evidence URLs as clickable links; CSV exports preserve the report's sections and fields as section/field/value rows.
- Added regression tests for employee exclusion, hidden private notes, and PDF/DOCX/CSV response formats.
- Corrected the web product-list API and Print Center catalog to call the shared desktop `business_tracking.available_stock()` calculation; the regression fixture covers dispatched, free, returned, damaged, expired and quarantined quantities and verifies available stock of 111.
- Run #976 passed 213 regression tests, React production build, Cloudflare Worker checks, Python compilation, Windows EXE compilation, installer generation, legacy v1.1.74 in-place upgrade with unchanged customer database hash and sentinel records, application launch smoke test, and v1.3.77 release asset verification.
- Remaining: compare generated DOCX/PDF layout and CSV columns/values against the EXE for each report type; verify evidence-link exposure and every report field against the same customer database; test report permissions in production. Do not mark Print Center Complete until these checks pass.


## Business Tracking web milestone — implementation added; verification pending

- Replaced the previous three basic inline forms with a dedicated Business Tracking workspace matching the desktop sub-tabs: Dashboard, Products & Inventory, Orders, Services & Members, and Employee Activities.
- Product creation now exposes the desktop database fields for SKU, category, brand, package type, unit, opening/received/reserved/dispatched/free/returned/damaged/expired/quarantined quantities, purchase/selling prices, reorder level, batch, expiry and storage location.
- Added a stock movement ledger API and UI for receive, reserve, release, dispatch, free/promotional, return, damage, expiry, quarantine and unquarantine movements. Each movement updates the aggregate product quantity and ledger record in one SQLite transaction; outbound movements are rejected when they exceed available stock.
- Order entry now exposes customer/contact, channel, payment mode, status, discount, order value, invoice, shipment, assigned employee and remarks. Order status updates use the existing status endpoint.
- Service and membership forms now expose training mode, service unit, duration, sessions, validity, price, member registration/start/expiry dates, purchased/completed sessions, assigned trainer, membership/payment status, invoice and remarks. Membership session/status updates are persisted through authenticated PATCH operations.
- Employee activities now expose employee, related order/service/product, task type, quantity/unit, start/completion time, status, proof reference and remarks; activity status updates preserve timestamps and automatically set start/completion time when transitioning to In Progress/Completed.
- Business overview now calculates low-stock counts using the same stock ledger formula as the desktop and correctly reads the bt_orders.order_status column.
- Business read APIs now require an authenticated session. New regression tests cover unauthenticated denial, full-field persistence, stock movement atomicity/overdraw protection, order lifecycle, membership sessions, activity status and overview counts.
- The additive implementation uses the existing bt_* tables; no customer table replacement, account/password migration, encryption-key change or updater contract change is included. CI, Windows installer/legacy upgrade, production deployment, and direct browser side-by-side verification remain pending. Do not mark this module Complete until those gates pass.


## Settings / database backup milestone — implementation added; verification pending

- Registered the existing standalone web database export/import routes with the FastAPI application; previously the route module was present but not imported, so the frontend's database backup controls could not reach it.
- Added authenticated `/api/system/db-info` with safe database size, integrity, table counts, backup count, app version and encrypted-sync status. It does not expose the absolute database path or account usernames.
- Added authenticated `/api/system/sync-now`, delegating to the existing `WebDatabaseSync.sync_now` manager without changing the Worker URL, installation ID, encryption secret, key derivation or snapshot path.
- Exposed database backup download in the web Settings page. Database restore is restricted to Admin/Developer, validates the uploaded SQLite database, retains a pre-import backup, and clears web sessions while preserving the imported account identities and password hashes.
- Added API regression tests for authentication, safe DB metadata, manual sync delegation, backup download, and Staff-versus-Admin restore permissions.
- [Run #981](https://github.com/yalangisexter-ux/audit-report/actions/runs/41954082587) passed 218 regression tests and the full Windows EXE, installer, legacy v1.1.74 database-preservation upgrade, launch smoke test and v1.3.77 release verification. Render loaded 80 API routes and the deployment reached live. A valid backup/restore round-trip with account-hash assertions is included in the next regression update. Render currently has no persistent disk mounted, so production restore must not be treated as durable until service storage is corrected.
