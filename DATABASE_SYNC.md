# Encrypted customer database sync

The app can upload encrypted SQLite snapshots to `customer-data/<installation-id>.db.enc`
in the public `yalangisexter-ux/audit-report` repository. Each installation keeps its own
random ID, so one customer's upload does not replace another installation's snapshot.

## Configure a customer installation

1. Sign in with an Admin account and open **Settings & Backup**.
2. Paste a fine-grained GitHub personal access token into **Encrypted GitHub database sync**.
3. Prefer a fine-grained token limited to this repository with **Contents: Read and write**.
   The app needs repository write access to create commits on `main`. Classic tokens may also
   work, but usually grant broader access than this feature needs.
4. Select **Save token & sync**. The app reports upload progress and errors in Settings.

The token is protected with Windows DPAPI for the current Windows account. It is never
written into source code, the installer, sync snapshots, or status messages. Each customer
computer that uploads needs its own configured token. A token entered on one computer is
not transferable to another Windows account.

The snapshot uses AES-256-GCM with a key derived from the token. Keep the token available
in an approved password manager: the same token is needed to decrypt older snapshots, even
if it has since been revoked. Rotating the token changes the snapshot encryption key.

The public repository stores only encrypted snapshot bytes, but still exposes the random
installation ID, commit times, and encrypted file sizes. Git history retains previous
encrypted snapshots. Uploads are debounced after database commits and retried on a later
save or app launch when offline. Local saves remain available if GitHub sync fails.

Snapshots omit `auth_users` and all local `settings` except the business `working_weekdays`
setting. Employee, task, attendance, audit, report-source, and archived-document data remain
in the encrypted database so an authorized developer can inspect the customer state.

## Decrypt a snapshot for debugging

Download the `.db.enc` file from the repository or run:

```powershell
python tools/decrypt_customer_snapshot.py <installation-id>
```

The utility prompts for the token without echoing it, verifies/decrypts the snapshot, checks
SQLite integrity, and writes a separate `.db` copy. It refuses to overwrite an existing file.

## Credential scope warning

GitHub tokens are repository-scoped, not directory-scoped. A token with Contents write access
to this application repository can modify source files as well as the encrypted data folder.
Use a dedicated fine-grained token with the narrowest available permissions, rotate it if
exposed, and do not paste it into chat, source, logs, or release artifacts.
