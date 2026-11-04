# Web / Windows EXE feature-parity tracker

Last inspected: 2026-11-04. Repository target: `main`. This is an evidence ledger, not a completion claim.

## Verification baseline

- Latest successful full workflow inspected: [run #955](https://github.com/yalangisexter-ux/audit-report/actions/runs/41881545692).
- The run passed the React production build, frontend bundle publication, Cloudflare JavaScript checks, Python compile, pytest (198 passed), Windows EXE packaging, installer creation, legacy v1.1.74 in-place upgrade/database-preservation smoke test, application launch smoke test, and v1.3.75 release asset verification.
- Latest published desktop release at inspection: [v1.3.75](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.75).
- Current main also contains automated encrypted customer snapshot updates. Do not replace, normalize, or re-encrypt those files as part of UI parity work.

## Screen-by-screen parity ledger

| Desktop screen / workflow | Web implementation inspected | Status | Remaining verification / gaps |
|---|---|---|---|
| Login, registration, password recovery | React login, pending registration, recovery question/reset; standalone sessions and case-sensitive account migration | Partial | Verify Admin/Developer/Staff role behavior against the EXE; web currently exposes account activation but not the full desktop role-change/password-admin workflow. |
| Home / Dashboard | KPI cards, today's tasks, quick actions | Partial | Desktop has richer dashboard cards, charts, attendance/task telemetry, clock, refresh behavior and role-aware shortcuts. Compare every chart/action and data calculation. |
| Employees | Create/list/edit/delete with name, employee code, department, designation, phone, email; API model also accepts joining date, notes and active | Partial | Web form does not expose all desktop fields, group management, custom ordering/reordering, target assignment and complete employee detail actions. |
| Task Manager | Create/list/edit/delete; API model accepts due time, priority, status, progress, target/actual quantity, next action, proof URL/note, manager note, expose-link and custom values | Partial | Web form and table expose only a subset. Add every desktop field, dynamic custom tracking fields, proof-link behavior, filtering/sorting, and all edit actions. |
| Employee Tracker | Web shows employee task/open-task counts | Partial | Desktop supports employee-specific task creation/editing, proof links, targets and detailed progress. |
| Attendance & Working Calendar | Daily roster, selected date, status marking, holiday declaration/removal | In progress | This change adds time/remarks editing, employee filter, selection/bulk editing, net hours and monthly totals. Verify UI and all API tests before marking complete. |
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
- Added regression coverage for desktop-compatible summary counting, bulk-edit preservation/clearing, and invalid time inputs.

## Completion gate

A row can move to **Complete** only after:
1. every desktop field and action has a corresponding web UI and API operation;
2. tests cover create/read/update/delete, permissions, edge cases and migration preservation;
3. functional verification is performed against the same representative customer database in web and EXE;
4. production deployment and health are verified;
5. the matching Windows build/release and web build pass.

No 100% parity claim is permitted while any row above remains Partial or In progress.
