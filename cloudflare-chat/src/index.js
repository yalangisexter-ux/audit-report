import { DurableObject } from "cloudflare:workers";

const encoder = new TextEncoder();
const MAX_BODY_BYTES = 16 * 1024;
const TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60;
const SOCKET_TICKET_TTL_SECONDS = 60;
const MAX_MESSAGE_LENGTH = 4000;
const PASSWORD_ITERATIONS = 310000;

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers },
  });
}
function b64url(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/u, "");
}
function fromB64url(value) {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  return Uint8Array.from(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=")), c => c.charCodeAt(0));
}
function randomToken(bytes = 32) { return b64url(crypto.getRandomValues(new Uint8Array(bytes))); }
async function sha256(value) { return new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(value))); }
function equalBytes(a, b) {
  if (a.length !== b.length) return false;
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a[i] ^ b[i];
  return difference === 0;
}
async function passwordHash(password, salt) {
  const key = await crypto.subtle.importKey("raw", encoder.encode(password), "PBKDF2", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: PASSWORD_ITERATIONS, hash: "SHA-256" }, key, 256,
  ));
}
async function makePasswordRecord(password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return { salt: b64url(salt), hash: b64url(await passwordHash(password, salt)) };
}
async function tokenKey(env) {
  if (!env.CHAT_JWT_SECRET || env.CHAT_JWT_SECRET.length < 32) throw new Error("Chat service is not configured.");
  return crypto.subtle.importKey("raw", encoder.encode(env.CHAT_JWT_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}
async function issueToken(env, user) {
  const now = Math.floor(Date.now() / 1000);
  const payload = b64url(encoder.encode(JSON.stringify({
    sub: user.id, username: user.username, role: user.role, iat: now, exp: now + TOKEN_TTL_SECONDS,
  })));
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", await tokenKey(env), encoder.encode(payload)));
  return payload + "." + b64url(signature);
}
async function authenticate(request, env) {
  const match = /^Bearer\s+([A-Za-z0-9_.-]+)$/u.exec(request.headers.get("Authorization") || "");
  if (!match) return null;
  const parts = match[1].split(".");
  if (parts.length !== 2) return null;
  try {
    const valid = await crypto.subtle.verify("HMAC", await tokenKey(env), fromB64url(parts[1]), encoder.encode(parts[0]));
    if (!valid) return null;
    const payload = JSON.parse(new TextDecoder().decode(fromB64url(parts[0])));
    if (!payload.sub || !Number.isFinite(payload.exp) || payload.exp <= Math.floor(Date.now() / 1000)) return null;
    return await env.DB.prepare("SELECT id, username, display_name, role, active FROM chat_users WHERE id = ? AND active = 1").bind(payload.sub).first();
  } catch { return null; }
}
async function readJson(request) {
  if (Number(request.headers.get("content-length") || 0) > MAX_BODY_BYTES) throw badRequest("Request body is too large.");
  const raw = await request.text();
  if (encoder.encode(raw).byteLength > MAX_BODY_BYTES) throw badRequest("Request body is too large.");
  try { return JSON.parse(raw || "{}"); } catch { throw badRequest("Invalid JSON request."); }
}
function badRequest(message) { return Object.assign(new Error(message), { status: 400 }); }
function normalizeUsername(value) { return String(value || "").trim().toLowerCase(); }
function validUsername(value) { return /^[a-z0-9._-]{2,40}$/u.test(value); }
function validPassword(value) {
  return typeof value === "string" && value.length >= 10 && value.length <= 256 &&
    /[A-Za-z]/u.test(value) && /\d/u.test(value);
}
function cleanDisplayName(value, fallback) { return (String(value || "").trim() || fallback).slice(0, 80); }
function originAllowed(request, env) {
  const origin = request.headers.get("Origin");
  if (!origin) return true;
  if (origin === new URL(request.url).origin) return true;
  return String(env.CHAT_ALLOWED_ORIGINS || "").split(",").map(v => v.trim()).filter(Boolean).includes(origin);
}
function withCors(response, request) {
  const origin = request.headers.get("Origin");
  if (!origin) return response;
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", origin);
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Authorization, Content-Type");
  headers.set("Access-Control-Max-Age", "600");
  headers.append("Vary", "Origin");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}
async function requireUser(request, env) {
  const user = await authenticate(request, env);
  if (!user) throw Object.assign(new Error("Sign in to chat again."), { status: 401 });
  return user;
}
async function requireMember(env, conversationId, userId) {
  const row = await env.DB.prepare("SELECT 1 AS allowed FROM conversation_members WHERE conversation_id = ? AND user_id = ?")
    .bind(conversationId, userId).first();
  if (!row) throw Object.assign(new Error("You do not have access to this conversation."), { status: 403 });
}
async function listConversations(env, userId) {
  const result = await env.DB.prepare(
    "SELECT c.id, c.kind, c.name, c.created_at, cm.member_role, " +
    "CASE WHEN c.kind = 'private' THEN (SELECT COALESCE(NULLIF(u.display_name, ''), u.username) " +
    "FROM conversation_members other JOIN chat_users u ON u.id = other.user_id " +
    "WHERE other.conversation_id = c.id AND other.user_id <> ? LIMIT 1) ELSE c.name END AS title, " +
    "(SELECT m.text FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message, " +
    "(SELECT m.created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message_at " +
    "FROM conversations c JOIN conversation_members cm ON cm.conversation_id = c.id " +
    "WHERE cm.user_id = ? ORDER BY COALESCE((SELECT m.created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1), c.created_at) DESC",
  ).bind(userId, userId).all();
  return result.results || [];
}
let supportTablesReady = false;
async function ensureSupportTables(env) {
  if (supportTablesReady || !env.DB) return;
  try {
    await env.DB.batch([
      env.DB.prepare("CREATE TABLE IF NOT EXISTS support_conversations (id TEXT PRIMARY KEY, user_name TEXT NOT NULL, last_message TEXT DEFAULT '', updated_at TEXT NOT NULL)"),
      env.DB.prepare("CREATE TABLE IF NOT EXISTS support_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL, sender_role TEXT NOT NULL, sender_name TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL)"),
      env.DB.prepare("CREATE INDEX IF NOT EXISTS idx_support_msgs_conv ON support_messages(conversation_id, id ASC)"),
    ]);
    supportTablesReady = true;
  } catch {}
}
async function routeApi(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method.toUpperCase();
  if (path === "/api/health" && method === "GET") return json({ ok: true, service: "raw-strength-chat", status: "ready" });

  if (path === "/api/auth/bootstrap" && method === "POST") {
    if (!env.CHAT_BOOTSTRAP_TOKEN) return json({ error: "Bootstrap is not enabled." }, 503);
    const supplied = request.headers.get("X-Bootstrap-Token") || "";
    if (!equalBytes(await sha256(supplied), await sha256(env.CHAT_BOOTSTRAP_TOKEN))) return json({ error: "Invalid bootstrap credential." }, 403);
    const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM chat_users").first();
    if (Number(count && count.count || 0) !== 0) return json({ error: "Bootstrap is already complete." }, 409);
    const body = await readJson(request);
    const username = normalizeUsername(body.username);
    if (!validUsername(username)) return json({ error: "Username must be 2–40 characters using letters, numbers, dot, underscore or hyphen." }, 400);
    if (!validPassword(body.password)) return json({ error: "Use a password of at least 10 characters containing a letter and a number." }, 400);
    const password = await makePasswordRecord(body.password);
    const now = new Date().toISOString();
    try {
      await env.DB.batch([
        env.DB.prepare("INSERT INTO bootstrap_guard(id, used_at) VALUES(1, ?)").bind(now),
        env.DB.prepare("INSERT INTO chat_users(username, display_name, role, password_salt, password_hash, active, created_at, updated_at) VALUES(?, ?, 'Admin', ?, ?, 1, ?, ?)")
          .bind(username, cleanDisplayName(body.displayName, username), password.salt, password.hash, now, now),
      ]);
    } catch {
      return json({ error: "Bootstrap is already complete or another administrator was created concurrently." }, 409);
    }
    const user = await env.DB.prepare("SELECT id, username, display_name, role, active FROM chat_users WHERE username = ?").bind(username).first();
    return json({ ok: true, user }, 201);
  }

  if (path === "/api/auth/login" && method === "POST") {
    const body = await readJson(request);
    const username = normalizeUsername(body.username);
    const password = typeof body.password === "string" ? body.password : "";
    if (!username || password.length > 256) return json({ error: "Invalid username or password." }, 400);
    const ip = request.headers.get("CF-Connecting-IP") || "native-client";
    const attemptKey = b64url(await sha256(username + ":" + ip));
    const now = Math.floor(Date.now() / 1000);
    await env.DB.prepare("DELETE FROM login_attempts WHERE window_started < ?").bind(now - 3600).run();
    const attempts = await env.DB.prepare("SELECT window_started, attempts FROM login_attempts WHERE attempt_key = ?").bind(attemptKey).first();
    if (attempts && Number(attempts.window_started) + 900 > now && Number(attempts.attempts) >= 10) {
      return json({ error: "Too many sign-in attempts. Try again in 15 minutes." }, 429);
    }
    const user = await env.DB.prepare("SELECT id, username, display_name, role, password_salt, password_hash, active FROM chat_users WHERE username = ? COLLATE NOCASE").bind(username).first();
    let accepted = false;
    if (user && user.active === 1 && user.password_salt && user.password_hash) {
      try { accepted = equalBytes(await passwordHash(password, fromB64url(user.password_salt)), fromB64url(user.password_hash)); } catch { accepted = false; }
    }
    if (!accepted) {
      const reset = !attempts || Number(attempts.window_started) + 900 <= now;
      const start = reset ? now : Number(attempts.window_started);
      const count = reset ? 1 : Number(attempts.attempts) + 1;
      await env.DB.prepare("INSERT INTO login_attempts(attempt_key, window_started, attempts) VALUES(?, ?, ?) ON CONFLICT(attempt_key) DO UPDATE SET window_started=excluded.window_started, attempts=excluded.attempts")
        .bind(attemptKey, start, count).run();
      return json({ error: "Invalid username or password." }, 401);
    }
    await env.DB.prepare("DELETE FROM login_attempts WHERE attempt_key = ?").bind(attemptKey).run();
    const publicUser = { id: user.id, username: user.username, displayName: user.display_name, role: user.role };
    return json({ ok: true, token: await issueToken(env, publicUser), expiresIn: TOKEN_TTL_SECONDS, user: publicUser });
  }

  // --- Real-Time Support Chat Endpoints for Customer <-> Support Desktop Clients ---
  if (path === "/api/support/conversations" && method === "GET") {
    await ensureSupportTables(env);
    const result = await env.DB.prepare(
      "SELECT id, user_name, last_message, updated_at FROM support_conversations ORDER BY updated_at DESC LIMIT 100"
    ).all();
    return json({ ok: true, conversations: result.results || [] });
  }

  if (path === "/api/support/messages" && method === "GET") {
    await ensureSupportTables(env);
    const convId = String(url.searchParams.get("conversation_id") || "").trim();
    if (!convId) return json({ error: "conversation_id is required." }, 400);
    const after = Number(url.searchParams.get("after") || 0);
    let result;
    if (after > 0) {
      result = await env.DB.prepare(
        "SELECT id, conversation_id, sender_role, sender_name, text, created_at FROM support_messages WHERE conversation_id = ? AND id > ? ORDER BY id ASC LIMIT 250"
      ).bind(convId, after).all();
    } else {
      result = await env.DB.prepare(
        "SELECT id, conversation_id, sender_role, sender_name, text, created_at FROM support_messages WHERE conversation_id = ? ORDER BY id ASC LIMIT 250"
      ).bind(convId).all();
    }
    return json({ ok: true, messages: result.results || [] });
  }

  if (path === "/api/support/send" && method === "POST") {
    await ensureSupportTables(env);
    const body = await readJson(request);
    const convId = String(body.conversation_id || "").trim().slice(0, 80);
    const senderRole = body.sender_role === "Support" ? "Support" : "User";
    const senderName = cleanDisplayName(body.sender_name, senderRole);
    const text = String(body.text || "").trim();
    if (!convId || !text) return json({ error: "Missing conversation ID or text." }, 400);
    if (text.length > MAX_MESSAGE_LENGTH) return json({ error: "Message must not exceed 4000 characters." }, 400);

    const now = new Date().toISOString();
    const preview = senderRole === "User" ? text : `Support: ${text}`;
    const cleanUser = senderRole === "User" ? senderName : convId.replace(/^user_/i, "");

    await env.DB.prepare(
      "INSERT INTO support_conversations(id, user_name, last_message, updated_at) VALUES(?, ?, ?, ?) " +
      "ON CONFLICT(id) DO UPDATE SET last_message = excluded.last_message, updated_at = excluded.updated_at"
    ).bind(convId, cleanUser, preview.slice(0, 100), now).run();

    const insertResult = await env.DB.prepare(
      "INSERT INTO support_messages(conversation_id, sender_role, sender_name, text, created_at) VALUES(?, ?, ?, ?, ?) RETURNING id"
    ).bind(convId, senderRole, senderName, text, now).first();

    const messageId = insertResult && insertResult.id ? insertResult.id : Date.now();
    return json({
      ok: true,
      message: {
        id: messageId,
        conversation_id: convId,
        sender_role: senderRole,
        sender_name: senderName,
        text,
        created_at: now
      }
    }, 201);
  }

  if (!path.startsWith("/api/")) return null;
  let user;
  try { user = await requireUser(request, env); }
  catch (error) { return json({ error: error.message }, error.status || 401); }

  if (path === "/api/auth/password" && method === "POST") {
    const body = await readJson(request);
    const currentPassword = typeof body.currentPassword === "string" ? body.currentPassword : "";
    if (!validPassword(body.newPassword)) return json({ error: "Use a password of at least 10 characters containing a letter and a number." }, 400);
    const record = await env.DB.prepare("SELECT password_salt, password_hash FROM chat_users WHERE id = ? AND active = 1").bind(user.id).first();
    let accepted = false;
    try {
      accepted = !!record && equalBytes(await passwordHash(currentPassword, fromB64url(record.password_salt)), fromB64url(record.password_hash));
    } catch { accepted = false; }
    if (!accepted) return json({ error: "Current password is incorrect." }, 401);
    const next = await makePasswordRecord(body.newPassword);
    await env.DB.prepare("UPDATE chat_users SET password_salt = ?, password_hash = ?, updated_at = ? WHERE id = ?")
      .bind(next.salt, next.hash, new Date().toISOString(), user.id).run();
    return json({ ok: true, message: "Password changed successfully." });
  }

  if (path === "/api/auth/me" && method === "GET") {
    return json({ ok: true, user: { id: user.id, username: user.username, displayName: user.display_name, role: user.role } });
  }
  if (path === "/api/users" && method === "GET") {
    const result = await env.DB.prepare("SELECT id, username, display_name, role FROM chat_users WHERE active = 1 ORDER BY display_name COLLATE NOCASE, username COLLATE NOCASE").all();
    return json({ ok: true, users: result.results || [] });
  }
  if (path === "/api/admin/users" && method === "POST") {
    if (user.role !== "Admin") return json({ error: "Administrator permission is required." }, 403);
    const body = await readJson(request);
    const username = normalizeUsername(body.username);
    const role = body.role === "Admin" ? "Admin" : "HR";
    if (!validUsername(username)) return json({ error: "Invalid username format." }, 400);
    if (!validPassword(body.password)) return json({ error: "Use a password of at least 10 characters containing a letter and a number." }, 400);
    const password = await makePasswordRecord(body.password);
    const now = new Date().toISOString();
    try {
      await env.DB.prepare("INSERT INTO chat_users(username, display_name, role, password_salt, password_hash, active, created_at, updated_at) VALUES(?, ?, ?, ?, ?, 1, ?, ?)")
        .bind(username, cleanDisplayName(body.displayName, username), role, password.salt, password.hash, now, now).run();
    } catch { return json({ error: "That chat username already exists." }, 409); }
    const created = await env.DB.prepare("SELECT id, username, display_name, role, active FROM chat_users WHERE username = ?").bind(username).first();
    return json({ ok: true, user: created }, 201);
  }
  if (path === "/api/conversations" && method === "GET") return json({ ok: true, conversations: await listConversations(env, user.id) });

  if (path === "/api/conversations/private" && method === "POST") {
    const body = await readJson(request);
    const target = await env.DB.prepare("SELECT id, username FROM chat_users WHERE username = ? COLLATE NOCASE AND active = 1")
      .bind(normalizeUsername(body.username)).first();
    if (!target) return json({ error: "No active chat user found with that username." }, 404);
    if (Number(target.id) === Number(user.id)) return json({ error: "Choose another user for a private chat." }, 400);
    const directKey = [Number(user.id), Number(target.id)].sort((a, b) => a - b).join(":");
    const conversationId = crypto.randomUUID();
    const now = new Date().toISOString();
    await env.DB.prepare("INSERT INTO conversations(id, kind, name, direct_key, created_by, created_at) VALUES(?, 'private', '', ?, ?, ?) ON CONFLICT(direct_key) DO NOTHING")
      .bind(conversationId, directKey, user.id, now).run();
    const conversation = await env.DB.prepare("SELECT id FROM conversations WHERE direct_key = ?").bind(directKey).first();
    await env.DB.batch([
      env.DB.prepare("INSERT OR IGNORE INTO conversation_members(conversation_id, user_id, member_role, joined_at) VALUES(?, ?, 'owner', ?)").bind(conversation.id, user.id, now),
      env.DB.prepare("INSERT OR IGNORE INTO conversation_members(conversation_id, user_id, member_role, joined_at) VALUES(?, ?, 'member', ?)").bind(conversation.id, target.id, now),
    ]);
    return json({ ok: true, conversations: await listConversations(env, user.id), conversationId: conversation.id }, 201);
  }

  if (path === "/api/conversations/group" && method === "POST") {
    const body = await readJson(request);
    const name = String(body.name || "").trim().slice(0, 80);
    if (name.length < 2) return json({ error: "Group name must contain at least 2 characters." }, 400);
    const requested = Array.isArray(body.usernames) ? body.usernames.map(normalizeUsername).filter(Boolean) : [];
    const names = [...new Set([user.username.toLowerCase(), ...requested])];
    if (names.length > 50) return json({ error: "A group can contain at most 50 members." }, 400);
    const placeholders = names.map(() => "?").join(",");
    const query = "SELECT id, username FROM chat_users WHERE active = 1 AND username IN (" + placeholders + ")";
    const users = await env.DB.prepare(query).bind(...names).all();
    if ((users.results || []).length !== names.length) return json({ error: "One or more group members do not exist or are inactive." }, 400);
    const conversationId = crypto.randomUUID();
    const now = new Date().toISOString();
    await env.DB.prepare("INSERT INTO conversations(id, kind, name, direct_key, created_by, created_at) VALUES(?, 'group', ?, NULL, ?, ?)")
      .bind(conversationId, name, user.id, now).run();
    await env.DB.batch(users.results.map(member => env.DB.prepare(
      "INSERT INTO conversation_members(conversation_id, user_id, member_role, joined_at) VALUES(?, ?, ?, ?)",
    ).bind(conversationId, member.id, Number(member.id) === Number(user.id) ? "owner" : "member", now)));
    return json({ ok: true, conversations: await listConversations(env, user.id), conversationId }, 201);
  }

  const memberRoute = /^\/api\/conversations\/([0-9a-f-]{36})\/members$/iu.exec(path);
  if (memberRoute && method === "POST") {
    const conversationId = memberRoute[1];
    const conversation = await env.DB.prepare("SELECT id, kind FROM conversations WHERE id = ?").bind(conversationId).first();
    if (!conversation || conversation.kind !== "group") return json({ error: "Group not found." }, 404);
    const membership = await env.DB.prepare("SELECT member_role FROM conversation_members WHERE conversation_id = ? AND user_id = ?").bind(conversationId, user.id).first();
    if (user.role !== "Admin" && (!membership || membership.member_role !== "owner")) return json({ error: "Only the group owner or an administrator can add members." }, 403);
    const body = await readJson(request);
    const target = await env.DB.prepare("SELECT id FROM chat_users WHERE username = ? COLLATE NOCASE AND active = 1").bind(normalizeUsername(body.username)).first();
    if (!target) return json({ error: "No active chat user found." }, 404);
    await env.DB.prepare("INSERT OR IGNORE INTO conversation_members(conversation_id, user_id, member_role, joined_at) VALUES(?, ?, 'member', ?)")
      .bind(conversationId, target.id, new Date().toISOString()).run();
    return json({ ok: true });
  }

  const historyRoute = /^\/api\/conversations\/([0-9a-f-]{36})\/messages$/iu.exec(path);
  if (historyRoute && method === "GET") {
    const conversationId = historyRoute[1];
    try { await requireMember(env, conversationId, user.id); } catch (error) { return json({ error: error.message }, error.status || 403); }
    const before = Number(url.searchParams.get("before") || 0);
    const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit") || 100)));
    const base = "SELECT m.id, m.conversation_id, m.sender_user_id, u.username, u.display_name, m.text, m.created_at, m.client_message_id " +
      "FROM messages m JOIN chat_users u ON u.id = m.sender_user_id WHERE m.conversation_id = ? ";
    const rows = before > 0
      ? await env.DB.prepare(base + "AND m.id < ? ORDER BY m.id DESC LIMIT ?").bind(conversationId, before, limit).all()
      : await env.DB.prepare(base + "ORDER BY m.id DESC LIMIT ?").bind(conversationId, limit).all();
    return json({ ok: true, messages: (rows.results || []).reverse() });
  }

  if (path === "/api/chat/ticket" && method === "POST") {
    const body = await readJson(request);
    const conversationId = String(body.conversationId || "");
    if (!/^[0-9a-f-]{36}$/iu.test(conversationId)) return json({ error: "Invalid conversation." }, 400);
    try { await requireMember(env, conversationId, user.id); } catch (error) { return json({ error: error.message }, error.status || 403); }
    const ticket = randomToken(32);
    await env.DB.prepare("DELETE FROM socket_tickets WHERE expires_at <= ?").bind(Math.floor(Date.now() / 1000)).run();
    await env.DB.prepare("INSERT INTO socket_tickets(ticket_hash, user_id, conversation_id, expires_at) VALUES(?, ?, ?, ?)")
      .bind(b64url(await sha256(ticket)), user.id, conversationId, Math.floor(Date.now() / 1000) + SOCKET_TICKET_TTL_SECONDS).run();
    return json({ ok: true, ticket, expiresIn: SOCKET_TICKET_TTL_SECONDS });
  }
  if (path === "/api/chat/ws" && method === "GET") return json({ error: "WebSocket upgrade required." }, 426);
  return json({ error: "API endpoint not found." }, 404);
}

async function websocketRoute(request, env) {
  const url = new URL(request.url);
  if (request.headers.get("Upgrade")?.toLowerCase() !== "websocket") return json({ error: "WebSocket upgrade required." }, 426);
  if (!originAllowed(request, env)) return json({ error: "Origin is not allowed." }, 403);
  if (url.pathname !== "/api/chat/ws") return json({ error: "Not found." }, 404);
  const ticket = url.searchParams.get("ticket") || "";
  if (ticket.length < 20 || ticket.length > 256) return json({ error: "Invalid or expired chat ticket." }, 401);
  const row = await env.DB.prepare("DELETE FROM socket_tickets WHERE ticket_hash = ? AND expires_at > ? RETURNING user_id, conversation_id")
    .bind(b64url(await sha256(ticket)), Math.floor(Date.now() / 1000)).first();
  if (!row) return json({ error: "Invalid or expired chat ticket." }, 401);
  const user = await env.DB.prepare("SELECT id, username, display_name, active FROM chat_users WHERE id = ?").bind(row.user_id).first();
  if (!user || user.active !== 1) return json({ error: "Chat account is inactive." }, 403);
  try { await requireMember(env, row.conversation_id, user.id); } catch { return json({ error: "Conversation access denied." }, 403); }
  const stub = env.CHAT_ROOM.get(env.CHAT_ROOM.idFromName(row.conversation_id));
  const headers = new Headers(request.headers);
  headers.set("X-Chat-User-ID", String(user.id));
  headers.set("X-Chat-Username", user.username);
  headers.set("X-Chat-Display-Name", user.display_name || user.username);
  headers.set("X-Chat-Conversation-ID", row.conversation_id);
  return stub.fetch(new Request(request, { headers }));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.headers.get("Upgrade")?.toLowerCase() === "websocket") {
      try { return await websocketRoute(request, env); }
      catch { return json({ error: "Unable to establish chat connection." }, 500); }
    }
    if (!originAllowed(request, env)) return json({ error: "Origin is not allowed." }, 403);
    if (request.method === "OPTIONS") return withCors(new Response(null, { status: 204 }), request);
    try {
      if (url.pathname.startsWith("/api/")) {
        return withCors(await routeApi(request, env) || json({ error: "API endpoint not found." }, 404), request);
      }
      if (env.ASSETS) return withCors(await env.ASSETS.fetch(request), request);
      return withCors(json({ error: "Not found." }, 404), request);
    } catch (error) {
      const status = Number(error.status) || 500;
      return withCors(json({ error: status >= 500 ? "The chat service encountered an error." : String(error.message || "Request failed.") }, status), request);
    }
  },
};

export class ChatRoom extends DurableObject {
  async fetch(request) {
    if (request.headers.get("Upgrade")?.toLowerCase() !== "websocket") return new Response("WebSocket upgrade required.", { status: 426 });
    const userId = Number(request.headers.get("X-Chat-User-ID") || 0);
    const conversationId = request.headers.get("X-Chat-Conversation-ID") || "";
    const username = request.headers.get("X-Chat-Username") || "";
    const displayName = request.headers.get("X-Chat-Display-Name") || username;
    if (!userId || !conversationId || !username) return new Response("Unauthorized.", { status: 401 });
    const pair = new WebSocketPair();
    const client = pair[0];
    const server = pair[1];
    this.ctx.acceptWebSocket(server);
    server.serializeAttachment({ userId, conversationId, username, displayName });
    const peers = [];
    for (const peer of this.ctx.getWebSockets()) {
      if (peer === server || peer.readyState !== WebSocket.OPEN) continue;
      const state = peer.deserializeAttachment();
      if (state && state.conversationId === conversationId && Number(state.userId) !== userId) {
        peers.push({ userId: Number(state.userId), displayName: state.displayName || state.username || "Employee" });
      }
    }
    server.send(JSON.stringify({ type: "ready", conversationId }));
    server.send(JSON.stringify({ type: "peers", peers: peers.map(peer => peer.userId) }));
    this.broadcastToConversation(conversationId, { type: "peer-joined", userId, displayName }, server);
    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(socket, rawMessage) {
    const attachment = socket.deserializeAttachment();
    if (!attachment || !attachment.userId || !attachment.conversationId) {
      socket.close(1008, "Missing session.");
      return;
    }
    let payload;
    try {
      if (typeof rawMessage !== "string" || rawMessage.length > 10000) throw new Error("Invalid message size.");
      payload = JSON.parse(rawMessage);
    } catch {
      socket.send(JSON.stringify({ type: "error", message: "Invalid message payload." }));
      return;
    }
    if (payload.type === "rtc-signal") {
      const targetUserId = Number(payload.targetUserId);
      const signal = payload.signal;
      const allowedKinds = new Set(["offer", "answer", "ice", "end", "reject", "busy"]);
      if (!targetUserId || targetUserId === Number(attachment.userId) || !signal || typeof signal !== "object" || !allowedKinds.has(String(signal.kind))) {
        socket.send(JSON.stringify({ type: "error", message: "Invalid screen-share signal." }));
        return;
      }
      const membership = await this.env.DB.prepare("SELECT 1 AS allowed FROM conversation_members WHERE conversation_id = ? AND user_id = ?")
        .bind(attachment.conversationId, attachment.userId).first();
      const targetMembership = await this.env.DB.prepare("SELECT 1 AS allowed FROM conversation_members WHERE conversation_id = ? AND user_id = ?")
        .bind(attachment.conversationId, targetUserId).first();
      if (!membership || !targetMembership) {
        socket.send(JSON.stringify({ type: "error", message: "Screen sharing is restricted to conversation members." }));
        return;
      }
      if (JSON.stringify(signal).length > 12000) {
        socket.send(JSON.stringify({ type: "error", message: "Screen-share signal is too large." }));
        return;
      }
      const signalRateKey = "rtc-rate:" + attachment.userId;
      const signalNow = Date.now();
      const signalPrior = await this.ctx.storage.get(signalRateKey) || [];
      const signalRecent = signalPrior.filter(timestamp => Number(timestamp) > signalNow - 60000);
      if (signalRecent.length >= 120) {
        socket.send(JSON.stringify({ type: "error", message: "Screen-share signaling rate limit reached." }));
        return;
      }
      signalRecent.push(signalNow);
      await this.ctx.storage.put(signalRateKey, signalRecent);
      const packet = {
        type: "rtc-signal",
        fromUserId: Number(attachment.userId),
        fromDisplayName: String(attachment.displayName || attachment.username || "Employee").slice(0, 80),
        signal,
      };
      this.broadcastToUser(attachment.conversationId, targetUserId, packet);
      return;
    }
    if (payload.type !== "message") return;
    const text = String(payload.text || "").trim();
    const clientMessageId = String(payload.clientMessageId || "");
    if (!text || text.length > MAX_MESSAGE_LENGTH) {
      socket.send(JSON.stringify({ type: "error", message: "Messages must contain 1–4000 characters." }));
      return;
    }
    if (!/^[0-9a-f-]{36}$/iu.test(clientMessageId)) {
      socket.send(JSON.stringify({ type: "error", message: "Invalid message identifier." }));
      return;
    }
    const membership = await this.env.DB.prepare("SELECT 1 AS allowed FROM conversation_members WHERE conversation_id = ? AND user_id = ?")
      .bind(attachment.conversationId, attachment.userId).first();
    if (!membership) {
      socket.send(JSON.stringify({ type: "error", message: "You no longer have access to this conversation." }));
      socket.close(1008, "Access revoked.");
      return;
    }
    const rateKey = "message-rate:" + attachment.userId;
    const now = Date.now();
    const prior = await this.ctx.storage.get(rateKey) || [];
    const recent = prior.filter(timestamp => Number(timestamp) > now - 60000);
    if (recent.length >= 30) {
      socket.send(JSON.stringify({ type: "error", message: "Message rate limit reached. Please wait a moment." }));
      return;
    }
    recent.push(now);
    await this.ctx.storage.put(rateKey, recent);
    await this.env.DB.prepare("INSERT OR IGNORE INTO messages(conversation_id, sender_user_id, text, created_at, client_message_id) VALUES(?, ?, ?, ?, ?)")
      .bind(attachment.conversationId, attachment.userId, text, new Date().toISOString(), clientMessageId).run();
    const message = await this.env.DB.prepare(
      "SELECT m.id, m.conversation_id, m.sender_user_id, u.username, u.display_name, m.text, m.created_at, m.client_message_id " +
      "FROM messages m JOIN chat_users u ON u.id = m.sender_user_id WHERE m.conversation_id = ? AND m.sender_user_id = ? AND m.client_message_id = ?",
    ).bind(attachment.conversationId, attachment.userId, clientMessageId).first();
    if (!message) {
      socket.send(JSON.stringify({ type: "error", message: "Message could not be saved. Please retry." }));
      return;
    }
    const event = JSON.stringify({ type: "message", message });
    for (const peer of this.ctx.getWebSockets()) {
      try {
        const state = peer.deserializeAttachment();
        if (state && state.conversationId === attachment.conversationId && peer.readyState === WebSocket.OPEN) peer.send(event);
      } catch {
        try { peer.close(1011, "Delivery failed."); } catch {}
      }
    }
  }
  broadcastToConversation(conversationId, packet, exceptSocket = null) {
    const event = JSON.stringify(packet);
    for (const peer of this.ctx.getWebSockets()) {
      if (peer === exceptSocket || peer.readyState !== WebSocket.OPEN) continue;
      try {
        const state = peer.deserializeAttachment();
        if (state && state.conversationId === conversationId) peer.send(event);
      } catch { try { peer.close(1011, "Delivery failed."); } catch {} }
    }
  }

  broadcastToUser(conversationId, targetUserId, packet) {
    const event = JSON.stringify(packet);
    for (const peer of this.ctx.getWebSockets()) {
      if (peer.readyState !== WebSocket.OPEN) continue;
      try {
        const state = peer.deserializeAttachment();
        if (state && state.conversationId === conversationId && Number(state.userId) === Number(targetUserId)) peer.send(event);
      } catch { try { peer.close(1011, "Delivery failed."); } catch {} }
    }
  }

  async webSocketClose(socket, code, reason) {
    try {
      const state = socket.deserializeAttachment();
      if (state?.conversationId && state?.userId) {
        this.broadcastToConversation(state.conversationId, { type: "peer-left", userId: Number(state.userId) }, socket);
      }
    } catch {}
    try { socket.close(code, reason); } catch {}
  }
  async webSocketError(socket) { try { socket.close(1011, "Connection error."); } catch {} }
}
