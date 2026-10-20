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
  wallpaper: localStorage.getItem("rsc_wallpaper") || "Ambient Glow",
  installId: localStorage.getItem("rsc_install_id") || "00000000000000000000000000000001",
  syncSecret: localStorage.getItem("rsc_sync_secret") || "Devlopershouse@1996#",
  deviceToken: localStorage.getItem("rsc_device_token") || "",
  deviceId: localStorage.getItem("rsc_device_id") || generateHex(32),
  deviceSecret: localStorage.getItem("rsc_device_secret") || generateHex(48),
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

  // If no employees, provide demo initial team
  if (!state.employees || state.employees.length === 0) {
    state.employees = [
      { id: 1, employee_code: "EMP001", name: "Alex Hunter", department: "Calisthenics", designation: "Head Trainer", phone: "+91 98765 43210", email: "alex@rawstrength.com", active: 1 },
      { id: 2, employee_code: "EMP002", name: "Sara Connor", department: "Operations", designation: "Floor Manager", phone: "+91 98765 43211", email: "sara@rawstrength.com", active: 1 },
      { id: 3, employee_code: "EMP003", name: "David Miller", department: "Training", designation: "Skills Specialist", phone: "+91 98765 43212", email: "david@rawstrength.com", active: 1 }
    ];
    saveLocalData();
  }
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
    const progress = Math.max(0, Math.min(100, Number(t.progress) || 0));
    const targetQ = t.target_qty || "—";
    const actualQ = t.actual_qty || "—";
    const nextAct = t.next_action || t.manager_note || "";
    return `
      <div class="task-card">
        <div class="task-card-top">
          <div class="task-title">${escapeHtml(t.title)}</div>
          <span class="task-priority-badge priority-${(t.priority || "normal").toLowerCase()}">${t.priority}</span>
        </div>
        <div class="task-meta-row" style="margin-top: 6px;">
          <span>👤 ${escapeHtml(emp ? emp.name : "Unassigned")}</span>
          <span>🏢 ${escapeHtml(emp ? (emp.department || "General") : "—")}</span>
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
        ${nextAct ? `<div style="margin-top: 6px; padding: 4px 8px; border-radius: 4px; background: rgba(99,102,241,0.08); font-size: 12px; color: #818CF8;">⚡ Next Action: ${escapeHtml(nextAct)}</div>` : ""}
      </div>
    `;
  }).join("");
}

document.getElementById("taskSearchInput")?.addEventListener("input", renderTasks);
document.getElementById("taskFilterStatus")?.addEventListener("change", renderTasks);
document.getElementById("taskFilterPriority")?.addEventListener("change", renderTasks);
document.getElementById("openNewTaskModalBtn")?.addEventListener("click", () => openTaskModal());

function updateModalDept() {
  const empSelect = document.getElementById("taskFormEmployee");
  const deptInput = document.getElementById("taskFormDepartment");
  if (!empSelect || !deptInput) return;
  const empId = empSelect.value;
  const emp = state.employees.find(e => e.id == empId);
  deptInput.value = emp ? (emp.department || "General") : "";
}

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

function openTaskModal(taskId = null) {
  const modal = document.getElementById("modalTask");
  const form = document.getElementById("formTask");
  const title = document.getElementById("modalTaskTitle");
  const empSelect = document.getElementById("taskFormEmployee");

  empSelect.innerHTML = state.employees.map(e => `<option value="${e.id}">${escapeHtml(e.name)} (${escapeHtml(e.department || "Staff")})</option>`).join("");

  if (taskId) {
    const t = state.tasks.find(x => x.id == taskId);
    if (!t) return;
    title.textContent = "Edit Task";
    document.getElementById("taskFormId").value = t.id;
    empSelect.value = t.employee_id;
    document.getElementById("taskFormDate").value = t.task_date;
    document.getElementById("taskFormTitle").value = t.title;
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
  } else {
    title.textContent = "Add New Task";
    form.reset();
    document.getElementById("taskFormId").value = "";
    document.getElementById("taskFormDate").value = state.currentDate;
    document.getElementById("taskFormTargetQty").value = "";
    document.getElementById("taskFormActualQty").value = "";
    document.getElementById("taskFormProgressVal").textContent = "0%";
    const expEl = document.getElementById("taskFormExposeLink");
    if (expEl) expEl.checked = false;
    document.getElementById("taskFormNextAction").value = "";
  }

  updateModalDept();
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
  const taskObj = {
    id: idVal ? Number(idVal) : Date.now(),
    employee_id: Number(document.getElementById("taskFormEmployee").value),
    task_date: document.getElementById("taskFormDate").value,
    title: document.getElementById("taskFormTitle").value.trim(),
    details: "",
    target_qty: (document.getElementById("taskFormTargetQty")?.value || "").trim(),
    actual_qty: (document.getElementById("taskFormActualQty")?.value || "").trim(),
    priority: document.getElementById("taskFormPriority").value,
    status: document.getElementById("taskFormStatus").value,
    progress: Number(document.getElementById("taskFormProgress").value),
    proof_url: document.getElementById("taskFormProofUrl").value.trim(),
    expose_link: document.getElementById("taskFormExposeLink")?.checked ? 1 : 0,
    next_action: nextActionVal,
    manager_note: nextActionVal
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

// Push to Cloud
async function pushToCloud(silent = false) {
  const feedback = document.getElementById("syncFeedbackMsg");
  if (feedback && !silent) feedback.textContent = "Registering device with sync service...";
  try {
    const token = await ensureDeviceRegistered();
    if (feedback && !silent) feedback.textContent = "Encrypting business data snapshot...";

    const payloadObj = {
      version: "1.3.15",
      employees: state.employees,
      attendance: state.attendance,
      tasks: state.tasks,
      timestamp: new Date().toISOString()
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
  renderDashboard();

  // Continuous background auto-sync every 30 seconds
  setInterval(() => pullFromCloud(true), 30000);
  setTimeout(() => pullFromCloud(true), 2500);
});
