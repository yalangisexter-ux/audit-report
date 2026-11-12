import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Download, Eye, FileText, FolderOpen, Printer } from 'lucide-react';
import { jsPDF } from 'jspdf';

export function generateExecutivePdf(text, meta = {}) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 36;
  const contentWidth = pageWidth - margin * 2;
  let y = margin;

  const checkPageBreak = (needed = 16) => {
    if (y + needed > pageHeight - margin - 25) {
      doc.addPage();
      y = margin;
      drawHeader();
    }
  };

  const drawHeader = () => {
    doc.setFillColor(16, 43, 66);
    doc.rect(margin, y, contentWidth, 40, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(255, 255, 255);
    doc.text('RAW STRENGTH CALISTHENICS', margin + 12, y + 17);
    doc.setFontSize(8);
    doc.setTextColor(0, 174, 234);
    doc.text('EXECUTIVE AUDIT  •  OPERATIONS OS  •  v1.3.82', margin + 12, y + 30);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(224, 242, 254);
    const dateStr = meta.date ? `Report Date: ${meta.date}` : `Date: ${new Date().toISOString().slice(0, 10)}`;
    doc.text(dateStr, pageWidth - margin - 12, y + 17, { align: 'right' });
    doc.text(meta.report_type || 'Operations Audit', pageWidth - margin - 12, y + 30, { align: 'right' });
    y += 50;
  };

  drawHeader();

  const lines = String(text || '').split('\n');
  for (let rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      y += 5;
      continue;
    }

    if (line.startsWith('RAW STRENGTH CALISTHENICS') || line.startsWith('Report date:') || line.startsWith('Scope:')) {
      continue;
    }

    if (
      line === 'DAILY SUMMARY' ||
      line.startsWith('EMPLOYEE:') ||
      line.startsWith('PRODUCT CATALOG') ||
      line.startsWith('SERVICE CATALOG') ||
      line.startsWith('ATTENDANCE SUMMARY') ||
      line.startsWith('PRODUCTIVITY') ||
      line.startsWith('STORE DIRECTORY')
    ) {
      checkPageBreak(38);
      y += 6;
      doc.setFillColor(240, 249, 255);
      doc.roundedRect(margin, y - 2, contentWidth, 20, 2, 2, 'F');
      doc.setDrawColor(0, 174, 234);
      doc.setLineWidth(2);
      doc.line(margin, y - 2, margin, y + 18);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(16, 43, 66);
      doc.text(line, margin + 8, y + 12);
      y += 24;
      continue;
    }

    if (line.startsWith('•') || line.startsWith('-')) {
      checkPageBreak(18);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(31, 41, 55);
      const splitLines = doc.splitTextToSize(line, contentWidth - 14);
      for (const sl of splitLines) {
        checkPageBreak(14);
        doc.text(sl, margin + 10, y + 7);
        y += 12;
      }
      continue;
    }

    if (line.includes(':')) {
      checkPageBreak(16);
      const colonIdx = line.indexOf(':');
      const label = line.slice(0, colonIdx + 1);
      const val = line.slice(colonIdx + 1);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.5);
      doc.setTextColor(16, 43, 66);
      const labelWidth = doc.getTextWidth(label + ' ');
      doc.text(label, margin + 6, y + 7);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(31, 41, 55);
      const splitVal = doc.splitTextToSize(val.trim(), contentWidth - labelWidth - 12);
      if (splitVal.length === 1) {
        doc.text(splitVal[0], margin + 6 + labelWidth, y + 7);
        y += 13;
      } else {
        doc.text(splitVal[0], margin + 6 + labelWidth, y + 7);
        y += 13;
        for (let i = 1; i < splitVal.length; i++) {
          checkPageBreak(13);
          doc.text(splitVal[i], margin + 6 + 14, y + 7);
          y += 12;
        }
      }
      continue;
    }

    checkPageBreak(15);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(55, 65, 81);
    const bodyLines = doc.splitTextToSize(line, contentWidth - 8);
    for (const bl of bodyLines) {
      checkPageBreak(13);
      doc.text(bl, margin + 6, y + 7);
      y += 12;
    }
  }

  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.5);
    doc.line(margin, pageHeight - margin + 4, pageWidth - margin, pageHeight - margin + 4);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(100, 116, 139);
    doc.text('Raw Strength Calisthenics  •  Confidential Operations Audit', margin, pageHeight - margin + 16);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - margin, pageHeight - margin + 16, { align: 'right' });
  }

  return doc;
}

const field = 'w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400';
const button = 'inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50';
const secondary = 'inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-cyan-200 disabled:opacity-50';
const defaults = {
  summary:true, identity:true, target:true, contact:false, work_status:true, late_links:true,
  missing_proof:true, target_status:true, tasks:true, target_qty:true, actual_qty:true,
  completion_pct:true, priority:true, details:true, due_time:true, proof:true,
  proof_notes:false, custom_values:true, next_action:true, remarks:true, expose_link:false,
  pending:true, attendance_identity:true, attendance_status:true,
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
    ['remarks','Manager remarks'],['expose_link','Expose full proof URLs'],['pending','Pending items']
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

const businessOptions = [
  ['business_products','Product catalog and available stock'],
  ['business_services','Service catalog']
];

const today = () => {
  const d = new Date();
  return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
};
const escapeHtml = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

export default function PrintCenter({ employees = [], archive = [], apiFetch, notify = () => {}, onOpenArchive = () => {} }) {
  const [report,setReport] = useState({date:today(),report_type:'Audit / EOD',employee_id:'',exclude_employee_id:'',output_format:'docx',options:{...defaults}});
  const [preferencesLoaded,setPreferencesLoaded] = useState(false);
  const preferenceWrites = useRef({});
  const previewSequence = useRef(0);
  const previewTimer = useRef(null);
  const [reportText,setReportText] = useState('');
  const [recordCount,setRecordCount] = useState(null);
  const [busy,setBusy] = useState(false);
  const [previewBusy,setPreviewBusy] = useState(false);
  const [archivedReportId,setArchivedReportId] = useState('');
  const individual = Boolean(report.employee_id);
  const selectedArchivedReport = archive.find(item => String(item.id) === String(archivedReportId)) || null;
  const archivedSelected = Boolean(selectedArchivedReport);
  const visibleOptions = useMemo(() => optionGroups[report.report_type] || optionGroups['Audit / EOD'], [report.report_type]);

  useEffect(() => {
    if (archivedReportId && !archive.some(item => String(item.id) === String(archivedReportId))) {
      setArchivedReportId('');
      setReportText('');
      setRecordCount(null);
    }
  }, [archive, archivedReportId]);

  useEffect(() => {
    let active = true;
    apiFetch('/reports/options').then(result => {
      if (!active) return;
      setReport(previous => ({
        ...previous,
        options: {
          ...defaults,
          ...(result?.options || {}),
          business_products: previous.options.business_products,
          business_services: previous.options.business_services
        }
      }));
    }).catch(error => {
      if (active) notify('Could not load saved report options: ' + error.message);
    }).finally(() => {
      if (active) setPreferencesLoaded(true);
    });
    return () => { active = false; };
  }, []);

  const changeArchivedReport = event => {
    const value = event.target.value;
    setArchivedReportId(value);
    setReportText(value
      ? 'Historical archived PDF selected. Use View / Print to open it, or Export Copy to download it.'
      : '');
    setRecordCount(null);
  };
  const payload = () => ({
    date:report.date,
    report_type:report.report_type,
    employee_id:report.employee_id ? Number(report.employee_id) : null,
    exclude_employee_id:!individual && report.exclude_employee_id ? Number(report.exclude_employee_id) : null,
    options:report.options
  });

  const runPreview = async () => {
    const requestId = ++previewSequence.current;
    setPreviewBusy(true);
    try {
      const result = await apiFetch('/reports/preview',{method:'POST',body:JSON.stringify(payload())});
      if (requestId === previewSequence.current) {
        setReportText(result.preview_text || 'The report service returned no preview content.');
        setRecordCount(result.record_count ?? null);
      }
    } catch (error) {
      if (requestId === previewSequence.current) notify(error.message);
    } finally {
      if (requestId === previewSequence.current) setPreviewBusy(false);
    }
  };

  const preview = async event => {
    if (event) event.preventDefault();
    if (archivedSelected) return;
    if (previewTimer.current !== null) {
      window.clearTimeout(previewTimer.current);
      previewTimer.current = null;
    }
    await runPreview();
  };

  useEffect(() => {
    if (!preferencesLoaded || archivedSelected) return undefined;
    const timer = window.setTimeout(() => {
      previewTimer.current = null;
      runPreview();
    }, 300);
    previewTimer.current = timer;
    return () => {
      window.clearTimeout(timer);
      if (previewTimer.current === timer) previewTimer.current = null;
      previewSequence.current += 1;
    };
  }, [
    preferencesLoaded, archivedSelected, report.date, report.report_type,
    report.employee_id, report.exclude_employee_id, report.options
  ]);

  const download = async (quiet = false) => {
    setBusy(true);
    try {
      if (!archivedSelected && report.output_format === 'pdf') {
        let content = reportText;
        if (!content) {
          const result = await apiFetch('/reports/preview', { method: 'POST', body: JSON.stringify(payload()) });
          content = result.preview_text || '';
          setReportText(content);
          setRecordCount(result.record_count ?? null);
        }
        if (!content) throw new Error('No report content available to generate PDF.');
        const slug = String(report.report_type || 'report').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'report';
        const filename = `raw-strength-${slug}-${report.date || 'report'}.pdf`;
        const doc = generateExecutivePdf(content, payload());
        doc.save(filename);
        if (!quiet) notify('Executive PDF report downloaded: ' + filename);
        return true;
      }

      const activeToken = localStorage.getItem('rsc_auth_token') || '';
      const response = archivedSelected
        ? await fetch('/api/archive/' + selectedArchivedReport.id + '/download', {
            headers: activeToken ? { Authorization: 'Bearer ' + activeToken } : {}
          })
        : await fetch('/api/reports/export', {
            method:'POST',
            headers:{
              'Content-Type':'application/json',
              ...(activeToken ? {Authorization:'Bearer '+activeToken} : {})
            },
            body:JSON.stringify({...payload(),output_format:report.output_format})
          });
      if (!response.ok) {
        const body = await response.json().catch(()=>({}));
        throw new Error(body.detail || (archivedSelected
          ? 'Archived report export failed (' + response.status + ').'
          : 'Report export failed ('+response.status+').'));
      }
      const blob = await response.blob();
      if (archivedSelected && blob.type !== 'application/pdf') {
        throw new Error('The archive service did not return a PDF file.');
      }
      const disposition = response.headers.get('Content-Disposition') || '';
      const name = disposition.match(/filename="?([^";]+)"?/i);
      const filename = name
        ? name[1].trim()
        : (archivedSelected
          ? (selectedArchivedReport.file_name || ('archive-' + selectedArchivedReport.id + '.pdf'))
          : 'raw-strength-report.'+report.output_format);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(()=>window.URL.revokeObjectURL(url),1500);
      if (!quiet) notify((archivedSelected ? 'Archived report copy downloaded: ' : 'Report downloaded: ')+filename);
      return true;
    } catch (error) {
      notify(error.message);
      return false;
    } finally {
      setBusy(false);
    }
  };

  const print = async () => {
    if (!archivedSelected && !reportText) return notify('Generate a report preview first.');
    if (!archivedSelected && report.output_format === 'csv') {
      return notify('CSV files are for data export and cannot be sent directly to the print handler. Choose Word or PDF to print, or use Generate / Save to export CSV.');
    }
    if (!archivedSelected && report.output_format === 'docx') {
      const exported = await download(true);
      if (exported) notify('Word report downloaded. Open it in Microsoft Word to print.');
      return;
    }

    if (!archivedSelected && report.output_format === 'pdf') {
      try {
        const doc = generateExecutivePdf(reportText, payload());
        const blobUrl = doc.output('bloburl');
        const printWindow = window.open(blobUrl, '_blank');
        if (!printWindow) {
          doc.save(`raw-strength-${report.date || 'report'}.pdf`);
          notify('Pop-up was blocked; your Executive PDF has been downloaded directly.');
        } else {
          notify('Executive PDF opened for preview and printing.');
        }
      } catch (err) {
        notify('Failed to generate PDF: ' + err.message);
      }
      return;
    }

    const target = window.open('', '_blank');
    if (!target) return notify('Allow pop-ups to open the PDF preview.');
    target.document.write('<!doctype html><html><head><title>Preparing Raw Strength PDF…</title></head><body style="font:14px Arial,sans-serif;padding:32px;color:#102B42">Preparing your branded PDF…</body></html>');
    target.document.close();
    setBusy(true);
    try {
      const token = localStorage.getItem('rsc_auth_token') || '';
      const response = await fetch('/api/archive/' + selectedArchivedReport.id + '/view', {
        headers: token ? { Authorization: 'Bearer ' + token } : {}
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Archived PDF could not be opened (' + response.status + ').');
      }
      const blob = await response.blob();
      if (blob.type !== 'application/pdf') throw new Error('The archive service did not return a PDF file.');
      const url = window.URL.createObjectURL(blob);
      target.opener = null;
      target.location.href = url;
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch (error) {
      target.close();
      notify(error.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleOption = (key, checked) => {
    setReport(previous=>({...previous,options:{...previous.options,[key]:checked}}));
    if (key !== 'business_products' && key !== 'business_services') {
      const previousWrite = preferenceWrites.current[key] || Promise.resolve();
      const nextWrite = previousWrite.catch(() => {}).then(() =>
        apiFetch('/reports/options', {
          method:'PUT',
          body:JSON.stringify({options:{[key]:checked}})
        })
      );
      preferenceWrites.current[key] = nextWrite;
      nextWrite.catch(error => notify('Could not save report option: ' + error.message));
    }
    setReportText('');
  };

  return <div className="space-y-4">
    <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div><h2 className="text-lg font-bold text-white">Print Center</h2><p className="text-xs text-slate-400">Preview, filter and export employee and operations reports.</p></div>
        <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">Windows report workflow</span>
      </div>
      <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" onSubmit={preview}>
        <label className="text-xs text-slate-400">Report date<input className={field+' mt-1'} type="date" max={today()} value={report.date} onChange={e=>{setReport(p=>({...p,date:e.target.value}));setReportText('')}} required disabled={archivedSelected}/></label>
        <label className="text-xs text-slate-400">Report type<select className={field+' mt-1'} value={report.report_type} onChange={e=>{setReport(p=>({...p,report_type:e.target.value}));setReportText('')}} disabled={archivedSelected}>{Object.keys(optionGroups).map(type=><option key={type}>{type}</option>)}</select></label>
        <label className="text-xs text-slate-400">Report scope<select className={field+' mt-1'} value={individual?'individual':'all'} onChange={e=>{setReport(p=>({...p,employee_id:e.target.value==='individual'?(employees[0]?.id?String(employees[0].id):''):'',exclude_employee_id:''}));setReportText('')}} disabled={archivedSelected}><option value="all">Consolidated — all employees</option><option value="individual">Individual — selected employee</option></select></label>
        <label className="text-xs text-slate-400">Output format<select className={field+' mt-1'} value={report.output_format} onChange={e=>setReport(p=>({...p,output_format:e.target.value}))} disabled={archivedSelected}><option value="docx">Word (.docx)</option><option value="pdf">PDF (.pdf)</option><option value="csv">CSV (.csv)</option></select></label>
        <label className="text-xs text-slate-400">Employee<select className={field+' mt-1'} disabled={!individual||archivedSelected} required={individual&&!archivedSelected} value={report.employee_id} onChange={e=>{setReport(p=>({...p,employee_id:e.target.value}));setReportText('')}}><option value="">Select employee</option>{employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name} ({employee.employee_code||'No ID'})</option>)}</select></label>
        <label className="text-xs text-slate-400">Exclude employee (consolidated only)<select className={field+' mt-1'} disabled={individual||archivedSelected} value={report.exclude_employee_id} onChange={e=>{setReport(p=>({...p,exclude_employee_id:e.target.value}));setReportText('')}}><option value="">Exclude none</option>{employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name} ({employee.employee_code||'No ID'})</option>)}</select></label>
        <label className="text-xs text-slate-400 sm:col-span-2 xl:col-span-2">Historical archived PDF (optional)
          <select className={field+' mt-1'} value={archivedReportId} onChange={changeArchivedReport}>
            <option value="">Generated report for selected date</option>
            {archive.map(item=><option key={item.id} value={item.id}>{item.report_date||'Unknown date'} — {item.file_name} — {item.employee_name||'All employees'}</option>)}
          </select>
        </label>
        <div className="flex items-end sm:col-span-2 xl:col-span-2"><button className={button+' w-full'} disabled={busy||previewBusy||!report.date||archivedSelected||!preferencesLoaded}><Eye size={16}/>{previewBusy?'Previewing…':'Generate preview'}</button></div>
      </form>
      <div className="mt-5 rounded-xl border border-white/10 bg-slate-950/60 p-3">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold text-cyan-200">{archivedSelected ? 'Historical archived PDF selected' : report.report_type+' content options'}</h3><span className="text-xs text-slate-500">Unchecked fields are omitted from preview and exports.</span></div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {visibleOptions.map(([key,label])=><label key={key} className="flex items-start gap-2 rounded-lg border border-white/5 px-3 py-2 text-xs text-slate-300"><input type="checkbox" className="mt-0.5 accent-cyan-400" checked={Boolean(report.options[key])} disabled={archivedSelected||!preferencesLoaded} onChange={e=>toggleOption(key,e.target.checked)}/><span>{label}</span></label>)}
        </div>
      </div>
      <div className="mt-5 rounded-xl border border-white/10 bg-slate-950/60 p-3">
        <h3 className="mb-3 text-sm font-bold text-cyan-200">Optional business data — include these catalogs in the report</h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {businessOptions.map(([key,label])=><label key={key} className="flex items-start gap-2 rounded-lg border border-white/5 px-3 py-2 text-xs text-slate-300"><input type="checkbox" className="mt-0.5 accent-cyan-400" checked={Boolean(report.options[key])} disabled={archivedSelected} onChange={e=>toggleOption(key,e.target.checked)}/><span>{label}</span></label>)}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className={button} onClick={()=>download()} disabled={busy||previewBusy||!preferencesLoaded}><Download size={16}/>{busy?'Preparing…':archivedSelected?'Export archived PDF copy':'Generate / Download '+report.output_format.toUpperCase()}</button>
        <button type="button" className={secondary} onClick={print} disabled={(!reportText&&!archivedSelected)||busy||previewBusy}><Printer size={16}/>{archivedSelected?'View / Print archived PDF':report.output_format==='docx'?'Download Word to print':report.output_format==='csv'?'CSV export only':'Open PDF preview / Print'}</button>
        <button type="button" className={secondary} onClick={onOpenArchive} disabled={busy||previewBusy}><FolderOpen size={16}/>Browse saved reports</button>
      </div>
      <p className="mt-3 text-xs text-slate-500">Employee exclusion applies only to this report. It never deletes or changes employee records. Report exports use the same filters and content options as the preview. Historical PDFs are read from the shared archive and are never modified by viewing or exporting.</p>
    </section>
    <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10">
      <div className="mb-3 flex items-center justify-between gap-2"><h3 className="font-bold text-white">Live report preview</h3>{recordCount!==null&&<span className="text-xs text-slate-400">{recordCount} employee records</span>}</div>
      {reportText?<pre className="max-h-[620px] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-950 p-4 text-xs leading-relaxed text-slate-300">{reportText}</pre>:<div className="rounded-lg border border-dashed border-white/10 p-8 text-center text-sm text-slate-500"><FileText className="mx-auto mb-2 opacity-50" size={28}/>Select report settings and generate a preview.</div>}
    </section>
  </div>;
}
