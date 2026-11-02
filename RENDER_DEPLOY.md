# Deploy the standalone web edition on Render

1. Connect `yalangisexter-ux/audit-report` to Render as a Blueprint and apply the existing `render.yaml`.
2. Render builds the full web application from `requirements-web.txt` and serves the checked-in production client in `frontend/dist`.
3. The Blueprint runs the web service in standalone mode with `AUDIT_DATA_DIR=/var/data` and attaches a 10 GB persistent disk at `/var/data`.
4. The service is intentionally configured as a single paid Starter instance. SQLite and the file-backed web session store must remain on the same persistent disk; do not scale this SQLite service horizontally.
5. Do not change `AUDIT_DATA_DIR` to an ephemeral path, remove the persistent disk, or downgrade the service to Render Free for real customer data. Render Free filesystems are ephemeral and can cause the database and login accounts to disappear after restarts or redeployments.

## Database and account persistence

- The standalone web database is `/var/data/web_employee_audit.db`.
- Web session state is stored under the same persistent data directory.
- `WEB_STANDALONE=1` disables desktop/cloud snapshot synchronization. The web service does not pull or overwrite the web database from the desktop database-sync Worker.
- First-admin setup is permitted only when the web database contains no active account. Once an Admin account exists, the setup endpoint rejects another setup request.
- Keep the existing persistent disk attached when deploying new versions. Do not delete or recreate it as part of routine deploys.
- Before any database migration or manual replacement, export a web database backup from Settings and retain a separate copy.
- Import an existing desktop `.db` file from **Settings → Standalone Web Database → Import old database**. The import validates SQLite integrity and required tables, retains a pre-import backup, and then replaces only the web database.
- Export a complete SQLite copy from the same Settings page. After an import, sign in using credentials contained in the imported database.

## Desktop application isolation

- The Windows EXE continues using its existing LocalAppData database and updater.
- The Render service builds and runs only the browser/web application. It does not package, replace, or publish the Windows EXE.
- Web and desktop databases are separate unless an administrator explicitly imports a compatible desktop database through the web Settings page.

## Mobile and desktop browser access

The browser interface is responsive and can be opened from a phone, tablet, or desktop browser. Use the same web URL and web account on each device. All requests reach the single web service instance backed by the persistent disk.

## Local development

```bash
python run_web.py --no-browser
# or
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

For local standalone testing, set `WEB_STANDALONE=1` and `AUDIT_DATA_DIR=./web-data` before starting the server.

## Payment gateway placeholders

The Settings page exposes Razorpay, Cashfree, Stripe and PayPal configuration status for administrator/developer accounts. The API returns only whether required environment variables are present and their names; it never returns secret values. Payment processing deliberately remains disabled until provider checkout adapters, signature-verified webhooks, refund handling and end-to-end sandbox tests are added.

Configure the following in Render Dashboard → audit-report-web → Environment. Do not enter secrets into the browser UI or commit them to Git.

- Razorpay test: `RAZORPAY_TEST_KEY_ID`, `RAZORPAY_TEST_KEY_SECRET`, `RAZORPAY_TEST_WEBHOOK_SECRET`
- Razorpay live: `RAZORPAY_LIVE_KEY_ID`, `RAZORPAY_LIVE_KEY_SECRET`, `RAZORPAY_LIVE_WEBHOOK_SECRET`
- Cashfree test: `CASHFREE_TEST_CLIENT_ID`, `CASHFREE_TEST_CLIENT_SECRET`, `CASHFREE_TEST_WEBHOOK_SECRET`
- Cashfree live: `CASHFREE_LIVE_CLIENT_ID`, `CASHFREE_LIVE_CLIENT_SECRET`, `CASHFREE_LIVE_WEBHOOK_SECRET`
- Stripe test: `STRIPE_TEST_PUBLISHABLE_KEY`, `STRIPE_TEST_SECRET_KEY`, `STRIPE_TEST_WEBHOOK_SECRET`
- Stripe live: `STRIPE_LIVE_PUBLISHABLE_KEY`, `STRIPE_LIVE_SECRET_KEY`, `STRIPE_LIVE_WEBHOOK_SECRET`
- PayPal test: `PAYPAL_TEST_CLIENT_ID`, `PAYPAL_TEST_CLIENT_SECRET`, `PAYPAL_TEST_WEBHOOK_ID`
- PayPal live: `PAYPAL_LIVE_CLIENT_ID`, `PAYPAL_LIVE_CLIENT_SECRET`, `PAYPAL_LIVE_WEBHOOK_ID`
- Store settings: `PAYMENT_CURRENCY=INR`, `PAYMENT_TAX_RATE_PERCENT`, `PAYMENT_SHIPPING_FLAT_RATE`

Credentials should first be configured in sandbox mode. Never switch live mode on until provider webhooks and order reconciliation are tested.
