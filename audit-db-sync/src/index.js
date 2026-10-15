const MAX_SNAPSHOT_BYTES = 60 * 1024 * 1024;
const MAX_JSON_BODY_BYTES = 85 * 1024 * 1024;
const INSTALLATION_RE = /^[0-9a-f]{32}$/;
const DEVICE_RE = /^[0-9a-f]{32}$/;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET") return json({ ok: true, service: "audit-db-sync" });
    if (url.pathname === "/register" && request.method === "POST") return handleRegister(request, env);
    if (url.pathname === "/push" && request.method === "POST") return handlePush(request, env);
    if (url.pathname === "/pull" && request.method === "POST") return handlePull(request, env);
    return json({ error: "Not found" }, 404);
  },
};

async function handleRegister(request, env) {
  if (!configured(env)) return json({ error: "Sync service is not configured" }, 503);
  const body = await readJson(request, 16 * 1024);
  if (body instanceof Response) return body;
  const installation_id = String(body?.installation_id || "");
  const device_id = String(body?.device_id || "");
  const device_secret = String(body?.device_secret || "");
  if (!INSTALLATION_RE.test(installation_id) || !DEVICE_RE.test(device_id) || device_secret.length < 32 || device_secret.length > 256) {
    return json({ error: "Invalid registration data" }, 400);
  }
  const secret_hash = await sha256Hex(device_secret);
  const registry = registryStub(env);
  const claim = await registry.fetch("https://registry/claim", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ installation_id, device_id, secret_hash }),
  });
  if (claim.status === 409) return json({ error: "This installation is already bound to another device" }, 409);
  if (!claim.ok) return json({ error: "Device registration failed" }, 503);
  const token = await createToken({
    iss: "raw-strength-audit-db-sync", aud: "raw-strength-audit-db-sync", device_id, installation_id,
  }, env.JWT_SECRET, 60 * 60 * 24 * 90);
  return json({ token });
}

async function handlePush(request, env) {
  const auth = await authenticate(request, env);
  if (auth instanceof Response) return auth;
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > MAX_JSON_BODY_BYTES) return json({ error: "Snapshot too large" }, 413);
  const body = await readJson(request, MAX_JSON_BODY_BYTES);
  if (body instanceof Response) return body;
  const content = String(body?.content || "");
  if (!content || content.length > Math.ceil(MAX_SNAPSHOT_BYTES / 3) * 4 + 16 ||
      !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(content)) {
    return json({ error: "Invalid encrypted snapshot content" }, 400);
  }
  let binary;
  try { binary = base64ToBytes(content); } catch { return json({ error: "Invalid snapshot encoding" }, 400); }
  if (binary.byteLength === 0 || binary.byteLength > MAX_SNAPSHOT_BYTES) return json({ error: "Snapshot too large or empty" }, 413);

  const path = "customer-data/" + auth.installation_id + ".db.enc";
  const endpoint = githubContentsUrl(env, path);
  const current = await fetch(endpoint, { method: "GET", headers: githubHeaders(env, "application/vnd.github+json") });
  let sha = null;
  if (current.ok) {
    const metadata = await current.json();
    sha = typeof metadata.sha === "string" ? metadata.sha : null;
    if (!sha) return json({ error: "GitHub returned invalid snapshot metadata" }, 502);
  } else if (current.status !== 404) {
    return json({ error: "Could not inspect the existing snapshot" }, 502);
  }
  const response = await fetch(endpoint, {
    method: "PUT",
    headers: githubHeaders(env, "application/vnd.github+json", true),
    body: JSON.stringify({
      message: "Update encrypted database snapshot for " + auth.installation_id,
      content, branch: "main", ...(sha ? { sha } : {}),
    }),
  });
  if (response.status === 409 || response.status === 422) {
    return json({ error: "Concurrent snapshot update detected; retry after pulling the latest data" }, 409);
  }
  if (!response.ok) return json({ error: "GitHub could not store the encrypted snapshot" }, 502);
  return json({ success: true });
}

async function handlePull(request, env) {
  const auth = await authenticate(request, env);
  if (auth instanceof Response) return auth;
  const path = "customer-data/" + auth.installation_id + ".db.enc";
  const response = await fetch(githubContentsUrl(env, path), {
    method: "GET", headers: githubHeaders(env, "application/vnd.github.raw+json"),
  });
  if (response.status === 404) return json({ error: "No remote snapshot for this installation" }, 404);
  if (!response.ok) return json({ error: "Could not retrieve the encrypted snapshot" }, 502);
  const length = Number(response.headers.get("Content-Length") || 0);
  if (length > MAX_SNAPSHOT_BYTES) return json({ error: "Snapshot too large" }, 413);
  return new Response(response.body, {
    status: 200,
    headers: { "Content-Type": "application/octet-stream", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
  });
}

async function authenticate(request, env) {
  if (!configured(env)) return json({ error: "Sync service is not configured" }, 503);
  const match = /^Bearer\s+(.+)$/i.exec(request.headers.get("Authorization") || "");
  if (!match) return json({ error: "Missing device token" }, 401);
  const payload = await verifyToken(match[1], env.JWT_SECRET);
  if (!payload || payload.iss !== "raw-strength-audit-db-sync" || payload.aud !== "raw-strength-audit-db-sync" ||
      !INSTALLATION_RE.test(payload.installation_id || "") || !DEVICE_RE.test(payload.device_id || "")) {
    return json({ error: "Invalid or expired device token" }, 401);
  }
  const check = await registryStub(env).fetch("https://registry/verify", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ installation_id: payload.installation_id, device_id: payload.device_id }),
  });
  if (!check.ok) return json({ error: "Device is not registered for this installation" }, 403);
  return payload;
}

export class DeviceRegistry {
  constructor(state) { this.state = state; this.storage = state.storage; }

  async fetch(request) {
    const url = new URL(request.url);
    const body = await readJson(request, 16 * 1024);
    if (body instanceof Response) return body;
    if (url.pathname === "/claim" && request.method === "POST") {
      const { installation_id, device_id, secret_hash } = body || {};
      if (!INSTALLATION_RE.test(installation_id || "") || !DEVICE_RE.test(device_id || "") || !/^[a-f0-9]{64}$/.test(secret_hash || "")) {
        return json({ error: "Invalid claim" }, 400);
      }
      const result = await this.storage.transaction(async txn => {
        const key = "installation:" + installation_id;
        const current = await txn.get(key);
        if (!current) {
          await txn.put(key, { installation_id, device_id, secret_hash, created_at: Date.now() });
          return "created";
        }
        if (current.device_id === device_id && constantTimeEqual(current.secret_hash, secret_hash)) return "same-device";
        return "conflict";
      });
      return result === "conflict" ? json({ error: "Installation already claimed" }, 409) : json({ success: true });
    }
    if (url.pathname === "/verify" && request.method === "POST") {
      const { installation_id, device_id } = body || {};
      if (!INSTALLATION_RE.test(installation_id || "") || !DEVICE_RE.test(device_id || "")) return json({ error: "Invalid device" }, 400);
      const record = await this.storage.get("installation:" + installation_id);
      if (!record || record.device_id !== device_id) return json({ error: "Device not registered" }, 403);
      return json({ success: true });
    }
    return json({ error: "Not found" }, 404);
  }
}

function configured(env) { return Boolean(env.JWT_SECRET && env.RELEASE_TOKEN_2 && env.DEVICE_REGISTRY); }
function registryStub(env) { return env.DEVICE_REGISTRY.get(env.DEVICE_REGISTRY.idFromName("installation-registry-v1")); }

function githubContentsUrl(env, path) {
  const owner = String(env.GITHUB_OWNER || "");
  const repo = String(env.GITHUB_REPO || "");
  if (!/^[A-Za-z0-9-]+$/.test(owner) || !/^[A-Za-z0-9_.-]+$/.test(repo)) throw new Error("Invalid repository configuration");
  return "https://api.github.com/repos/" + owner + "/" + repo + "/contents/" + path;
}
function githubHeaders(env, accept, jsonBody = false) {
  return {
    Authorization: "Bearer " + env.RELEASE_TOKEN_2,
    Accept: accept,
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "RawStrengthEmployeeAuditManager-DB-Sync",
    ...(jsonBody ? { "Content-Type": "application/json" } : {}),
  };
}
async function readJson(request, maxBytes) {
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > maxBytes) return json({ error: "Request too large" }, 413);
  try {
    const text = await request.text();
    if (new TextEncoder().encode(text).byteLength > maxBytes) return json({ error: "Request too large" }, 413);
    return JSON.parse(text);
  } catch { return json({ error: "Invalid JSON" }, 400); }
}
async function sha256Hex(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, "0")).join("");
}
function base64ToBytes(value) {
  const binary = atob(value);
  const output = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) output[i] = binary.charCodeAt(i);
  return output;
}
function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, Math.min(i + 0x8000, bytes.length)));
  return btoa(binary);
}
function base64UrlEncode(bytes) { return bytesToBase64(bytes).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_"); }
function base64UrlDecode(value) {
  return base64ToBytes(value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4));
}
async function createToken(payload, secret, lifetimeSeconds) {
  const now = Math.floor(Date.now() / 1000);
  const header = base64UrlEncode(new TextEncoder().encode(JSON.stringify({ alg: "HS256", typ: "JWT" })));
  const body = base64UrlEncode(new TextEncoder().encode(JSON.stringify({ ...payload, iat: now, exp: now + lifetimeSeconds })));
  const unsigned = header + "." + body;
  return unsigned + "." + base64UrlEncode(await sign(unsigned, secret));
}
async function verifyToken(token, secret) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const header = JSON.parse(new TextDecoder().decode(base64UrlDecode(parts[0])));
    if (header.alg !== "HS256" || header.typ !== "JWT") return null;
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
    if (!await crypto.subtle.verify("HMAC", key, base64UrlDecode(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]))) return null;
    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(parts[1])));
    const now = Math.floor(Date.now() / 1000);
    if (!Number.isInteger(payload.iat) || !Number.isInteger(payload.exp) || payload.iat > now + 60 || payload.exp <= now) return null;
    return payload;
  } catch { return null; }
}
async function sign(value, secret) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
}
function constantTimeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return difference === 0;
}
function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
}
export const __test = { createToken, verifyToken, sha256Hex, base64ToBytes, bytesToBase64 };
