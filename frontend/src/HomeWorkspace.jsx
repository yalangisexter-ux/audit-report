import React from 'react';
import { UserPlus, Shield, CheckCircle2, Users, Plus } from 'lucide-react';
import { ALL_APP_MODULES as DEFAULT_MODULES, ACCESS_LEVEL_PRESETS as DEFAULT_PRESETS, ACCESS_LEVEL_OPTIONS as DEFAULT_OPTIONS } from './App';

const WORKSPACE_GUIDE = [
  ['📊', 'Dashboard', "Review today's totals, recent tasks, and employee productivity.", 'Open the dashboard to review workforce and task telemetry.', 'dashboard'],
  ['👥', 'Employees', 'Add or edit employee identity, department, job title, and optional contact details.', 'Example: Operations · Coordinator · phone and email optional.', 'employees'],
  ['✅', 'Task Manager', 'Choose a date or employee, then add, edit, or remove tasks and update evidence, status, or progress.', 'Example: Prepare daily report · In progress · 60%.', 'tasks'],
  ['📝', 'Employee Tracker', 'Choose an employee and date, then review their assigned tasks.', 'Use Task Manager for changes; this page is read-only.', 'tracker'],
  ['🟢', 'Attendance', 'Select a date to record present, absent, or leave; add check-in/out times and manage holidays.', 'Example: Present · 09:00 check-in · 17:30 check-out.', 'attendance'],
  ['🖨️', 'Print Center', 'Select a report type, date, scope, employee, and PDF, Word, or CSV format.', 'For Audit / EOD, use the section options to control included details.', 'reports'],
  ['📁', 'EOD Archive', 'Upload historical PDFs, associate employee/date, then view, export, refresh, or remove archived files.', 'Archived documents remain part of the database and its backup workflow.', 'archive'],
  ['💼', 'Business Tracking', 'Track catalog products, inventory stock, customer orders, gym memberships, and employee activities.', 'Example: Stock reorders · Order tracking · Membership sessions left.', 'business'],
  ['🏪', 'Store Directory', 'Maintain the directory of sports nutrition and supplement stores across India.', 'Review verified addresses, websites, and Google Maps links.', 'customers'],
  ['💬', 'Live Chat', 'Use team collaboration channels for shift announcements, audit coordination, and daily notes.', 'Private/group chat uses its separate membership sign-in.', 'chat'],
  ['🛍️', 'Online Storefront', 'Public e-commerce storefront for USA–Raw Strength customer orders.', 'Browse catalog, place COD orders, and manage orders in Business Tracking.', 'storefront'],
  ['⚙️', 'Settings & Backup', 'Set working days, create or restore backups, manage account security, and export employees.', 'Create and verify a backup before restoring data or replacing a production build.', 'settings']
];

const metricCards = [
  ['📦', 'Catalog Products', 'products', 'Active products in inventory'],
  ['⚠️', 'Reorder Alerts', 'low_stock', 'Items at or below reorder level'],
  ['🛒', 'Customer Orders', 'orders', 'Total sales orders logged'],
  ['🏋️', 'Active Members', 'members', 'Active memberships and plans']
];

const numberText = value => Number(value || 0).toLocaleString();
const moneyText = value => '₹' + Number(value || 0).toLocaleString(undefined, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

export default function HomeWorkspace({
  user,
  business,
  theme,
  onThemeChange,
  wallpaper,
  wallpaperStyles = [],
  onWallpaperChange,
  onCustomWallpaperUpload,
  canRollback,
  canAdminEmployees,
  employees = [],
  authUsers = [],
  newAccount,
  setNewAccount,
  createManagedAccount,
  showCreatePerms,
  setShowCreatePerms,
  createPermsDraft,
  setCreatePermsDraft,
  openPermissionsModal,
  toggleAccountActive,
  openRecoveryModal,
  onNavigate
}) {
  const open = target => {
    if (target === 'storefront') {
      window.location.hash = '#store';
      window.location.reload();
      return;
    }
    onNavigate?.(target);
  };

  const modules = DEFAULT_MODULES;
  const presets = DEFAULT_PRESETS;
  const accessOptions = DEFAULT_OPTIONS;

  return (
    <div className="space-y-6">
      {/* 1. Executive Session Strip */}
      <section className="relative overflow-hidden rounded-3xl border border-cyan-400/40 bg-gradient-to-r from-slate-900/95 via-indigo-950/80 to-slate-900/95 backdrop-blur-2xl p-5 sm:p-6 shadow-[0_20px_50px_-10px_rgba(0,0,0,0.8),0_0_35px_rgba(6,182,212,0.18)]">
        <div className="pointer-events-none absolute -right-20 -top-20 h-52 w-52 rounded-full bg-cyan-500/15 blur-3xl" />
        <div className="pointer-events-none absolute -left-20 -bottom-20 h-52 w-52 rounded-full bg-purple-500/15 blur-3xl" />
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-[10px] font-black uppercase tracking-widest text-cyan-400 bg-cyan-400/15 px-2.5 py-1 rounded-md border border-cyan-400/30 shadow-sm">
                SIGNED IN
              </span>
              <h2 className="text-xl sm:text-2xl font-black text-white truncate tracking-tight">
                {user?.display_name || user?.username || 'Executive User'}
              </h2>
              <span className="rounded-full bg-indigo-500/25 border border-indigo-400/40 px-3 py-0.5 text-xs font-extrabold text-indigo-200">
                {user?.role || 'Administrator'}
              </span>
              <button
                type="button"
                onClick={openRecoveryModal}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold transition border ${
                  user?.has_recovery_question
                    ? 'border-emerald-400/40 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25'
                    : 'border-amber-400/40 bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 animate-pulse'
                }`}
                title="Configure or change confidential password recovery question"
              >
                <Shield size={13} />
                {user?.has_recovery_question ? 'Recovery: Configured' : 'Recovery: Set Up Now'}
              </button>
            </div>
            <p className="mt-2 text-xs font-medium text-slate-400 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
              Version {business?.version || '1.3.82'} · Cloudflare D1 Native Database · Continuous Encrypted Sync Active
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={() => open('dashboard')}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 via-sky-400 to-indigo-500 px-4 py-2.5 text-xs sm:text-sm font-black text-slate-950 shadow-lg shadow-cyan-400/25 transition-all hover:brightness-110 hover:scale-[1.02] active:scale-[0.98]"
            >
              📊 Executive Dashboard ➔
            </button>
            <a
              href="https://github.com/yalangisexter-ux/audit-report/releases/latest/download/RawStrengthEmployeeAuditManager-Setup.exe"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 px-4 py-2.5 text-xs sm:text-sm font-black text-white shadow-lg shadow-purple-600/25 transition-all hover:brightness-110 hover:scale-[1.02] active:scale-[0.98]"
              title="Download official Windows Desktop Installer (.exe)"
            >
              💻 Download Desktop App (.exe)
            </a>
            <button
              type="button"
              onClick={() => open('settings')}
              className="rounded-xl border border-white/15 bg-slate-900/90 px-3.5 py-2.5 text-xs font-bold text-slate-200 hover:border-cyan-400/50 hover:bg-slate-800 transition"
            >
              ⬇ Update application
            </button>
            {canRollback && (
              <button
                type="button"
                onClick={() => open('settings')}
                className="rounded-xl border border-amber-300/40 bg-amber-950/30 px-3.5 py-2.5 text-xs font-bold text-amber-200 hover:bg-amber-300/20 transition"
              >
                ↶ Previous versions
              </button>
            )}
          </div>
        </div>
        <p className="mt-3.5 border-t border-white/10 pt-2.5 text-[11px] text-slate-400">
          The Update Center provides stable Windows installer downloads and password-protected previous versions. The browser does not execute or roll back a Windows installer.
        </p>
      </section>

      {/* 2. Business Tracking & Operations Section (Top Executive KPIs) */}
      <section className="relative overflow-hidden rounded-3xl border border-cyan-400/30 bg-slate-900/80 p-5 sm:p-6 shadow-2xl backdrop-blur-2xl">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-cyan-400/20 text-cyan-300 border border-cyan-400/40 text-sm font-bold">
                💼
              </span>
              <h2 className="text-lg sm:text-xl font-black text-white tracking-tight">Business tracking &amp; operations</h2>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" /> Live D1 Ledger
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">Live operational figures synchronized directly from the Cloudflare D1 business ledger.</p>
          </div>
          <div className="flex items-center gap-2.5">
            <a
              href="/#store"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-400/40 bg-cyan-400/15 px-3.5 py-2 text-xs font-bold text-cyan-200 hover:bg-cyan-400/25 transition shadow-sm"
            >
              🛍️ Visit Storefront ↗
            </a>
            <button
              type="button"
              onClick={() => open('business')}
              className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-xs font-black text-slate-950 hover:brightness-110 transition shadow-md shadow-cyan-400/20"
            >
              Open Business Tracking ➔
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3.5 xl:grid-cols-4">
          {metricCards.map(([icon, title, key, subtitle]) => (
            <button
              key={key}
              type="button"
              onClick={() => open('business')}
              className="metric-card-2027 group relative overflow-hidden rounded-2xl border border-white/15 bg-slate-950/80 backdrop-blur-xl p-5 text-left transition-all duration-300 hover:border-cyan-400/50 shadow-xl hover:shadow-[0_20px_45px_rgba(0,0,0,0.8),0_0_30px_rgba(6,182,212,0.3)] hover:-translate-y-1"
            >
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-cyan-400 via-indigo-500 to-purple-500 opacity-80 group-hover:opacity-100 transition-opacity" />
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-slate-300 group-hover:text-cyan-300 transition-colors flex items-center gap-1.5">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-cyan-400/10 border border-cyan-400/25 text-sm">{icon}</span>
                  {title}
                </p>
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <p className="mt-3 text-2xl sm:text-3xl font-black tabular-nums text-white group-hover:text-cyan-300 transition-colors drop-shadow-[0_2px_10px_rgba(34,211,238,0.3)]">
                {business ? numberText(business[key]) : '—'}
              </p>
              <p className="mt-1 text-[11px] text-slate-400">{subtitle}</p>
            </button>
          ))}
        </div>
        <p className="mt-4 rounded-xl bg-slate-950/80 p-3 text-xs text-slate-400 border border-white/10 flex items-center justify-between flex-wrap gap-2">
          <span>● {business ? numberText(business.activities) : '—'} employee business activities logged · {moneyText(business?.total_sales)} total order sales recorded.</span>
          <span className="text-[11px] text-cyan-400 font-mono">D1 Edge Latency: &lt;15ms</span>
        </p>
      </section>

      {/* 3. Workspace Guide matching EXE styling with 5px left accent */}
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg sm:text-xl font-black text-white tracking-tight">Workspace guide</h2>
            <p className="mt-0.5 text-xs text-slate-400">Select any operations module to launch it directly.</p>
          </div>
          <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">12 Core Modules</span>
        </div>
        <div className="grid gap-3.5 md:grid-cols-2">
          {WORKSPACE_GUIDE.map(([icon, title, guidance, example, target]) => (
            <button
              key={target}
              type="button"
              onClick={() => open(target)}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl p-4 sm:p-5 text-left transition-all duration-300 hover:border-cyan-400/50 hover:bg-slate-900/95 hover:shadow-[0_15px_40px_rgba(0,0,0,0.7),0_0_25px_rgba(6,182,212,0.2)] hover:-translate-y-1"
            >
              <div className="absolute top-0 left-0 bottom-0 w-1 bg-gradient-to-b from-cyan-400 to-indigo-500 opacity-80 group-hover:w-1.5 transition-all" />
              <div className="flex items-center gap-3 pl-1">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-cyan-400/30 bg-gradient-to-br from-cyan-400/20 to-indigo-500/10 text-2xl font-bold shadow-inner">
                  {icon}
                </span>
                <span className="min-w-0 flex-1 text-sm sm:text-base font-extrabold text-white group-hover:text-cyan-300 transition">
                  {title}
                </span>
                <span className="text-cyan-400 text-lg transition-transform duration-200 group-hover:translate-x-1.5 font-bold">➔</span>
              </div>
              <p className="mt-2.5 text-xs leading-relaxed text-slate-300 pl-1">{guidance}</p>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500 pl-1">{example}</p>
            </button>
          ))}
        </div>
      </section>

      {/* 4. Account Creation for Employees directly on Home */}
      {canAdminEmployees && (
        <section className="rounded-3xl border border-cyan-400/35 bg-slate-900/85 p-5 sm:p-7 shadow-2xl backdrop-blur-2xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div>
              <div className="flex items-center gap-2.5">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-tr from-cyan-400 to-indigo-500 text-slate-950 font-black shadow-md shadow-cyan-400/20">
                  <UserPlus size={19} />
                </span>
                <h2 className="text-base sm:text-xl font-black text-white tracking-tight">
                  Employee Account Creation &amp; Mapping
                </h2>
                <span className="rounded-full bg-cyan-400/15 border border-cyan-400/35 px-2.5 py-0.5 text-[11px] font-bold text-cyan-300">
                  Onboarding Hub
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Create login accounts for employees directly from Home: map to an existing employee record, assign role, and set initial credentials.
              </p>
            </div>
            <button
              type="button"
              onClick={() => open('settings')}
              className="text-xs font-bold text-cyan-300 hover:underline flex items-center gap-1"
            >
              All User Accounts &amp; Settings ↗
            </button>
          </div>

          <form className="mt-5 grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3" onSubmit={createManagedAccount}>
            <label className="text-xs font-bold text-slate-300">
              Map to Employee *
              <select
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400 transition"
                value={newAccount?.employee_id || ''}
                onChange={e => {
                  const empId = e.target.value;
                  const emp = employees.find(x => String(x.id) === String(empId));
                  setNewAccount?.(p => ({
                    ...p,
                    employee_id: empId,
                    display_name: p.display_name && p.display_name !== p.username ? p.display_name : (emp ? emp.name : p.display_name)
                  }));
                }}
              >
                <option value="">Select Employee to Map…</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.name} ({emp.employee_code || 'EMP' + emp.id}) — {emp.department || 'General'}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs font-bold text-slate-300">
              Username *
              <input
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-slate-950 px-3 py-2.5 text-xs text-white font-mono outline-none focus:border-cyan-400 transition"
                placeholder="e.g. rahul.sharma"
                value={newAccount?.username || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, username: e.target.value }))}
                maxLength={64}
                required
              />
            </label>

            <label className="text-xs font-bold text-slate-300">
              Display Name *
              <input
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400 transition"
                placeholder="e.g. Rahul Sharma"
                value={newAccount?.display_name || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, display_name: e.target.value }))}
                maxLength={100}
                required
              />
            </label>

            <label className="text-xs font-bold text-slate-300">
              Role / Access Level
              <select
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400 transition"
                value={newAccount?.role || 'Employee'}
                onChange={e => {
                  const r = e.target.value;
                  setNewAccount?.(p => ({ ...p, role: r }));
                  const presetKey = r.toLowerCase();
                  if (presets[presetKey]) setCreatePermsDraft?.({ ...presets[presetKey] });
                }}
              >
                {['Employee', 'Staff', 'HR', 'Admin', 'Developer'].map(role => (
                  <option key={role} value={role} disabled={role === 'Developer' && String(user?.role || '').toLowerCase() !== 'developer'}>
                    {role} {role === 'Employee' ? '(Attendance & Self-Tasks only)' : ''}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-xs font-bold text-slate-300">
              Initial Password *
              <input
                className="mt-1.5 w-full rounded-xl border border-white/15 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400 transition"
                type="password"
                autoComplete="new-password"
                placeholder="Minimum 8 characters"
                minLength={8}
                value={newAccount?.password || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, password: e.target.value }))}
                required
              />
            </label>

            <div className="flex flex-col justify-end">
              <div className="rounded-xl border border-cyan-400/25 bg-cyan-950/50 p-2.5 text-xs text-cyan-200">
                <div className="flex items-center gap-1.5 font-bold text-white">
                  <Shield size={14} className="text-cyan-400 shrink-0" /> Account Recovery
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
                  Account owners configure their confidential recovery question &amp; answer upon login.
                </p>
              </div>
            </div>

            {/* Custom Permissions Toggle */}
            <div className="sm:col-span-2 xl:col-span-3 flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={() => setShowCreatePerms?.(v => !v)}
                className="inline-flex items-center gap-1.5 text-xs font-bold text-cyan-300 hover:underline"
              >
                <Shield size={14} />
                {showCreatePerms ? 'Hide custom permissions' : 'Customize module permissions for new account (Optional)'}
              </button>
              <span className="text-[11px] text-slate-500">
                Default: {newAccount?.role || 'Employee'} preset applied
              </span>
            </div>

            {showCreatePerms && (
              <div className="sm:col-span-2 xl:col-span-3 rounded-2xl border border-cyan-400/30 bg-slate-950/80 p-3.5 shadow-inner">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <span className="text-xs font-bold text-slate-200">Granular Module Permissions:</span>
                  <div className="flex flex-wrap gap-1.5 text-xs">
                    <button type="button" onClick={() => setCreatePermsDraft?.({ ...presets.admin })} className="rounded bg-emerald-500/20 px-2 py-0.5 text-emerald-300 border border-emerald-500/30 font-semibold">Admin</button>
                    <button type="button" onClick={() => setCreatePermsDraft?.({ ...presets.hr })} className="rounded bg-cyan-500/20 px-2 py-0.5 text-cyan-300 border border-cyan-500/30 font-semibold">HR</button>
                    <button type="button" onClick={() => setCreatePermsDraft?.({ ...presets.staff })} className="rounded bg-amber-500/20 px-2 py-0.5 text-amber-300 border border-amber-500/30 font-semibold">Staff</button>
                    <button type="button" onClick={() => setCreatePermsDraft?.({ ...presets.employee })} className="rounded bg-purple-500/20 px-2 py-0.5 text-purple-300 border border-purple-500/30 font-semibold">Employee</button>
                  </div>
                </div>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 max-h-56 overflow-y-auto p-1">
                  {modules.map(m => (
                    <label key={m.id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-900 border border-white/10 px-2.5 py-1.5 text-xs text-slate-300">
                      <span className="truncate">{m.icon} {m.name}</span>
                      <select
                        className="rounded border border-white/15 bg-slate-950 px-2 py-1 text-xs text-white"
                        value={createPermsDraft?.[m.id] || 'read'}
                        onChange={e => setCreatePermsDraft?.(p => ({ ...p, [m.id]: e.target.value }))}
                      >
                        {accessOptions.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label.split(' ')[1]}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              </div>
            )}

            <div className="sm:col-span-2 xl:col-span-3 pt-2 flex items-center justify-end">
              <button
                type="submit"
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-5 py-2.5 text-xs sm:text-sm font-black text-slate-950 hover:brightness-110 transition shadow-lg shadow-cyan-400/25"
              >
                <UserPlus size={16} /> Create &amp; Activate Employee Account
              </button>
            </div>
          </form>

          {/* Quick Active Accounts Summary on Home */}
          {authUsers && authUsers.length > 0 && (
            <div className="mt-6 border-t border-white/10 pt-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Active User Accounts ({authUsers.length})
                </span>
                <span className="text-[11px] text-slate-500">
                  Showing top mapped accounts
                </span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-950/60">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 font-semibold bg-white/[0.02]">
                      <th className="py-2.5 px-3">Username</th>
                      <th className="py-2.5 px-3">Display Name</th>
                      <th className="py-2.5 px-3">Role</th>
                      <th className="py-2.5 px-3">Mapped Employee</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {authUsers.slice(0, 5).map(a => (
                      <tr key={a.id} className="border-b border-white/5 hover:bg-white/[0.03] transition-colors">
                        <td className="py-2.5 px-3 font-mono text-cyan-200 font-bold">{a.username}</td>
                        <td className="py-2.5 px-3 text-white font-medium">{a.display_name}</td>
                        <td className="py-2.5 px-3">
                          <span className="rounded-full bg-indigo-500/20 border border-indigo-400/30 px-2.5 py-0.5 text-[11px] font-bold text-indigo-200">
                            {a.role}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {a.employee_name ? (
                            <span className="text-emerald-300 font-medium">
                              {a.employee_name} ({a.employee_code || 'EMP' + a.employee_id})
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">Unmapped</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider ${
                            a.active ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${a.active ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                            {a.active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            type="button"
                            onClick={() => openPermissionsModal?.(a)}
                            className="rounded-lg border border-purple-400/30 bg-purple-500/10 px-2.5 py-1 text-[11px] font-bold text-purple-200 hover:bg-purple-500/20 transition"
                          >
                            🛡️ Permissions
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      {/* 5. Quick Appearance Controls */}
      <section className="rounded-3xl border border-white/10 bg-slate-900/70 p-5 shadow-xl backdrop-blur-xl">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-white">Quick appearance controls</h2>
            <p className="mt-0.5 text-xs text-slate-400">Appearance preferences are saved in your local workspace session.</p>
          </div>
          <button type="button" onClick={() => open('settings')} className="text-xs font-bold text-cyan-300 hover:underline">
            More settings ↗
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-xs font-semibold text-slate-400">Theme
            <select aria-label="Home theme" className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400 transition" value={theme} onChange={event => onThemeChange?.(event.target.value)}>
              {['day', 'night', 'ocean', 'sunset'].map(value => <option key={value} value={value}>{value[0].toUpperCase() + value.slice(1)}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-400">Live wallpaper
            <select aria-label="Home live wallpaper" className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400 transition" value={wallpaper} onChange={event => onWallpaperChange?.(event.target.value)}>
              {wallpaperStyles.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-400">Custom wallpaper
            <input aria-label="Browse custom wallpaper" className="mt-1 block w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 file:mr-2 file:rounded-lg file:border-0 file:bg-cyan-400 file:px-2.5 file:py-1.5 file:text-xs file:font-bold file:text-slate-950" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" onChange={onCustomWallpaperUpload}/>
          </label>
        </div>
      </section>
    </div>
  );
}
