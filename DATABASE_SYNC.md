# Encrypted customer database sync

The app stores one encrypted SQLite snapshot per customer installation at
`customer-data/<installation-id>.db.enc` in the `yalangisexter-ux/audit-report` repository.

**Desktop EXE and Android APK share the same cloud installation by default**
(`c4cf201d3c68e2fcaf60aa05fd423d9a`) so accounts (`auth_users`), employees, tasks, and
attendance can be merged conflict-free across devices. Existing custom installation IDs are
never overwritten. Use **Link / Change ID** on desktop (or Settings on mobile) only when you
intentionally want a separate cloud namespace.

Snapshots may be a full SQLite database (desktop) or a JSON business manifest (mobile). Both
formats are accepted on pull. Merges are additive: local users and records are preserved.

## Configure and push

1. Sign in with an Admin account and open **Settings & Backup**.
2. Enter a fine-grained GitHub personal access token limited to this repository with
   **Contents: Read and write**, then select **Save token**.
3. Local database changes remain on the computer. Select **Push to Git DB** when you want to
   upload the current snapshot. Saving a token, saving records, opening the app, and restarting
   the app do not upload anything.

The token is protected with Windows DPAPI for the current Windows account. It is not stored in
source code, the installer, the encrypted snapshot, or status messages. Each computer that pushes
needs its own configured credential.

The snapshot is compressed and encrypted with AES-256-GCM using a key derived from the token.
Keep the token available in an approved password manager: the same token is needed to decrypt
snapshots encrypted with it, even if that token is later revoked. Rotating the token changes the
snapshot encryption key.

The public repository contains encrypted snapshot bytes, but still exposes installation IDs,
commit times, encrypted file sizes, and prior encrypted snapshots in Git history. The GitHub token
can write to the repository; use a dedicated fine-grained token with the narrowest available
permissions. A Git branch conflict is reported as an error so the customer can retry the push.
Failed pushes do not change or delete the local database.

When upgrading from an older app that had Developer Mode enabled, startup validates and archives
the isolated local work database, restores the saved customer database, and removes the retired
mode settings before enabling Git sync. Archived work files remain on the customer's computer;
they are not uploaded. If the customer recovery copy is missing or invalid, startup stops before
syncing and leaves the current database untouched.

Snapshots **include** `auth_users` (for shared login across EXE and APK) and omit local-only
settings except the business `working_weekdays` setting. Employee, task, attendance, audit,
report-source, and archived-document data remain in the encrypted database.

## Decrypt a customer snapshot for debugging

Run:

```powershell
python tools/decrypt_customer_snapshot.py <installation-id>
```

The utility prompts for the token without echoing it, verifies the snapshot and SQLite integrity,
and writes a separate `.db` copy. It refuses to overwrite an existing file.
