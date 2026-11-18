import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const config = readFileSync(resolve(here, "..", "wrangler.toml"), "utf8");

test("DB-sync Wrangler config retains the production R2 backup binding", () => {
  assert.match(config, /^\\[\\[r2_buckets\\]\\]$/m);
  assert.match(config, /^binding\\s*=\\s*"CUSTOMER_BACKUPS"$/m);
  assert.match(config, /^bucket_name\\s*=\\s*"raw-strength-customer-backups"$/m);
});
