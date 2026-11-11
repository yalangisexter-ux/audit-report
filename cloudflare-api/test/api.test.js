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

test("attendance mark persists the selected date and blocks declared holidays", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "attendance-session";
  let saved = null;
  let holiday = null;
  let writes = 0;
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions s JOIN auth_users")) {
                return values[0] === tokenHash ? { id: user.id, username: user.username, display_name: user.username, role: user.role } : null;
              }
              if (sql.includes("FROM holidays")) return holiday;
              if (sql.includes("FROM employees WHERE id=?")) return { id: 1 };
              if (sql.includes("FROM attendance WHERE employee_id=? AND work_date=?")) return saved;
              return null;
            },
            async run() {
              if (sql.startsWith("INSERT INTO attendance")) {
                writes++;
                saved = {
                  id: 1, employee_id: values[0], work_date: values[1],
                  attendance_status: values[2], check_in: values[3], check_out: values[4],
                  break_minutes: values[5], attendance_note: values[6], updated_at: values[7],
                };
              }
              return { success: true, meta: { changes: 1 } };
            },
          };
        },
      };
    },
  };
  const env = { DB };
  const payload = { employee_id: 1, work_date: "2026-11-11", attendance_status: "Present", check_in: "09:00", check_out: "17:00", break_minutes: 30, attendance_note: "Verified" };
  const response = await worker.fetch(request("/api/attendance/mark", "POST", payload, token), env);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.attendance.work_date, payload.work_date);
  assert.equal(body.attendance.attendance_status, "Present");
  assert.equal(body.attendance.check_in, "09:00");
  assert.equal(writes, 1);

  holiday = { holiday_name: "Declared holiday" };
  const blocked = await worker.fetch(request("/api/attendance/mark", "POST", { ...payload, work_date: "2026-11-12" }, token), env);
  assert.equal(blocked.status, 409);
  assert.equal(writes, 1);
});

test("D1 dashboard returns desktop-compatible KPI and productivity payloads", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "dashboard-session";
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions s JOIN auth_users")) {
                return values[0] === tokenHash ? { id: user.id, username: user.username, display_name: user.username, role: user.role } : null;
              }
              if (sql.includes("FROM settings")) return { value: "0,1,2,3,4,6" };
              return null;
            },
            async all() {
              if (sql.includes("FROM employees WHERE active=1")) return { results: [{ id: 1, employee_code: "EMP001", name: "Test Employee", department: "Operations", designation: "Staff", joining_date: "2026-11-01", active: 1, display_order: 1 }] };
              if (sql.includes("FROM attendance") && sql.includes("work_date=?")) return { results: [] };
              if (sql.includes("FROM tasks t JOIN employees")) return { results: [] };
              if (sql.includes("MIN(activity_date)")) return { results: [] };
              if (sql.includes("SELECT employee_id,task_date,progress,status")) return { results: [] };
              if (sql.includes("SELECT employee_id,work_date,attendance_status,check_in")) return { results: [] };
              if (sql.includes("SELECT holiday_date")) return { results: [] };
              return { results: [] };
            },
          };
        },
      };
    },
  };
  const response = await worker.fetch(request("/api/dashboard", "GET", null, token), { DB });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.kpis.total_employees, 1);
  assert.equal(body.kpis.not_checked_today, 1);
  assert.equal(body.productivity.length, 1);
  assert.equal(body.productivity[0].name, "Test Employee");
  assert.equal(body.attendance_roster[0].status, "Not checked");
});
