import React, { useMemo, useState } from 'react';
import { Download, Eye, FileText, Printer } from 'lucide-react';

const field = 'w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400';
const button = 'inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50';
const secondary = 'inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-cyan-200 disabled:opacity-50';
const defaults = {
  summary:true, identity:true, target:true, contact:false, work_status:true, late_links:true,
  missing_proof:true, target_status:true, tasks:true, target_qty:true, actual_qty:true,
  completion_pct:true, priority:true, details:true, due_time:true, proof:true,
  proof_notes:false, custom_values:true, next_action:true, remarks:true, expose_link:false,
  pending:true, attendance:true, attendance_identity:true, attendance_status:true,
  attendance_times:true, attendance_remarks:true, attendance_summary:true,
  details_identity:true, details_contact:true, details_joining:true, details_status:true,
  details_notes:true, productivity_identity:true, productivity_metrics:true,
  productivity_explanation:true, productivity_tracking:true, productivity_tasks:true,
  business_products:false, business_services:false
};
const optionGroups = {
  'Audit / EOD': [
    ['summary','Daily summary'],['identity','Employee ID / department / role'],['contact','Phone / email'],
    ['target','Employee target'],['work_status','Work / EOD status'],['late_links','Late / links status'],
    ['missing_proof','Missing proof'],['target_status','Target status'],['tasks','Task names and status'],
    ['target_qty','Target quantity'],['actual_qty','Actual quantity'],['completion_pct','Completion %'],
    ['priority','Priority'],['details','Task details'],['due_time','Due time'],['proof','Proof / evidence'],
    ['proof_notes','Proof notes'],['custom_values','Custom tracking fields'],['next_action','Next action'],
    ['remarks','Manager remarks'],['expose_link','Expose full proof URLs'],['pending','Pending items'],
    ['attendance','Attendance status and times'],['business_products','Product catalog and available stock'],
    ['business_services','Service catalog']
  ],
  'Employee Attendance': [
    ['attendance_summary','Attendance summary'],['attendance_identity','Employee ID / department'],
    ['attendance_status','Attendance status'],['attendance_times','Check-in / check-out / break / net hours'],
    ['attendance_remarks','Attendance remarks']
  ],
  'Employee Details': [
    ['details_identity','Employee ID / department / role'],['details_contact','Phone / email'],
    ['details_joining','Joining date'],['details_status','Active / inactive status'],['details_notes','Employee notes']
  ],
  'Employee Productivity': [
    ['productivity_identity','Employee ID / department'],['productivity_metrics','Productivity scores'],
    ['productivity_explanation','Scoring explanation'],['productivity_tracking','Tracking and attendance totals'],
    ['productivity_tasks','Task progress details']
  ]
};

const today = () => {
  const d = new Date();
  return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
};
const escapeHtml = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

export default function PrintCenter({ employees = [], apiFetch, notify = () => {} }) {
  const [report,setReport] = useState({date:today(),report_type:'Audit / EOD',employee_id:'',exclude_employee_id:'',output_format:'pdf',options:{...defaults}});
  const [reportText,setReportText] = useState('');
  const [recordCount,setRecordCount] = useState(null);
  const [busy,setBusy] = useState(false);
  const individual = Boolean(report.employee_id);
  const visibleOptions = useMemo(() => optionGroups[report.report_type] || optionGroups['Audit / EOD'], [report.report_type]);
  const payload = () => ({
    date:report.date,
    report_type:report.report_type,
    employee_id:report.employee_id ? Number(report.employee_id) : null,
    exclude_employee_id:!individual && report.exclude_employee_id ? Number(report.exclude_employee_id) : null,
    options:report.options
  });

  const preview = async event => {
    if (event) event.preventDefault();
    setBusy(true);
    try {
      const result = await apiFetch('/reports/preview',{method:'POST',body:JSON.stringify(payload())});
      setReportText(result.preview_text || 'The report service returned no preview content.');
      setRecordCount(result.record_count ?? null);
    } catch (error) {
      notify(error.message);
    } finally {
      setBusy(false);
    }
  };

  const download = async () => {
    setBusy(true);
    try {
      const response = await fetch('/api/reports/export',{
        method:'POST',
        headers:{
          'Content-Type':'application/json',
          ...(localStorage.getItem('rsc_auth_token') ? {Authorization:'Bearer '+localStorage.getItem('rsc_auth_token')} : {})
        },
        body:JSON.stringify({...payload(),output_format:report.output_format})
      });
      if (!response.ok) {
        const body = await response.json().catch(()=>({}));
        throw new Error(body.detail || 'Report export failed ('+response.status+').');
      }
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      const name = disposition.match(/filename="?([^";]+)"?/i);
      const filename = name ? name[1] : 'raw-strength-report.'+report.output_format;
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(()=>window.URL.revokeObjectURL(url),1500);
      notify('Report downloaded: '+filename);
    } catch (error) {
      notify(error.message);
    } finally {
      setBusy(false);
    }
  };

  const print = () => {
    if (!reportText) return notify('Generate a report preview first.');
    const target = window.open('','_blank');
    if (!target) return notify('Allow pop-ups to open the print preview.');
    target.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Raw Strength Report</title><style>@page{size:A4;margin:16mm}body{font:12px Arial,sans-serif;color:#111;line-height:1.45}h1{font-size:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:11px Arial,sans-serif}</style></head><body><h1>Raw Strength Calisthenics</h1><pre>'+escapeHtml(reportText)+'</pre><script>window.onload=()=>{window.focus();window.print()}<\/script></body></html>');
    target.document.close();
  };

  const toggleOption = (key, checked) => {
    setReport(previous=>({...previous,options:{...previous.options,[key]:checked}}));
    setReportText('');
  };

  return <div className="space-y-4">
    <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div><h2 className="text-lg font-bold text-white">Print Center</h2><p className="text-xs text-slate-400">Preview, filter and export employee and operations reports.</p></div>
        <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">Windows report workflow</span>
      </div>
      <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={preview}>
        <label className="text-xs text-slate-400">Report date<input className={field+' mt-1'} type="date" max={today()} value={report.date} onChange={e=>{setReport(p=>({...p,date:e.target.value}));setReportText('')}} required/></label>
        <label className="text-xs text-slate-400">Report type<select className={field+' mt-1'} value={report.report_type} onChange={e=>{setReport(p=>({...p,report_type:e.target.value}));setReportText('')}}>{Object.keys(optionGroups).map(type=><option key={type}>{type}</option>)}</select></label>
        <label className="text-xs text-slate-400">Report scope<select className={field+' mt-1'} value={individual?'individual':'all'} onChange={e=>{setReport(p=>({...p,employee_id:e.target.value==='individual'?(employees[0]?.id?String(employees[0].id):''):'',exclude_employee_id:''}));setReportText('')}}><option value="all">Consolidated — all employees</option><option value="individual">Individual — selected employee</option></select></label>
        <label className="text-xs text-slate-400">Output format<select className={field+' mt-1'} value={report.output_format} onChange={e=>setReport(p=>({...p,output_format:e.target.value}))}><option value="docx">Word (.docx)</option><option value="pdf">PDF (.pdf)</option><option value="csv">CSV (.csv)</option></select></label>
        <label className="text-xs text-slate-400">Employee<select className={field+' mt-1'} disabled={!individual} required={individual} value={report.employee_id} onChange={e=>{setReport(p=>({...p,employee_id:e.target.value}));setReportText('')}}><option value="">Select employee</option>{employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name} ({employee.employee_code||'No ID'})</option>)}</select></label>
        <label className="text-xs text-slate-400">Exclude employee (consolidated only)<select className={field+' mt-1'} disabled={individual} value={report.exclude_employee_id} onChange={e=>{setReport(p=>({...p,exclude_employee_id:e.target.value}));setReportText('')}}><option value="">Exclude none</option>{employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name} ({employee.employee_code||'No ID'})</option>)}</select></label>
        <div className="flex items-end sm:col-span-2 xl:col-span-2"><button className={button+' w-full'} disabled={busy||!report.date}><Eye size={16}/>{busy?'Working…':'Generate preview'}</button></div>
      </form>
      <div className="mt-5 rounded-xl border border-white/10 bg-slate-950/60 p-3">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold text-cyan-200">{report.report_type} content options</h3><span className="text-xs text-slate-500">Unchecked fields are omitted from preview and exports.</span></div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {visibleOptions.map(([key,label])=><label key={key} className="flex items-start gap-2 rounded-lg border border-white/5 px-3 py-2 text-xs text-slate-300"><input type="checkbox" className="mt-0.5 accent-cyan-400" checked={Boolean(report.options[key])} onChange={e=>toggleOption(key,e.target.checked)}/><span>{label}</span></label>)}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className={button} onClick={download} disabled={busy}><Download size={16}/>{busy?'Preparing…':'Generate / Download '+report.output_format.toUpperCase()}</button>
        <button type="button" className={secondary} onClick={print} disabled={!reportText||busy}><Printer size={16}/>Print preview / Save PDF</button>
      </div>
      <p className="mt-3 text-xs text-slate-500">Employee exclusion applies only to this report. It never deletes or changes employee records. Report exports use the same filters and content options as the preview.</p>
    </section>
    <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
      <div className="mb-3 flex items-center justify-between gap-2"><h3 className="font-bold text-white">Live report preview</h3>{recordCount!==null&&<span className="text-xs text-slate-400">{recordCount} employee records</span>}</div>
      {reportText?<pre className="max-h-[620px] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-950 p-4 text-xs leading-relaxed text-slate-300">{reportText}</pre>:<div className="rounded-lg border border-dashed border-white/10 p-8 text-center text-sm text-slate-500"><FileText className="mx-auto mb-2 opacity-50" size={28}/>Select report settings and generate a preview.</div>}
    </section>
  </div>;
}
