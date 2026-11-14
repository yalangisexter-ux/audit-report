import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Download, Eye, RefreshCw, Trash2, Upload, FileText } from 'lucide-react';

const field = 'w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400';
const button = 'inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50';
const secondary = 'inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-slate-200 disabled:opacity-40';

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

export default function ArchiveManager({
  items = [], employees = [], apiFetch, notify, refresh, isAdmin = false, token = ''
}) {
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [reportDate, setReportDate] = useState('');
  const [notes, setNotes] = useState('');
  const [uploading, setUploading] = useState(false);
  const [action, setAction] = useState('');
  const fileInput = useRef(null);

  const visibleItems = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return items;
    return items.filter(row => [
      row.file_name, row.employee_name, row.report_date, row.uploaded_at, row.notes
    ].some(value => String(value ?? '').toLowerCase().includes(term)));
  }, [items, search]);

  const selected = items.find(row => Number(row.id) === Number(selectedId)) || null;

  useEffect(() => {
    if (!items.length) {
      if (selectedId !== null) setSelectedId(null);
      return;
    }
    if (!items.some(row => Number(row.id) === Number(selectedId))) {
      setSelectedId(items[0].id);
    }
  }, [items, selectedId]);

  const authHeaders = () => {
    const activeToken = token || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('rsc_auth_token') : '') || (typeof localStorage !== 'undefined' ? localStorage.getItem('rsc_auth_token') : '') || '';
    return activeToken ? { Authorization: 'Bearer ' + activeToken } : {};
  };

  const uploadFiles = async event => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setUploading(true);
    let saved = 0;
    try {
      for (const file of files) {
        const payload = new FormData();
        payload.append('file', file);
        if (employeeId) payload.append('employee_id', employeeId);
        if (reportDate) payload.append('report_date', reportDate);
        payload.append('notes', notes);
        await apiFetch('/archive', { method: 'POST', body: payload });
        saved += 1;
      }
      notify('Archived ' + saved + ' PDF file(s).');
      setNotes('');
      await refresh();
    } catch (error) {
      notify(saved
        ? 'Archived ' + saved + ' of ' + files.length + ' files; remaining uploads stopped: ' + error.message
        : error.message);
      if (saved) await refresh();
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const openOrExport = async kind => {
    if (!selected || action) return;
    const previewWindow = kind === 'view' ? window.open('about:blank', '_blank') : null;
    setAction(kind);
    try {
      const response = await fetch('/api/archive/' + selected.id + '/' + kind, {
        headers: authHeaders()
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Could not retrieve the archived PDF.');
      }
      const objectUrl = URL.createObjectURL(await response.blob());
      if (kind === 'view' && previewWindow) {
        previewWindow.opener = null;
        previewWindow.location = objectUrl;
      } else {
        if (previewWindow) previewWindow.close();
        const link = document.createElement('a');
        link.href = objectUrl;
        if (kind === 'download') {
          link.download = selected.file_name || ('archive-' + selected.id + '.pdf');
        } else {
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
        }
        document.body.appendChild(link);
        link.click();
        link.remove();
      }
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (error) {
      if (previewWindow) previewWindow.close();
      notify(error.message);
    } finally {
      setAction('');
    }
  };

  const deleteSelected = async () => {
    if (!selected || action) return;
    if (!isAdmin) {
      notify('Only an Admin or Developer can delete archived documents.');
      return;
    }
    if (!window.confirm('Permanently delete "' + selected.file_name + '" from the archive?')) return;
    setAction('delete');
    try {
      await apiFetch('/archive/' + selected.id, { method: 'DELETE' });
      notify('Archived PDF deleted.');
      setSelectedId(null);
      await refresh();
    } catch (error) {
      notify(error.message);
    } finally {
      setAction('');
    }
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white">Historical EOD Archive</h2>
            <p className="mt-1 text-sm text-slate-400">Store and retrieve historical audit PDFs in the shared customer database.</p>
          </div>
          <button type="button" className={secondary} onClick={() => refresh()} disabled={uploading || !!action}>
            <RefreshCw size={16}/> Refresh
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <label className="text-xs text-slate-400">Associate employee
            <select className={field + ' mt-1'} value={employeeId} onChange={event => setEmployeeId(event.target.value)}>
              <option value="">Unassigned / All employees</option>
              {employees.map(employee => (
                <option key={employee.id} value={employee.id}>
                  {employee.name} ({employee.employee_code || employee.id})
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">Report date
            <input className={field + ' mt-1'} type="date" value={reportDate} onChange={event => setReportDate(event.target.value)}/>
          </label>
          <label className="text-xs text-slate-400 sm:col-span-2 xl:col-span-1">Notes
            <input className={field + ' mt-1'} value={notes} onChange={event => setNotes(event.target.value)} maxLength={500} placeholder="Optional archive notes"/>
          </label>
        </div>
        <input
          ref={fileInput}
          className="hidden"
          type="file"
          accept="application/pdf,.pdf"
          multiple
          onChange={uploadFiles}
        />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" className={button} onClick={() => fileInput.current?.click()} disabled={uploading}>
            <Upload size={16}/>{uploading ? 'Uploading PDFs…' : 'Upload PDF(s)'}
          </button>
          <span className="text-xs text-slate-500">Multiple PDFs can be uploaded together. The selected employee, report date and notes are applied to each file.</span>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-white">Archived audit documents · {items.length}</h3>
            <p className="mt-1 text-xs text-slate-500">Select one document to view, export or delete it.</p>
          </div>
          <input className={field + ' max-w-sm'} value={search} onChange={event => setSearch(event.target.value)} placeholder="Search file, employee, date or notes"/>
        </div>
        <div className="overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-950/80 text-xs uppercase text-slate-500">
              <tr>
                <th className="p-3">Select</th>
                <th className="p-3">File name</th>
                <th className="p-3">Employee</th>
                <th className="p-3">Report date</th>
                <th className="p-3">Uploaded</th>
                <th className="p-3">Notes</th>
                <th className="p-3">Size</th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.map(row => (
                <tr
                  key={row.id}
                  className={'cursor-pointer border-t border-white/5 ' + (Number(row.id) === Number(selectedId) ? 'bg-cyan-950/35 text-white' : 'text-slate-300 hover:bg-white/5')}
                  onClick={() => setSelectedId(row.id)}
                >
                  <td className="p-3">
                    <input
                      type="radio"
                      name="archive-selected"
                      aria-label={'Select ' + row.file_name}
                      checked={Number(row.id) === Number(selectedId)}
                      onChange={() => setSelectedId(row.id)}
                    />
                  </td>
                  <td className="p-3 font-semibold"><span className="inline-flex items-center gap-2"><FileText size={15}/>{row.file_name}</span></td>
                  <td className="p-3">{row.employee_name || 'Unassigned / All'}</td>
                  <td className="p-3 whitespace-nowrap">{row.report_date || 'Unknown'}</td>
                  <td className="p-3 whitespace-nowrap text-xs text-slate-400">{row.uploaded_at || '—'}</td>
                  <td className="p-3 max-w-xs truncate" title={row.notes || ''}>{row.notes || '—'}</td>
                  <td className="p-3 whitespace-nowrap text-xs text-slate-400">{formatBytes(row.size_bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!visibleItems.length && <p className="p-6 text-center text-sm text-slate-500">No archived PDFs match this search.</p>}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button type="button" className={button} onClick={() => openOrExport('view')} disabled={!selected || !!action}>
            <Eye size={16}/>{action === 'view' ? 'Opening…' : 'View Selected'}
          </button>
          <button type="button" className={secondary} onClick={() => openOrExport('download')} disabled={!selected || !!action}>
            <Download size={16}/>{action === 'download' ? 'Exporting…' : 'Export Selected'}
          </button>
          <button type="button" className="inline-flex items-center justify-center gap-2 rounded-lg border border-rose-400/30 px-4 py-2.5 text-sm font-semibold text-rose-300 disabled:opacity-40" onClick={deleteSelected} disabled={!selected || !isAdmin || !!action}>
            <Trash2 size={16}/>{action === 'delete' ? 'Deleting…' : 'Delete Selected'}
          </button>
          {!isAdmin && <span className="text-xs text-slate-500">Delete is restricted to Admin and Developer accounts.</span>}
        </div>
      </section>
      <p className="text-xs text-slate-500">Archived PDFs remain in the application database and its backups. Viewing and exporting do not modify the stored document.</p>
    </div>
  );
}
