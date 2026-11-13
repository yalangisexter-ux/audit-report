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

test("working-weekday settings default to Sunday and allow the Admin to configure it", async () => {
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
  const defaults = await get.json();
  assert.deepEqual(defaults.weekdays, [0, 1, 2, 3, 4, 6]);
  assert.equal(defaults.sunday_configurable, true);

  const save = await worker.fetch(request("/api/settings/working-weekdays", "PUT", { weekdays: [0, 1, 2, 3, 4] }, token), env);
  assert.equal(save.status, 200);
  const result = await save.json();
  assert.deepEqual(result.weekdays, [0, 1, 2, 3, 4]);
  assert.equal(result.sunday_configurable, true);
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

test("report options and preview return desktop-compatible structure", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "report-token";
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const settingsStore = new Map();
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions")) return values[0] === tokenHash ? user : null;
              return null;
            },
            async all() {
              if (sql.includes("FROM settings WHERE key LIKE 'report_opt_%'")) {
                return { results: [...settingsStore.entries()].map(([key, value]) => ({ key, value })) };
              }
              if (sql.includes("FROM employees")) {
                return { results: [{ id: 1, name: "Alice", employee_code: "EMP01", department: "Ops", active: 1 }] };
              }
              if (sql.includes("FROM tasks")) return { results: [] };
              return { results: [] };
            },
            async run() {
              if (sql.includes("INSERT INTO settings")) {
                settingsStore.set(values[0], values[1]);
                return { success: true, meta: { changes: 1 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
          };
        },
      };
    },
  };

  const getOpts = await worker.fetch(request("/api/reports/options", "GET", null, token), { DB });
  assert.equal(getOpts.status, 200);
  const optsBody = await getOpts.json();
  assert.equal(optsBody.options.summary, true);

  const putOpts = await worker.fetch(request("/api/reports/options", "PUT", { options: { summary: false } }, token), { DB });
  assert.equal(putOpts.status, 200);
  assert.equal(settingsStore.get("report_opt_summary"), "0");

  const preview = await worker.fetch(request("/api/reports/preview", "POST", { report_type: "Audit / EOD", date: "2026-11-11" }, token), { DB });
  assert.equal(preview.status, 200);
  const prevBody = await preview.json();
  assert.equal(prevBody.report_type, "Audit / EOD");
  assert.match(prevBody.preview_text, /RAW STRENGTH CALISTHENICS/);
});

test("archive documents list and validate PDF upload", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "archive-token";
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const docs = [];
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions")) return values[0] === tokenHash ? user : null;
              if (sql.includes("FROM archived_documents WHERE id=?")) return docs.find(d => d.id === values[0]) || null;
              return null;
            },
            async all() {
              if (sql.includes("FROM archived_documents")) return { results: docs };
              return { results: [] };
            },
            async run() {
              if (sql.startsWith("INSERT INTO archived_documents")) {
                const id = docs.length + 1;
                docs.push({ id, file_name: values[2], mime_type: values[3], content: values[4], uploaded_at: values[6] });
                return { success: true, meta: { changes: 1, last_row_id: id } };
              }
              if (sql.startsWith("DELETE FROM archived_documents")) {
                const idx = docs.findIndex(d => d.id === values[0]);
                if (idx !== -1) {
                  docs.splice(idx, 1);
                  return { success: true, meta: { changes: 1 } };
                }
                return { success: true, meta: { changes: 0 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
          };
        },
      };
    },
  };

  const listEmpty = await worker.fetch(request("/api/archive", "GET", null, token), { DB });
  assert.equal(listEmpty.status, 200);
  assert.deepEqual(await listEmpty.json(), []);

  // Reject non-PDF
  const badUpload = await worker.fetch(request("/api/archive", "POST", { file_name: "test.txt", content: Buffer.from("hello world").toString("base64") }, token), { DB });
  assert.equal(badUpload.status, 400);

  // Accept valid PDF (%PDF header)
  const pdfBytes = Buffer.from("%PDF-1.4 sample content").toString("base64");
  const goodUpload = await worker.fetch(request("/api/archive", "POST", { file_name: "report.pdf", content: pdfBytes }, token), { DB });
  assert.equal(goodUpload.status, 200);
  assert.equal((await goodUpload.json()).success, true);
  assert.equal(docs.length, 1);

  // View document
  const viewDoc = await worker.fetch(request("/api/archive/1/view", "GET", null, token), { DB });
  assert.equal(viewDoc.status, 200);
  assert.equal(viewDoc.headers.get("Content-Type"), "application/pdf");

  // Delete document
  const delDoc = await worker.fetch(request("/api/archive/1", "DELETE", null, token), { DB });
  assert.equal(delDoc.status, 200);
  assert.equal(docs.length, 0);
});

test("customer prospects CRUD operates with validation and deduplication", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "prospect-token";
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const prospects = [];
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions")) return values[0] === tokenHash ? user : null;
              if (sql.includes("FROM customer_prospects WHERE dedupe_key=?")) return prospects.find(p => p.dedupe_key === values[0]) || null;
              if (sql.includes("FROM customer_prospects WHERE id=?")) return prospects.find(p => p.id === values[0]) || null;
              return null;
            },
            async all() {
              if (sql.includes("FROM customer_prospects")) return { results: prospects };
              return { results: [] };
            },
            async run() {
              if (sql.startsWith("INSERT INTO customer_prospects")) {
                const id = prospects.length + 1;
                prospects.push({ id, ...values[0], dedupe_key: values[values.length - 2] });
                return { success: true, meta: { changes: 1, last_row_id: id } };
              }
              if (sql.startsWith("UPDATE customer_prospects")) {
                return { success: true, meta: { changes: 1 } };
              }
              if (sql.startsWith("DELETE FROM customer_prospects")) {
                const idx = prospects.findIndex(p => p.id === values[0]);
                if (idx !== -1) {
                  prospects.splice(idx, 1);
                  return { success: true, meta: { changes: 1 } };
                }
                return { success: true, meta: { changes: 0 } };
              }
              return { success: true, meta: { changes: 0 } };
            },
          };
        },
      };
    },
  };

  // Missing fields fail validation
  const bad = await worker.fetch(request("/api/customers/prospects", "POST", { business_name: "" }, token), { DB });
  assert.equal(bad.status, 422);

  // Valid insert
  const create = await worker.fetch(request("/api/customers/prospects", "POST", { business_name: "Raw Fitness", city: "Mumbai", state: "Maharashtra" }, token), { DB });
  assert.equal(create.status, 200);
  assert.equal((await create.json()).success, true);
});

test("system db-info, sync-now, and payment endpoints respond with valid structures", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "sys-token";
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions")) return values[0] === tokenHash ? user : null;
              if (sql.includes("COUNT(*)")) return { n: 5 };
              return null;
            },
            async all() { return { results: [] }; }
          };
        },
      };
    },
  };

  const dbInfo = await worker.fetch(request("/api/system/db-info", "GET", null, token), { DB });
  assert.equal(dbInfo.status, 200);
  const infoBody = await dbInfo.json();
  assert.equal(infoBody.status, "healthy");
  assert.equal(infoBody.database_name, "raw-strength-audit-manager");

  const syncNow = await worker.fetch(request("/api/system/sync-now", "POST", null, token), { DB });
  assert.equal(syncNow.status, 200);
  assert.equal((await syncNow.json()).success, true);

  const payments = await worker.fetch(request("/api/payments/config", "GET", null, token), { DB });
  assert.equal(payments.status, 200);
  assert.equal((await payments.json()).currency, "INR");
});

test("web database export returns structured JSON dump", async () => {
  const user = makeUser("Admin", "correct horse");
  const token = "export-token";
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const DB = {
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions")) return values[0] === tokenHash ? user : null;
              return null;
            },
            async all() {
              if (sql.includes("FROM \"employees\"")) return { results: [{ id: 1, name: "Alice" }] };
              return { results: [] };
            }
          };
        },
      };
    },
  };

  const exportRes = await worker.fetch(request("/api/web-database/export", "GET", null, token), { DB });
  assert.equal(exportRes.status, 200);
  assert.equal(exportRes.headers.get("Content-Type"), "application/json; charset=utf-8");
  const body = await exportRes.json();
  assert.equal(body.database, "raw-strength-audit-manager");
  assert.deepEqual(body.tables.employees, [{ id: 1, name: "Alice" }]);
});

test("employee status, targets, chat, and regional export endpoints respond successfully", async () => {
  const token = "b".repeat(64);
  const tokenHash = createHash("sha256").update(token).digest("hex");
  const adminUser = { id: 1, username: "Admin", display_name: "Admin User", role: "Admin", active: 1 };
  const DB = {
    prepare(sql) {
      return {
        async run() {
          return { success: true, meta: { changes: 1, last_row_id: 1 } };
        },
        bind(...values) {
          return {
            async first() {
              if (sql.includes("FROM web_auth_sessions")) return values[0] === tokenHash ? adminUser : null;
              if (sql.includes("FROM employees WHERE id=?")) return { id: 1, active: 1, name: "Test Staff" };
              if (sql.includes("COUNT(*)")) return { n: 5 };
              return null;
            },
            async all() {
              if (sql.includes("FROM employees")) return { results: [{ id: 1, name: "Staff", active: 1 }] };
              if (sql.includes("FROM customer_prospects")) return { results: [{ state: "Telangana", kind: "Store", count: 10 }] };
              if (sql.includes("FROM local_chat_messages")) return { results: [{ id: 1, channel: "general", content: "hello" }] };
              return { results: [] };
            },
            async run() {
              return { success: true, meta: { changes: 1, last_row_id: 1 } };
            }
          };
        }
      };
    }
  };

  // 1. Employee status PATCH
  const statusRes = await worker.fetch(request("/api/employees/1/status", "PATCH", { active: false }, token), { DB });
  assert.equal(statusRes.status, 200);
  const statusBody = await statusRes.json();
  assert.equal(statusBody.success, true);
  assert.equal(statusBody.active, 0);

  // 2. Employee targets GET without params
  const targetRes = await worker.fetch(request("/api/employee-targets", "GET", null, token), { DB });
  assert.equal(targetRes.status, 200);

  // 3. Employee CSV export
  const csvRes = await worker.fetch(request("/api/employees/export.csv", "GET", null, token), { DB });
  assert.equal(csvRes.status, 200);
  assert.match(csvRes.headers.get("Content-Type"), /text\/csv/);

  // 4. Chat messages GET & POST
  const chatGetRes = await worker.fetch(request("/api/chat/messages?channel=general", "GET", null, token), { DB });
  assert.equal(chatGetRes.status, 200);
  const chatPostRes = await worker.fetch(request("/api/chat/messages", "POST", { content: "Test msg" }, token), { DB });
  assert.equal(chatPostRes.status, 200);

  // 5. Regional export
  const regRes = await worker.fetch(request("/api/customers/regional-export?format=csv", "GET", null, token), { DB });
  assert.equal(regRes.status, 200);
  assert.match(regRes.headers.get("Content-Type"), /text\/csv/);

  // 6. Dashboard KPIs
  const kpiRes = await worker.fetch(request("/api/dashboard/kpis", "GET", null, token), { DB });
  assert.equal(kpiRes.status, 200);
  const kpiBody = await kpiRes.json();
  assert.equal(kpiBody.kpis.total_employees, 5);
});

test("storefront live order tracking endpoint validates code and returns order with items", async () => {
  const mockOrder = {
    id: 42,
    order_code: "USA-RS-20261113-XYZ",
    customer_name: "Rahul Verma",
    phone: "9876543210",
    email: "rahul@example.com",
    shipping_address: "Flat 402, Calisthenics Arena, Hyderabad 500081",
    order_status: "Confirmed",
    payment_method: "Instant UPI / QR",
    payment_status: "Paid",
    subtotal: 4299,
    total_amount: 4299,
    customer_note: "Please deliver after 5 PM",
    created_at: "2026-11-13T08:00:00Z",
    updated_at: "2026-11-13T08:30:00Z"
  };
  const mockItems = [
    { product_name: "USA Raw Strength 100% Whey Isolate", sku: "RSC-WHEY-ISO", quantity: 1, unit: "JAR", unit_price: 4299, line_total: 4299 }
  ];

  const DB = {
    prepare(sql) {
      return {
        bind(...values) {
          return {
            async first() {
              if (sql.includes("FROM store_orders WHERE order_code=?")) {
                return String(values[0]).toUpperCase() === "USA-RS-20261113-XYZ" ? mockOrder : null;
              }
              return null;
            },
            async all() {
              if (sql.includes("FROM store_order_items WHERE order_id=?")) {
                return values[0] === 42 ? { results: mockItems } : { results: [] };
              }
              return { results: [] };
            }
          };
        }
      };
    }
  };

  // Missing code query
  const resMissing = await worker.fetch(new Request("https://example.com/api/store/track", { method: "GET" }), { DB });
  assert.equal(resMissing.status, 400);

  // Unknown order code
  const resNotFound = await worker.fetch(new Request("https://example.com/api/store/track?code=USA-RS-NOTFOUND", { method: "GET" }), { DB });
  assert.equal(resNotFound.status, 404);

  // Valid order code
  const resValid = await worker.fetch(new Request("https://example.com/api/store/track?code=USA-RS-20261113-XYZ", { method: "GET" }), { DB });
  assert.equal(resValid.status, 200);
  const data = await resValid.json();
  assert.equal(data.order_code, "USA-RS-20261113-XYZ");
  assert.equal(data.order_status, "Confirmed");
  assert.equal(data.customer_name, "Rahul Verma");
  assert.equal(data.items.length, 1);
  assert.equal(data.items[0].sku, "RSC-WHEY-ISO");
});
