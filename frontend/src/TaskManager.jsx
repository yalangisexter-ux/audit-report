import { useEffect, useMemo, useState } from 'react';
import { Plus, Pencil, Trash2, CheckSquare, Square, ExternalLink, Link2, Save, X, RefreshCw, Check, Send } from 'lucide-react';

const field = 'w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400';
const btn = 'inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50';
const statuses = ['', 'Not started','In progress','Partially completed','Submitted','Completed','Blocked','Pending review','Pending','Cancelled'];
const priorities = ['Low','Normal','High','Urgent'];
const today = () => { const d = new Date(); return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-'); };
const emptyTask = () => ({
  task_date: today(), employee_id: '', department: '', title: '', details: '', due_time: '',
  target_qty: '', actual_qty: '', progress: 0, priority: 'Normal', status: 'Not started',
  proof_url: '', proof_note: '', next_action: '', expose_link: false, approval_status: 'Pending'
});

function customRowsFrom(task) {
  let raw = task?.custom_fields ?? task?.custom_values ?? [];
  if (typeof raw === 'string') {
    try { raw = JSON.parse(raw); }
    catch { raw = raw.split(/\r?\n/).filter(Boolean).map(line => { const i=line.indexOf(':'); return i<0?{key:line.trim(),value:''}:{key:line.slice(0,i).trim(),value:line.slice(i+1).trim()}; }); }
  }
  if (Array.isArray(raw)) return raw.map(item => ({key:String(item?.key ?? item?.k ?? ''),value:String(item?.value ?? item?.v ?? '')}));
  if (raw && typeof raw === 'object') return Object.entries(raw).map(([key,value])=>({key:String(key),value:String(value??'')}));
  return [];
}

function TaskFields({value,onChange,employees,customRows,setCustomRows,lockAssignment=false,lockDate=false,isAdmin=false,isEmployee=false}) {
  const update = (key,next) => onChange(previous => {
    const updated = {...previous,[key]:next};
    if (key === 'employee_id' || key === 'task_date') {
      updated.target_qty = '';
      updated.actual_qty = '';
    }
    if (key === 'status' && next === 'Completed') updated.progress = 100;
    if (key === 'progress' && Number(next) === 100) updated.status = 'Completed';
    if (key === 'target_qty' || key === 'actual_qty') {
      const target = Number(key === 'target_qty' ? next : updated.target_qty);
      const actual = Number(key === 'actual_qty' ? next : updated.actual_qty);
      if (Number.isFinite(target) && Number.isFinite(actual) && target > 0) {
        updated.progress = Math.max(0,Math.min(100,Math.round(actual/target*100)));
        if (updated.progress === 100) updated.status = 'Completed';
        else if (updated.progress > 0 && updated.status === 'Not started') updated.status = 'Partially completed';
      }
    }
    return updated;
  });
  const updateRow = (index,key,next) => setCustomRows(rows=>rows.map((row,i)=>i===index?{...row,[key]:next}:row));
  const addRow = key => setCustomRows(rows=>[...rows,{key:key||'',value:''}]);
  return <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
    <label className="text-xs text-slate-400">Task date<input className={field+' mt-1'} type="date" required disabled={lockDate} value={value.task_date||today()} onChange={e=>update('task_date',e.target.value)}/></label>
    <label className="text-xs text-slate-400">Employee *<select className={field+' mt-1'} required disabled={lockAssignment || isEmployee} value={value.employee_id??''} onChange={e=>update('employee_id',e.target.value)}><option value="">Select employee</option>{employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name} ({employee.employee_code||employee.id})</option>)}</select></label>
    <label className="text-xs text-slate-400">Department / section<input className={field+' mt-1'} value={value.department??''} onChange={e=>update('department',e.target.value)} placeholder="Select or enter department"/></label>
    <label className="text-xs text-slate-400 md:col-span-2 xl:col-span-3">Assigned task *<input className={field+' mt-1'} required value={value.title??''} onChange={e=>update('title',e.target.value)} placeholder="Enter assigned task title / description"/></label>
    <label className="text-xs text-slate-400">Due time<input className={field+' mt-1'} type="time" value={value.due_time??''} onChange={e=>update('due_time',e.target.value)}/></label>
    <label className="text-xs text-slate-400">Target quantity<input className={field+' mt-1'} value={value.target_qty??''} onChange={e=>update('target_qty',e.target.value)} placeholder="e.g. 10"/></label>
    <label className="text-xs text-slate-400">Actual quantity<input className={field+' mt-1'} value={value.actual_qty??''} onChange={e=>update('actual_qty',e.target.value)} placeholder="e.g. 5"/></label>
    <label className="text-xs text-slate-400">Completion %<input className={field+' mt-1'} type="number" min="0" max="100" value={Number(value.progress)||0} onChange={e=>update('progress',Number(e.target.value))}/></label>
    <label className="text-xs text-slate-400">Priority<select className={field+' mt-1'} value={value.priority||'Normal'} onChange={e=>update('priority',e.target.value)}>{priorities.map(item=><option key={item}>{item}</option>)}</select></label>
    <label className="text-xs text-slate-400">Status<select className={field+' mt-1'} value={value.status??'Not started'} onChange={e=>update('status',e.target.value)}>{statuses.map(item=><option key={item||'__blank'} value={item}>{item||'Not selected'}</option>)}</select></label>
    {isAdmin && (
      <label className="text-xs text-slate-400">Admin approval status<select className={field+' mt-1'} value={value.approval_status||'Pending'} onChange={e=>update('approval_status',e.target.value)}><option value="Pending">⏳ Pending approval</option><option value="Approved">✓ Approved</option><option value="Rejected">✕ Rejected</option></select></label>
    )}
    {isEmployee && (
      <div className="flex items-center gap-2 rounded-lg border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-200 md:col-span-2 xl:col-span-3">
        <span>Approval status: <b className="uppercase">{value.approval_status || 'Pending'}</b></span>
        <span className="text-slate-400">· Admin will review, edit, and approve your submitted tasks to generate the EOD report.</span>
      </div>
    )}
    <label className="text-xs text-slate-400 md:col-span-2 xl:col-span-3">Task details / notes<textarea className={field+' mt-1'} rows="2" value={value.details??''} onChange={e=>update('details',e.target.value)}/></label>
    <label className="text-xs text-slate-400 md:col-span-2 xl:col-span-3">Proof / evidence links (one URL or path per line)<textarea className={field+' mt-1'} rows="2" value={value.proof_url??''} onChange={e=>update('proof_url',e.target.value)} placeholder="https://..."/></label>
    <label className="text-xs text-slate-400">Proof note<input className={field+' mt-1'} value={value.proof_note??''} onChange={e=>update('proof_note',e.target.value)}/></label>
    <label className="text-xs text-slate-400 md:col-span-2">Next action / manager follow-up<textarea className={field+' mt-1'} rows="2" value={value.next_action??''} onChange={e=>update('next_action',e.target.value)}/></label>
    <label className="flex items-center gap-2 self-end rounded-lg border border-white/10 p-3 text-xs text-slate-300"><input type="checkbox" checked={Boolean(value.expose_link)} onChange={e=>update('expose_link',e.target.checked)}/> Expose full evidence URL in reports</label>
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3 md:col-span-2 xl:col-span-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2"><div><h3 className="text-sm font-bold text-white">Custom tracking fields</h3><p className="text-xs text-slate-500">Add any key/value pair, such as Tracked By, Client, Location or Equipment.</p></div><button type="button" className="rounded-lg border border-cyan-400/30 px-3 py-2 text-xs text-cyan-200" onClick={()=>addRow('')}>+ Add field</button></div>
      <div className="mb-3 flex flex-wrap gap-1">{['Tracked By','Client','Location','Batch','Priority Code','Machine','Tag','Reviewer'].map(key=><button type="button" key={key} onClick={()=>addRow(key)} className="rounded-md border border-white/10 px-2 py-1 text-[11px] text-cyan-200">+ {key}</button>)}</div>
      <div className="space-y-2">{customRows.map((row,index)=><div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2"><input className={field} aria-label="Custom field name" placeholder="Field name" value={row.key} onChange={e=>updateRow(index,'key',e.target.value)}/><input className={field} aria-label="Custom field value" placeholder="Value" value={row.value} onChange={e=>updateRow(index,'value',e.target.value)}/><button type="button" className="rounded-lg border border-rose-400/20 px-3 text-rose-300" onClick={()=>setCustomRows(rows=>rows.filter((_,i)=>i!==index))}>×</button></div>)}</div>
    </div>
  </div>;
}

export default function TaskManager({tasks=[],employees=[],user,apiFetch,onReload,notify,mode='manager'}) {
  const trackerMode = mode === 'tracker';
  const isEmployee = String(user?.role||'').toLowerCase() === 'employee';
  let perms = user?.permissions;
  if (typeof perms === 'string') { try { perms = JSON.parse(perms); } catch { perms = null; } }
  const taskAccess = (perms && typeof perms === 'object' && perms.tasks)
    ? perms.tasks
    : (isEmployee ? 'approval' : (['admin','developer'].includes(String(user?.role||'').toLowerCase()) ? 'full' : 'write'));
  const canDelete = taskAccess === 'full' && !isEmployee;
  const isAdmin = (taskAccess === 'full' || ['admin','developer'].includes(String(user?.role||'').toLowerCase())) && !isEmployee;

  const [form,setForm] = useState(emptyTask);
  const [createOpen,setCreateOpen] = useState(!trackerMode);
  const [customRows,setCustomRows] = useState([]);
  const [editing,setEditing] = useState(null);
  const [editForm,setEditForm] = useState(emptyTask);
  const [editRows,setEditRows] = useState([]);
  const [filters,setFilters] = useState(()=>({
    date: today(),
    employee: isEmployee && user?.employee_id ? String(user.employee_id) : (trackerMode ? '' : 'all'),
    status: 'all',
    priority: 'all',
    department: 'all',
    approval: 'all',
    search: ''
  }));

  useEffect(()=>{
    if(isEmployee && user?.employee_id){
      setFilters(prev => ({...prev, employee: String(user.employee_id)}));
      setForm(prev => ({...prev, employee_id: String(user.employee_id)}));
    }
  },[isEmployee, user?.employee_id]);

  useEffect(()=>{
    if(!trackerMode)return;
    setForm(previous=>({...previous,task_date:filters.date,employee_id:isEmployee&&user?.employee_id?String(user.employee_id):(filters.employee||'')}));
  },[trackerMode,filters.date,filters.employee,isEmployee,user?.employee_id]);

  useEffect(()=>{
    const activeForm = editing ? editForm : form;
    const employeeId = Number(activeForm.employee_id);
    const taskDate = String(activeForm.task_date||'').trim();
    if(!employeeId||!taskDate)return;
    let active = true;
    apiFetch('/employee-targets?employee_id='+encodeURIComponent(employeeId)+'&target_date='+encodeURIComponent(taskDate))
      .then(target=>{
        if(!active)return;
        const setActiveForm = editing ? setEditForm : setForm;
        setActiveForm(previous=>{
          if(Number(previous.employee_id)!==employeeId||String(previous.task_date||'')!==taskDate)return previous;
          return {...previous,target_qty:previous.target_qty||target.target||'',actual_qty:previous.actual_qty||target.target_status||''};
        });
      })
      .catch(()=>{});
    return ()=>{active=false;};
  },[editing,form.employee_id,form.task_date,editForm.employee_id,editForm.task_date]);

  const [selected,setSelected] = useState([]);
  const [bulkOpen,setBulkOpen] = useState(false);
  const [bulk,setBulk] = useState({
    title:{apply:false,value:''},status:{apply:false,value:'In progress'},priority:{apply:false,value:'Normal'},custom_values:{apply:false,value:''},
    progress:{apply:false,value:0},target_qty:{apply:false,value:''},actual_qty:{apply:false,value:''},
    department:{apply:false,value:''},next_action:{apply:false,value:''},expose_link:{apply:false,value:false},
    approval_status:{apply:false,value:'Approved'}
  });

  const departments = useMemo(()=>[...new Set((tasks||[]).map(task=>String(task.department||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b)),[tasks]);

  const visibleTasks = useMemo(()=>{
    const term=filters.search.trim().toLowerCase();
    return (tasks||[]).filter(task=>{
      if(isEmployee && user?.employee_id && Number(task.employee_id) !== Number(user.employee_id)) return false;
      if(trackerMode && !filters.employee)return false;
      if(filters.date!=='all' && String(task.task_date||'')!==filters.date)return false;
      if(filters.employee!=='all' && String(task.employee_id)!==filters.employee)return false;
      if(filters.status!=='all' && String(task.status||'')!==filters.status)return false;
      if(filters.priority!=='all' && String(task.priority||'')!==filters.priority)return false;
      if(filters.department!=='all' && String(task.department||'')!==filters.department)return false;
      if(filters.approval!=='all') {
        const isAppr = String(task.approval_status||'').toLowerCase() === 'approved';
        if (filters.approval === 'Approved' && !isAppr) return false;
        if (filters.approval === 'Pending' && isAppr) return false;
      }
      const custom=customRowsFrom(task).map(row=>row.key+': '+row.value).join(' ');
      const haystack=[task.id,task.title,task.employee_name,task.employee_code,task.department,task.status,task.priority,task.approval_status,task.next_action,task.manager_note,task.proof_url,custom].join(' ').toLowerCase();
      return !term || haystack.includes(term);
    }).sort((a,b)=>String(b.task_date||'').localeCompare(String(a.task_date||''))||Number(b.id)-Number(a.id));
  },[tasks,filters,trackerMode,isEmployee,user?.employee_id]);

  const updateFilter=(key,value)=>{setFilters(previous=>({...previous,[key]:value}));setSelected([]);};
  const refresh=async()=>{try{await onReload();notify('Task list refreshed');}catch(error){notify(error.message);}};

  const saveCreate=async event=>{
    event.preventDefault();
    const effectiveEmpId = isEmployee && user?.employee_id ? Number(user.employee_id) : Number(form.employee_id);
    if(!form.title.trim()||!effectiveEmpId){notify('Task title and employee are required.');return;}
    const payload={
      ...form,
      employee_id: effectiveEmpId,
      progress:Number(form.progress)||0,
      expose_link:form.expose_link?1:0,
      approval_status: isEmployee ? 'Pending' : (form.approval_status || 'Pending'),
      custom_values:customRows.filter(row=>row.key.trim()||row.value.trim()).map(row=>({key:row.key.trim(),value:row.value.trim()}))
    };
    payload.manager_note=payload.next_action||'';
    if(payload.status==='Completed')payload.progress=100;
    try{
      await apiFetch('/tasks',{method:'POST',body:JSON.stringify(payload)});
      const reset=emptyTask();
      if(isEmployee && user?.employee_id){
        reset.employee_id = String(user.employee_id);
      } else if(trackerMode){
        reset.task_date=filters.date;
        reset.employee_id=filters.employee;
        setCreateOpen(false);
      }
      setForm(reset);
      setCustomRows([]);
      await onReload();
      notify('Task created successfully');
    }
    catch(error){notify(error.message);}
  };

  const openEdit=task=>{
    setEditing(task);
    setEditForm({
      task_date:task.task_date||today(),employee_id:String(task.employee_id??''),department:task.department||'',
      title:task.title||'',details:task.details||'',due_time:task.due_time||'',target_qty:task.target_qty||'',
      actual_qty:task.actual_qty||'',progress:Number(task.progress)||0,priority:task.priority||'Normal',
      status:task.status??'Not started',proof_url:task.proof_url||'',proof_note:task.proof_note||'',
      next_action:task.next_action||task.manager_note||'',expose_link:Boolean(task.expose_link),
      approval_status:task.approval_status||'Pending'
    });
    setEditRows(customRowsFrom(task));
  };

  const saveEdit=async event=>{
    event.preventDefault();
    const effectiveEmpId = isEmployee && user?.employee_id ? Number(user.employee_id) : Number(editForm.employee_id);
    if(!editForm.title.trim()||!effectiveEmpId){notify('Task title and employee are required.');return;}
    const payload={
      ...editForm,
      employee_id: effectiveEmpId,
      progress:Number(editForm.progress)||0,
      expose_link:editForm.expose_link?1:0,
      approval_status: isEmployee ? 'Pending' : (editForm.approval_status || 'Pending'),
      custom_values:editRows.filter(row=>row.key.trim()||row.value.trim()).map(row=>({key:row.key.trim(),value:row.value.trim()}))
    };
    payload.manager_note=payload.next_action||'';
    if(payload.status==='Completed')payload.progress=100;
    try{
      await apiFetch('/tasks/'+editing.id,{method:'PUT',body:JSON.stringify(payload)});
      setEditing(null);
      await onReload();
      notify('Task updated successfully');
    }
    catch(error){notify(error.message);}
  };

  const approveTask=async(task)=>{
    try{
      await apiFetch('/tasks/'+task.id+'/approve',{
        method:'POST',
        body:JSON.stringify({approval_status:'Approved'})
      });
      await onReload();
      notify(`Task #${task.id} approved by Admin`);
    }catch(error){notify(error.message);}
  };

  const submitTask=async(task)=>{
    try{
      const payload={
        ...task,
        status:'Submitted',
        progress:Math.max(Number(task.progress)||0, 100),
        approval_status:'Pending',
        submitted_at:new Date().toISOString()
      };
      await apiFetch('/tasks/'+task.id,{method:'PUT',body:JSON.stringify(payload)});
      await onReload();
      notify(`Task #${task.id} submitted for Admin approval`);
    }catch(error){notify(error.message);}
  };

  const deleteTask=async task=>{
    if(!canDelete || isEmployee){notify('Employees cannot delete tasks.');return;}
    if(!window.confirm('Permanently delete task #'+task.id+'?'))return;
    try{await apiFetch('/tasks/'+task.id,{method:'DELETE'});setSelected(ids=>ids.filter(id=>id!==Number(task.id)));await onReload();notify('Task deleted');}
    catch(error){notify(error.message);}
  };

  const openProof=task=>{
    const links=String(task.proof_url||'').split(/\r?\n/).map(value=>value.trim()).filter(Boolean);
    const webLinks=links.filter(value=>/^https?:\/\//i.test(value));
    if(!webLinks.length){notify(links.length?'This proof is a local file path and is not directly accessible from the browser.':'No proof link has been entered.');return;}
    webLinks.forEach((url,index)=>window.open(url,'_blank','noopener,noreferrer'));
  };

  const beginCreate=()=>{
    const next=emptyTask();
    if(isEmployee && user?.employee_id){
      next.employee_id=String(user.employee_id);
    } else if(trackerMode){
      if(!filters.employee){notify('Select an employee first.');return;}
      next.task_date=filters.date;
      next.employee_id=filters.employee;
    }
    setForm(next);setCustomRows([]);setCreateOpen(true);
  };

  const selectVisible=()=>{
    const ids=visibleTasks.map(task=>Number(task.id));
    setSelected(current=>ids.length&&ids.every(id=>current.includes(id))?current.filter(id=>!ids.includes(id)):[...new Set([...current,...ids])]);
  };

  const applyBulk=async()=>{
    const updates={};
    Object.entries(bulk).forEach(([key,item])=>{if(item.apply)updates[key]=item.value;});
    if(!Object.keys(updates).length){notify('Select at least one field to apply.');return;}
    if(updates.next_action!==undefined)updates.manager_note=updates.next_action;
    if(updates.expose_link!==undefined)updates.expose_link=updates.expose_link?1:0;
    try{
      const result=await apiFetch('/tasks/bulk-edit',{method:'POST',body:JSON.stringify({task_ids:selected,updates})});
      setSelected([]);
      setBulkOpen(false);
      await onReload();
      notify('Updated '+result.updated+' selected task(s).');
    }
    catch(error){notify(error.message);}
  };

  const approveSelected=async()=>{
    if(!selected.length)return;
    try{
      const result=await apiFetch('/tasks/bulk-edit',{method:'POST',body:JSON.stringify({task_ids:selected,updates:{approval_status:'Approved'}})});
      setSelected([]);
      await onReload();
      notify(`Approved ${result.updated} selected task(s).`);
    }catch(error){notify(error.message);}
  };

  const completed=visibleTasks.filter(task=>['completed','submitted'].includes(String(task.status||'').toLowerCase())).length;
  const inProgress=visibleTasks.filter(task=>['in progress','partially completed'].includes(String(task.status||'').toLowerCase())).length;
  const pending=visibleTasks.filter(task=>['not started','pending','pending review','blocked'].includes(String(task.status||'').toLowerCase())).length;
  const approvedCount=visibleTasks.filter(task=>String(task.approval_status||'').toLowerCase()==='approved').length;
  const pendingApprovalCount=visibleTasks.filter(task=>String(task.approval_status||'').toLowerCase()!=='approved').length;

  const trackerSummary=useMemo(()=>{
    const status=task=>String(task.status??'').trim().toLowerCase();
    const completed=visibleTasks.filter(task=>['completed','submitted'].includes(status(task))).length;
    const blocked=visibleTasks.filter(task=>status(task)==='blocked').length;
    const inProgress=visibleTasks.filter(task=>status(task)==='in progress').length;
    const pending=visibleTasks.filter(task=>!['completed','submitted','cancelled','blocked','in progress'].includes(status(task))).length;
    const approved=visibleTasks.filter(task=>String(task.approval_status||'').toLowerCase()==='approved').length;
    const average=visibleTasks.length?Math.round(visibleTasks.reduce((total,task)=>total+(Number(task.progress)||0),0)/visibleTasks.length):0;
    return {total:visibleTasks.length,completed,inProgress,pending,blocked,approved,average};
  },[visibleTasks]);

  const bulkField=(key,label,type='text',options=[])=><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulk[key].apply} onChange={e=>setBulk(previous=>({...previous,[key]:{...previous[key],apply:e.target.checked}}))}/> Apply {label}</span>{type==='select'?<select className={field} value={bulk[key].value} onChange={e=>setBulk(previous=>({...previous,[key]:{...previous[key],value:e.target.value}}))}>{options.map(option=><option key={option||'__blank'} value={option}>{option||'Not selected'}</option>)}</select>:type==='checkbox'?<input type="checkbox" checked={Boolean(bulk[key].value)} onChange={e=>setBulk(previous=>({...previous,[key]:{...previous[key],value:e.target.checked}}))}/>:type==='textarea'?<textarea className={field} rows="2" value={bulk[key].value} onChange={e=>setBulk(previous=>({...previous,[key]:{...previous[key],value:e.target.value}}))}/>:<input className={field} type={type} value={bulk[key].value} onChange={e=>setBulk(previous=>({...previous,[key]:{...previous[key],value:e.target.value}}))}/>}</label>;

  return <div className="space-y-4">
    {(!trackerMode || createOpen) && <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-bold text-white">{isEmployee ? 'Create / Submit Your Daily Task' : (trackerMode ? 'Add task for selected employee' : 'Create new task')}</h2>
          <p className="text-xs text-slate-500">{isEmployee ? 'Record tasks you completed today. Admin will review and approve them for EOD reports.' : 'Assignment, target/progress, evidence and custom tracking.'}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">
            {isEmployee ? 'Self Task' : 'New assignment'}
          </span>
          {trackerMode&&<button type="button" onClick={()=>setCreateOpen(false)} className="rounded-lg border border-white/10 px-3 py-1 text-xs text-slate-300">Close</button>}
        </div>
      </div>
      <form onSubmit={saveCreate}>
        <TaskFields value={form} onChange={setForm} employees={employees} customRows={customRows} setCustomRows={setCustomRows} lockAssignment={trackerMode || isEmployee} lockDate={trackerMode} isAdmin={isAdmin} isEmployee={isEmployee}/>
        <div className="mt-4 flex justify-end">
          <button className={btn} disabled={!employees.length || (trackerMode&&!filters.employee)}>
            <Plus size={16}/> {isEmployee ? 'Create Task for Review' : 'Create task'}
          </button>
        </div>
      </form>
    </section>}

    {trackerMode && <>
      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-[220px] flex-1 text-xs text-slate-400">
            Employee
            {isEmployee ? (
              <div className={field+' mt-1 flex items-center justify-between bg-slate-900 text-cyan-200 border-cyan-400/30'}>
                <span>{user?.employee_name || employees.find(e=>String(e.id)===String(user?.employee_id))?.name || 'Self'}</span>
                <span className="text-[10px] font-bold uppercase text-cyan-400">Your Account</span>
              </div>
            ) : (
              <select className={field+' mt-1'} value={filters.employee} onChange={e=>updateFilter('employee',e.target.value)}>
                <option value="">Select employee</option>
                {employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name} ({employee.employee_code||employee.id})</option>)}
              </select>
            )}
          </label>
          <label className="min-w-[160px] text-xs text-slate-400">Task date<input className={field+' mt-1'} type="date" value={filters.date} onChange={e=>updateFilter('date',e.target.value)}/></label>
          <button type="button" onClick={refresh} className="rounded-lg border border-white/10 px-3 py-2.5 text-sm text-cyan-200"><RefreshCw size={15} className="inline"/> Refresh</button>
          <button type="button" onClick={beginCreate} disabled={!filters.employee && !isEmployee} className={btn}><Plus size={15}/> Add task</button>
        </div>
      </section>
      <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-bold text-white">Employee Activity &amp; Progression</h2><p className="text-xs text-slate-500">Daily assignment progression and status logs.</p></div><span className="text-xs text-slate-500">{employees.find(employee=>String(employee.id)===filters.employee)?.name||(isEmployee ? user?.employee_name : 'No employee selected')}</span></div>
        <p className="rounded-xl border border-white/10 bg-slate-950/70 p-3 text-sm text-slate-200">{filters.employee||isEmployee?(trackerSummary.total+' tasks · '+trackerSummary.completed+' completed/submitted · '+trackerSummary.approved+' approved · '+trackerSummary.inProgress+' in progress · '+trackerSummary.pending+' pending'):'Select an employee to view assigned tasks.'}</p>
        <div className="mt-3 flex items-center gap-3"><span className="whitespace-nowrap text-xs text-slate-400">Average task progress: {trackerSummary.average}%</span><div role="progressbar" aria-label="Average task progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow={trackerSummary.average} className="h-3 flex-1 overflow-hidden rounded-full bg-slate-950"><div className="h-full rounded-full bg-cyan-400 transition-all" style={{width:trackerSummary.average+'%'}}/></div></div>
        <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[950px] text-left text-xs"><thead className="bg-slate-950 text-[10px] uppercase text-slate-500"><tr>{['Task ID','Task','Priority','Status','Approval','Progress','Due time','Proof link','Manager remarks','Actions'].map(label=><th key={label} className="border-b border-white/10 px-3 py-3">{label}</th>)}</tr></thead><tbody>{visibleTasks.map(task=>{
          const links=String(task.proof_url||'').split(/\r?\n/).map(value=>value.trim()).filter(Boolean);
          const isApproved=String(task.approval_status||'').toLowerCase()==='approved';
          return <tr key={task.id} className="border-b border-white/5 align-top text-slate-300">
            <td className="px-3 py-3">{task.id}</td><td className="max-w-64 px-3 py-3"><b className="text-white">{task.title}</b>{task.details&&<p className="mt-1 whitespace-pre-wrap text-slate-500">{task.details}</p>}</td><td className="px-3 py-3">{task.priority||'Normal'}</td><td className="px-3 py-3">{String(task.status??'').trim()||'Not selected'}</td>
            <td className="px-3 py-3 whitespace-nowrap">
              <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold ${isApproved ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'}`}>
                {isApproved ? '✓ Approved' : '⏳ Pending'}
              </span>
            </td>
            <td className="px-3 py-3">{Number(task.progress)||0}%</td><td className="px-3 py-3 whitespace-nowrap">{task.due_time||'—'}</td>
            <td className="max-w-48 px-3 py-3">{links.length?links.map((link,index)=><div key={index} className="truncate">{/^https?:\/\//i.test(link)?<a href={link} target="_blank" rel="noreferrer" className="text-cyan-300 underline">Proof {index+1} <ExternalLink size={10} className="inline"/></a>:<span title={link}>{link}</span>}</div>):'—'}</td>
            <td className="max-w-48 px-3 py-3 whitespace-pre-wrap">{task.manager_note||task.next_action||'—'}</td>
            <td className="px-3 py-3">
              <div className="flex flex-col gap-1.5">
                {isAdmin && !isApproved && <button type="button" onClick={()=>approveTask(task)} className="text-left font-bold text-emerald-300 hover:text-emerald-200"><Check size={12} className="inline mr-1"/> Approve</button>}
                {isEmployee && !['submitted','completed'].includes(String(task.status||'').toLowerCase()) && <button type="button" onClick={()=>submitTask(task)} className="text-left font-bold text-cyan-300 hover:text-cyan-200"><Send size={12} className="inline mr-1"/> Submit</button>}
                <button type="button" onClick={()=>openEdit(task)} className="text-left text-cyan-300"><Pencil size={12} className="inline mr-1"/> Edit</button>
                <button type="button" onClick={()=>openProof(task)} className="text-left text-cyan-300"><Link2 size={12} className="inline mr-1"/> Open proof</button>
                {canDelete&&<button type="button" onClick={()=>deleteTask(task)} className="text-left text-rose-300"><Trash2 size={12} className="inline mr-1"/> Delete</button>}
              </div>
            </td>
          </tr>;
        })}</tbody></table>{!visibleTasks.length&&<p className="py-8 text-center text-sm text-slate-500">{filters.employee||isEmployee?'No tasks assigned on the selected date.':'Choose an employee to view assigned tasks.'}</p>}</div>
      </section>
    </>}

    {!trackerMode && (
    <section className="rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-bold text-white">{isEmployee ? 'My Tasks · ' : 'Task Manager · '}{visibleTasks.length} tasks</h2>
          <p className="text-xs text-slate-500">{isEmployee ? 'Review, update, and submit your tasks. Admin will approve before EOD report generation.' : 'Select one or more tasks to edit, approve, or apply bulk updates.'}</p>
        </div>
        <button type="button" onClick={refresh} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200"><RefreshCw size={15}/> Refresh</button>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <label className="text-xs text-slate-400">Date<input className={field+' mt-1'} type="date" disabled={filters.date==='all'} value={filters.date==='all'?today():filters.date} onChange={e=>updateFilter('date',e.target.value)}/><span className="mt-2 flex items-center gap-2"><input type="checkbox" checked={filters.date==='all'} onChange={e=>updateFilter('date',e.target.checked?'all':today())}/> All dates</span></label>
        <label className="text-xs text-slate-400">
          Employee
          {isEmployee ? (
            <div className={field+' mt-1 flex items-center justify-between bg-slate-900 text-cyan-200 border-cyan-400/30'}>
              <span className="truncate">{user?.employee_name || 'Self'}</span>
              <span className="text-[10px] font-bold uppercase text-cyan-400">Locked</span>
            </div>
          ) : (
            <select className={field+' mt-1'} value={filters.employee} onChange={e=>updateFilter('employee',e.target.value)}><option value="all">All employees</option>{employees.map(employee=><option key={employee.id} value={employee.id}>{employee.name}</option>)}</select>
          )}
        </label>
        <label className="text-xs text-slate-400">Status<select className={field+' mt-1'} value={filters.status} onChange={e=>updateFilter('status',e.target.value)}><option value="all">All statuses</option>{statuses.map(status=><option key={status||'__blank'} value={status}>{status||'Not selected'}</option>)}</select></label>
        <label className="text-xs text-slate-400">Approval<select className={field+' mt-1'} value={filters.approval} onChange={e=>updateFilter('approval',e.target.value)}><option value="all">All approval states</option><option value="Approved">✓ Approved only</option><option value="Pending">⏳ Pending approval</option></select></label>
        <label className="text-xs text-slate-400">Priority<select className={field+' mt-1'} value={filters.priority} onChange={e=>updateFilter('priority',e.target.value)}><option value="all">All priorities</option>{priorities.map(priority=><option key={priority}>{priority}</option>)}</select></label>
        <label className="text-xs text-slate-400">Search<input className={field+' mt-1'} value={filters.search} onChange={e=>updateFilter('search',e.target.value)} placeholder="Task, employee, proof…"/></label>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        {[['Total tasks',visibleTasks.length],['Approved by Admin',approvedCount],['Pending approval',pendingApprovalCount],['Completed / submitted',completed],['In progress',inProgress]].map(([label,count])=><div key={label} className="rounded-xl border border-white/10 bg-slate-950/70 p-3"><p className="text-[11px] text-slate-500">{label}</p><p className="mt-1 text-xl font-black text-cyan-200">{count}</p></div>)}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <button type="button" onClick={selectVisible} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200">{visibleTasks.length&&visibleTasks.every(task=>selected.includes(Number(task.id)))?'Clear visible selection':'Select all visible'}</button>
        <span className="text-xs text-slate-500">{selected.length} selected</span>
        {isAdmin && <button type="button" disabled={!selected.length} onClick={approveSelected} className="rounded-lg border border-emerald-400/40 bg-emerald-500/20 px-3 py-2 text-sm font-bold text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-40"><Check size={14} className="inline mr-1"/> Approve selected</button>}
        {isAdmin && <button type="button" disabled={!selected.length} onClick={()=>setBulkOpen(open=>!open)} className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40">Bulk edit selected</button>}
      </div>

      {bulkOpen && isAdmin && <div className="mb-4 rounded-xl border border-cyan-400/20 bg-slate-950/60 p-4">
        <div className="mb-3 flex items-center justify-between"><h3 className="font-bold text-white">Bulk edit {selected.length} selected task(s)</h3><button type="button" onClick={()=>setBulkOpen(false)} className="text-slate-400"><X size={16}/></button></div>
        <p className="mb-3 text-xs text-slate-500">Only checked fields are changed. Unchecked fields and all other task data remain untouched.</p>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {bulkField('approval_status','approval status','select',['Approved','Pending','Rejected'])}
          {bulkField('status','status','select',statuses)}
          {bulkField('title','assigned task')}
          {bulkField('department','department')}
          {bulkField('target_qty','target quantity')}
          {bulkField('actual_qty','actual quantity')}
          {bulkField('progress','completion %','number')}
          {bulkField('priority','priority','select',priorities)}
          {bulkField('custom_values','custom values','textarea')}
          {bulkField('next_action','next action')}
          {bulkField('expose_link','expose links','checkbox')}
        </div>
        <div className="mt-4 flex justify-end"><button type="button" className={btn} onClick={applyBulk}><Save size={15}/> Apply to selected</button></div>
      </div>}

      <div className="overflow-x-auto"><table className="w-full min-w-[1600px] text-left text-xs"><thead className="bg-slate-950 text-[10px] uppercase text-slate-500"><tr>{['Select','ID','Date','Employee','Department','Assigned task','Approval','Target / actual','Progress','Priority','Status','Due','Proof / link','Custom values','Next action','Submitted','Actions'].map(label=><th key={label} className="border-b border-white/10 px-2 py-3">{label}</th>)}</tr></thead><tbody>{visibleTasks.map(task=>{
        const links=String(task.proof_url||'').split(/\r?\n/).map(value=>value.trim()).filter(Boolean);
        const custom=customRowsFrom(task);
        const isApproved=String(task.approval_status||'').toLowerCase()==='approved';
        return <tr key={task.id} className="border-b border-white/5 align-top text-slate-300">
          <td className="px-2 py-3"><input type="checkbox" aria-label={'Select task '+task.id} checked={selected.includes(Number(task.id))} onChange={()=>setSelected(ids=>ids.includes(Number(task.id))?ids.filter(id=>id!==Number(task.id)):[...ids,Number(task.id)])}/></td>
          <td className="px-2 py-3">{task.id}</td><td className="px-2 py-3 whitespace-nowrap">{task.task_date||'—'}</td><td className="px-2 py-3">{task.employee_name||'—'}<div className="text-[10px] text-slate-500">{task.employee_code||''}</div></td>
          <td className="px-2 py-3">{task.department||'—'}</td><td className="max-w-56 px-2 py-3"><b className="text-white">{task.title}</b>{task.details&&<details className="mt-1"><summary className="cursor-pointer text-[10px] text-cyan-300">Details</summary><p className="mt-1 whitespace-pre-wrap text-slate-400">{task.details}</p></details>}</td>
          <td className="px-2 py-3 whitespace-nowrap">
            <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold ${isApproved ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'}`}>
              {isApproved ? '✓ Approved' : '⏳ Pending'}
            </span>
          </td>
          <td className="px-2 py-3 whitespace-nowrap">{task.target_qty||'—'} / {task.actual_qty||'—'}</td><td className="px-2 py-3">{Number(task.progress)||0}%</td><td className="px-2 py-3">{task.priority||'Normal'}</td><td className="px-2 py-3">{task.status||'Not selected'}</td><td className="px-2 py-3">{task.due_time||'—'}</td>
          <td className="max-w-48 px-2 py-3">{links.length?links.map((link,index)=><div key={index} className="truncate">{/^https?:\/\//i.test(link)?<a href={link} target="_blank" rel="noreferrer" className="text-cyan-300 underline">Evidence {index+1} <ExternalLink size={10} className="inline"/></a>:<span title={link}>{link}</span>}</div>):'—'}{task.expose_link?<span className="mt-1 block text-[10px] text-emerald-300">Exposed in reports</span>:null}</td>
          <td className="max-w-48 px-2 py-3">{custom.length?custom.map((row,index)=><div key={index}>{row.key}: {row.value}</div>):'—'}</td><td className="max-w-40 px-2 py-3 whitespace-pre-wrap">{task.next_action||task.manager_note||'—'}</td><td className="px-2 py-3 whitespace-nowrap">{task.submitted_at||'—'}</td>
          <td className="px-2 py-3">
            <div className="flex flex-col gap-1.5">
              {isAdmin && !isApproved && <button type="button" onClick={()=>approveTask(task)} className="text-left font-bold text-emerald-300 hover:text-emerald-200"><Check size={12} className="inline mr-1"/> Approve</button>}
              {isEmployee && !['submitted','completed'].includes(String(task.status||'').toLowerCase()) && <button type="button" onClick={()=>submitTask(task)} className="text-left font-bold text-cyan-300 hover:text-cyan-200"><Send size={12} className="inline mr-1"/> Submit</button>}
              <button type="button" onClick={()=>openEdit(task)} className="text-left text-cyan-300"><Pencil size={12} className="inline mr-1"/> Edit</button>
              <button type="button" onClick={()=>openProof(task)} className="text-left text-cyan-300"><Link2 size={12} className="inline mr-1"/> Open proof</button>
              {canDelete&&<button type="button" onClick={()=>deleteTask(task)} className="text-left text-rose-300"><Trash2 size={12} className="inline mr-1"/> Delete</button>}
            </div>
          </td>
        </tr>;
      })}</tbody></table>        {!visibleTasks.length && (
          <div className="py-12 text-center">
            <p className="text-sm font-semibold text-slate-400">No tasks match the selected filters.</p>
            {filters.date !== 'all' && (tasks || []).length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-slate-500 mb-2">There are {(tasks || []).length} total tasks across other dates.</p>
                <button
                  type="button"
                  onClick={() => updateFilter('date', 'all')}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-400/40 bg-cyan-500/10 px-4 py-2 text-xs font-bold text-cyan-300 hover:bg-cyan-500/20 transition shadow-sm"
                >
                  📅 Show All Dates ({(tasks || []).length} tasks)
                </button>
              </div>
            )}
          </div>
        )}</div>
    </section>
    )}

    {editing&&<div className="fixed inset-0 z-[110] grid place-items-center overflow-y-auto bg-black/75 p-4"><section className="my-6 w-full max-w-5xl rounded-2xl border border-cyan-400/20 bg-slate-900 p-5 shadow-2xl"><div className="mb-4 flex items-center justify-between"><div><h2 className="font-bold text-white">Edit Task #{editing.id}</h2><p className="text-xs text-slate-500">Submitted at: {editing.submitted_at||'Not submitted yet'} · Original submission time is preserved.</p></div><button type="button" onClick={()=>setEditing(null)} className="text-slate-400"><X size={18}/></button></div><form onSubmit={saveEdit}><TaskFields value={editForm} onChange={setEditForm} employees={employees} customRows={editRows} setCustomRows={setEditRows} lockAssignment={isEmployee} isAdmin={isAdmin} isEmployee={isEmployee}/><div className="mt-5 flex justify-end gap-2"><button type="button" className="rounded-lg border border-white/10 px-4 py-2 text-sm" onClick={()=>setEditing(null)}>Cancel</button><button className={btn}><Save size={15}/> Update task</button></div></form></section></div>}
  </div>;
}