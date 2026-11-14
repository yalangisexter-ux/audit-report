import React, { useState, useEffect, useMemo } from 'react';
import { 
  CheckCheck, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  Coffee, 
  FileText, 
  UserCheck, 
  ShieldCheck, 
  AlertCircle, 
  ExternalLink, 
  Sparkles,
  Calendar,
  User,
  Search,
  Filter
} from 'lucide-react';

export default function ApprovalsHub({ apiFetch, notify, loadData, user, canAdmin }) {
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [pendingData, setPendingData] = useState({
    attendance: [],
    tasks: [],
    accounts: [],
    counts: { total: 0, attendance: 0, tasks: 0, accounts: 0 }
  });

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/approvals/pending');
      setPendingData({
        attendance: res.attendance || [],
        tasks: res.tasks || [],
        accounts: res.accounts || [],
        counts: res.counts || {
          attendance: (res.attendance || []).length,
          tasks: (res.tasks || []).length,
          accounts: (res.accounts || []).length,
          total: (res.attendance || []).length + (res.tasks || []).length + (res.accounts || []).length
        }
      });
    } catch (err) {
      notify('Failed to load pending approvals: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingApprovals();
  }, []);

  // Attendance Actions
  const handleApproveAttendance = async (row, action) => {
    if (actionBusy) return;
    setActionBusy(true);
    try {
      await apiFetch('/attendance/approve', {
        method: 'POST',
        body: JSON.stringify({
          work_date: row.work_date,
          employee_ids: [row.employee_id],
          action
        })
      });
      notify(`Attendance for ${row.employee_name} (${row.work_date}) ${action === 'approve' ? 'approved' : 'rejected'}`);
      setPendingData(prev => {
        const nextAtt = prev.attendance.filter(r => !(r.employee_id === row.employee_id && r.work_date === row.work_date));
        return {
          ...prev,
          attendance: nextAtt,
          counts: {
            ...prev.counts,
            attendance: nextAtt.length,
            total: nextAtt.length + prev.tasks.length + prev.accounts.length
          }
        };
      });
      loadData?.(row.work_date);
    } catch (err) {
      notify('Approval action failed: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  const handleApproveAllAttendance = async () => {
    if (actionBusy || pendingData.attendance.length === 0) return;
    const ok = window.confirm(`Are you sure you want to approve all ${pendingData.attendance.length} pending attendance records?`);
    if (!ok) return;
    setActionBusy(true);
    try {
      const res = await apiFetch('/attendance/approve', {
        method: 'POST',
        body: JSON.stringify({ all_pending: true, action: 'approve' })
      });
      notify(`All ${res.count || pendingData.attendance.length} pending attendance records approved!`);
      setPendingData(prev => ({
        ...prev,
        attendance: [],
        counts: {
          ...prev.counts,
          attendance: 0,
          total: prev.tasks.length + prev.accounts.length
        }
      }));
      loadData?.();
    } catch (err) {
      notify('Failed to approve all attendance: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  // Task Actions
  const handleApproveTask = async (task, action, markCompleted = true) => {
    if (actionBusy) return;
    setActionBusy(true);
    try {
      await apiFetch(`/tasks/${task.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({
          approval_status: action === 'approve' ? 'Approved' : 'Rejected',
          mark_completed: markCompleted
        })
      });
      notify(`Task "${task.title}" ${action === 'approve' ? 'approved and marked completed' : 'rejected'}`);
      setPendingData(prev => {
        const nextTasks = prev.tasks.filter(t => t.id !== task.id);
        return {
          ...prev,
          tasks: nextTasks,
          counts: {
            ...prev.counts,
            tasks: nextTasks.length,
            total: prev.attendance.length + nextTasks.length + prev.accounts.length
          }
        };
      });
      loadData?.();
    } catch (err) {
      notify('Failed to update task approval: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  const handleApproveAllTasks = async () => {
    if (actionBusy || pendingData.tasks.length === 0) return;
    const ok = window.confirm(`Are you sure you want to approve and complete all ${pendingData.tasks.length} pending tasks?`);
    if (!ok) return;
    setActionBusy(true);
    try {
      const res = await apiFetch('/tasks/approve-all', {
        method: 'POST',
        body: JSON.stringify({ action: 'approve' })
      });
      notify(`All ${res.count || pendingData.tasks.length} pending tasks approved and completed!`);
      setPendingData(prev => ({
        ...prev,
        tasks: [],
        counts: {
          ...prev.counts,
          tasks: 0,
          total: prev.attendance.length + prev.accounts.length
        }
      }));
      loadData?.();
    } catch (err) {
      notify('Failed to approve all tasks: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  // Account Actions
  const handleActivateAccount = async (account) => {
    if (actionBusy) return;
    setActionBusy(true);
    try {
      await apiFetch(`/auth/users/${account.id}/active`, {
        method: 'PATCH',
        body: JSON.stringify({ active: true })
      });
      notify(`Account "${account.username}" activated successfully!`);
      setPendingData(prev => {
        const nextAcc = prev.accounts.filter(a => a.id !== account.id);
        return {
          ...prev,
          accounts: nextAcc,
          counts: {
            ...prev.counts,
            accounts: nextAcc.length,
            total: prev.attendance.length + prev.tasks.length + nextAcc.length
          }
        };
      });
    } catch (err) {
      notify('Failed to activate account: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  const handleDeleteAccount = async (account) => {
    if (actionBusy) return;
    const ok = window.confirm(`Permanently reject and delete account request "${account.username}"?`);
    if (!ok) return;
    setActionBusy(true);
    try {
      await apiFetch(`/auth/users/${account.id}`, { method: 'DELETE' });
      notify(`Account request "${account.username}" rejected and removed`);
      setPendingData(prev => {
        const nextAcc = prev.accounts.filter(a => a.id !== account.id);
        return {
          ...prev,
          accounts: nextAcc,
          counts: {
            ...prev.counts,
            accounts: nextAcc.length,
            total: prev.attendance.length + prev.tasks.length + nextAcc.length
          }
        };
      });
    } catch (err) {
      notify('Failed to delete account request: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  // Filtering
  const filteredAttendance = useMemo(() => {
    if (filter !== 'all' && filter !== 'attendance') return [];
    if (!searchTerm.trim()) return pendingData.attendance;
    const q = searchTerm.toLowerCase();
    return pendingData.attendance.filter(r => 
      (r.employee_name && r.employee_name.toLowerCase().includes(q)) ||
      (r.employee_code && r.employee_code.toLowerCase().includes(q)) ||
      (r.department && r.department.toLowerCase().includes(q)) ||
      (r.work_date && r.work_date.includes(q)) ||
      (r.attendance_status && r.attendance_status.toLowerCase().includes(q)) ||
      (r.attendance_note && r.attendance_note.toLowerCase().includes(q))
    );
  }, [pendingData.attendance, filter, searchTerm]);

  const filteredTasks = useMemo(() => {
    if (filter !== 'all' && filter !== 'tasks') return [];
    if (!searchTerm.trim()) return pendingData.tasks;
    const q = searchTerm.toLowerCase();
    return pendingData.tasks.filter(t => 
      (t.title && t.title.toLowerCase().includes(q)) ||
      (t.employee_name && t.employee_name.toLowerCase().includes(q)) ||
      (t.department && t.department.toLowerCase().includes(q)) ||
      (t.task_date && t.task_date.includes(q)) ||
      (t.details && t.details.toLowerCase().includes(q))
    );
  }, [pendingData.tasks, filter, searchTerm]);

  const filteredAccounts = useMemo(() => {
    if (filter !== 'all' && filter !== 'accounts') return [];
    if (!searchTerm.trim()) return pendingData.accounts;
    const q = searchTerm.toLowerCase();
    return pendingData.accounts.filter(a => 
      (a.username && a.username.toLowerCase().includes(q)) ||
      (a.display_name && a.display_name.toLowerCase().includes(q)) ||
      (a.role && a.role.toLowerCase().includes(q))
    );
  }, [pendingData.accounts, filter, searchTerm]);

  const totalVisibleCount = filteredAttendance.length + filteredTasks.length + filteredAccounts.length;

  return (
    <div className="space-y-6">
      {/* 1. Header Hero Command Strip */}
      <section className="relative overflow-hidden rounded-3xl border border-cyan-400/35 bg-gradient-to-r from-slate-900/95 via-indigo-950/80 to-slate-900/95 p-5 sm:p-7 shadow-[0_20px_50px_-10px_rgba(0,0,0,0.8),0_0_35px_rgba(6,182,212,0.18)] backdrop-blur-2xl">
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-cyan-500/15 blur-3xl" />
        <div className="pointer-events-none absolute -left-20 -bottom-20 h-56 w-56 rounded-full bg-amber-500/15 blur-3xl" />

        <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-tr from-amber-400 to-amber-500 text-slate-950 font-black shadow-lg shadow-amber-400/25">
                <CheckCheck size={20} />
              </span>
              <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Executive Approvals Hub
              </h1>
              <span className="rounded-full bg-amber-400/20 border border-amber-400/40 px-3 py-0.5 text-xs font-black text-amber-200">
                Admin Queue
              </span>
            </div>
            <p className="mt-1.5 text-xs text-slate-300 max-w-2xl leading-relaxed">
              Review and approve employee attendance records, multiple break intervals, work task submissions, and onboarding account requests before permanent database persistence.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={fetchPendingApprovals}
              disabled={loading || actionBusy}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-slate-900/90 px-3.5 py-2 text-xs font-bold text-slate-200 hover:border-cyan-400/40 hover:bg-slate-800 transition shadow-sm"
              title="Refresh requests queue"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              <span>Refresh Queue</span>
            </button>
            {pendingData.attendance.length > 0 && (
              <button
                type="button"
                onClick={handleApproveAllAttendance}
                disabled={actionBusy}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-2 text-xs font-black text-slate-950 hover:brightness-110 shadow-lg shadow-emerald-500/25 transition active:scale-[0.98]"
                title="Approve all pending employee attendance records in one click"
              >
                <CheckCircle2 size={14} />
                <span>Approve All Attendance ({pendingData.attendance.length})</span>
              </button>
            )}
            {pendingData.tasks.length > 0 && (
              <button
                type="button"
                onClick={handleApproveAllTasks}
                disabled={actionBusy}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-xs font-black text-slate-950 hover:brightness-110 shadow-lg shadow-cyan-400/25 transition active:scale-[0.98]"
                title="Approve all pending tasks in one click"
              >
                <CheckCircle2 size={14} />
                <span>Approve All Tasks ({pendingData.tasks.length})</span>
              </button>
            )}
          </div>
        </div>

        {/* Metric Cards Banner */}
        <div className="relative z-10 mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-3.5 backdrop-blur-xl">
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">Total Pending</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-black text-amber-300 font-mono">{pendingData.counts.total}</span>
              <span className="text-[11px] text-slate-400">requests</span>
            </div>
          </div>
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-950/20 p-3.5 backdrop-blur-xl">
            <span className="text-[10px] font-black uppercase tracking-wider text-emerald-300 block">Attendance &amp; Breaks</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-black text-emerald-300 font-mono">{pendingData.counts.attendance}</span>
              <span className="text-[11px] text-slate-400">submissions</span>
            </div>
          </div>
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-950/20 p-3.5 backdrop-blur-xl">
            <span className="text-[10px] font-black uppercase tracking-wider text-cyan-300 block">Tasks &amp; Work</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-black text-cyan-300 font-mono">{pendingData.counts.tasks}</span>
              <span className="text-[11px] text-slate-400">completions</span>
            </div>
          </div>
          <div className="rounded-2xl border border-purple-400/20 bg-purple-950/20 p-3.5 backdrop-blur-xl">
            <span className="text-[10px] font-black uppercase tracking-wider text-purple-300 block">New Accounts</span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-black text-purple-300 font-mono">{pendingData.counts.accounts}</span>
              <span className="text-[11px] text-slate-400">registrations</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Filter & Search Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {[
            { id: 'all', label: 'All Requests', count: pendingData.counts.total },
            { id: 'attendance', label: '🟢 Attendance & Breaks', count: pendingData.counts.attendance },
            { id: 'tasks', label: '✅ Tasks & Work', count: pendingData.counts.tasks },
            { id: 'accounts', label: '👤 New Accounts', count: pendingData.counts.accounts }
          ].map(t => (
            <button
              key={t.id}
              type="button"
              onClick={() => setFilter(t.id)}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                filter === t.id
                  ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-400/40 shadow-sm'
                  : 'bg-slate-900/80 text-slate-400 border border-white/10 hover:text-white hover:bg-slate-800'
              }`}
            >
              <span>{t.label}</span>
              <span className={`rounded-full px-1.5 py-0.2 text-[10px] font-black ${
                filter === t.id ? 'bg-cyan-400 text-slate-950' : 'bg-white/10 text-slate-300'
              }`}>
                {t.count}
              </span>
            </button>
          ))}
        </div>

        <div className="relative min-w-56 flex-1 sm:flex-initial">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search employee, task, department or date…"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-white/15 bg-slate-900/90 pl-9 pr-3.5 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-cyan-400 transition"
          />
        </div>
      </div>

      {/* 3. Empty Queue Zero State */}
      {totalVisibleCount === 0 && !loading && (
        <div className="rounded-3xl border border-emerald-500/25 bg-slate-900/60 p-10 text-center backdrop-blur-xl">
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-300 text-3xl shadow-lg shadow-emerald-500/20">
            <Sparkles size={32} />
          </div>
          <h3 className="mt-4 text-lg font-black text-white">Queue Clear — All Requests Approved</h3>
          <p className="mt-1 text-xs text-slate-400 max-w-md mx-auto">
            There are no pending employee attendance submissions, break reviews, tasks, or account registrations awaiting Admin approval.
          </p>
        </div>
      )}

      {/* 4. Attendance & Multiple Breaks Submissions Section */}
      {(filter === 'all' || filter === 'attendance') && filteredAttendance.length > 0 && (
        <section className="rounded-3xl border border-white/10 bg-slate-900/80 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4 mb-4">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-xl bg-emerald-500/15 text-emerald-300 border border-emerald-400/30 text-sm">
                🟢
              </span>
              <div>
                <h2 className="text-base sm:text-lg font-black text-white">
                  Employee Attendance &amp; Breaks Awaiting Approval
                </h2>
                <p className="text-[11px] text-slate-400">
                  Review shift timings and multiple break intervals submitted by employees before committing to the permanent ledger.
                </p>
              </div>
            </div>
            <span className="rounded-full bg-amber-400/15 border border-amber-400/35 px-2.5 py-0.5 text-xs font-bold text-amber-200">
              {filteredAttendance.length} Pending
            </span>
          </div>

          <div className="space-y-3.5">
            {filteredAttendance.map(row => {
              let breaksList = [];
              try {
                breaksList = typeof row.breaks === 'string' ? JSON.parse(row.breaks) : (Array.isArray(row.breaks) ? row.breaks : []);
              } catch {}
              const breakMins = Number(row.break_minutes || 0);
              const breakHrs = (breakMins / 60).toFixed(2);

              // Net work hours calculation
              let netHours = '0.00';
              if (row.check_in && row.check_out) {
                const [ciH, ciM] = row.check_in.split(':').map(Number);
                const [coH, coM] = row.check_out.split(':').map(Number);
                if (![ciH, ciM, coH, coM].some(Number.isNaN)) {
                  let totalM = (coH * 60 + coM) - (ciH * 60 + ciM);
                  if (totalM < 0) totalM += 1440;
                  const netM = Math.max(0, totalM - breakMins);
                  netHours = (netM / 60).toFixed(2);
                }
              }

              return (
                <div
                  key={`${row.employee_id}-${row.work_date}`}
                  className="rounded-2xl border border-white/10 bg-slate-950/70 p-4 sm:p-5 transition hover:border-cyan-400/40 hover:bg-slate-950/90"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-black text-sm sm:text-base text-white">
                          {row.employee_name}
                        </span>
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-cyan-300 border border-white/10">
                          {row.employee_code || 'EMP' + row.employee_id}
                        </span>
                        <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[11px] font-bold text-indigo-200 border border-indigo-400/30">
                          {row.department || 'General'}
                        </span>
                        <span className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-2 py-0.5 text-[11px] font-bold text-amber-300 border border-amber-400/30">
                          <Clock size={11} /> {row.work_date}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        Designation: <span className="text-slate-200 font-semibold">{row.designation || 'Staff'}</span>
                        {row.attendance_note && (
                          <span className="ml-2 italic text-cyan-200/90">· Note: "{row.attendance_note}"</span>
                        )}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApproveAttendance(row, 'approve')}
                        disabled={actionBusy}
                        className="inline-flex items-center gap-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-3.5 py-1.5 text-xs font-black text-slate-950 hover:brightness-110 shadow-md shadow-emerald-500/20 transition active:scale-[0.98]"
                      >
                        <CheckCircle2 size={13} />
                        <span>✓ Approve</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApproveAttendance(row, 'reject')}
                        disabled={actionBusy}
                        className="inline-flex items-center gap-1 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-300 transition"
                      >
                        <XCircle size={13} />
                        <span>✕ Reject</span>
                      </button>
                    </div>
                  </div>

                  {/* Operational Metrics Bar */}
                  <div className="mt-3.5 grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-3 border-t border-white/10 text-xs">
                    <div className="rounded-xl bg-slate-900/80 p-2.5 border border-white/5">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Attendance Status</span>
                      <span className={`inline-block mt-0.5 font-bold ${
                        row.attendance_status === 'Present' ? 'text-emerald-300' :
                        row.attendance_status === 'Leave' ? 'text-amber-300' :
                        row.attendance_status === 'Company Holiday' ? 'text-purple-300' : 'text-rose-300'
                      }`}>
                        ● {row.attendance_status}
                      </span>
                    </div>

                    <div className="rounded-xl bg-slate-900/80 p-2.5 border border-white/5">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Shift Timing</span>
                      <span className="font-mono font-bold text-white mt-0.5 block">
                        {row.check_in || '—'} ➔ {row.check_out || '—'}
                      </span>
                    </div>

                    <div className="rounded-xl bg-slate-900/80 p-2.5 border border-white/5">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Break Hours (Total)</span>
                      <div className="flex items-baseline gap-1 mt-0.5">
                        <span className="font-mono font-black text-cyan-300 text-sm">{breakHrs} hrs</span>
                        <span className="text-[10px] text-slate-400">({breakMins}m)</span>
                      </div>
                    </div>

                    <div className="rounded-xl bg-slate-900/80 p-2.5 border border-white/5">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Net Work Hours</span>
                      <span className="font-mono font-black text-emerald-300 text-sm mt-0.5 block">
                        {netHours} hrs
                      </span>
                    </div>
                  </div>

                  {/* Multiple Break Interval Details */}
                  {breaksList.length > 0 && (
                    <div className="mt-2.5 rounded-xl border border-cyan-400/20 bg-cyan-950/20 p-2.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-300 block mb-1.5 flex items-center gap-1">
                        <Coffee size={12} /> Logged Break Intervals ({breaksList.length}):
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {breaksList.map((b, idx) => (
                          <span
                            key={b.id || idx}
                            className="inline-flex items-center gap-1 rounded-lg border border-cyan-400/30 bg-cyan-950/60 px-2 py-1 text-[11px] font-medium text-cyan-200"
                          >
                            <span>{b.type || 'Break'}</span>
                            <span className="text-white font-bold">{b.minutes}m</span>
                            {b.start && b.end && (
                              <span className="text-slate-400 text-[10px]">({b.start} – {b.end})</span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 5. Tasks & Work Submissions Section */}
      {(filter === 'all' || filter === 'tasks') && filteredTasks.length > 0 && (
        <section className="rounded-3xl border border-white/10 bg-slate-900/80 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4 mb-4">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-xl bg-cyan-500/15 text-cyan-300 border border-cyan-400/30 text-sm">
                ✅
              </span>
              <div>
                <h2 className="text-base sm:text-lg font-black text-white">
                  Employee Task Submissions Awaiting Approval
                </h2>
                <p className="text-[11px] text-slate-400">
                  Review submitted tasks, completion evidence, proof links, and deliverable notes before marking completed.
                </p>
              </div>
            </div>
            <span className="rounded-full bg-amber-400/15 border border-amber-400/35 px-2.5 py-0.5 text-xs font-bold text-amber-200">
              {filteredTasks.length} Pending
            </span>
          </div>

          <div className="space-y-3.5">
            {filteredTasks.map(task => (
              <div
                key={task.id}
                className="rounded-2xl border border-white/10 bg-slate-950/70 p-4 sm:p-5 transition hover:border-cyan-400/40 hover:bg-slate-950/90"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-black text-sm sm:text-base text-white">
                        {task.title}
                      </span>
                      <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[11px] font-bold text-indigo-200 border border-indigo-400/30">
                        {task.department || 'General'}
                      </span>
                      <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[11px] font-bold text-cyan-200 border border-cyan-400/30">
                        👤 {task.employee_name}
                      </span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300 border border-white/10">
                        📅 {task.task_date}
                      </span>
                    </div>

                    {task.details && (
                      <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">
                        {task.details}
                      </p>
                    )}

                    {/* Proof Link / Note */}
                    {(task.proof_url || task.proof_note) && (
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                        {task.proof_url && (
                          <a
                            href={task.proof_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded-md border border-cyan-400/40 bg-cyan-500/15 px-2.5 py-1 text-[11px] font-bold text-cyan-200 hover:bg-cyan-500/25 transition"
                          >
                            <ExternalLink size={11} />
                            <span>View Proof Artifact ↗</span>
                          </a>
                        )}
                        {task.proof_note && (
                          <span className="text-slate-400 italic">Proof note: "{task.proof_note}"</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleApproveTask(task, 'approve', true)}
                      disabled={actionBusy}
                      className="inline-flex items-center gap-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-3.5 py-1.5 text-xs font-black text-slate-950 hover:brightness-110 shadow-md shadow-emerald-500/20 transition active:scale-[0.98]"
                    >
                      <CheckCircle2 size={13} />
                      <span>✓ Approve &amp; Complete</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApproveTask(task, 'reject', false)}
                      disabled={actionBusy}
                      className="inline-flex items-center gap-1 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-300 transition"
                    >
                      <XCircle size={13} />
                      <span>✕ Reject</span>
                    </button>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-white/5">
                  <div className="flex items-center gap-3">
                    <span>Priority: <strong className="text-white">{task.priority || 'Normal'}</strong></span>
                    {task.due_time && <span>Due: <strong className="text-white">{task.due_time}</strong></span>}
                    <span>Progress: <strong className="text-cyan-300 font-mono">{task.progress || 100}%</strong></span>
                  </div>
                  <span className="rounded-full bg-amber-400/15 border border-amber-400/30 px-2 py-0.5 text-[10px] font-bold text-amber-200">
                    Status: {task.status || 'Submitted'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 6. Account Registrations Section */}
      {(filter === 'all' || filter === 'accounts') && filteredAccounts.length > 0 && (
        <section className="rounded-3xl border border-white/10 bg-slate-900/80 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4 mb-4">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-xl bg-purple-500/15 text-purple-300 border border-purple-400/30 text-sm">
                👤
              </span>
              <div>
                <h2 className="text-base sm:text-lg font-black text-white">
                  New Account Registrations Awaiting Activation
                </h2>
                <p className="text-[11px] text-slate-400">
                  Employees who requested accounts via self-registration. Activate to grant portal login access.
                </p>
              </div>
            </div>
            <span className="rounded-full bg-purple-400/15 border border-purple-400/35 px-2.5 py-0.5 text-xs font-bold text-purple-200">
              {filteredAccounts.length} Pending
            </span>
          </div>

          <div className="space-y-3.5">
            {filteredAccounts.map(acc => (
              <div
                key={acc.id}
                className="rounded-2xl border border-white/10 bg-slate-950/70 p-4 sm:p-5 flex flex-wrap items-center justify-between gap-3 transition hover:border-purple-400/40"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">{acc.display_name || acc.username}</span>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-cyan-300">
                      @{acc.username}
                    </span>
                    <span className="rounded-full bg-purple-500/20 px-2.5 py-0.5 text-[11px] font-bold text-purple-200 border border-purple-400/30">
                      {acc.role || 'Staff'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    Requested on: {acc.created_at ? new Date(acc.created_at).toLocaleString() : 'Recently'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleActivateAccount(acc)}
                    disabled={actionBusy}
                    className="inline-flex items-center gap-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-3.5 py-1.5 text-xs font-black text-slate-950 hover:brightness-110 shadow-md shadow-emerald-500/20 transition active:scale-[0.98]"
                  >
                    <UserCheck size={13} />
                    <span>✓ Activate Account</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteAccount(acc)}
                    disabled={actionBusy}
                    className="inline-flex items-center gap-1 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-300 transition"
                  >
                    <XCircle size={13} />
                    <span>✕ Delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
