# USA–Raw Strength multi-channel sales connectors

This is an additive connector foundation for the Cloudflare Worker + D1 sales ledger. It does not alter the desktop SQLite database, existing storefront orders, employee records, or inventory quantities.

## Supported channel registry

| Channel | Authorization model | Current integration state |
|---|---|---|
| Amazon India | Selling Partner API (LWA OAuth + AWS request signing) | Channel registry + signed inbound webhook/import framework; live SP-API polling still requires registered app and seller authorization |
| Flipkart | Seller API app / access token | Channel registry + inbound event/import framework; live API polling requires seller API app approval and token setup |
| Meesho | Partner-approved API or seller export | Import/webhook adapter path; no undocumented/private API scraping |
| Shopify | Admin API OAuth/token + webhooks | Channel registry + inbound event/import framework; live API polling requires shop authorization |
| WooCommerce | REST API consumer key/secret + webhooks | Channel registry + inbound event/import framework; live API polling requires store API keys |
| Etsy | OAuth 2.0 + approved scopes/webhooks | Channel registry + inbound event/import framework; live API polling requires app approval and shop authorization |
| eBay | OAuth 2.0 Sell APIs | Channel registry + inbound event/import framework; live API polling requires developer app and seller authorization |
| Other | Custom partner feed / signed webhook | Generic signed webhook adapter and normalized order ingestion |

Official references:
- Amazon SP-API onboarding: https://developer-docs.amazon.com/sp-api/docs/onboarding-overview
- Flipkart Seller API: https://seller.flipkart.com/api-docs/index.html
- Shopify Admin API: https://shopify.dev/docs/api/admin-graphql
- WooCommerce APIs: https://developer.woocommerce.com/docs/apis/
- Etsy webhooks: https://developers.etsy.com/documentation/essentials/webhooks/
- eBay Fulfillment API: https://developer.ebay.com/develop/api/sell/fulfillment_api
- Meesho access must be confirmed through its seller/partner channel; do not scrape seller portals or bypass access controls.

## API

All management routes require a signed-in Admin or Developer session.

- GET /api/sales-channels — channel registry and non-secret status.
- POST /api/sales-channels — create channel. Body: { platform, account_label, credentials }.
- PUT /api/sales-channels/:id/credentials — replace encrypted credential object.
- POST /api/sales-channels/:id/webhook-secret/rotate — rotate webhook secret.
- DELETE /api/sales-channels/:id — disable channel and clear stored credentials.
- GET /api/sales-orders — unified imported marketplace orders.
- GET /api/sales-notifications — internal sales notifications.
- GET/POST /api/sales-channels/:id/product-mappings — map an external SKU to an existing bt_products.id.
- POST /api/sales-channels/:id/sync — records a sync attempt and returns blocked_credentials until a platform API driver is configured and verified.
- POST /api/sales-channels/:id/webhook — signed event ingestion. Send the one-time channel secret in X-RS-Channel-Secret, a stable X-Event-Id, and optional X-Event-Type.

Webhook order payloads are normalized from common fields (external order ID, status, total, currency, buyer/shipping data and line items). A unique (channel_id, external_order_id) key prevents duplicate orders; (channel_id, external_event_id) makes event delivery idempotent. Raw payloads are retained for audit; credentials are AES-GCM encrypted and never returned by API responses.

## Required deployment configuration

Set Worker secret CONNECTOR_ENCRYPTION_KEY to a cryptographically random 32-byte key encoded as 64 hex characters. Keep it in Cloudflare Worker secrets, never in Git, D1 plaintext, frontend code, or chat. Losing this key makes encrypted channel credentials unrecoverable; back it up in the organization's secret manager.

The deployment workflow applies the new additive D1 migration before deploying the Worker. It does not modify or drop existing tables.

## Safety boundaries / remaining activation work

- No marketplace inventory or price write-back is performed.
- No marketplace customer data is copied to the local EXE database by this Worker; imported data stays in the shared D1 sales ledger.
- SKU mappings require explicit Admin confirmation; titles are never used to auto-merge inventory.
- The webhook secret is displayed once at channel creation/rotation; store it in the marketplace webhook configuration.
- Live pull/sync is not yet activated. Each marketplace requires seller-owned app registration, approved scopes, credentials and a platform-specific polling/webhook signature adapter. The framework intentionally reports blocked_credentials rather than pretending to sync. Amazon SP-API requires LWA authorization and signed requests; Flipkart requires a separately registered seller API app; Meesho needs an approved partner/API route or seller export.
- The first production activation should be read-only order import, followed by reconciliation tests. Inventory write-back, fulfilment actions, refunds and customer notifications need separate explicit authorization and per-platform verification.