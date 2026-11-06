import React from 'react';

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
  onNavigate
}) {
  const open = target => onNavigate?.(target);

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-cyan-400/25 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-extrabold tracking-[0.18em] text-cyan-300">RAW STRENGTH CALISTHENICS</p>
            <h2 className="mt-1 text-xl font-black text-white">Welcome to your workspace</h2>
            <p className="mt-2 text-sm text-slate-300">Signed in as <b className="text-white">{user?.display_name || user?.username || 'User'}</b> · {user?.role || 'Account'}</p>
            <p className="mt-1 text-xs text-slate-500">Version {business?.version || 'Current web build'} · Web database with encrypted snapshot sync</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => open('settings')} className="rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 hover:bg-cyan-300">⬇ Update application</button>
            {canRollback && <button type="button" onClick={() => open('settings')} className="rounded-lg border border-amber-300/30 px-4 py-2.5 text-sm font-semibold text-amber-100 hover:bg-amber-300/10">↶ Previous versions</button>}
          </div>
        </div>
        <p className="mt-3 border-t border-white/10 pt-3 text-xs text-slate-400">The Update Center provides stable Windows installer downloads and password-protected previous versions. The browser does not execute or roll back a Windows installer.</p>
      </section>

      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-white">Quick appearance controls</h2>
            <p className="mt-1 text-xs text-slate-500">These preferences are stored in this browser, not in the shared customer database.</p>
          </div>
          <button type="button" onClick={() => open('settings')} className="text-xs font-semibold text-cyan-300">More settings ↗</button>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-xs font-semibold text-slate-400">Theme
            <select aria-label="Home theme" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100" value={theme} onChange={event => onThemeChange?.(event.target.value)}>
              {['day', 'night', 'ocean', 'sunset'].map(value => <option key={value} value={value}>{value[0].toUpperCase() + value.slice(1)}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-400">Live wallpaper
            <select aria-label="Home live wallpaper" className="mt-1 w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100" value={wallpaper} onChange={event => onWallpaperChange?.(event.target.value)}>
              {wallpaperStyles.map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-400">Custom wallpaper
            <input aria-label="Browse custom wallpaper" className="mt-1 block w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-xs text-slate-300 file:mr-2 file:rounded-md file:border-0 file:bg-cyan-400 file:px-3 file:py-2 file:text-xs file:font-bold file:text-slate-950" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" onChange={onCustomWallpaperUpload}/>
          </label>
        </div>
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div><h2 className="text-lg font-black text-white">Workspace guide</h2><p className="mt-1 text-xs text-slate-500">Select a workspace to open it directly.</p></div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {WORKSPACE_GUIDE.map(([icon, title, guidance, example, target]) => (
            <button key={target} type="button" onClick={() => open(target)} className="group rounded-xl border border-white/10 bg-slate-900/70 p-4 text-left transition hover:border-cyan-400/50 hover:bg-slate-900">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-cyan-400/20 bg-cyan-400/10 text-xl">{icon}</span>
                <span className="min-w-0 flex-1 text-sm font-bold text-white">{title}</span>
                <span className="text-cyan-300 transition group-hover:translate-x-1">↗</span>
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-300">{guidance}</p>
              <p className="mt-2 text-[11px] leading-5 text-slate-500">{example}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div><h2 className="text-lg font-black text-white">Business tracking &amp; operations</h2><p className="mt-1 text-xs text-slate-500">Live summary from the shared business database.</p></div>
          <button type="button" onClick={() => open('business')} className="rounded-lg border border-cyan-400/25 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-400/10">Open Business Tracking ↗</button>
        </div>
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {metricCards.map(([icon, title, key, subtitle]) => (
            <button key={key} type="button" onClick={() => open('business')} className="rounded-xl border border-white/10 bg-slate-950/70 p-3 text-left transition hover:border-cyan-400/40">
              <p className="text-xs font-semibold text-slate-400">{icon} {title}</p>
              <p className="mt-2 text-2xl font-black tabular-nums text-cyan-300">{business ? numberText(business[key]) : '—'}</p>
              <p className="mt-1 text-[11px] text-slate-500">{subtitle}</p>
            </button>
          ))}
        </div>
        <p className="mt-3 rounded-lg bg-slate-950/70 p-3 text-xs text-slate-400">
          ● {business ? numberText(business.activities) : '—'} employee business activities logged · {moneyText(business?.total_sales)} total order sales recorded.
        </p>
      </section>
    </div>
  );
}
