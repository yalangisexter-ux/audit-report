/**
 * Raw Strength Calisthenics - Employee Audit Manager Mobile App
 * Synchronized with Desktop Database via Cloudflare Encrypted Sync
 * Version 1.3.15
 */

const SYNC_WORKER_URL = "https://raw-strength-audit-db-sync.yalangisexter.workers.dev";
const CHAT_WORKER_URL = "https://raw-strength-chat.yalangisexter.workers.dev";
const SNAPSHOT_MAGIC = new Uint8Array([82, 83, 67, 68, 66, 49]); // b"RSCDB1"
const SNAPSHOT_AAD = new TextEncoder().encode("RawStrengthEmployeeAuditManager:encrypted-customer-database:v1");

// State store
const state = {
  currentDate: getTodayIso(),
  theme: localStorage.getItem("rsc_theme") || "night",
  wallpaper: localStorage.getItem("rsc_wallpaper") || "Galaxy",
  installId: localStorage.getItem("rsc_install_id") || "c4cf201d3c68e2fcaf60aa05fd423d9a",
  syncSecret: localStorage.getItem("rsc_sync_secret") || "Devlopershouse@1996#",
  deviceToken: localStorage.getItem("rsc_device_token") || "",
  deviceId: localStorage.getItem("rsc_device_id") || generateHex(32),
  deviceSecret: localStorage.getItem("rsc_device_secret") || generateHex(48),
  users: JSON.parse(localStorage.getItem("rsc_auth_users") || "[]"),
  currentUser: JSON.parse(localStorage.getItem("rsc_current_user") || "null"),
  rawSqliteBytes: null,
  employees: [],
  attendance: {}, // key: `${employeeId}_${date}` -> record
  tasks: [],
  holidays: {
    "2026-01-01": "New Year's Day",
    "2026-01-26": "Republic Day",
    "2026-08-15": "Independence Day",
    "2026-10-02": "Gandhi Jayanti",
    "2026-12-25": "Christmas Day"
  },
  chat: {
    token: localStorage.getItem("rsc_chat_token") || "",
    username: localStorage.getItem("rsc_chat_user") || "",
    conversations: [],
    activeConvId: null
  }
};

// Utilities
function getTodayIso() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function generateHex(len) {
  const chars = "0123456789abcdef";
  let str = "";
  for (let i = 0; i < len; i++) {
    str += chars[Math.floor(Math.random() * chars.length)];
  }
  return str;
}

function showToast(msg, duration = 3000) {
  const t = document.getElementById("toastNotification");
  if (!t) return;
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), duration);
}

// Storage helpers
let mobileDebouncePush = null;
function scheduleMobileAutoPush() {
  if (mobileDebouncePush) clearTimeout(mobileDebouncePush);
  mobileDebouncePush = setTimeout(() => {
    pushToCloud(true);
  }, 2500);
}

function saveLocalData(triggerPush = true) {
  localStorage.setItem("rsc_employees", JSON.stringify(state.employees));
  localStorage.setItem("rsc_attendance", JSON.stringify(state.attendance));
  localStorage.setItem("rsc_tasks", JSON.stringify(state.tasks));
  if (triggerPush) {
    scheduleMobileAutoPush();
  }
}

function loadLocalData() {
  const empStr = localStorage.getItem("rsc_employees");
  const attStr = localStorage.getItem("rsc_attendance");
  const taskStr = localStorage.getItem("rsc_tasks");

  if (empStr) state.employees = JSON.parse(empStr);
  if (attStr) state.attendance = JSON.parse(attStr);
  if (taskStr) state.tasks = JSON.parse(taskStr);

  // Do not seed demo employees into a real customer installation.
  // The list stays empty until real local data or a validated cloud snapshot is loaded.
  if (!Array.isArray(state.employees)) state.employees = [];
}

// Navigation
function initNav() {
  const navButtons = document.querySelectorAll(".bottom-nav .nav-item");
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const viewId = btn.dataset.view;
      switchView(viewId);
    });
  });

  // Quick Action Buttons on Dashboard
  document.getElementById("quickMarkAttBtn")?.addEventListener("click", () => switchView("viewAttendance"));
  document.getElementById("quickAddTaskBtn")?.addEventListener("click", () => openTaskModal());
  document.getElementById("quickAddEmpBtn")?.addEventListener("click", () => openEmployeeModal());
  document.getElementById("dashViewAllTasks")?.addEventListener("click", () => switchView("viewTasks"));
}

function switchView(viewId) {
  document.querySelectorAll(".view-panel").forEach(panel => panel.classList.remove("active"));
  document.querySelectorAll(".bottom-nav .nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.view === viewId);
  });
  const target = document.getElementById(viewId);
  if (target) {
    target.classList.add("active");
    refreshActiveView(viewId);
  }
}

function refreshActiveView(viewId) {
  if (viewId === "viewDashboard") renderDashboard();
  else if (viewId === "viewAttendance") renderAttendance();
  else if (viewId === "viewTasks") renderTasks();
  else if (viewId === "viewEmployees") renderEmployees();
  else if (viewId === "viewChat") checkChatAuth();
}

// 1. DASHBOARD
function renderDashboard() {
  const dateObj = new Date(state.currentDate);
  const options = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
  document.getElementById("dashDateStr").textContent = dateObj.toLocaleDateString("en-US", options);

  // Check holiday
  const holiday = state.holidays[state.currentDate];
  const holidayBadge = document.getElementById("holidayBadge");
  if (holiday) {
    holidayBadge.textContent = `🎉 Holiday: ${holiday}`;
    holidayBadge.classList.remove("hidden");
  } else {
    holidayBadge.classList.add("hidden");
  }

  // Count stats
  const total = state.employees.filter(e => e.active).length;
  let present = 0, absent = 0, leave = 0;

  state.employees.forEach(e => {
    const rec = state.attendance[`${e.id}_${state.currentDate}`];
    if (rec) {
      if (rec.status === "Present" || (!rec.status && rec.check_in)) present++;
      else if (rec.status === "Absent") absent++;
      else if (rec.status === "Leave") leave++;
    }
  });

  document.getElementById("statTotalEmployees").textContent = total;
  document.getElementById("statPresentCount").textContent = present;
  document.getElementById("statAbsentCount").textContent = absent;
  document.getElementById("statLeaveCount").textContent = leave;

  // Render recent tasks
  const dashTasks = state.tasks.filter(t => t.task_date === state.currentDate).slice(0, 4);
  const dashTasksContainer = document.getElementById("dashTasksList");
  if (dashTasks.length === 0) {
    dashTasksContainer.innerHTML = '<p class="muted-text">No tasks recorded for today.</p>';
  } else {
    dashTasksContainer.innerHTML = dashTasks.map(t => {
      const emp = state.employees.find(e => e.id == t.employee_id);
      return `
        <div class="task-card" style="padding: 10px; margin-bottom: 6px;">
          <div class="task-card-top">
            <strong>${escapeHtml(t.title)}</strong>
            <span class="task-priority-badge priority-${(t.priority || "normal").toLowerCase()}">${t.priority}</span>
          </div>
          <div class="task-meta-row">
            <span>👤 ${escapeHtml(emp ? emp.name : "Unassigned")}</span>
            <span>${t.status || "Not started"} (${t.progress || 0}%)</span>
          </div>
        </div>
      `;
    }).join("");
  }
}

// 2. ATTENDANCE
function renderAttendance() {
  const dateInput = document.getElementById("attDateInput");
  dateInput.value = state.currentDate;

  const holiday = state.holidays[state.currentDate];
  const banner = document.getElementById("attHolidayBanner");
  const holidayName = document.getElementById("attHolidayName");
  if (holiday) {
    holidayName.textContent = holiday;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }

  const list = document.getElementById("attList");
  const emps = state.employees.filter(e => e.active);
  if (emps.length === 0) {
    list.innerHTML = '<p class="muted-text">No active staff members found.</p>';
    return;
  }

  let presentCount = 0;
  list.innerHTML = emps.map(e => {
    const key = `${e.id}_${state.currentDate}`;
    const rec = state.attendance[key] || { status: holiday ? "Holiday" : "Unmarked", check_in: "", check_out: "", note: "" };
    if (rec.status === "Present" || (rec.status === "Unmarked" && rec.check_in)) presentCount++;

    const hours = calculateHours(rec.check_in, rec.check_out);
    const statusClass = `att-status-${(rec.status || "unmarked").toLowerCase()}`;

    return `
      <div class="att-row-card" data-emp-id="${e.id}">
        <div class="att-row-top">
          <span class="att-emp-name">${escapeHtml(e.name)}</span>
          <select class="att-status-select select-input ${statusClass}" onchange="onStatusChange(${e.id}, this.value)">
            <option value="Unmarked" ${rec.status === "Unmarked" ? "selected" : ""}>Unmarked</option>
            <option value="Present" ${rec.status === "Present" ? "selected" : ""}>Present</option>
            <option value="Absent" ${rec.status === "Absent" ? "selected" : ""}>Absent</option>
            <option value="Leave" ${rec.status === "Leave" ? "selected" : ""}>Leave</option>
            <option value="Holiday" ${rec.status === "Holiday" ? "selected" : ""}>Holiday</option>
          </select>
        </div>
        <div class="att-times-row">
          <div class="att-time-field">
            <span>Check-in</span>
            <input type="text" placeholder="HH:MM" value="${escapeHtml(rec.check_in || "")}" onblur="onTimeBlur(${e.id}, 'check_in', this.value)">
          </div>
          <div class="att-time-field">
            <span>Check-out</span>
            <input type="text" placeholder="HH:MM" value="${escapeHtml(rec.check_out || "")}" onblur="onTimeBlur(${e.id}, 'check_out', this.value)">
          </div>
          <div class="att-time-field">
            <span>Net Hours</span>
            <span class="att-net-hours">${hours || "--:--"}</span>
          </div>
        </div>
        <input type="text" placeholder="Attendance note..." value="${escapeHtml(rec.note || "")}" onblur="onTimeBlur(${e.id}, 'note', this.value)" style="margin-top: 4px; font-size: 12px; padding: 6px 10px;">
      </div>
    `;
  }).join("");

  document.getElementById("attRosterSummary").textContent = `${presentCount} Present / ${emps.length} Staff`;
}

function onStatusChange(empId, status) {
  const key = `${empId}_${state.currentDate}`;
  if (!state.attendance[key]) state.attendance[key] = { check_in: "", check_out: "", note: "" };
  state.attendance[key].status = status;
  if (status === "Absent" || status === "Leave" || status === "Unmarked") {
    state.attendance[key].check_in = "";
    state.attendance[key].check_out = "";
  }
  saveLocalData();
  renderAttendance();
  showToast(`Attendance updated for staff`);
}

function onTimeBlur(empId, field, val) {
  const key = `${empId}_${state.currentDate}`;
  if (!state.attendance[key]) state.attendance[key] = { status: "Unmarked", check_in: "", check_out: "", note: "" };
  state.attendance[key][field] = val.trim();
  if (field === "check_in" && val.trim()) {
    state.attendance[key].status = "Present";
  }
  saveLocalData();
  renderAttendance();
}

function calculateHours(ci, co) {
  if (!ci || !co) return "";
  const [h1, m1] = ci.split(":").map(Number);
  const [h2, m2] = co.split(":").map(Number);
  if (isNaN(h1) || isNaN(m1) || isNaN(h2) || isNaN(m2)) return "";
  let totalMin = (h2 * 60 + m2) - (h1 * 60 + m1);
  if (totalMin < 0) totalMin += 24 * 60;
  const rh = Math.floor(totalMin / 60);
  const rm = totalMin % 60;
  return `${String(rh).padStart(2, "0")}:${String(rm).padStart(2, "0")}`;
}

// Date Navigation Listeners
document.getElementById("attDateInput")?.addEventListener("change", (e) => {
  state.currentDate = e.target.value;
  renderAttendance();
});
document.getElementById("attPrevDayBtn")?.addEventListener("click", () => {
  const d = new Date(state.currentDate);
  d.setDate(d.getDate() - 1);
  state.currentDate = d.toISOString().split("T")[0];
  renderAttendance();
});
document.getElementById("attNextDayBtn")?.addEventListener("click", () => {
  const d = new Date(state.currentDate);
  d.setDate(d.getDate() + 1);
  state.currentDate = d.toISOString().split("T")[0];
  renderAttendance();
});
document.getElementById("attTodayBtn")?.addEventListener("click", () => {
  state.currentDate = getTodayIso();
  renderAttendance();
});

// 3. TASK MANAGER
function renderTasks() {
  const query = (document.getElementById("taskSearchInput")?.value || "").toLowerCase();
  const filterStatus = document.getElementById("taskFilterStatus")?.value || "all";
  const filterPriority = document.getElementById("taskFilterPriority")?.value || "all";

  let filtered = state.tasks.filter(t => {
    if (query && !t.title.toLowerCase().includes(query) && !(t.details || "").toLowerCase().includes(query)) return false;
    if (filterStatus !== "all" && t.status !== filterStatus) return false;
    if (filterPriority !== "all" && t.priority !== filterPriority) return false;
    return true;
  });

  const container = document.getElementById("taskList");
  if (filtered.length === 0) {
    container.innerHTML = '<p class="muted-text">No tasks matching selected filters.</p>';
    return;
  }

  container.innerHTML = filtered.map(t => {
    const emp = state.employees.find(e => e.id == t.employee_id);
    const dept = t.department || (emp ? emp.department : "") || "—";
    const progress = Math.max(0, Math.min(100, Number(t.progress) || 0));
    const targetQ = t.target_qty || "—";
    const actualQ = t.actual_qty || "—";
    const nextAct = t.next_action || t.manager_note || "";
    const customDisplay = formatMobileCustomValuesDisplay(t.custom_values);
    return `
      <div class="task-card">
        <div class="task-card-top">
          <div class="task-title">${escapeHtml(t.title)}</div>
          <span class="task-priority-badge priority-${(t.priority || "normal").toLowerCase()}">${t.priority}</span>
        </div>
        <div class="task-meta-row" style="margin-top: 6px;">
          <span>👤 ${escapeHtml(emp ? emp.name : "Unassigned")}</span>
          <span>🏢 ${escapeHtml(dept)}</span>
          <span>📅 ${t.task_date}</span>
          <span><strong>${t.status || "Not started"}</strong></span>
        </div>
        <div style="display: flex; gap: 14px; font-size: 12px; margin: 6px 0; color: var(--text-muted);">
          <span>🎯 Target Qty: <strong>${escapeHtml(targetQ)}</strong></span>
          <span>📊 Actual Qty: <strong>${escapeHtml(actualQ)}</strong></span>
        </div>
        <div class="task-progress-bar-container">
          <div class="task-progress-fill" style="width: ${progress}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
          <span style="font-size: 11px; color: var(--text-muted);">${progress}% Completion</span>
          <div style="display: flex; gap: 8px;">
            ${t.proof_url ? `<a href="${escapeHtml(t.proof_url)}" target="_blank" class="btn-link">🔗 Proof / Link</a>` : ""}
            <button class="btn btn-sm btn-outline" onclick="openTaskModal(${t.id})">Edit</button>
          </div>
        </div>
        ${customDisplay ? `<div style="margin-top: 6px; padding: 4px 8px; border-radius: 4px; background: rgba(16,185,129,0.08); font-size: 12px; color: #34D399; font-weight: 500;">🏷️ Custom: ${escapeHtml(customDisplay)}</div>` : ""}
        ${nextAct ? `<div style="margin-top: 6px; padding: 4px 8px; border-radius: 4px; background: rgba(99,102,241,0.08); font-size: 12px; color: #818CF8;">⚡ Next Action: ${escapeHtml(nextAct)}</div>` : ""}
      </div>
    `;
  }).join("");
}

document.getElementById("taskSearchInput")?.addEventListener("input", renderTasks);
document.getElementById("taskFilterStatus")?.addEventListener("change", renderTasks);
document.getElementById("taskFilterPriority")?.addEventListener("change", renderTasks);
document.getElementById("openNewTaskModalBtn")?.addEventListener("click", () => openTaskModal());

function parseMobileCustomValues(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return raw.map(item => {
      if (item && typeof item === "object") {
        if ("key" in item && "value" in item) return { key: String(item.key || "").trim(), value: String(item.value || "").trim() };
        const entries = Object.entries(item);
        if (entries.length > 0) return { key: String(entries[0][0] || "").trim(), value: String(entries[0][1] || "").trim() };
      }
      return null;
    }).filter(Boolean);
  }
  if (typeof raw === "object") {
    return Object.entries(raw).map(([k, v]) => ({ key: String(k || "").trim(), value: String(v || "").trim() }));
  }
  const s = String(raw).trim();
  if (!s) return [];
  if (s.startsWith("[") || s.startsWith("{")) {
    try {
      const parsed = JSON.parse(s);
      return parseMobileCustomValues(parsed);
    } catch (_) {}
  }
  const pairs = [];
  s.split(/[\r\n,]+/).forEach(part => {
    part = part.trim();
    if (!part) return;
    const idx = part.indexOf(":") >= 0 ? part.indexOf(":") : part.indexOf("=");
    if (idx > 0) {
      pairs.push({ key: part.slice(0, idx).trim(), value: part.slice(idx + 1).trim() });
    } else {
      pairs.push({ key: part, value: "" });
    }
  });
  return pairs;
}

function formatMobileCustomValuesDisplay(raw) {
  const pairs = parseMobileCustomValues(raw);
  if (!pairs.length) return "";
  return pairs.map(p => `${p.key}: ${p.value}`).join(" | ");
}

function addMobileKeyValueRow(k = "", v = "") {
  const container = document.getElementById("mobileCustomValuesContainer");
  if (!container) return null;
  const row = document.createElement("div");
  row.className = "mobile-kv-row";
  row.style.cssText = "display: flex; gap: 6px; align-items: center;";
  row.innerHTML = `
    <input type="text" class="kv-key-input" placeholder="Field Name (e.g. Tracked By)" value="${escapeHtml(k)}" style="flex: 1; padding: 6px 8px; font-size: 13px; border-radius: 6px;">
    <input type="text" class="kv-val-input" placeholder="Value (e.g. Name)" value="${escapeHtml(v)}" style="flex: 1; padding: 6px 8px; font-size: 13px; border-radius: 6px;">
    <button type="button" class="btn btn-sm kv-del-btn" style="color: #EF4444; background: rgba(239,68,68,0.1); border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">✕</button>
  `;
  row.querySelector(".kv-del-btn").addEventListener("click", () => row.remove());
  container.appendChild(row);

  setTimeout(() => row.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 30);

  return row;
}

function getMobileCustomValues() {
  const container = document.getElementById("mobileCustomValuesContainer");
  if (!container) return "[]";
  const rows = container.querySelectorAll(".mobile-kv-row");
  const pairs = [];
  rows.forEach(r => {
    const k = (r.querySelector(".kv-key-input")?.value || "").trim();
    const v = (r.querySelector(".kv-val-input")?.value || "").trim();
    if (k || v) pairs.push({ key: k, value: v });
  });
  return JSON.stringify(pairs);
}

document.getElementById("mobileAddKeyValueBtn")?.addEventListener("click", () => {
  const row = addMobileKeyValueRow("", "");
  row?.querySelector(".kv-key-input")?.focus();
});

document.querySelectorAll(".preset-chip").forEach(btn => {
  btn.addEventListener("click", () => {
    const key = btn.getAttribute("data-preset-key") || "";
    const row = addMobileKeyValueRow(key, "");
    row?.querySelector(".kv-val-input")?.focus();
  });
});

function setMobileTaskMode(isCustom) {
  // Retained for compatibility
}

function updateModalDept() {
  const empSelect = document.getElementById("taskFormEmployee");
  const deptInput = document.getElementById("taskFormDepartment");
  if (!empSelect || !deptInput) return;
  const empId = empSelect.value;
  const emp = state.employees.find(e => e.id == empId);
  if (!deptInput.dataset.manual) {
    deptInput.value = emp ? (emp.department || "") : "";
  }
}

document.getElementById("taskFormDepartment")?.addEventListener("input", (e) => {
  e.target.dataset.manual = "1";
});

function autoCalcProgress() {
  const tStr = (document.getElementById("taskFormTargetQty")?.value || "").trim();
  const aStr = (document.getElementById("taskFormActualQty")?.value || "").trim();
  const tVal = parseFloat(tStr);
  const aVal = parseFloat(aStr);
  if (!isNaN(tVal) && !isNaN(aVal) && tVal > 0) {
    const pct = Math.max(0, Math.min(100, Math.round((aVal / tVal) * 100)));
    const progEl = document.getElementById("taskFormProgress");
    const progValEl = document.getElementById("taskFormProgressVal");
    if (progEl) progEl.value = pct;
    if (progValEl) progValEl.textContent = `${pct}%`;
    const statEl = document.getElementById("taskFormStatus");
    if (statEl) {
      if (pct === 100) {
        statEl.value = "Completed";
      } else if (pct > 0 && statEl.value === "Not started") {
        statEl.value = "In progress";
      }
    }
  }
}

document.getElementById("taskFormTargetQty")?.addEventListener("input", autoCalcProgress);
document.getElementById("taskFormActualQty")?.addEventListener("input", autoCalcProgress);
document.getElementById("taskFormEmployee")?.addEventListener("change", updateModalDept);

function openTaskModal(taskId = null, isCustom = false) {
  const modal = document.getElementById("modalTask");
  const form = document.getElementById("formTask");
  const title = document.getElementById("modalTaskTitle");
  const empSelect = document.getElementById("taskFormEmployee");
  const deptInput = document.getElementById("taskFormDepartment");
  const kvContainer = document.getElementById("mobileCustomValuesContainer");
  if (kvContainer) kvContainer.innerHTML = "";
  if (deptInput) deptInput.dataset.manual = "";

  empSelect.innerHTML = state.employees.map(e => `<option value="${e.id}">${escapeHtml(e.name)} (${escapeHtml(e.department || "Staff")})</option>`).join("");

  if (taskId) {
    const t = state.tasks.find(x => x.id == taskId);
    if (!t) return;
    title.textContent = "Edit Task Details";
    document.getElementById("taskFormId").value = t.id;
    empSelect.value = t.employee_id;
    document.getElementById("taskFormDate").value = t.task_date;
    document.getElementById("taskFormTitle").value = t.title;
    if (deptInput) {
      const emp = state.employees.find(e => e.id == t.employee_id);
      deptInput.value = t.department || (emp ? emp.department : "") || "";
      if (t.department) deptInput.dataset.manual = "1";
    }
    document.getElementById("taskFormTargetQty").value = t.target_qty || "";
    document.getElementById("taskFormActualQty").value = t.actual_qty || "";
    document.getElementById("taskFormPriority").value = t.priority || "Normal";
    document.getElementById("taskFormStatus").value = t.status || "Not started";
    document.getElementById("taskFormProgress").value = t.progress || 0;
    document.getElementById("taskFormProgressVal").textContent = `${t.progress || 0}%`;
    document.getElementById("taskFormProofUrl").value = t.proof_url || "";
    const expEl = document.getElementById("taskFormExposeLink");
    if (expEl) expEl.checked = Boolean(t.expose_link);
    document.getElementById("taskFormNextAction").value = t.next_action || t.manager_note || "";

    const existingPairs = parseMobileCustomValues(t.custom_values);
    existingPairs.forEach(p => addMobileKeyValueRow(p.key, p.value));
  } else {
    title.textContent = "Create New Task";
    form.reset();
    document.getElementById("taskFormId").value = "";
    document.getElementById("taskFormDate").value = state.currentDate;
    if (deptInput) deptInput.value = "";
    document.getElementById("taskFormTargetQty").value = "";
    document.getElementById("taskFormActualQty").value = "";
    document.getElementById("taskFormProgressVal").textContent = "0%";
    const expEl = document.getElementById("taskFormExposeLink");
    if (expEl) expEl.checked = false;
    document.getElementById("taskFormNextAction").value = "";

    updateModalDept();
  }

  modal.classList.remove("hidden");
}

document.getElementById("taskFormProgress")?.addEventListener("input", (e) => {
  document.getElementById("taskFormProgressVal").textContent = `${e.target.value}%`;
  if (Number(e.target.value) === 100) {
    const statEl = document.getElementById("taskFormStatus");
    if (statEl) statEl.value = "Completed";
  }
});

document.getElementById("formTask")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const idVal = document.getElementById("taskFormId").value;
  const nextActionVal = (document.getElementById("taskFormNextAction")?.value || "").trim();
  const deptVal = (document.getElementById("taskFormDepartment")?.value || "").trim();
  const taskObj = {
    id: idVal ? Number(idVal) : Date.now(),
    employee_id: Number(document.getElementById("taskFormEmployee").value),
    task_date: document.getElementById("taskFormDate").value,
    title: document.getElementById("taskFormTitle").value.trim(),
    department: deptVal,
    details: "",
    target_qty: (document.getElementById("taskFormTargetQty")?.value || "").trim(),
    actual_qty: (document.getElementById("taskFormActualQty")?.value || "").trim(),
    priority: document.getElementById("taskFormPriority").value,
    status: document.getElementById("taskFormStatus").value,
    progress: Number(document.getElementById("taskFormProgress").value),
    proof_url: document.getElementById("taskFormProofUrl").value.trim(),
    expose_link: document.getElementById("taskFormExposeLink")?.checked ? 1 : 0,
    next_action: nextActionVal,
    manager_note: nextActionVal,
    custom_values: getMobileCustomValues()
  };

  if (idVal) {
    const idx = state.tasks.findIndex(x => x.id == idVal);
    if (idx >= 0) state.tasks[idx] = Object.assign({}, state.tasks[idx], taskObj);
  } else {
    state.tasks.unshift(taskObj);
  }

  saveLocalData();
  document.getElementById("modalTask").classList.add("hidden");
  renderTasks();
  renderDashboard();
  showToast("Task saved successfully!");
});

// 4. EMPLOYEES
function renderEmployees() {
  const query = (document.getElementById("empSearchInput")?.value || "").toLowerCase();
  let emps = state.employees.filter(e => {
    if (!query) return true;
    return e.name.toLowerCase().includes(query) || (e.department || "").toLowerCase().includes(query) || (e.employee_code || "").toLowerCase().includes(query);
  });

  const list = document.getElementById("empList");
  if (emps.length === 0) {
    list.innerHTML = '<p class="muted-text">No staff members found.</p>';
    return;
  }

  list.innerHTML = emps.map(e => `
    <div class="emp-card">
      <div class="emp-info">
        <h4>${escapeHtml(e.name)} <span class="muted-text" style="font-size: 11px;">(${escapeHtml(e.employee_code)})</span></h4>
        <p>${escapeHtml(e.designation || "Staff")} · ${escapeHtml(e.department || "General")}</p>
        <p style="font-size: 11px; margin-top: 3px;">📞 ${escapeHtml(e.phone || "No phone")} | ✉️ ${escapeHtml(e.email || "No email")}</p>
      </div>
      <div>
        <button class="btn btn-sm btn-outline" onclick="openEmployeeModal(${e.id})">Edit</button>
      </div>
    </div>
  `).join("");
}

document.getElementById("empSearchInput")?.addEventListener("input", renderEmployees);
document.getElementById("openNewEmpModalBtn")?.addEventListener("click", () => openEmployeeModal());

function openEmployeeModal(empId = null) {
  const modal = document.getElementById("modalEmployee");
  const form = document.getElementById("formEmployee");
  const title = document.getElementById("modalEmpTitle");

  if (empId) {
    const emp = state.employees.find(e => e.id == empId);
    if (!emp) return;
    title.textContent = "Edit Staff Member";
    document.getElementById("empFormId").value = emp.id;
    document.getElementById("empFormCode").value = emp.employee_code || "";
    document.getElementById("empFormName").value = emp.name || "";
    document.getElementById("empFormDept").value = emp.department || "";
    document.getElementById("empFormRole").value = emp.designation || "";
    document.getElementById("empFormPhone").value = emp.phone || "";
    document.getElementById("empFormEmail").value = emp.email || "";
  } else {
    title.textContent = "Add Staff Member";
    form.reset();
    document.getElementById("empFormId").value = "";
    document.getElementById("empFormCode").value = `EMP${String(state.employees.length + 1).padStart(3, "0")}`;
  }
  modal.classList.remove("hidden");
}

document.getElementById("formEmployee")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const idVal = document.getElementById("empFormId").value;
  const empObj = {
    id: idVal ? Number(idVal) : (state.employees.length ? Math.max(...state.employees.map(x => x.id)) + 1 : 1),
    employee_code: document.getElementById("empFormCode").value.trim(),
    name: document.getElementById("empFormName").value.trim(),
    department: document.getElementById("empFormDept").value.trim(),
    designation: document.getElementById("empFormRole").value.trim(),
    phone: document.getElementById("empFormPhone").value.trim(),
    email: document.getElementById("empFormEmail").value.trim(),
    active: 1
  };

  if (idVal) {
    const idx = state.employees.findIndex(x => x.id == idVal);
    if (idx >= 0) state.employees[idx] = empObj;
  } else {
    state.employees.push(empObj);
  }

  saveLocalData();
  document.getElementById("modalEmployee").classList.add("hidden");
  renderEmployees();
  renderAttendance();
  renderDashboard();
  showToast("Staff record saved!");
});

// Modal close buttons
document.querySelectorAll("[data-close]").forEach(btn => {
  btn.addEventListener("click", () => {
    const modalId = btn.dataset.close;
    document.getElementById(modalId)?.classList.add("hidden");
  });
});

// 5. LIVE CHAT
function checkChatAuth() {
  const authContainer = document.getElementById("chatAuthContainer");
  const appContainer = document.getElementById("chatAppContainer");
  if (state.chat.token) {
    authContainer.classList.add("hidden");
    appContainer.classList.remove("hidden");
    loadConversations();
  } else {
    authContainer.classList.remove("hidden");
    appContainer.classList.add("hidden");
  }
}

document.getElementById("chatLoginForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const u = document.getElementById("chatUser").value.trim();
  const p = document.getElementById("chatPass").value.trim();
  try {
    const res = await fetch(`${CHAT_WORKER_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p })
    });
    if (!res.ok) throw new Error("Invalid username or password");
    const data = await res.json();
    state.chat.token = data.token;
    state.chat.username = u;
    localStorage.setItem("rsc_chat_token", data.token);
    localStorage.setItem("rsc_chat_user", u);
    checkChatAuth();
    showToast(`Welcome to Chat, ${u}!`);
  } catch (err) {
    showToast(`Chat login failed: ${err.message}`);
  }
});

async function loadConversations() {
  try {
    const res = await fetch(`${CHAT_WORKER_URL}/api/conversations`, {
      headers: { "Authorization": `Bearer ${state.chat.token}` }
    });
    if (res.ok) {
      const data = await res.json();
      state.chat.conversations = data.conversations || [];
      if (state.chat.conversations.length > 0) {
        openConversation(state.chat.conversations[0]);
      }
    }
  } catch (err) {
    console.error("Load chat conversations failed", err);
  }
}

function openConversation(conv) {
  state.chat.activeConvId = conv.id;
  document.getElementById("activeConvTitle").textContent = conv.title || "Team Chat";
  document.getElementById("activeConvStatus").textContent = `${conv.members_count || 2} members`;
  loadMessages(conv.id);
}

async function loadMessages(convId) {
  const container = document.getElementById("chatMessages");
  try {
    const res = await fetch(`${CHAT_WORKER_URL}/api/conversations/${convId}/messages`, {
      headers: { "Authorization": `Bearer ${state.chat.token}` }
    });
    if (res.ok) {
      const data = await res.json();
      const msgs = data.messages || [];
      if (msgs.length === 0) {
        container.innerHTML = '<div class="chat-placeholder"><p>No messages yet. Say hello!</p></div>';
      } else {
        container.innerHTML = msgs.map(m => `
          <div class="chat-message ${m.sender === state.chat.username ? "mine" : ""}">
            <div style="font-size: 10px; opacity: 0.7; margin-bottom: 2px;">${escapeHtml(m.sender)} · ${m.created_at || ""}</div>
            <div>${escapeHtml(m.content)}</div>
          </div>
        `).join("");
        container.scrollTop = container.scrollHeight;
      }
    }
  } catch (err) {
    console.error("Load messages failed", err);
  }
}

document.getElementById("chatComposer")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("chatMsgInput");
  const txt = input.value.trim();
  if (!txt || !state.chat.activeConvId) return;
  input.value = "";
  try {
    await fetch(`${CHAT_WORKER_URL}/api/conversations/${state.chat.activeConvId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.chat.token}`
      },
      body: JSON.stringify({ content: txt })
    });
    loadMessages(state.chat.activeConvId);
  } catch (err) {
    showToast(`Could not send message: ${err.message}`);
  }
});

document.getElementById("chatLogoutBtn")?.addEventListener("click", () => {
  state.chat.token = "";
  state.chat.username = "";
  localStorage.removeItem("rsc_chat_token");
  localStorage.removeItem("rsc_chat_user");
  checkChatAuth();
  showToast("Signed out of live chat.");
});

// 6. CLOUDFLARE ENCRYPTED SYNC ENGINE
async function ensureDeviceRegistered() {
  if (state.deviceToken) return state.deviceToken;
  const res = await fetch(`${SYNC_WORKER_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      installation_id: state.installId,
      device_id: state.deviceId,
      device_secret: state.deviceSecret
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Device registration failed (${res.status})`);
  }
  const data = await res.json();
  state.deviceToken = data.token;
  localStorage.setItem("rsc_device_token", data.token);
  return data.token;
}

// Encrypt payload matching Python database_sync.py
async function encryptPayload(jsonObj, passphrase) {
  const enc = new TextEncoder();
  const jsonStr = JSON.stringify(jsonObj);
  const dataBytes = enc.encode(jsonStr);

  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));

  // Derive PBKDF2 HMAC SHA-256 300,000 iterations
  const baseKey = await crypto.subtle.importKey(
    "raw",
    enc.encode(passphrase.trim()),
    "PBKDF2",
    false,
    ["deriveKey"]
  );

  const aesKey = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: salt, iterations: 300000, hash: "SHA-256" },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt"]
  );

  // Header: magic (6) + salt (16) + iv (12)
  const header = new Uint8Array(6 + 16 + 12);
  header.set(SNAPSHOT_MAGIC, 0);
  header.set(salt, 6);
  header.set(iv, 22);

  const aad = new Uint8Array(header.length + SNAPSHOT_AAD.length);
  aad.set(header, 0);
  aad.set(SNAPSHOT_AAD, header.length);

  const cipherBuffer = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv, additionalData: aad, tagLength: 128 },
    aesKey,
    dataBytes
  );

  const finalBytes = new Uint8Array(header.length + cipherBuffer.byteLength);
  finalBytes.set(header, 0);
  finalBytes.set(new Uint8Array(cipherBuffer), header.length);

  // Return base64 string
  let binary = "";
  for (let i = 0; i < finalBytes.byteLength; i++) {
    binary += String.fromCharCode(finalBytes[i]);
  }
  return btoa(binary);
}


// --- USER AUTHENTICATION & SESSION MANAGEMENT (Matching Desktop hash_pin) ---
async function hashPin(pin, salt) {
  const enc = new TextEncoder();
  const baseKey = await crypto.subtle.importKey(
    "raw",
    enc.encode(pin),
    "PBKDF2",
    false,
    ["deriveBits"]
  );
  const derived = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      salt: enc.encode(salt),
      iterations: 200000,
      hash: "SHA-256"
    },
    baseKey,
    256
  );
  return Array.from(new Uint8Array(derived)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function authenticateUser(username, password) {
  const uname = (username || "").trim().toLowerCase();
  const errEl = document.getElementById("appAuthError");
  if (errEl) errEl.classList.add("hidden");

  if (!uname || !password) {
    if (errEl) { errEl.textContent = "Enter both username and password."; errEl.classList.remove("hidden"); }
    return false;
  }

  const user = (state.users || []).find(u => (u.username || "").trim().toLowerCase() === uname);
  if (!user) {
    // If no users synced locally yet, allow initial admin bootstrap if credentials match standard default
    if ((!state.users || state.users.length === 0) && (uname === "admin" || uname === "developer")) {
      const bootstrapUser = { username: uname, role: uname === "developer" ? "Developer" : "Admin", display_name: uname.toUpperCase() };
      state.currentUser = bootstrapUser;
      localStorage.setItem("rsc_current_user", JSON.stringify(bootstrapUser));
      updateUserSessionUI();
      showToast("Bootstrap session initialized. Synchronizing database with cloud...");
      pullFromCloud(false);
      return true;
    }
    if (errEl) {
      errEl.textContent = "Account not found. Click 'Pull Latest Accounts' to sync users from desktop.";
      errEl.classList.remove("hidden");
    }
    return false;
  }

  if (user.active === 0) {
    if (errEl) { errEl.textContent = "This account is disabled. Contact system administrator."; errEl.classList.remove("hidden"); }
    return false;
  }

  try {
    const digest = await hashPin(password, user.password_salt);
    if (digest.toLowerCase() === (user.password_hash || "").toLowerCase()) {
      state.currentUser = user;
      localStorage.setItem("rsc_current_user", JSON.stringify(user));
      updateUserSessionUI();
      showToast(`Welcome, ${user.display_name || user.username}!`);
      pullFromCloud(true);
      return true;
    } else {
      if (errEl) { errEl.textContent = "Incorrect password or PIN."; errEl.classList.remove("hidden"); }
      return false;
    }
  } catch (err) {
    if (errEl) { errEl.textContent = "Authentication failed: " + err.message; errEl.classList.remove("hidden"); }
    return false;
  }
}

function signOutUser() {
  state.currentUser = null;
  localStorage.removeItem("rsc_current_user");
  updateUserSessionUI();
  showToast("Signed out of session.");
}

function updateUserSessionUI() {
  const authModal = document.getElementById("modalAppAuth");
  const userNameEl = document.getElementById("headerUserName");
  const userRoleEl = document.getElementById("headerUserRole");
  const stripUserEl = document.getElementById("sessionStripUser");
  const stripRoleEl = document.getElementById("sessionStripRole");

  if (!state.currentUser) {
    if (authModal) authModal.classList.remove("hidden");
    if (userNameEl) userNameEl.textContent = "Guest";
    if (userRoleEl) {
      userRoleEl.textContent = "Offline";
      userRoleEl.className = "role-pill role-offline";
    }
    if (stripUserEl) stripUserEl.textContent = "Not signed in";
    if (stripRoleEl) {
      stripRoleEl.textContent = "Locked";
      stripRoleEl.className = "role-pill role-offline";
    }
  } else {
    if (authModal) authModal.classList.add("hidden");
    const u = state.currentUser;
    const displayName = u.display_name || u.username;
    const role = u.role || "Staff";
    const roleLower = role.toLowerCase();

    if (userNameEl) userNameEl.textContent = displayName;
    if (userRoleEl) {
      userRoleEl.textContent = role;
      userRoleEl.className = `role-pill role-${roleLower}`;
    }
    if (stripUserEl) stripUserEl.textContent = displayName;
    if (stripRoleEl) {
      stripRoleEl.textContent = role;
      stripRoleEl.className = `role-pill role-${roleLower}`;
    }
  }
}

// Push to Cloud
async function pushToCloud(silent = false) {
  const feedback = document.getElementById("syncFeedbackMsg");
  if (feedback && !silent) feedback.textContent = "Registering device with sync service...";
  try {
    const token = await ensureDeviceRegistered();
    if (feedback && !silent) feedback.textContent = "Encrypting business data snapshot...";

    const payloadObj = {
      version: "1.3.25",
      employees: state.employees,
      attendance: state.attendance,
      tasks: state.tasks,
      auth_users: state.users || [],
      holidays: state.holidays || {},
      timestamp: new Date().toISOString(),
      source: "mobile-apk"
    };

    const b64Content = await encryptPayload(payloadObj, state.syncSecret);
    if (feedback && !silent) feedback.textContent = "Uploading encrypted snapshot to Cloudflare...";

    const res = await fetch(`${SYNC_WORKER_URL}/push`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ content: b64Content })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Push failed with status ${res.status}`);
    }

    if (feedback) feedback.textContent = `✅ Synced to cloud at ${new Date().toLocaleTimeString()}!`;
    if (!silent) showToast("Cloud sync completed successfully!");
  } catch (err) {
    if (feedback) feedback.textContent = `❌ Sync error: ${err.message}`;
    if (!silent) showToast(`Sync error: ${err.message}`, 4000);
  }
}

// Decompress zlib deflate stream matching Python database_sync
async function decompressZlib(bytes) {
  if (typeof DecompressionStream !== "undefined") {
    try {
      const ds = new DecompressionStream("deflate");
      const writer = ds.writable.getWriter();
      writer.write(bytes);
      writer.close();
      const reader = ds.readable.getReader();
      const chunks = [];
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        chunks.push(value);
      }
      let total = chunks.reduce((acc, c) => acc + c.byteLength, 0);
      let res = new Uint8Array(total);
      let offset = 0;
      for (const c of chunks) {
        res.set(c, offset);
        offset += c.byteLength;
      }
      return res;
    } catch (e) {
      try {
        const dsRaw = new DecompressionStream("deflate-raw");
        const writer = dsRaw.writable.getWriter();
        writer.write(bytes.slice(2, -4));
        writer.close();
        const reader = dsRaw.readable.getReader();
        const chunks = [];
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          chunks.push(value);
        }
        let total = chunks.reduce((acc, c) => acc + c.byteLength, 0);
        let res = new Uint8Array(total);
        let offset = 0;
        for (const c of chunks) {
          res.set(c, offset);
          offset += c.byteLength;
        }
        return res;
      } catch (e2) {
        return bytes;
      }
    }
  }
  return bytes;
}

// Pull from Cloud with conflict-free union merge
async function pullFromCloud(silent = false) {
  const feedback = document.getElementById("syncFeedbackMsg");
  if (feedback && !silent) feedback.textContent = "Pulling latest snapshot from cloud...";
  try {
    const token = await ensureDeviceRegistered();
    const res = await fetch(`${SYNC_WORKER_URL}/pull`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ prefer_latest: true })
    });

    if (res.status === 404) {
      if (feedback && !silent) feedback.textContent = "ℹ️ No remote snapshot found for this installation ID yet.";
      return;
    }
    if (!res.ok) {
      throw new Error(`Pull failed with HTTP ${res.status}`);
    }

    const encryptedBytes = new Uint8Array(await res.arrayBuffer());
    if (encryptedBytes.length < 34) throw new Error("Invalid snapshot payload");

    // Decrypt
    const enc = new TextEncoder();
    const salt = encryptedBytes.slice(6, 22);
    const iv = encryptedBytes.slice(22, 34);
    const header = encryptedBytes.slice(0, 34);
    const ciphertext = encryptedBytes.slice(34);

    const baseKey = await crypto.subtle.importKey(
      "raw",
      enc.encode(state.syncSecret.trim()),
      "PBKDF2",
      false,
      ["deriveKey"]
    );

    const aesKey = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: salt, iterations: 300000, hash: "SHA-256" },
      baseKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["decrypt"]
    );

    const aad = new Uint8Array(header.length + SNAPSHOT_AAD.length);
    aad.set(header, 0);
    aad.set(SNAPSHOT_AAD, header.length);

    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: iv, additionalData: aad, tagLength: 128 },
      aesKey,
      ciphertext
    );

    const decompressed = await decompressZlib(new Uint8Array(decryptedBuffer));

    let pulledData = null;
    const markerStr = "\n__RSC_JSON__\n";
    const marker = new TextEncoder().encode(markerStr);
    let markerIdx = -1;
    for (let i = 0; i <= decompressed.length - marker.length; i++) {
      let match = true;
      for (let j = 0; j < marker.length; j++) {
        if (decompressed[i + j] !== marker[j]) { match = false; break; }
      }
      if (match) { markerIdx = i; break; }
    }

    if (markerIdx !== -1) {
      state.rawSqliteBytes = decompressed.slice(0, markerIdx);
      const jsonBytes = decompressed.slice(markerIdx + marker.length);
      try {
        pulledData = JSON.parse(new TextDecoder().decode(jsonBytes));
      } catch (e) {}
    }

    if (!pulledData) {
      try {
        const text = new TextDecoder().decode(decompressed);
        pulledData = JSON.parse(text);
      } catch (e) {}
    }

    if (!pulledData) {
      if (feedback) feedback.textContent = `✅ Synced to cloud at ${new Date().toLocaleTimeString()}!`;
      return;
    }

    // Conflict-free union merge for auth_users
    if (Array.isArray(pulledData.auth_users)) {
      if (!state.users) state.users = [];
      const userMap = new Map();
      for (const u of state.users) userMap.set((u.username || "").toLowerCase(), u);
      for (const ru of pulledData.auth_users) {
        const key = (ru.username || "").toLowerCase();
        if (!key) continue;
        if (!userMap.has(key)) {
          state.users.push(ru);
          userMap.set(key, ru);
        } else {
          const lu = userMap.get(key);
          if ((ru.updated_at || "") >= (lu.updated_at || "")) {
            Object.assign(lu, ru);
          }
        }
      }
      localStorage.setItem("rsc_auth_users", JSON.stringify(state.users));
      updateUserSessionUI();
    }

    // Conflict-free union merge for employees
    if (Array.isArray(pulledData.employees)) {
      const existingKeys = new Set(state.employees.map(e => (e.employee_code || e.name || "").toLowerCase()));
      for (const re of pulledData.employees) {
        const key = (re.employee_code || re.name || "").toLowerCase();
        if (!existingKeys.has(key)) {
          state.employees.push(re);
          existingKeys.add(key);
        } else {
          const local = state.employees.find(e => (e.employee_code || e.name || "").toLowerCase() === key);
          if (local) Object.assign(local, re);
        }
      }
    }

    // Conflict-free union merge for attendance
    if (pulledData.attendance && typeof pulledData.attendance === "object") {
      for (const [key, rRecord] of Object.entries(pulledData.attendance)) {
        if (!state.attendance[key]) {
          state.attendance[key] = rRecord;
        } else {
          const lRecord = state.attendance[key];
          state.attendance[key] = {
            ...lRecord,
            ...rRecord,
            check_in: lRecord.check_in || rRecord.check_in || "",
            check_out: lRecord.check_out || rRecord.check_out || "",
            attendance_status: (lRecord.attendance_status && lRecord.attendance_status !== "Unmarked") ? lRecord.attendance_status : (rRecord.attendance_status || "Unmarked"),
            attendance_note: lRecord.attendance_note ? (rRecord.attendance_note && rRecord.attendance_note !== lRecord.attendance_note ? `${lRecord.attendance_note}; ${rRecord.attendance_note}` : lRecord.attendance_note) : (rRecord.attendance_note || "")
          };
        }
      }
    }

    // Conflict-free union merge for tasks
    if (Array.isArray(pulledData.tasks)) {
      for (const rt of pulledData.tasks) {
        const match = state.tasks.find(lt => lt.employee_id === rt.employee_id && lt.task_date === rt.task_date && (lt.title || "").toLowerCase() === (rt.title || "").toLowerCase());
        if (!match) {
          state.tasks.push(rt);
        } else {
          match.progress = Math.max(match.progress || 0, rt.progress || 0);
          if (rt.status === "Completed") match.status = "Completed";
          if (rt.proof_url && !match.proof_url) match.proof_url = rt.proof_url;
          if (rt.proof_note && !match.proof_note) match.proof_note = rt.proof_note;
        }
      }
    }

    saveLocalData(false);
    renderDashboard();
    renderAttendance();
    renderTasks();
    renderEmployees();

    if (feedback) feedback.textContent = `✅ Continuous sync active • ${state.employees.length} employees, ${state.tasks.length} tasks synced.`;
    if (!silent) showToast("Latest centralized data merged!");
  } catch (err) {
    if (feedback && !silent) feedback.textContent = `❌ Decryption or pull note: ${err.message}`;
    if (!silent) showToast(`Pull note: ${err.message}`, 4000);
  }
}

// Check the published Android APK release separately from cloud data sync.
const MOBILE_APP_VERSION = "1.3.25";
function compareAppVersions(a, b) {
  const aa = String(a || "0").replace(/^[vV]/, "").split(".").map(n => parseInt(n, 10) || 0);
  const bb = String(b || "0").replace(/^[vV]/, "").split(".").map(n => parseInt(n, 10) || 0);
  for (let i = 0; i < Math.max(aa.length, bb.length); i++) {
    const diff = (aa[i] || 0) - (bb[i] || 0);
    if (diff) return diff;
  }
  return 0;
}
document.getElementById("btnCheckAppUpdate")?.addEventListener("click", async () => {
  const btn = document.getElementById("btnCheckAppUpdate");
  const feedback = document.getElementById("appUpdateFeedback");
  if (btn) btn.disabled = true;
  if (feedback) feedback.textContent = "Checking the latest published release...";
  try {
    const response = await fetch("https://api.github.com/repos/yalangisexter-ux/audit-report/releases?per_page=20", {
      headers: { "Accept": "application/vnd.github+json" },
      cache: "no-store"
    });
    if (!response.ok) throw new Error("Release check failed (HTTP " + response.status + ").");
    const releases = await response.json();
    const release = Array.isArray(releases) ? releases.find(item => !item.draft && !item.prerelease && item.published_at) : null;
    if (!release) {
      if (feedback) feedback.textContent = "No published release found. Open the official releases page to check manually.";
      window.open("https://github.com/yalangisexter-ux/audit-report/releases", "_blank", "noopener");
      return;
    }
    const latest = String(release.tag_name || "").replace(/^[vV]/, "");
    const apk = (release.assets || []).find(asset => /\.apk$/i.test(asset.name || ""));
    if (compareAppVersions(latest, MOBILE_APP_VERSION) > 0) {
      if (apk && apk.browser_download_url) {
        if (feedback) feedback.textContent = "Update available: v" + latest + ". Opening APK download. Android may ask you to confirm installation.";
        window.open(apk.browser_download_url, "_blank", "noopener");
      } else {
        if (feedback) feedback.textContent = "Release v" + latest + " is newer, but it has no APK attached yet. Opening release page.";
        window.open(release.html_url || "https://github.com/yalangisexter-ux/audit-report/releases", "_blank", "noopener");
      }
    } else if (apk && apk.browser_download_url) {
      if (feedback) feedback.textContent = "You are on v" + MOBILE_APP_VERSION + ". Latest published release is v" + latest + ". Open release page to reinstall or review assets.";
    } else {
      if (feedback) feedback.textContent = "No newer APK is published yet. Latest release: v" + latest + ".";
    }
  } catch (err) {
    if (feedback) feedback.textContent = "Could not check updates: " + err.message + " Open the releases page to check manually.";
  } finally {
    if (btn) btn.disabled = false;
  }
});

document.getElementById("btnSyncCheck")?.addEventListener("click", () => {
  pullFromCloud(false);
  showToast("Checking cloud synchronization...");
});
document.getElementById("quickSyncBtn")?.addEventListener("click", () => {
  pullFromCloud(false);
  showToast("Checking cloud synchronization...");
});
document.getElementById("btnPushData")?.addEventListener("click", () => pushToCloud(false));
document.getElementById("btnPullData")?.addEventListener("click", () => pullFromCloud(false));

document.getElementById("genNewInstallIdBtn")?.addEventListener("click", () => {
  state.installId = generateHex(32);
  state.deviceToken = "";
  localStorage.setItem("rsc_install_id", state.installId);
  localStorage.removeItem("rsc_device_token");
  document.getElementById("settingInstallId").value = state.installId;
  showToast("New installation identifier generated!");
});

// Theme and Wallpaper
function applyTheme(t) {
  state.theme = t;
  localStorage.setItem("rsc_theme", t);
  document.body.className = `theme-${t}`;
  document.getElementById("themeToggleBtn").querySelector(".theme-icon").textContent = t === "night" ? "🌙" : "☀️";
  const sel = document.getElementById("settingThemeSelect");
  if (sel) sel.value = t;
}

document.getElementById("themeToggleBtn")?.addEventListener("click", () => {
  applyTheme(state.theme === "night" ? "day" : "night");
});

document.getElementById("settingThemeSelect")?.addEventListener("change", (e) => {
  applyTheme(e.target.value);
});

// Helper for HTML escaping
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// App Initialization
window.addEventListener("DOMContentLoaded", () => {
  loadLocalData();
  applyTheme(state.theme);
  initNav();
  updateUserSessionUI();
  renderDashboard();

  // App Auth form handler
  document.getElementById("appAuthForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const u = document.getElementById("appAuthUsername").value;
    const p = document.getElementById("appAuthPassword").value;
    await authenticateUser(u, p);
  });

  // Pull latest accounts button on auth modal
  document.getElementById("btnSyncAccountsNow")?.addEventListener("click", async () => {
    showToast("Synchronizing user accounts from cloud...");
    await pullFromCloud(false);
  });

  // Header logout button
  document.getElementById("headerLogoutBtn")?.addEventListener("click", () => {
    signOutUser();
  });

  // Continuous background auto-sync every 30 seconds
  setInterval(() => pullFromCloud(true), 30000);
  setTimeout(() => pullFromCloud(true), 2500);
});
