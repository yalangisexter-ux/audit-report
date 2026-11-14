import React, { useEffect, useState } from 'react';
import { Download, RefreshCw, RotateCcw, ShieldCheck } from 'lucide-react';

const formatDate = value => {
  if (!value) return 'Unknown';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
};

const formatSize = value => {
  const bytes = Number(value);
  return Number.isFinite(bytes) && bytes > 0 ? (bytes / 1024 / 1024).toFixed(1) + ' MB' : 'Unknown size';
};

export default function UpdateCenter({ apiFetch, notify, canRollback, card, field, btn }) {
  const [info, setInfo] = useState(null);
  const [checking, setChecking] = useState(false);
  const [rollbackPassword, setRollbackPassword] = useState('');
  const [rollbackBusy, setRollbackBusy] = useState(false);
  const [rollbackVersions, setRollbackVersions] = useState([]);
  const [rollbackMessage, setRollbackMessage] = useState('');
  const [error, setError] = useState('');

  const checkUpdates = async () => {
    setChecking(true);
    setError('');
    try {
      const result = await apiFetch('/update-center');
      setInfo(result);
      if (result.status === 'offline') setError(result.message || 'GitHub release check is in rate-limit cooldown. Direct Windows desktop download link remains available below.');
    } catch (requestError) {
      setError(requestError.message || 'GitHub release metadata check is in cooldown. Direct download remains active.');
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkUpdates();
  }, []);

  const loadRollbackOptions = async event => {
    event.preventDefault();
    setRollbackBusy(true);
    setRollbackMessage('');
    try {
      const result = await apiFetch('/update-center/rollback-options', {
        method: 'POST',
        body: JSON.stringify({ password: rollbackPassword })
      });
      setRollbackVersions(result.versions || []);
      setRollbackMessage(result.message || 'Previous installers loaded.');
      setRollbackPassword('');
    } catch (requestError) {
      setRollbackVersions([]);
      setRollbackMessage(requestError.message || 'Could not verify rollback access.');
      notify?.(requestError.message || 'Could not verify rollback access.');
    } finally {
      setRollbackBusy(false);
    }
  };

  const latest = info?.latest_release;

  return <section className={card + ' mt-4'}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-bold text-white">Application update center</h2>
        <p className="mt-1 text-xs text-slate-400">Current application version: {info?.current_version || 'Loading…'}</p>
      </div>
      <button type="button" className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-50" onClick={checkUpdates} disabled={checking}>
        <RefreshCw size={15} className={checking ? 'animate-spin' : ''}/>{checking ? 'Checking…' : 'Check for updates'}
      </button>
    </div>

    {error && <p role="alert" className="mt-3 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-sm text-amber-200">{error}</p>}
    {info?.status === 'cached' && <p className="mt-3 text-xs text-amber-200">GitHub is temporarily unavailable; showing the last cached release list.</p>}

    {info && latest && <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs font-semibold text-cyan-200">Latest stable: {info.latest_version}</span>
        <span className={info.update_available ? 'text-xs font-semibold text-emerald-300' : 'text-xs text-slate-400'}>
          {info.update_available ? 'A newer Windows installer is available' : 'No newer stable Windows installer found'}
        </span>
      </div>
      <h3 className="mt-3 text-sm font-bold text-white">{latest.title}</h3>
      <p className="mt-1 text-xs text-slate-500">Published {formatDate(latest.published_at)} · {formatSize(latest.asset_size)}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <a className={btn} href={latest.download_url} target="_blank" rel="noopener noreferrer">
          <Download size={15}/> Download Windows installer
        </a>
        {latest.release_url && <a className="inline-flex items-center rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200" href={latest.release_url} target="_blank" rel="noopener noreferrer">Release notes</a>}
      </div>
      {latest.body && <details className="mt-3">
        <summary className="cursor-pointer text-xs font-semibold text-slate-300">View release notes</summary>
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/20 p-3 text-xs text-slate-300">{latest.body}</pre>
      </details>}
    </div>}

    {(!latest) && (
      <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/60 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-white">Official Windows Desktop App (.exe)</h3>
            <p className="mt-1 text-xs text-slate-400">Stable release installer with automatic offline D1 cache & continuous encrypted sync.</p>
          </div>
          <a
            className={btn}
            href="https://github.com/yalangisexter-ux/audit-report/releases/latest/download/RawStrengthEmployeeAuditManager-Setup.exe"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Download size={15}/> Download Windows (.exe)
          </a>
        </div>
      </div>
    )}

    <p className="mt-3 text-xs text-slate-500">This download is the Windows EXE installer. The browser cannot install or execute it. The hosted web client is updated through the production deployment pipeline.</p>
    <p className="mt-1 text-xs text-slate-500">Last checked: {formatDate(info?.checked_at)}</p>

    {canRollback && <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
      <div className="flex items-center gap-2 text-sm font-bold text-amber-100"><ShieldCheck size={16}/> Previous Windows versions</div>
      <p className="mt-1 text-xs text-slate-400">Admin / Developer verification is required, matching the desktop rollback permission boundary.</p>
      <form className="mt-3 flex flex-wrap gap-2" onSubmit={loadRollbackOptions}>
        <input className={field + ' min-w-[220px] flex-1'} type="password" autoComplete="current-password" value={rollbackPassword} onChange={event => setRollbackPassword(event.target.value)} placeholder="Current Admin / Developer password" required/>
        <button type="submit" className="inline-flex items-center gap-2 rounded-lg border border-amber-300/30 px-4 py-2 text-sm font-semibold text-amber-100 disabled:opacity-50" disabled={rollbackBusy || !rollbackPassword}>
          <RotateCcw size={15}/>{rollbackBusy ? 'Verifying…' : 'Load previous versions'}
        </button>
      </form>
      {rollbackMessage && <p role="status" className="mt-3 text-xs text-slate-300">{rollbackMessage}</p>}
      {rollbackVersions.length > 0 && <div className="mt-3 space-y-2">
        {rollbackVersions.map(release => <div key={release.tag} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-950/70 p-3">
          <div><p className="text-sm font-semibold text-white">{release.title} · {release.version}</p><p className="text-xs text-slate-500">{formatDate(release.published_at)} · {formatSize(release.asset_size)} · {release.sha256 ? 'SHA-256 metadata available' : 'Legacy release without GitHub digest metadata'}</p></div>
          <a className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-cyan-200" href={release.download_url} target="_blank" rel="noopener noreferrer"><Download size={14}/> Download installer</a>
        </div>)}
      </div>}
      <p className="mt-3 text-xs text-amber-100/80">Downloading a previous installer does not perform rollback in the browser. Before installing it on Windows, create and verify a database backup; older application code may not support newer database features.</p>
    </div>}
  </section>;
}
