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
