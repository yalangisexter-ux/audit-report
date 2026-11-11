import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";
import { webcrypto, createHash, pbkdf2Sync } from "node:crypto";

globalThis.crypto ||= webcrypto;
function makeDb(users = []) {
  const sessions = new Map();
  const statements = [];
  return {
    sessions, statements,
    prepare(sql) {
      const state = { sql, values: [] }; statements.push(state);
      return {
        bind(...values) {
          state.values = values;
          return {
            async first() {
              if (sql.includes("FROM auth_users")) {
                return users.find(u => u.username === values[0] && u.active === 1) || null;
              }
              if (sql.includes("FROM web_auth_sessions")) {
                const [hash, now] = values;
                const s = sessions.get(hash);
                if (!s || s.expires_at <= now) return null;
                return users.find(u => u.id === s.user_id && u.active === 1) || null;
              }
              if (sql.includes("COUNT(*)")) return { n: 0 };
              return null;
            },
            async run() {
              if (sql.startsWith("INSERT INTO web_auth_sessions")) {
                sessions.set(values[0], { user_id: values[1], expires_at: values[3] });
                return { success: true, meta: { changes: 1 } };
              }
              if (sql.startsWith("DELETE FROM web_auth_sessions")) {
                const existed = sessions.delete(values[0]);
                return { success: true, meta: { changes: existed ? 1 : 0 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
          };
        },
        async first() { return null; },
      };
    },
  };
}
function makeUser(username, password) {
  const salt = "test-salt";
  const hash = pbkdf2Sync(password, salt, 200000, 32, "sha256").toString("hex");
  return { id: 1, username, display_name: username, role: "Admin", password_salt: salt, password_hash: hash, active: 1 };
}
function request(path, method = "GET", body, token) {
  return new Request("https://api.test" + path, {
    method, headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: "Bearer " + token } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
}
test("health responds using D1 and reports counts", async () => {
  const DB = makeDb();
  DB.prepare = sql => ({ first: async () => ({ n: 0 }), bind: () => ({ first: async () => ({ n: 0 }) }) });
  const response = await worker.fetch(request("/api/health"), { DB });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).database_connected, true);
});
test("login preserves exact-case usernames and creates a hashed session", async () => {
  const DB = makeDb([makeUser("Admin", "correct horse")]);
  const env = { DB, ALLOWED_ORIGINS: "https://example.pages.dev" };
  const wrongCase = await worker.fetch(request("/api/auth/login", "POST", { username: "admin", password: "correct horse" }), env);
  assert.equal(wrongCase.status, 401);
  const login = await worker.fetch(request("/api/auth/login", "POST", { username: "Admin", password: "correct horse" }), env);
  assert.equal(login.status, 200);
  const data = await login.json();
  assert.equal(data.user.username, "Admin");
  assert.equal(DB.sessions.size, 1);
  assert.equal([...DB.sessions.keys()][0], createHash("sha256").update(data.token).digest("hex"));
  const me = await worker.fetch(request("/api/auth/me", "GET", null, data.token), env);
  assert.equal(me.status, 200);
  assert.equal((await me.json()).user.username, "Admin");
  const logout = await worker.fetch(request("/api/auth/logout", "POST", {}, data.token), env);
  assert.equal(logout.status, 200);
  const after = await worker.fetch(request("/api/auth/me", "GET", null, data.token), env);
  assert.equal(after.status, 401);
});
test("invalid password is rejected without creating a session", async () => {
  const DB = makeDb([makeUser("Admin", "correct horse")]);
  const response = await worker.fetch(request("/api/auth/login", "POST", { username: "Admin", password: "wrong" }), { DB });
  assert.equal(response.status, 401);
  assert.equal(DB.sessions.size, 0);
});
test("missing D1 binding fails closed", async () => {
  const response = await worker.fetch(request("/api/health"), {});
  assert.equal(response.status, 503);
});

test("protected employee API rejects requests without a valid session", async () => {
  const DB = makeDb([makeUser("Admin", "correct horse")]);
  const response = await worker.fetch(request("/api/employees"), { DB });
  assert.equal(response.status, 401);
});

test("working-weekday settings always include Sunday for the Admin calendar", async () => {
  const user = makeUser("Admin", "correct horse");
  const DB = makeDb([user]);
  const token = "test-admin-session";
  DB.sessions.set(createHash("sha256").update(token).digest("hex"), {
    user_id: user.id,
    expires_at: new Date(Date.now() + 60000).toISOString(),
  });
  const env = { DB };
  const get = await worker.fetch(request("/api/settings/working-weekdays", "GET", null, token), env);
  assert.equal(get.status, 200);
  assert.deepEqual((await get.json()).weekdays, [0, 1, 2, 3, 4, 6]);

  const save = await worker.fetch(request("/api/settings/working-weekdays", "PUT", { weekdays: [0, 1, 2, 3, 4] }, token), env);
  assert.equal(save.status, 200);
  const result = await save.json();
  assert.deepEqual(result.weekdays, [0, 1, 2, 3, 4, 6]);
  assert.equal(result.sunday_required, true);
});
