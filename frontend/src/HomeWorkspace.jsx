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
    <div className="space-y-5">
      {/* Executive Session Strip matching desktop EXE benchmark */}
      <section className="rounded-2xl border border-cyan-400/25 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest text-cyan-400 bg-cyan-400/10 px-2 py-0.5 rounded border border-cyan-400/20">
                SIGNED IN
              </span>
              <h2 className="text-lg sm:text-xl font-black text-white truncate">
                {user?.display_name || user?.username || 'Executive User'}
              </h2>
              <span className="rounded-full bg-indigo-500/20 border border-indigo-400/30 px-2.5 py-0.5 text-xs font-bold text-indigo-300">
                {user?.role || 'Administrator'}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Version {business?.version || '1.3.82'} · Cloudflare D1 Native Database · Encrypted Sync Active
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => open('dashboard')}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 via-sky-500 to-indigo-500 px-4 py-2.5 text-sm font-extrabold text-slate-950 shadow-md transition hover:brightness-110"
            >
              📊 Executive Dashboard ➔
            </button>
            <a
              href="https://github.com/yalangisexter-ux/audit-report/releases/latest/download/RawStrengthEmployeeAuditManager-Setup.exe"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 px-4 py-2.5 text-sm font-extrabold text-white shadow-md transition hover:brightness-110"
              title="Download official Windows Desktop Installer (.exe)"
            >
              💻 Download Desktop App (.exe)
            </a>
            <button
              type="button"
              onClick={() => open('settings')}
              className="rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-xs font-bold text-slate-200 hover:border-cyan-400/40"
            >
              ⬇ Update application
            </button>
            {canRollback && (
              <button
                type="button"
                onClick={() => open('settings')}
                className="rounded-xl border border-amber-300/30 bg-amber-950/20 px-3 py-2.5 text-xs font-semibold text-amber-200 hover:bg-amber-300/10"
              >
                ↶ Previous versions
              </button>
            )}
          </div>
        </div>
        <p className="mt-3 border-t border-white/10 pt-2 text-[11px] text-slate-500">
          The Update Center provides stable Windows installer downloads and password-protected previous versions. The browser does not execute or roll back a Windows installer.
        </p>
      </section>

      {/* Account Creation for Employees directly on Home */}
      {canAdminEmployees && (
        <section className="rounded-2xl border border-cyan-400/30 bg-slate-900/90 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-400 text-slate-950 font-bold">
                  <UserPlus size={18} />
                </span>
                <h2 className="text-base sm:text-lg font-black text-white">
                  Employee Account Creation &amp; Mapping
                </h2>
                <span className="rounded-full bg-cyan-400/10 border border-cyan-400/30 px-2.5 py-0.5 text-[11px] font-bold text-cyan-300">
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
              className="text-xs font-semibold text-cyan-300 hover:underline"
            >
              All User Accounts &amp; Settings ↗
            </button>
          </div>

          <form className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={createManagedAccount}>
            <label className="text-xs font-semibold text-slate-300">
              Map to Employee *
              <select
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
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

            <label className="text-xs font-semibold text-slate-300">
              Username *
              <input
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white font-mono outline-none focus:border-cyan-400"
                placeholder="e.g. rahul.sharma"
                value={newAccount?.username || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, username: e.target.value }))}
                maxLength={64}
                required
              />
            </label>

            <label className="text-xs font-semibold text-slate-300">
              Display Name *
              <input
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                placeholder="e.g. Rahul Sharma"
                value={newAccount?.display_name || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, display_name: e.target.value }))}
                maxLength={100}
                required
              />
            </label>

            <label className="text-xs font-semibold text-slate-300">
              Role / Access Level
              <select
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
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

            <label className="text-xs font-semibold text-slate-300">
              Initial Password *
              <input
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                type="password"
                autoComplete="new-password"
                placeholder="Minimum 8 characters"
                minLength={8}
                value={newAccount?.password || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, password: e.target.value }))}
                required
              />
            </label>

            <label className="text-xs font-semibold text-slate-300">
              Recovery Question
              <select
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-cyan-400"
                value={newAccount?.security_question || ''}
                onChange={e => setNewAccount?.(p => ({ ...p, security_question: e.target.value }))}
              >
                <option value="">(Account owner configures on sign-in)</option>
                {['What was the name of your first school?', 'What is the name of the city where you were born?', 'What was your childhood nickname?', 'What is the name of your first teacher?', 'What was the first concert or live event you attended?'].map(q => (
                  <option key={q} value={q}>{q}</option>
                ))}
              </select>
            </label>

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
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-2.5 text-xs sm:text-sm font-bold text-slate-950 hover:bg-cyan-300 transition shadow-lg shadow-cyan-400/20"
              >
                <UserPlus size={16} /> Create &amp; Activate Employee Account
              </button>
            </div>
          </form>

          {/* Quick Active Accounts Summary on Home */}
          {authUsers && authUsers.length > 0 && (
            <div className="mt-5 border-t border-white/10 pt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Active User Accounts ({authUsers.length})
                </span>
                <span className="text-[11px] text-slate-500">
                  Showing top mapped accounts
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 font-semibold">
                      <th className="py-2 px-2">Username</th>
                      <th className="py-2 px-2">Display Name</th>
                      <th className="py-2 px-2">Role</th>
                      <th className="py-2 px-2">Mapped Employee</th>
                      <th className="py-2 px-2">Status</th>
                      <th className="py-2 px-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {authUsers.slice(0, 5).map(a => (
                      <tr key={a.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                        <td className="py-2 px-2 font-mono text-cyan-200">{a.username}</td>
                        <td className="py-2 px-2 text-white font-medium">{a.display_name}</td>
                        <td className="py-2 px-2">
                          <span className="rounded bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-slate-200">
                            {a.role}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-slate-300">
                          {a.employee_name ? (
                            <span className="text-emerald-300 font-medium">
                              {a.employee_name} ({a.employee_code || 'EMP' + a.employee_id})
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">Unmapped</span>
                          )}
                        </td>
                        <td className="py-2 px-2">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            a.active ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                          }`}>
                            {a.active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-right">
                          <button
                            type="button"
                            onClick={() => openPermissionsModal?.(a)}
                            className="rounded-lg border border-purple-400/30 bg-purple-500/10 px-2 py-1 text-[11px] font-bold text-purple-200 hover:bg-purple-500/20 transition"
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

      {/* Quick Appearance Controls */}
      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-white">Quick appearance controls</h2>
            <p className="mt-0.5 text-xs text-slate-400">Appearance preferences are saved in your local workspace session.</p>
          </div>
          <button type="button" onClick={() => open('settings')} className="text-xs font-semibold text-cyan-300 hover:underline">
            More settings ↗
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-xs font-semibold text-slate-400">Theme
            <select aria-label="Home theme" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400" value={theme} onChange={event => onThemeChange?.(event.target.value)}>
              {['day', 'night', 'ocean', 'sunset'].map(value => <option key={value} value={value}>{value[0].toUpperCase() + value.slice(1)}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-400">Live wallpaper
            <select aria-label="Home live wallpaper" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400" value={wallpaper} onChange={event => onWallpaperChange?.(event.target.value)}>
              {wallpaperStyles.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-400">Custom wallpaper
            <input aria-label="Browse custom wallpaper" className="mt-1 block w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 file:mr-2 file:rounded-md file:border-0 file:bg-cyan-400 file:px-2.5 file:py-1.5 file:text-xs file:font-bold file:text-slate-950" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" onChange={onCustomWallpaperUpload}/>
          </label>
        </div>
      </section>

      {/* Workspace Guide matching EXE styling with 5px left accent */}
      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-black text-white">Workspace guide</h2>
            <p className="mt-0.5 text-xs text-slate-400">Select any operations module to launch it directly.</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {WORKSPACE_GUIDE.map(([icon, title, guidance, example, target]) => (
            <button
              key={target}
              type="button"
              onClick={() => open(target)}
              className="group rounded-xl border border-white/10 border-l-4 border-l-cyan-400 bg-slate-900/75 p-4 text-left transition hover:border-cyan-400/60 hover:border-l-purple-500 hover:bg-slate-900 shadow-md"
            >
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-cyan-400/30 bg-cyan-400/10 text-xl font-bold">
                  {icon}
                </span>
                <span className="min-w-0 flex-1 text-sm font-bold text-white group-hover:text-cyan-300 transition">
                  {title}
                </span>
                <span className="text-cyan-400 transition group-hover:translate-x-1 font-bold">➔</span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-300">{guidance}</p>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{example}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Business Tracking & Operations Section */}
      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-black text-white">Business tracking &amp; operations</h2>
            <p className="mt-0.5 text-xs text-slate-400">Live summary from the Cloudflare D1 business ledger.</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/#store"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-400/20"
            >
              🛍️ Visit Storefront ↗
            </a>
            <button
              type="button"
              onClick={() => open('business')}
              className="rounded-lg bg-cyan-400 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition"
            >
              Open Business Tracking ➔
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {metricCards.map(([icon, title, key, subtitle]) => (
            <button
              key={key}
              type="button"
              onClick={() => open('business')}
              className="rounded-xl border border-white/10 bg-slate-950/70 p-3 text-left transition hover:border-cyan-400/40"
            >
              <p className="text-xs font-semibold text-slate-400">{icon} {title}</p>
              <p className="mt-2 text-2xl font-black tabular-nums text-cyan-300">{business ? numberText(business[key]) : '—'}</p>
              <p className="mt-1 text-[11px] text-slate-500">{subtitle}</p>
            </button>
          ))}
        </div>
        <p className="mt-3 rounded-lg bg-slate-950/70 p-3 text-xs text-slate-400 border border-white/5">
          ● {business ? numberText(business.activities) : '—'} employee business activities logged · {moneyText(business?.total_sales)} total order sales recorded.
        </p>
      </section>
    </div>
  );
}
