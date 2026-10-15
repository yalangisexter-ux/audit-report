# Cloudflare Live Chat — Setup and Operations

This service adds employee-to-employee private conversations and authorized groups to the Windows desktop app and a responsive browser/mobile interface. It uses a separate chat identity database and does not upload the existing Audit Manager SQLite business database.

## Architecture

- Cloudflare Workers: HTTPS API, chat sign-in, account provisioning, authorization, and single-use WebSocket tickets.
- Durable Objects with WebSocket hibernation: one coordination room per conversation for real-time delivery.
- Cloudflare D1: chat accounts, memberships, message history, one-use socket tickets, and login rate-limit counters.
- ../chat-web: responsive web/mobile client served by the Worker assets binding.
- ../cloudflare_chat.py: Windows desktop chat tab.

Chat accounts are separate from local Windows application accounts. This prevents the backend from trusting a username or role supplied by the desktop client. A chat administrator provisions accounts through the Live Chat page.

## Cloudflare resources

The configured D1 database is `rsc-employee-chat-livescreen-sharing`. Its ID is configured in `wrangler.toml`. Keep the existing `my-llm-api` Worker unchanged; the chat uses a separate Worker named `raw-strength-employee-chat`.

## Deploy from GitHub Actions (Free plan)

The manual workflow is `.github/workflows/deploy-cloudflare-chat.yml`. It applies D1 migrations, sets Worker secrets, and deploys the chat Worker and web assets. It does not run automatically on every push.

Before running it, configure these values in GitHub repository settings:

**Settings → Secrets and variables → Actions → Variables**
- `CLOUDFLARE_ACCOUNT_ID`: the account ID shown in your Cloudflare dashboard URL/account details.

**Settings → Secrets and variables → Actions → Secrets**
- `CLOUDFLARE_API_TOKEN`: a Cloudflare API token with Workers Scripts edit, D1 edit, and account access needed for Durable Objects and Workers assets deployment.
- `CHAT_JWT_SECRET`: a randomly generated secret of at least 32 characters.
- `CHAT_BOOTSTRAP_TOKEN`: a separate long, random, one-time administrator-bootstrap token.

Do not paste secrets into issues, commits, source files, or this chat. Prefer a narrowly scoped Cloudflare API token; never use your Cloudflare account password. The GitHub environment named `cloudflare-chat` may require approval depending on repository environment settings.

Then open **Actions → Deploy Cloudflare Live Chat → Run workflow**, select the `feature/cloudflare-live-chat` branch, and run it. Review the logs for migration and deployment errors. The workflow must complete successfully before the Worker is considered deployed.

## First administrator

After deployment, use the bootstrap endpoint exactly once to create the first chat Admin. Replace the URL and credentials locally. Do not paste the token or password into source control or chat:

~~~sh
curl -X POST "https://YOUR-WORKER-URL/api/auth/bootstrap" \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Token: YOUR_BOOTSTRAP_TOKEN" \
  --data '{"username":"admin","displayName":"Chat Administrator","password":"CHOOSE_A_STRONG_PASSWORD"}'
~~~

After the first administrator exists, bootstrap permanently refuses further attempts. Rotate or remove the bootstrap token after initialization. Do not re-run deployment with a new bootstrap token after bootstrap unless you intentionally plan its rotation.

## Desktop application

Open the Live Chat page, enter the deployed Worker base URL (for example, `https://raw-strength-employee-chat.YOUR-SUBDOMAIN.workers.dev`), and sign in with a chat account. The URL is stored in the existing local settings table. Chat passwords and session tokens are not written to the business database. Sessions last up to 12 hours; sign in again when a session expires.

The desktop client uses HTTPS for API calls and WSS for live delivery. If Cloudflare is unavailable, the rest of the Audit Manager remains usable.

## Web and mobile

Open the deployed Worker URL in a browser. The responsive page supports sign-in, private conversations, groups, group membership, message history, reconnects, and administrator account provisioning. Users can use the browser's Add to Home Screen option on supported mobile devices.

## Security controls

- Passwords are salted and derived with PBKDF2-HMAC-SHA-256 (310,000 iterations); plaintext passwords are never stored.
- Signed API sessions expire after 12 hours. User accounts are rechecked in D1 for authenticated API calls.
- WebSocket tickets are random, single-use, hashed in D1, and expire after 60 seconds. Reusable bearer tokens are not placed in WebSocket URLs.
- Every history request, WebSocket ticket request, and WebSocket message checks conversation membership.
- Only Admin chat accounts can provision users. Group owners and Admins can add members.
- Login attempts are rate limited per username/client address; each Durable Object limits message bursts.
- Browser CORS denies unconfigured origins except the same origin and explicitly configured origins.
- Never commit Worker secrets, production tokens, customer messages, or D1 exports to Git.

## Validation and release

- **npm run check** validates Worker JavaScript syntax.
- **python -m pytest -q** runs the Windows application regression tests.
- Test sign-in, account provisioning, private/group access isolation, persisted history, reconnects, and a packaged Windows build before production rollout.
- A successful GitHub workflow is not proof of functional end-to-end chat. Verify login, admin provisioning, private and group messages, persistence after refresh, unauthorized membership denial, and reconnect behavior before calling it production-ready.
