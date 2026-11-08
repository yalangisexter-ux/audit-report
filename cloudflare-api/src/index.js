const encoder = new TextEncoder();
const TOKEN_BYTES = 32;
const SESSION_DAYS = 30;
const PBKDF2_ITERATIONS = 200000;

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = new Set(String(env.ALLOWED_ORIGINS || "").split(",").map(v => v.trim()).filter(Boolean));
    const headers = {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Vary": "Origin",
      ...(allowed.has(origin) ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true" } : {}),
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
    };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (!env.DB) return json({ error: "D1 binding is not configured" }, 503, headers);
    const url = new URL(request.url);
    try {
      if (url.pathname === "/api/health" && request.method === "GET") {
        const [employees, tasks] = await Promise.all([
          env.DB.prepare("SELECT COUNT(*) AS n FROM employees").first(),
          env.DB.prepare("SELECT COUNT(*) AS n FROM tasks").first(),
        ]);
        return json({ status: "healthy", service: "raw-strength-cloudflare-api", database_connected: true,
          total_employees: Number(employees?.n || 0), total_tasks: Number(tasks?.n || 0) }, 200, headers);
      }
      if (url.pathname === "/api/auth/login" && request.method === "POST") {
        const body = await readJson(request);
        if (!body || typeof body.username !== "string" || typeof body.password !== "string" ||
            body.username.length > 128 || body.password.length > 1024) return json({ error: "Invalid username or password" }, 400, headers);
        const user = await env.DB.prepare(
          "SELECT id, username, display_name, role, password_salt, password_hash FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1"
        ).bind(body.username.trim()).first();
        if (!user || !await verifyPassword(body.password, user.password_salt, user.password_hash)) {
          return json({ error: "Invalid username or password" }, 401, headers);
        }
        const token = randomHex(TOKEN_BYTES);
        const tokenHash = await sha256(token);
        const now = new Date();
        const created = now.toISOString();
        const expires = new Date(now.getTime() + SESSION_DAYS * 86400000).toISOString();
        await env.DB.prepare("DELETE FROM web_auth_sessions WHERE expires_at <= ?").bind(created).run();
        await env.DB.prepare("INSERT INTO web_auth_sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)")
          .bind(tokenHash, user.id, created, expires).run();
        return json({ token, user: { id: user.id, username: user.username,
          display_name: user.display_name || user.username, role: user.role } }, 200, headers);
      }
      if (url.pathname === "/api/auth/me" && request.method === "GET") {
        const user = await currentUser(request, env);
        if (!user) return json({ error: "Login required" }, 401, headers);
        return json({ user }, 200, headers);
      }
      if (url.pathname === "/api/auth/logout" && request.method === "POST") {
        const token = bearer(request);
        if (!token) return json({ error: "Login required" }, 401, headers);
        const hash = await sha256(token);
        const result = await env.DB.prepare("DELETE FROM web_auth_sessions WHERE token_hash = ?").bind(hash).run();
        if (!result.success || !result.meta?.changes) return json({ error: "Login required" }, 401, headers);
        return json({ success: true }, 200, headers);
      }
      return json({ error: "Not found" }, 404, headers);
    } catch (error) {
      console.error("Cloudflare API request failed", { path: url.pathname, message: String(error?.message || error) });
      return json({ error: "Internal API error" }, 500, headers);
    }
  },
};

async function currentUser(request, env) {
  const token = bearer(request);
  if (!token || token.length > 256) return null;
  const hash = await sha256(token);
  const row = await env.DB.prepare(
    "SELECT u.id, u.username, u.display_name, u.role FROM web_auth_sessions s JOIN auth_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1"
  ).bind(hash, new Date().toISOString()).first();
  return row ? { id: row.id, username: row.username, display_name: row.display_name || row.username, role: row.role } : null;
}
function bearer(request) {
  const value = request.headers.get("Authorization") || "";
  const match = /^Bearer\s+(.+)$/i.exec(value);
  return match ? match[1].trim() : "";
}
async function verifyPassword(password, salt, expected) {
  if (typeof salt !== "string" || typeof expected !== "string" || !/^[a-f0-9]{64}$/i.test(expected)) return false;
  const key = await crypto.subtle.importKey("raw", encoder.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", salt: encoder.encode(salt), iterations: PBKDF2_ITERATIONS, hash: "SHA-256" }, key, 256);
  const actual = [...new Uint8Array(bits)].map(v => v.toString(16).padStart(2, "0")).join("");
  return constantTimeEqual(actual, expected.toLowerCase());
}
function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
async function sha256(value) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return [...new Uint8Array(digest)].map(v => v.toString(16).padStart(2, "0")).join("");
}
function randomHex(bytes) {
  const data = crypto.getRandomValues(new Uint8Array(bytes));
  return [...data].map(v => v.toString(16).padStart(2, "0")).join("");
}
async function readJson(request) {
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > 16384) throw new Error("Request too large");
  return request.json();
}
function json(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}
