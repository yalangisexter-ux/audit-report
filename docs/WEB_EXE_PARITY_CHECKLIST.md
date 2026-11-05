# Web / Windows EXE feature-parity tracker

Last inspected: 2026-11-05 21:39 IST. Repository target: `main`. This is an evidence ledger, not a completion claim.

## Verification baseline

- Latest successful full regression + Windows installer verification: [Master Build and Test run #1102](https://github.com/yalangisexter-ux/audit-report/actions/runs/42054888962), commit `8c61bb9becbd7dbbb4a38a42bfebf5d25207670d`, passed **274 regression tests** in 12m17s. React production build/frontend publication, Cloudflare Worker validation/tests, Python compilation, PyInstaller EXE build, Inno Setup installer, legacy v1.1.74 in-place upgrade, uninstall/reinstall customer-database hash + SQLite integrity/sentinel checks, native Windows launch smoke test, Actions artifact upload and public v1.3.81 release-asset verification all passed. Five later commits on current `main` add only four encrypted `customer-data/*.db.enc` snapshots (comparison `8c61bb9...6131b6f`); the Live Chat web integration commits below are newer than this verified baseline and await CI.
- Latest published desktop release is [v1.3.81](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.81). Run #1102 rebuilt the installer from commit `8c61bb9becbd7dbbb4a38a42bfebf5d25207670d`, uploaded it to the public release and verified exactly one non-draft/non-prerelease installer asset. Direct installer: [RawStrengthEmployeeAuditManager-Setup.exe](https://github.com/yalangisexter-ux/audit-report/releases/download/v1.3.81/RawStrengthEmployeeAuditManager-Setup.exe). Verified release asset SHA-256: `231b73d3476dd338d98e83a6874618b8b300890652c8c21a03de261cbe9ece1c`.
- Latest published desktop release is [v1.3.81](https://github.com/yalangisexter-ux/audit-report/releases/tag/v1.3.81). Version metadata is consistently v1.3.81 across `build_info.py`, `installer.iss`, `version_info.txt`, `.github/workflows/master.yml`, and `frontend/package.json`. Do not bump for minor web-only parity corrections (daily employee target/report sync, Store Directory workbook/region/export work, and read-API security).
- Follow-ups are committed directly to `main`; generated encrypted customer snapshot files are preserved and no feature branches or PRs are used.
- Cloudflare DB-sync Worker version **809**, deployment `7750fd42-8700-454c-87cf-930c9c468a02`, is at **100%** traffic (latest deployment 2026-11-05 07:48 UTC; Worker commit annotation `f64f344bb42acd1881a5fe92fc269e7ad83fde5f`). Existing Durable Object namespace and binding types remain present. Run #1099 passed the isolated Worker validation/test step.
- Last confirmed Render deployment was application commit `8d01e178f265e303855273f17ba35e637669cdb4`, deployment `dep-dbm5r6jbc2fs73apuko0`, at 2026-11-05 10:44 UTC; it reported Live and `HEAD /` returned HTTP 200. Render health could not be rechecked in this run because no workspace is selected in the Render connector. One workspace is available, but explicit user confirmation is required before selecting it; no Render resource was changed.
- The last recorded live-dashboard inspection found the Render service on Free, without a persistent disk or health-check path, using older build/start commands and auto-deploying every commit. Repository `render.yaml` describes `checksPass`, build filters and `/api/health`, but adoption is not revalidated in this run. Free filesystem durability and write-to-snapshot recovery remain blockers; no paid plan or storage change was made.
- The web migration is **not complete**. The screen-by-screen rows below remain Partial or In progress until every desktop action, field, permission and workflow has been browser-verified against the EXE using representative customer data, and production sync/health checks pass.

## Screen-by-screen parity ledger

| Desktop screen / workflow | Web implementation inspected | Status | Remaining verification / gaps |
|---|---|---|---|
| Login, registration, password recovery, account management | React login, pending registration, recovery question/reset, Admin-created active accounts, role changes, activation/deactivation and Admin password reset | In progress | Run the new account-management regression suite and verify every role/permission edge against the EXE in a browser using representative customer accounts. |
| Home / Dashboard | KPI cards, today's tasks, quick actions | Partial | Desktop has richer dashboard cards, charts, attendance/task telemetry, clock, refresh behavior and role-aware shortcuts. Compare every chart/action and data calculation. |
| Employees | Create/list/edit/status and soft/permanent delete with safety backup; employee code, name, section/department, designation, phone, email, joining date and notes; employee-group create/rename/delete/order and custom employee ordering/move-to-group APIs | In progress | Browser-verify every field, group action, inactive-employee flow and role matrix against the EXE using representative customer data. |
| Task Manager | Dedicated React UI/API cover assignment, date, department, details, due time, target/actual, per-employee/per-date target and target-status read/write, progress, priority, status (including Not selected), proof URL/note, next action, report-link exposure, dynamic custom fields, filters, search, selection, full desktop bulk-edit fields, evidence opening and Admin/Developer-only delete | In progress | Run #1102 passed 274 regression tests and the v1.3.81 EXE/installer pipeline. The daily employee target read/write correction preserves existing target values when legacy clients omit quantity fields. Browser functional verification against the EXE and production sync/storage checks remain. |
| Employee Tracker | Dedicated React Task Manager in Tracker mode with employee/date selectors, task KPIs, filtered task list, add/edit/delete, proof opening and shared Task Manager API/model | In progress | Runs #966/#967 verified the tracker UI/API and regression coverage. Still require direct browser side-by-side testing against the EXE using representative customer data, plus production sync/storage verification. |
| Attendance & Working Calendar | Daily roster, selected date, status marking, time/remarks editing, employee filter, multi-selection, selective bulk edit, net hours, monthly totals and holiday declaration/removal | In progress | Run #1102 passed the new date-change persistence regressions within all 274 tests. Pending check-in/check-out/remarks are flushed using the old row date before navigation; invalid values block navigation, and stale editors cannot undo toolbar status changes. Direct side-by-side verification on a representative customer database, role restrictions and legacy attendance detail display remain. |
| Print Center / Reports | Dedicated React Print Center with four report types, consolidated/individual/excluded employee scope, date and report-specific field toggles, preview, PDF/DOCX/CSV export APIs and exposed evidence-link handling | In progress | Run #1099 passed 270 regression tests including employee exclusion, hidden-field behavior, branded PDF logo/metadata/embedded font, DOCX/CSV exports and full stock-ledger calculation; React build, Python compilation, EXE/installer, legacy upgrade and launch smoke also passed. Still require document-layout/field-by-field comparison against the EXE and production permission checks. |
| Historical EOD Archive | Multi-PDF upload, employee/date/notes association, searchable selection, inline view, export, refresh, Admin/Developer delete | In progress | Automated auth/RBAC and metadata regression coverage added; direct browser side-by-side verification and production storage/sync checks remain. |
| Business Tracking | Dedicated React workspace with Dashboard, Products & Inventory, stock movement ledger, Orders, Services & Members, and Employee Activities | In progress | Automated API and UI regression coverage plus direct browser/EXE side-by-side verification, permission checks and production sync/storage verification are pending. |
| Store Directory / Scraping | Evidence-backed public merchant scraping, create/edit/delete APIs, branch-aware dedupe, address/email/website/Maps fields, Admin/Developer edit/delete permissions, encrypted-sync callback on scrape commits, stable keyset API pagination, 100-row React paging, workbook import/merge, regional benchmark import, filtered CSV/XLSX exports, regional summary and print previews | In progress | Run #1099 passed the 2,505-record no-gap/no-duplicate pagination regression and Store Directory workbook/benchmark/export safety tests. Browser-verify filters/exclusions, map links, print workflows, real merchant source accuracy and dedupe against representative customer data. |
| Live Chat | Main React Live Chat tab now embeds the existing Worker-served client for private/group conversations, authorized membership, reconnect, WebRTC audio/video and screen sharing; it also offers reload and open-in-new-tab actions. The chat service keeps its own sign-in and membership boundary. | Partial | The iframe integration and its authentication boundary have source-level regression tests, but these commits are newer than run #1102. Browser-verify embed storage, camera/microphone/display-capture permissions, private/group membership and reconnect against the desktop workflow. The desktop support-chat tab still needs a field/action comparison, and chat identity is not yet unified with the Audit Manager login. |
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

## User account management milestone — implementation added; CI verification pending

- Added Admin/Developer-only account creation from Settings, including username, display name, role, initial password and recovery question/answer. New accounts are active immediately, matching the Windows Manage User Accounts workflow; public self-registration remains pending until an Admin activates it.
- Added role changes for Staff, HR, Admin and Developer accounts. The last active Admin cannot be demoted. Developer accounts and Developer-role assignment remain restricted to Developer callers to preserve the web application's existing developer-account isolation.
- Added Admin password reset using the same desktop_app.hash_pin PBKDF2 scheme as the EXE. Password plaintext is never logged or returned.
- Account deactivation, role changes and password resets invalidate the target's in-memory and persistent web sessions. Account actions are recorded in audit_log; existing usernames, IDs, password hashes and recovery hashes are not rewritten by role changes.
- Added seven regression tests covering account creation and case-insensitive duplicate rejection, role updates without hash changes, last-Admin protection, password hashing/session invalidation, Staff denial, Developer isolation, and standalone persistent-session invalidation.
- This major account-management milestone is configured as v1.3.79 across build_info.py, installer.iss, version_info.txt, and .github/workflows/master.yml. CI, Windows packaging, legacy database-upgrade verification, release publication and production deployment must pass before calling the milestone verified.

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

## Main React Live Chat integration — implementation added; CI verification pending

- Replaced the main React tab's legacy general-channel-only message list/composer with the existing Worker-hosted private/group chat client served from the same `chat-web/` assets used by the Cloudflare Worker.
- Added a responsive in-app frame, explicit reload and open-in-new-tab actions, and camera/microphone/display-capture/fullscreen permission delegation so the existing audio/video and screen-share flows can run inside the web workspace.
- The component resolves `VITE_CHAT_WORKER_URL` only as an HTTPS origin and falls back to the same public Worker origin used by the desktop chat module. No chat password or Audit Manager bearer token is copied into the frame.
- Kept the separate chat-service sign-in and member-only authorization boundary explicit; this change does not claim single sign-on or identity unification.
- Added `tests/test_web_live_chat_integration.py` to guard the React navigation, Worker asset origin, iframe permissions, safe new-tab relationship and separate-auth boundary. Run #1103 failed at Vite import resolution because the first commit referenced the component before its follow-up commit added it; runs #1104/#1105 are revalidating the complete source state. Browser functional comparison and production deployment checks remain open. No version bump is appropriate for this web-only integration.

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
- Version metadata is advanced consistently to v1.3.81 for this cross-device account-identity integrity milestone. Windows installer build, legacy upgrade, launch smoke test, production deployment and live account/sync round-trip remain pending until CI and deployment finish.



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
- Added regression coverage for legacy Monday–Friday settings, Sunday attendance summary counts, Admin/Developer-only weekday configuration, invalid weekday values, and authorization of the generic settings API. CI and production deployment verification for this correction are pending.

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

### Store Directory scraper encrypted-sync callback — CI verification pending

- Found that the background scraper opened a raw SQLite connection, bypassing `SyncableSQLiteConnection` and its encrypted snapshot commit callback. Scraped records could therefore be saved locally without being marked pending for cloud sync.
- Changed the scraper to use the shared `api.get_db()` connection and close its dependency generator reliably. Empty scrape results do not create a needless sync write.
- Added a regression test that stubs the crawler, verifies a prospect is inserted, and asserts that the encrypted-sync manager receives exactly one pending notification.
- Commit: [dfd7a2f](https://github.com/yalangisexter-ux/audit-report/commit/dfd7a2f09093ce8ac96f8fc8dcf824b0459c4d96). [Run #1057](https://github.com/yalangisexter-ux/audit-report/actions/runs/42017224257) is still running; do not treat this fix as CI-verified until it completes. The commit was deployed to Render and Uvicorn startup plus the root HEAD/GET 200 probe succeeded.

### Administrator credential hash preservation — CI verification pending

- The Render startup helper previously replaced an existing Admin/admin password hash when the configured deployment secret did not match it. That could silently change customer credentials during Blueprint adoption.
- The helper now preserves existing exact-case account IDs, display names, password salts and hashes. It only heals role/active metadata, refuses to auto-reset an existing account with a missing hash, and uses deployment secrets only when creating a genuinely missing account.
- Updated regression coverage verifies that a later deployment with different secrets cannot rotate either existing account hash, while a missing Developer account can still be provisioned.
- Commit: [a6abc0e](https://github.com/yalangisexter-ux/audit-report/commit/a6abc0eb87308bcc9af059660edb695becef1051). [Run #1058](https://github.com/yalangisexter-ux/audit-report/actions/runs/42018091578) is running; this helper is not yet CI-verified and is not active in the live Render start command until the Blueprint plan is approved.

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
## Print Center PDF font regression diagnosis — 2026-11-05

- GitHub Actions runs #1084 through #1088 repeatedly failed at the same single assertion in `test_web_print_center_exports_pdf_docx_and_csv`; the other 265 tests in #1088 passed.
- The generated PDF was valid, branded, included the Raw Strength logo and metadata, but ReportLab did not serialize the registration alias `RawStrengthSans` into the PDF. TrueType fonts are embedded under the font face's internal DejaVu name, often with a subset prefix.
- The regression assertion is corrected to verify the embedded `DejaVuSans` face name and `/FontFile2` font program rather than the Python-side registration alias. This tests the actual embedded font and avoids a false negative.
- The correction is not considered verified until the next complete GitHub Actions run passes; no version bump is appropriate for this test-only fix.

## Store Directory pagination re-inspection — 2026-11-05

- Re-inspection of current `main` confirms keyset pagination is present in `web_ops_routes.py`: `limit` is capped at 1,000 and `before_id` advances a descending ID cursor. The React `fetchAllProspects()` requests every page, then `prospectRows` applies the current search/filter set and displays 100 rows at a time.
- `test_customer_prospect_api_keyset_pagination_returns_every_row_once` verifies a 2,505-record fixture returns all IDs exactly once. This is source/test evidence, not production proof that all 5,003 restored records are visible to a real authenticated browser session.
- The earlier statement that pagination had not landed was incorrect and is superseded by this evidence. The current main also includes workbook import/merge, regional benchmark import, filtered CSV/XLSX exports, regional summary and print-preview code with regression coverage; Store Directory remains In progress until browser/production verification is complete.
