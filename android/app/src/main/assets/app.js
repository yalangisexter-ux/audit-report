/**
 * Raw Strength Calisthenics - Employee Audit Manager Mobile App
 * Synchronized with Desktop Database via Cloudflare Encrypted Sync
 * Version 1.3.12
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
function saveLocalData() {
  localStorage.setItem("rsc_employees", JSON.stringify(state.employees));
  localStorage.setItem("rsc_attendance", JSON.stringify(state.attendance));
  localStorage.setItem("rsc_tasks", JSON.stringify(state.tasks));
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
    return `
      <div class="task-card">
        <div class="task-card-top">
          <div class="task-title">${escapeHtml(t.title)}</div>
          <span class="task-priority-badge priority-${(t.priority || "normal").toLowerCase()}">${t.priority}</span>
        </div>
        ${t.details ? `<p class="muted-text" style="font-size: 13px;">${escapeHtml(t.details)}</p>` : ""}
        <div class="task-meta-row">
          <span>👤 ${escapeHtml(emp ? emp.name : "Unassigned")}</span>
          <span>📅 ${t.task_date}</span>
          <span><strong>${t.status || "Not started"}</strong></span>
        </div>
        <div class="task-progress-bar-container">
          <div class="task-progress-fill" style="width: ${progress}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
          <span style="font-size: 11px; color: var(--text-muted);">${progress}% Completed</span>
          <div style="display: flex; gap: 8px;">
            ${t.proof_url ? `<a href="${escapeHtml(t.proof_url)}" target="_blank" class="btn-link">🔗 Proof Link</a>` : ""}
            <button class="btn btn-sm btn-outline" onclick="openTaskModal(${t.id})">Edit</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

document.getElementById("taskSearchInput")?.addEventListener("input", renderTasks);
document.getElementById("taskFilterStatus")?.addEventListener("change", renderTasks);
document.getElementById("taskFilterPriority")?.addEventListener("change", renderTasks);
document.getElementById("openNewTaskModalBtn")?.addEventListener("click", () => openTaskModal());

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
    document.getElementById("taskFormDetails").value = t.details || "";
    document.getElementById("taskFormPriority").value = t.priority || "Normal";
    document.getElementById("taskFormStatus").value = t.status || "Not started";
    document.getElementById("taskFormProgress").value = t.progress || 0;
    document.getElementById("taskFormProgressVal").textContent = `${t.progress || 0}%`;
    document.getElementById("taskFormProofUrl").value = t.proof_url || "";
  } else {
    title.textContent = "Add New Task";
    form.reset();
    document.getElementById("taskFormId").value = "";
    document.getElementById("taskFormDate").value = state.currentDate;
    document.getElementById("taskFormProgressVal").textContent = "0%";
  }

  modal.classList.remove("hidden");
}

document.getElementById("taskFormProgress")?.addEventListener("input", (e) => {
  document.getElementById("taskFormProgressVal").textContent = `${e.target.value}%`;
});

document.getElementById("formTask")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const idVal = document.getElementById("taskFormId").value;
  const taskObj = {
    id: idVal ? Number(idVal) : Date.now(),
    employee_id: Number(document.getElementById("taskFormEmployee").value),
    task_date: document.getElementById("taskFormDate").value,
    title: document.getElementById("taskFormTitle").value.trim(),
    details: document.getElementById("taskFormDetails").value.trim(),
    priority: document.getElementById("taskFormPriority").value,
    status: document.getElementById("taskFormStatus").value,
    progress: Number(document.getElementById("taskFormProgress").value),
    proof_url: document.getElementById("taskFormProofUrl").value.trim()
  };

  if (idVal) {
    const idx = state.tasks.findIndex(x => x.id == idVal);
    if (idx >= 0) state.tasks[idx] = taskObj;
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
async function pushToCloud() {
  const feedback = document.getElementById("syncFeedbackMsg");
  feedback.textContent = "Registering device with sync service...";
  try {
    const token = await ensureDeviceRegistered();
    feedback.textContent = "Encrypting business data snapshot...";

    const payloadObj = {
      version: "1.3.11",
      employees: state.employees,
      attendance: state.attendance,
      tasks: state.tasks,
      timestamp: new Date().toISOString()
    };

    const b64Content = await encryptPayload(payloadObj, state.syncSecret);
    feedback.textContent = "Uploading encrypted snapshot to Cloudflare...";

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

    feedback.textContent = `✅ Synced to cloud at ${new Date().toLocaleTimeString()}!`;
    showToast("Cloud sync completed successfully!");
  } catch (err) {
    feedback.textContent = `❌ Sync error: ${err.message}`;
    showToast(`Sync error: ${err.message}`, 4000);
  }
}

// Pull from Cloud
async function pullFromCloud() {
  const feedback = document.getElementById("syncFeedbackMsg");
  feedback.textContent = "Pulling latest snapshot from cloud...";
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
      feedback.textContent = "ℹ️ No remote snapshot found for this installation ID yet.";
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

    const decrypted = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: iv, additionalData: aad, tagLength: 128 },
      aesKey,
      ciphertext
    );

    const jsonStr = new TextDecoder().decode(decrypted);
    const pulledData = JSON.parse(jsonStr);

    if (pulledData.employees) state.employees = pulledData.employees;
    if (pulledData.attendance) state.attendance = pulledData.attendance;
    if (pulledData.tasks) state.tasks = pulledData.tasks;

    saveLocalData();
    renderDashboard();
    renderAttendance();
    renderTasks();
    renderEmployees();

    feedback.textContent = `✅ Successfully pulled latest changes! Updated ${state.employees.length} employees, ${state.tasks.length} tasks.`;
    showToast("Latest data pulled and merged!");
  } catch (err) {
    feedback.textContent = `❌ Decryption or pull failed: ${err.message}`;
    showToast(`Pull failed: ${err.message}`, 4000);
  }
}

document.getElementById("btnPushData")?.addEventListener("click", pushToCloud);
document.getElementById("btnPullData")?.addEventListener("click", pullFromCloud);
document.getElementById("quickSyncBtn")?.addEventListener("click", pushToCloud);

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
});
