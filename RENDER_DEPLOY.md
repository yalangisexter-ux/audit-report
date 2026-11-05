# Render web deployment and encrypted database synchronization

## Deployment model

The browser application runs as a single Render web service. The Windows EXE continues to use its own LocalAppData database and updater; the Render process never opens that local Windows database.

The web service keeps a separate SQLite working copy at `web-data/web_employee_audit.db` (or the directory supplied by `AUDIT_DATA_DIR`). It participates in the same logical customer installation through the Cloudflare encrypted snapshot Worker:

1. On first database initialization, `api_server.ensure_database()` creates the web working copy and `WebDatabaseSync.bootstrap()` pulls the snapshot for the configured `DB_SYNC_INSTALLATION_ID`.
2. The snapshot is decrypted and SQLite-validated locally, then merged without replacing existing rows or account identities. The same installation ID and encryption secret must be used by the EXE and web service.
3. Web database commits mark the working copy dirty. The sync manager asynchronously encrypts and pushes a snapshot through the Worker.
4. The web poller checks the remote snapshot every 60 seconds. Remote changes are merged into the web working copy and any resulting local merge is queued for upload.
5. The Worker stores only encrypted snapshot bytes in the repository's `customer-data/` directory. Exact-installation pulls return 404 when that installation has no snapshot; they must never fall back to another customer's snapshot.

This is an eventually consistent, encrypted snapshot/merge design. It is not a shared SQLite file or a transactionally live network database. Desktop-to-web and web-to-desktop changes become visible after the relevant push/poll cycle.

## Free-tier storage limits

The current Render service is on the Free plan and has no persistent disk. The repository Blueprint is aligned to that deployment:

- one Free web instance;
- no Render disk or paid-plan upgrade;
- `WEB_STANDALONE=1` for a separate web SQLite working copy;
- `DB_SYNC_WORKER_URL`, `DB_SYNC_INSTALLATION_ID`, and `DB_SYNC_ENCRYPTION_SECRET` for encrypted snapshot sync;
- `/api/health` as the configured health-check path;
- deployment only after GitHub checks pass, with build filters excluding encrypted customer snapshot files.

Because the Free filesystem is ephemeral, the local SQLite file, local backups, sync-device credentials, and login sessions can disappear after a restart or redeploy. The database is reconstructed from the encrypted snapshot on the next bootstrap. Users may need to sign in again after a restart.

There is an unavoidable short write-to-snapshot window: if the Render process stops after a database commit but before the asynchronous encrypted upload succeeds, that last change may not yet exist in the remote snapshot. The Settings sync status and Worker upload result must be monitored. Keep independent customer database exports before migrations or recovery work. For zero-loss production guarantees, a persistent disk or external transactional database is required; do not upgrade the Render plan or incur a charge without explicit approval.

## Account and encryption safety

- Preserve the exact-case `Admin` and `admin` account identities and their existing password salts/hashes. The web login adapter verifies the desktop PBKDF2 hash; do not replace the accounts or rotate credentials during routine deploys.
- Do not change `DB_SYNC_INSTALLATION_ID`, `DB_SYNC_ENCRYPTION_SECRET`, the Worker URL, or the snapshot encryption format without a tested migration and recovery plan.
- If the secret is missing or a snapshot cannot be decrypted/validated, sync must fail closed. Never overwrite an unreadable remote snapshot or enable first-admin setup merely because the local working copy is empty.
- Worker snapshot commits use the Render skip phrase `[skip render]`. The Worker regression tests verify that this phrase is present and that an installation with no snapshot cannot read another installation's snapshot.

## Render service configuration reconciliation

The Render service inspected on 2026-11-05 was live on the Free plan, but its dashboard settings still differed from this Blueprint: auto-deploy was set to every commit, no health-check path was configured, and its build/start commands were older than the repository configuration. Apply/sync the Blueprint in the Render dashboard to adopt the build filter, checks-pass deployment gate, React production build, current start command, and health check. The available Render connection can inspect deployments and logs but cannot edit those service-level settings directly.

## Desktop application isolation

- The Windows EXE continues using its existing LocalAppData database and in-app updater.
- Render builds and runs only the browser application. It does not package, replace, or publish the Windows EXE.
- Web and EXE use separate local SQLite working copies and converge through installation-scoped encrypted snapshots. Do not describe them as directly sharing one SQLite file.

## Local development

```bash
WEB_STANDALONE=1 AUDIT_DATA_DIR=./web-data python run_web.py --no-browser
# or
WEB_STANDALONE=1 AUDIT_DATA_DIR=./web-data uvicorn api_server:app --host 0.0.0.0 --port 8000
```

## Payment gateway placeholders

The Settings page exposes Razorpay, Cashfree, Stripe and PayPal configuration status for administrator/developer accounts. The API returns only whether required environment variables are present and their names; it never returns secret values. Payment processing remains disabled until provider checkout adapters, signature-verified webhooks, refund handling and end-to-end sandbox tests are added.

Configure payment secrets only in Render Dashboard → audit-report-web → Environment. Never enter secrets into the browser UI or commit them to Git.

- Razorpay test: `RAZORPAY_TEST_KEY_ID`, `RAZORPAY_TEST_KEY_SECRET`, `RAZORPAY_TEST_WEBHOOK_SECRET`
- Razorpay live: `RAZORPAY_LIVE_KEY_ID`, `RAZORPAY_LIVE_KEY_SECRET`, `RAZORPAY_LIVE_WEBHOOK_SECRET`
- Cashfree test: `CASHFREE_TEST_CLIENT_ID`, `CASHFREE_TEST_CLIENT_SECRET`, `CASHFREE_TEST_WEBHOOK_SECRET`
- Cashfree live: `CASHFREE_LIVE_CLIENT_ID`, `CASHFREE_LIVE_CLIENT_SECRET`, `CASHFREE_LIVE_WEBHOOK_SECRET`
- Stripe test: `STRIPE_TEST_PUBLISHABLE_KEY`, `STRIPE_TEST_SECRET_KEY`, `STRIPE_TEST_WEBHOOK_SECRET`
- Stripe live: `STRIPE_LIVE_PUBLISHABLE_KEY`, `STRIPE_LIVE_SECRET_KEY`, `STRIPE_LIVE_WEBHOOK_SECRET`
- PayPal test: `PAYPAL_TEST_CLIENT_ID`, `PAYPAL_TEST_CLIENT_SECRET`, `PAYPAL_TEST_WEBHOOK_ID`
- PayPal live: `PAYPAL_LIVE_CLIENT_ID`, `PAYPAL_LIVE_CLIENT_SECRET`, `PAYPAL_LIVE_WEBHOOK_ID`
- Store settings: `PAYMENT_CURRENCY=INR`, `PAYMENT_TAX_RATE_PERCENT`, `PAYMENT_SHIPPING_FLAT_RATE`

Start with sandbox mode. Never enable live payments until provider webhooks and order reconciliation are tested.
