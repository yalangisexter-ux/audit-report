# Web / Windows EXE feature-parity tracker

Last inspected: 2026-11-05. Repository target: `main`. This is an evidence ledger, not a completion claim.

## Verification baseline

- Latest successful Task Manager workflows: [run #961](https://github.com/yalangisexter-ux/audit-report/actions/runs/41903793821) and [run #962](https://github.com/yalangisexter-ux/audit-report/actions/runs/41903866497). Both passed 206 regression tests, React production build, Cloudflare checks, Python compilation, Windows EXE packaging, installer generation, legacy v1.1.74 database-preservation upgrade, launch smoke test and v1.3.77 release asset verification.
- Run #959 passed the React production build, frontend bundle publication, Cloudflare JavaScript checks, isolated database-sync Worker tests, Python compilation, regression suite, Windows EXE packaging, installer creation, legacy v1.1.74 in-place upgrade with unchanged customer database hash and records, application launch smoke test, and v1.3.76 release asset verification.
- Latest published desktop release: [v1.3.77](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.77); the verified installer asset is published and the v1.1.74 in-place upgrade preserved the customer database hash and records.
- Render served the new frontend bundle commit `103aa9182a1e70376dfecf68b7ea8ebb06894199` and subsequent encrypted snapshot deployments reached `live`; logs show application startup complete and HTTP 200 for `/`. The service is still configured as a Free instance without a persistent disk or `/api/health` health-check path, unlike `render.yaml` (Starter + `/var/data` disk); storage durability therefore remains a production blocker until the actual service configuration is reconciled.
- The Employee Directory parity milestone is configured as **v1.3.77**; its release remains pending regression, Windows packaging, legacy upgrade, and production deployment gates.

- Current main also contains automated encrypted customer snapshot updates. Do not replace, normalize, or re-encrypt those files as part of UI parity work. Employee Directory is configured as v1.3.77; its release remains pending CI and production verification.

## Screen-by-screen parity ledger

| Desktop screen / workflow | Web implementation inspected | Status | Remaining verification / gaps |
|---|---|---|---|
| Login, registration, password recovery | React login, pending registration, recovery question/reset; standalone sessions and case-sensitive account migration | Partial | Verify Admin/Developer/Staff role behavior against the EXE; web currently exposes account activation but not the full desktop role-change/password-admin workflow. |
| Home / Dashboard | KPI cards, today's tasks, quick actions | Partial | Desktop has richer dashboard cards, charts, attendance/task telemetry, clock, refresh behavior and role-aware shortcuts. Compare every chart/action and data calculation. |
| Employees | Create/list/edit/delete with name, employee code, department, designation, phone, email; API model also accepts joining date, notes and active | Partial | Web form does not expose all desktop fields, group management, custom ordering/reordering, target assignment and complete employee detail actions. |
| Task Manager | Dedicated React UI/API cover assignment, date, department, details, due time, target/actual, progress, priority, status (including Not selected), proof URL/note, next action, report-link exposure, dynamic custom fields, filters, search, selection, full desktop bulk-edit fields, evidence opening and Admin/Developer-only delete | In progress | CI #961/#962 passed 206 tests, EXE/installer, legacy database-preservation upgrade and smoke test; Render frontend is live. Still need browser functional verification against the EXE and same customer data, plus verify production encrypted sync and persistent storage. |
| Employee Tracker | Web shows employee task/open-task counts | Partial | Desktop supports employee-specific task creation/editing, proof links, targets and detailed progress. |
| Attendance & Working Calendar | Daily roster, selected date, status marking, time/remarks editing, employee filter, multi-selection, selective bulk edit, net hours, monthly totals and holiday declaration/removal | In progress | API/desktop regression coverage passed in run #958 (201 tests). Still requires direct side-by-side functional verification on a representative customer database, including role restrictions and legacy attendance detail display. |
| Print Center / Reports | Four report types, text preview and browser print/save-to-PDF | Partial | Desktop supports consolidated/individual scope, excluded employee, option checkboxes, historical PDF selection, DOCX/PDF/CSV exports and evidence-link controls. Web does not yet expose all of these controls/formats. |
| Historical EOD Archive | Upload, download, list, Admin/Developer delete | Partial | Desktop additionally supports view/open selected and export selected; verify notes/employee/date metadata and access restrictions. |
| Business Tracking | Products, services, orders and members basic CRUD/listing | Partial | Desktop inventory fields, stock movement/reservation/returns/damage, service sessions, activity assignment, payment/order lifecycle and full report options are not all exposed in web UI. |
| Store Directory / Scraping | Public merchant scraping, prospect create/edit/delete, archive and status endpoints | Partial | Verify all desktop prospect fields, scrape sources, filters, deduplication, multi-location evidence and export/report workflows. |
| Live Chat | General-channel message list/send in web | Partial | Desktop supports private conversations and authorized groups; web needs channel/user selection, unread state, reconnect and role/permission parity. |
| Settings & Backup | Web account activation and DB info | Partial | Desktop includes backup/restore, password/recovery changes, employee CSV, expose-all-links, Google Sheets sync, working weekdays, sync diagnostics, theme/wallpaper, updater and rollback controls. |
| Cloud sync / customer data | Web standalone encrypted snapshot bootstrap/polling; installation-scoped database sync | Partial | Verify multi-device conflict behavior, identity/password hash preservation, rollback/recovery and production health under real customer data. |
| Updater / rollback | Web exposes update-check API; desktop has in-app update and rollback | Partial | Web browser update workflow and desktop rollback are not equivalent; retain the EXE updater contract and verify old-customer upgrade path on every release. |

## Attendance milestone added in this change

- The web attendance roster now exposes the desktop's core daily fields: status, check-in, check-out, net hours and remarks.
- Added employee filtering, multi-selection, field-selective bulk edit, holiday banner/lockout and monthly workday/present/absent/leave/holiday/total-present summary.
- Added authenticated attendance read/write/summary endpoints, server-side time/status/holiday validation, and atomic bulk persistence.
- Added regression coverage for desktop-compatible summary counting, bulk-edit preservation/clearing, invalid time inputs and attendance API persistence. Run #958 passed all 201 tests, Windows EXE packaging, installer creation, legacy v1.1.74 database-preservation upgrade, and launch smoke test.
- The attendance milestone is released as v1.3.75; v1.3.76 is configured for the next verified release build.

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

## Next parity milestone — Employee Tracker

- Compare the desktop employee/date selector, task summary/progress, task table and add/edit/delete/open-proof actions with the web tracker.
- Preserve the shared Task Manager permission and evidence-link behavior; do not create a second task data model.
