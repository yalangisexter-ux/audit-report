# Cloudflare Live Chat — Setup and Operations

This service adds employee-to-employee private conversations and authorized groups to the Windows desktop app and a responsive browser/mobile interface. It uses a separate chat identity database and does not upload the existing Audit Manager SQLite business database.

## Architecture

- Cloudflare Workers: HTTPS API, chat sign-in, account provisioning, authorization, and single-use WebSocket tickets.
- Durable Objects with WebSocket hibernation: one coordination room per conversation for real-time delivery.
- Cloudflare D1: chat accounts, memberships, message history, one-use socket tickets, and login rate-limit counters.
- ../chat-web: responsive web/mobile client served by the Worker assets binding.
- ../cloudflare_chat.py: Windows desktop chat tab.

Chat accounts are separate from local Windows application accounts. This prevents the backend from trusting a username or role supplied by the desktop client. A chat administrator provisions accounts through the Live Chat page.

## Prerequisites

- Cloudflare account with Workers, Durable Objects, and D1 enabled.
- Node.js 20+ and npm.
- Wrangler authentication: run **npx wrangler login**.
- A unique strong JWT signing secret and one-time bootstrap token. Never commit these secrets or put them in the desktop app.

## First deployment

Run from this directory:

1. Install Wrangler: **npm install**.
2. Create the D1 database: **npx wrangler d1 create rsc-employee-chat**.
3. Copy the returned database ID into wrangler.toml, replacing **REPLACE_WITH_D1_DATABASE_ID**.
4. Apply the D1 migration: **npm run db:remote**.
5. Set a random JWT secret (at least 32 characters): **npx wrangler secret put CHAT_JWT_SECRET**.
6. Set a separate bootstrap credential: **npx wrangler secret put CHAT_BOOTSTRAP_TOKEN**.
7. If using a custom web domain, set CHAT_ALLOWED_ORIGINS in wrangler.toml to exact comma-separated HTTPS origins, without paths. The Worker automatically allows its own origin. Native Windows API calls do not send a browser Origin header.
8. Deploy: **npm run deploy**.

The first deploy does not create an administrator automatically. After deploying, call the bootstrap endpoint exactly once to create the first chat Admin. Replace the URL and credentials locally. Do not paste the token or password into source control or chat:

~~~sh
curl -X POST "https://YOUR-WORKER-URL/api/auth/bootstrap" \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Token: YOUR_BOOTSTRAP_TOKEN" \
  --data '{"username":"admin","displayName":"Chat Administrator","password":"CHOOSE_A_STRONG_PASSWORD"}'
~~~

After the first administrator exists, bootstrap permanently refuses further attempts. Remove or rotate CHAT_BOOTSTRAP_TOKEN after initialization using Wrangler secrets. The administrator can then create employee chat accounts from the desktop app or web interface.

## Desktop application

Open the Live Chat page, enter the deployed Worker base URL (for example, https://raw-strength-employee-chat.YOUR-SUBDOMAIN.workers.dev), and sign in with a chat account. The URL is stored in the existing local settings table. Chat passwords and session tokens are not written to the business database. Sessions last up to 12 hours; sign in again when a session expires.

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
- Deployment requires a Cloudflare account and a real D1 database ID. The committed configuration intentionally has a placeholder until the customer-owned Cloudflare account is configured. A GitHub source commit does not deploy the Worker.
