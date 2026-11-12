import React, { useEffect, useMemo, useState } from 'react';
import brandLogo from '../../assets/raw_strength_brand.png';
import galaxyWallpaper from '../../assets/wallpapers/photos/galaxy.jpg';
import milkyWayWallpaper from '../../assets/wallpapers/photos/milky_way.jpg';
import oceanWallpaper from '../../assets/wallpapers/photos/ocean_waves.jpg';
import shivaWallpaper from '../../assets/wallpapers/photos/lord_shiva.jpg';
import couplesWallpaper from '../../assets/wallpapers/photos/love_couples.jpg';
import {
  LayoutDashboard, CheckSquare, CalendarCheck, Users, Printer, Briefcase, Settings,
  RefreshCw, CheckCircle2, Menu, LogOut, MessageCircle, Store, Archive, ClipboardList,
  Plus, Trash2, Search, Download, Clock3, Upload, Globe, FileText
} from 'lucide-react';
import TaskManager from './TaskManager';
import PrintCenter from './PrintCenter';
import ArchiveManager from './ArchiveManager';
import BusinessTracking from './BusinessTracking';
import LiveChat from './LiveChat';
import UpdateCenter from './UpdateCenter';
import HomeWorkspace from './HomeWorkspace';
import Storefront from './Storefront.jsx';

const API = '/api';
const today = () => { const d = new Date(); return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-'); };
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const navItems = [
  ['home','🏠  Home',LayoutDashboard],['dashboard','📊  Dashboard',LayoutDashboard],
  ['employees','👥  Employees',Users],['tasks','✅  Task Manager',CheckSquare],
  ['tracker','📝  Employee Tracker',ClipboardList],['attendance','🟢  Attendance',CalendarCheck],
  ['reports','🖨️  Print Center',Printer],['archive','📁  EOD Archive',Archive],
  ['business','💼  Business Tracking',Briefcase],['customers','🏪  Store Directory',Store],
  ['chat','💬  Live Chat',MessageCircle],['settings','⚙️  Settings & Backup',Settings]
];
const card='rounded-2xl border border-white/10 bg-slate-900/65 p-4 shadow-xl shadow-black/10';
const field='w-full min-w-0 rounded-lg border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400';
const btn='inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-50';

const APPEARANCE_THEMES = ['day','night','ocean','sunset'];
const WALLPAPER_STYLES = ['Ambient Glow','Aurora Waves','Starfield','Floating Bubbles','Rainfall','Matrix Drift','Galaxy','Milky Way','Milky Way Waves','Ocean Waves','Lord Shiva','Love Couple','Love & Couples','Cyberpunk Neon','Calisthenics Power','Cosmic Nebula','Custom Image'];
const PHOTO_WALLPAPER_URLS = {
  'Galaxy': galaxyWallpaper,
  'Milky Way': milkyWayWallpaper,
  'Milky Way Waves': milkyWayWallpaper,
  'Ocean Waves': oceanWallpaper,
  'Lord Shiva': shivaWallpaper,
  'Love Couple': couplesWallpaper,
  'Love & Couples': couplesWallpaper
};
const openAppearanceDb = () => new Promise((resolve,reject) => {
  if(!window.indexedDB){reject(new Error('This browser does not support local wallpaper storage.'));return;}
  const request=window.indexedDB.open('rsc-web-appearance',1);
  request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains('assets'))db.createObjectStore('assets');};
  request.onsuccess=()=>resolve(request.result);
  request.onerror=()=>reject(request.error||new Error('Could not open local appearance storage.'));
});
const readCustomWallpaper = async () => {
  const db=await openAppearanceDb();
  return new Promise((resolve,reject)=>{const request=db.transaction('assets','readonly').objectStore('assets').get('custom-wallpaper');request.onsuccess=()=>{db.close();resolve(request.result||null)};request.onerror=()=>{db.close();reject(request.error)};});
};
const writeCustomWallpaper = async file => {
  const db=await openAppearanceDb();
  return new Promise((resolve,reject)=>{const tx=db.transaction('assets','readwrite');tx.objectStore('assets').put(file,'custom-wallpaper');tx.oncomplete=()=>{db.close();resolve(true)};tx.onerror=()=>{db.close();reject(tx.error)};tx.onabort=()=>{db.close();reject(tx.error||new Error('Wallpaper save was cancelled.'))};});
};
const deleteCustomWallpaper = async () => {
  const db=await openAppearanceDb();
  return new Promise((resolve,reject)=>{const tx=db.transaction('assets','readwrite');tx.objectStore('assets').delete('custom-wallpaper');tx.oncomplete=()=>{db.close();resolve(true)};tx.onerror=()=>{db.close();reject(tx.error)};tx.onabort=()=>{db.close();reject(tx.error)};});
};

function AnalogClock({ now }) {
  const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
  const minuteAngle = now.getMinutes() * 6 + seconds * 0.1;
  const hourAngle = (now.getHours() % 12) * 30 + minuteAngle / 12;
  const secondAngle = seconds * 6;
  return <svg viewBox="0 0 64 64" width="44" height="44" role="img"
    aria-label={"Analog clock " + now.toLocaleTimeString()}
    className="shrink-0 text-cyan-300">
    <circle cx="32" cy="32" r="29" fill="rgba(2,6,23,.82)" stroke="currentColor" strokeWidth="2"/>
    {Array.from({length:12},(_,index)=><line key={index} x1="32" y1="5" x2="32" y2={index%3===0?10:8}
      stroke="currentColor" strokeWidth={index%3===0?2:1} strokeLinecap="round"
      transform={"rotate("+(index*30)+" 32 32)"}/>)}
    <line x1="32" y1="32" x2="32" y2="20" stroke="#e2e8f0" strokeWidth="3.2" strokeLinecap="round"
      transform={"rotate("+hourAngle+" 32 32)"}/>
    <line x1="32" y1="32" x2="32" y2="11" stroke="#67e8f9" strokeWidth="2.2" strokeLinecap="round"
      transform={"rotate("+minuteAngle+" 32 32)"}/>
    <line x1="32" y1="35" x2="32" y2="8" stroke="#f59e0b" strokeWidth="1.1" strokeLinecap="round"
      transform={"rotate("+secondAngle+" 32 32)"}/>
    <circle cx="32" cy="32" r="2.6" fill="#f59e0b"/>
  </svg>;
}

function HeaderClock({ clockMode, onToggleMode }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <button
      type="button"
      aria-label={"Switch to " + (clockMode === 'digital' ? 'analog' : 'digital') + " clock"}
      title={"Switch to " + (clockMode === 'digital' ? 'Analog' : 'Digital') + " clock"}
      onClick={onToggleMode}
      className="hidden min-w-[108px] items-center justify-center rounded-lg border border-white/10 px-2 py-1 text-cyan-300 hover:border-cyan-400/40 disabled:opacity-50 sm:flex"
    >
      {clockMode === 'digital' ? (
        <span className="flex flex-col items-end text-[10px] leading-tight">
          <span>{now.toLocaleDateString(undefined, { weekday: 'short', day: '2-digit', month: 'short' })}</span>
          <span className="font-semibold tabular-nums">
            {now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
          </span>
        </span>
      ) : (
        <span className="flex items-center gap-2">
          <AnalogClock now={now} />
          <span className="text-[10px]">Analog</span>
        </span>
      )}
    </button>
  );
}

function Panel({ title, children, actions }) {
  return (
    <section className={card}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-bold text-white">{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  );
}

function Rows({ items, keys, onDelete, onEdit }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] text-left text-sm">
        <thead className="text-xs uppercase text-slate-500">
          <tr>
            {keys.map(k => (
              <th className="border-b border-white/10 px-3 py-3" key={k}>
                {k.replaceAll('_', ' ')}
              </th>
            ))}
            {(onDelete || onEdit) && <th className="border-b border-white/10 px-3 py-3">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {items.map((x, i) => (
            <tr key={x.id ?? i} className="border-b border-white/5 text-slate-300">
              {keys.map(k => (
                <td className={'px-3 py-3 ' + (k === 'address' ? 'max-w-[280px] whitespace-normal' : '')} key={k}>
                  {['maps', 'website'].includes(k) && /^https?:\/\//i.test(String(x[k] || '')) ? (
                    <a className="text-cyan-300 underline underline-offset-2" href={String(x[k])} target="_blank" rel="noopener noreferrer">
                      {k === 'maps' ? 'Open Maps' : 'Open website'}
                    </a>
                  ) : (
                    String(x[k] ?? '—')
                  )}
                </td>
              ))}
              {(onDelete || onEdit) && (
                <td className="px-3 py-3">
                  <div className="flex gap-3">
                    {onEdit && (
                      <button className="text-cyan-300" onClick={() => onEdit(x)}>
                        Edit
                      </button>
                    )}
                    {onDelete && (
                      <button className="text-rose-300" onClick={() => onDelete(x)} aria-label="Delete">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && <p className="py-6 text-center text-sm text-slate-500">No records found.</p>}
    </div>
  );
}

function FormInput({ label, name, form, onChange, type = 'text', placeholder = '', required = false }) {
  return (
    <label className="block min-w-0 space-y-1">
      <span className="text-xs font-semibold text-slate-400">{label}</span>
      <input
        className={field}
        type={type}
        required={required}
        value={form[name] ?? ''}
        placeholder={placeholder}
        onChange={e => onChange(name, type === 'number' ? Number(e.target.value) : e.target.value)}
      />
    </label>
  );
}

export default function App() {
  const [storeRoute, setStoreRoute] = useState(() => {
    return window.location.pathname === '/store' || window.location.pathname.startsWith('/store/') || window.location.hash === '#store' || window.location.hash.startsWith('#/store') || window.location.hash.startsWith('#store');
  });
  useEffect(() => {
    const handleLocation = () => {
      setStoreRoute(window.location.pathname === '/store' || window.location.pathname.startsWith('/store/') || window.location.hash === '#store' || window.location.hash.startsWith('#/store') || window.location.hash.startsWith('#store'));
    };
    window.addEventListener('hashchange', handleLocation);
    window.addEventListener('popstate', handleLocation);
    return () => {
      window.removeEventListener('hashchange', handleLocation);
      window.removeEventListener('popstate', handleLocation);
    };
  }, []);
  const [tab,setTab]=useState('home'),[sidebar,setSidebar]=useState(false),[sidebarCollapsed,setSidebarCollapsed]=useState(false);
  const [token,setToken]=useState(()=>localStorage.getItem('rsc_auth_token')||'');
  const [user,setUser]=useState(null),[checked,setChecked]=useState(false);
  const [login,setLogin]=useState({username:'',password:''}),[error,setError]=useState('');
  const [authMode,setAuthMode]=useState('login'),[showPassword,setShowPassword]=useState(false);
  const [authProfile,setAuthProfile]=useState({display_name:'',security_question:'What was the name of your first school?',security_answer:'',confirm_password:''});
  const [passwordChange,setPasswordChange]=useState({current_password:'',new_password:'',confirm_password:''});
  const [recoveryQuestion,setRecoveryQuestion]=useState(''),[recoveryReady,setRecoveryReady]=useState(false);
  const [authNotice,setAuthNotice]=useState(''),[authUsers,setAuthUsers]=useState([]);
  const [googleSheetsPassword,setGoogleSheetsPassword]=useState(''),[googleSheetsBusy,setGoogleSheetsBusy]=useState(false),[googleSheetsStatus,setGoogleSheetsStatus]=useState('');
  const [accountRoleDrafts,setAccountRoleDrafts]=useState({});
  const [accountPasswordResetTarget,setAccountPasswordResetTarget]=useState(null);
  const [accountPasswordDraft,setAccountPasswordDraft]=useState({password:'',confirm:''});
  const [newAccount,setNewAccount]=useState({username:'',display_name:'',role:'Employee',employee_id:'',password:'',security_question:'What was the name of your first school?',security_answer:''});
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const [data,setData]=useState({dashboard:null,homeBusiness:null,employees:[],employeeGroups:[],tasks:[],attendance:{date:today(),roster:[],remarks_options:[]},attendanceSummary:{rows:[]},holidays:[],products:[],services:[],orders:[],members:[],prospects:[],messages:[],print:null,archive:[],db:null});
  const [query,setQuery]=useState('');
  const [prospectStateFilter,setProspectStateFilter]=useState('all');
  const [prospectKindFilter,setProspectKindFilter]=useState('pure product selling stores');
  const [prospectWebsiteFilter,setProspectWebsiteFilter]=useState('all');
  const [prospectVerificationFilter,setProspectVerificationFilter]=useState('all');
  const [prospectContactFilter,setProspectContactFilter]=useState('all');
  const [prospectExcludeFilter,setProspectExcludeFilter]=useState('none');
  const [prospectExcludeKind,setProspectExcludeKind]=useState('all');
  const [prospectExcludeState,setProspectExcludeState]=useState('all');
  const [prospectExcludeName,setProspectExcludeName]=useState('');
  const [prospectExcludeDistrict,setProspectExcludeDistrict]=useState('');
  const [prospectExcludeKeywords,setProspectExcludeKeywords]=useState('');
  const [prospectPage,setProspectPage]=useState(1);
  const [storeWorkbook,setStoreWorkbook]=useState(null),[dashboardWorkbook,setDashboardWorkbook]=useState(null);
  const [storeImportBusy,setStoreImportBusy]=useState(false),[dashboardImportBusy,setDashboardImportBusy]=useState(false);
  const [regionalSummary,setRegionalSummary]=useState({rows:[],totals:{}});
  const [regionalTerritoryFilter,setRegionalTerritoryFilter]=useState('all');
  const [employeeForm,setEmployeeForm]=useState({name:'',employee_code:'',department:'',designation:'',phone:'',email:'',joining_date:'',notes:''});
  const [employeeDepartment,setEmployeeDepartment]=useState('all'),[employeeSort,setEmployeeSort]=useState('serial'),[employeeSelectedId,setEmployeeSelectedId]=useState(null);
  const [moveToGroup,setMoveToGroup]=useState('');
  const [groupManagerOpen,setGroupManagerOpen]=useState(false),[groupNameDraft,setGroupNameDraft]=useState(''),[groupRenameDraft,setGroupRenameDraft]=useState(''),[groupSelected,setGroupSelected]=useState('');
  const [attendanceFilter,setAttendanceFilter]=useState('all');
  const [attendanceDrafts,setAttendanceDrafts]=useState({});
  const [attendanceBusy,setAttendanceBusy]=useState(false);
  const [selectedAttendanceIds,setSelectedAttendanceIds]=useState([]);
  const [attendanceRemarksTarget,setAttendanceRemarksTarget]=useState(null),[attendanceRemarksDraft,setAttendanceRemarksDraft]=useState('');
  const [bulkAttendance,setBulkAttendance]=useState({apply_status:false,status:'Present',apply_check_in:false,check_in:'',apply_check_out:false,check_out:'',apply_remarks:false,remarks:''});
  const [form,setForm]=useState({name:'',employee_code:'',department:'',designation:'',phone:'',email:'',title:'',task_date:today(),employee_id:'',priority:'Normal',status:'Not started',details:'',sku:'',category:'General',brand:'',base_unit:'PCS',opening_stock:0,received_qty:0,reorder_level:0,selling_price:0,training_mode:'In-Person',standard_price:0,customer_name:'',order_value:0,full_name:'',plan_name:'',business_name:'',business_category:'',kind:'Store',area:'',city:'',state:'',contact_person:'',address:'',website:'',maps:'',followup_date:'',call_time:'',connection:'',verified:'No',response:'',notes:'',content:'',channel:'general'});
  const [report,setReport]=useState({date:today(),report_type:'Audit / EOD',employee_id:''});
  const [reportText,setReportText]=useState('');
  const [editRecord,setEditRecord]=useState(null);
  const [holidayForm,setHolidayForm]=useState({holiday_date:today(),holiday_name:''});
  const [scrapeState,setScrapeState]=useState('');
  const [scrapeCategory,setScrapeCategory]=useState('Pure Product Selling Stores');
  const [scrapeQuery,setScrapeQuery]=useState('supplement store sports nutrition whey protein');
  const [scrapeBusy,setScrapeBusy]=useState(false);
  const [scrapeStatus,setScrapeStatus]=useState('');
  const [restoreFile,setRestoreFile]=useState(null),[restoreBusy,setRestoreBusy]=useState(false);
  const [workingWeekdays,setWorkingWeekdays]=useState([0,1,2,3,4,6]),[workingWeekdaysBusy,setWorkingWeekdaysBusy]=useState(false);
  const [theme,setTheme]=useState(()=>{const saved=localStorage.getItem('rsc_web_theme')||'night';return APPEARANCE_THEMES.includes(saved)?saved:'night';});
  const [wallpaper,setWallpaper]=useState(()=>{const saved=localStorage.getItem('rsc_web_wallpaper')||'Galaxy';return WALLPAPER_STYLES.includes(saved)?saved:'Galaxy';});
  const [clockMode,setClockMode]=useState(()=>{const saved=String(localStorage.getItem('rsc_web_clock_mode')||'digital').trim().toLowerCase();return ['digital','analog'].includes(saved)?saved:'digital';});
  const [customWallpaperUrl,setCustomWallpaperUrl]=useState('');
  const [customWallpaperName,setCustomWallpaperName]=useState(()=>localStorage.getItem('rsc_web_custom_wallpaper_name')||'');
  const [appearanceBusy,setAppearanceBusy]=useState(false);

  const apiFetch=async(path,options={})=>{
    const headers={...(options.headers||{})};
    const active=token||localStorage.getItem('rsc_auth_token')||'';
    if(active) headers.Authorization='Bearer '+active;
    if(options.body && !(options.body instanceof FormData)) headers['Content-Type']='application/json';
    const res=await fetch(API+path,{...options,headers});
    if(res.status===401){localStorage.removeItem('rsc_auth_token');setToken('');setUser(null);}
    if(!res.ok){const body=await res.json().catch(()=>({}));throw new Error(body.detail||('Request failed ('+res.status+')'));}
    return res.status===204?null:res.json();
  };
  const fetchAllProspects=async()=>{
    const pageSize=1000;
    const records=[];
    let beforeId=null;
    while(true){
      const cursor=beforeId===null?'':'&before_id='+encodeURIComponent(beforeId);
      const page=await apiFetch('/customers/prospects?limit='+pageSize+cursor);
      if(!Array.isArray(page))throw new Error('Unexpected Store Directory response.');
      records.push(...page);
      if(page.length<pageSize)return records;
      const nextId=Number(page[page.length-1]?.id);
      if(!Number.isSafeInteger(nextId)||nextId<1||(beforeId!==null&&nextId>=beforeId))throw new Error('Store Directory pagination did not advance.');
      beforeId=nextId;
    }
  };
  const load=async(attendanceDate=data.attendance.date||today())=>{
    if(!token)return;
    setBusy(true);
    const selectedAttendanceDate=attendanceDate||today();
    const jobs=[
      ['dashboard','/dashboard',null],['homeBusiness','/home/business-snapshot',null],['employees','/employees?active_only=false',[]],['employeeGroups','/employee-groups',[]],['tasks','/tasks',[]],
      ['attendance','/attendance?work_date='+encodeURIComponent(selectedAttendanceDate),{date:selectedAttendanceDate,roster:[],remarks_options:[]}],
      ['attendanceSummary','/attendance/summary?work_date='+encodeURIComponent(selectedAttendanceDate),{rows:[]}],
      ['holidays','/holidays',[]],
      ['products','/business/products',[]],['services','/business/services',[]],
      ['orders','/business/orders',[]],['members','/business/members',[]],
      ['messages','/chat/messages?channel=general',[]],
      ['print','/print-center/summary',null],['archive','/archive',[]],['db','/system/db-info',null]
    ];
    const results=await Promise.all(jobs.map(async([key,path,fallback])=>{try{return [key,await apiFetch(path)]}catch(e){return [key,fallback]}}));
    const nextData=Object.fromEntries(results);
    if(tab==='customers'){
      try{nextData.prospects=await fetchAllProspects();}
      catch(e){nextData.prospects=data.prospects||[];notify('Store Directory refresh failed: '+e.message);}
      try{setRegionalSummary(await apiFetch('/customers/regional-summary'));}
      catch(e){setRegionalSummary({rows:[],totals:{}});notify('Regional dashboard refresh failed: '+e.message);}
    }
    setData(prev=>({...prev,...nextData}));setSelectedAttendanceIds([]);setBusy(false);
  };
  useEffect(()=>{(async()=>{if(!token){setChecked(true);return;}try{const r=await fetch(API+'/auth/me',{headers:{Authorization:'Bearer '+token}});if(!r.ok)throw 0;const j=await r.json();setUser(j.user);setChecked(true);}catch{localStorage.removeItem('rsc_auth_token');setToken('');setUser(null);setChecked(true);}})()},[]);
  useEffect(()=>{if(user&&token)load()},[user,token]);

  useEffect(()=>{
    document.documentElement.dataset.rscTheme=theme;
    document.body.dataset.rscTheme=theme;
    if (theme === 'night') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
    document.body.dataset.rscWallpaper=wallpaper;
    const imageUrl=wallpaper==='Custom Image'?customWallpaperUrl:(PHOTO_WALLPAPER_URLS[wallpaper]||'');
    document.body.style.setProperty('--rsc-wallpaper-image',imageUrl?('url("'+imageUrl+'")'):'none');
    localStorage.setItem('rsc_web_theme',theme);
    localStorage.setItem('rsc_web_wallpaper',wallpaper);
  },[theme,wallpaper,customWallpaperUrl]);
  useEffect(()=>{
    let active=true,loadedUrl='';
    readCustomWallpaper().then(blob=>{
      if(!active||!blob)return;
      loadedUrl=URL.createObjectURL(blob);
      setCustomWallpaperUrl(loadedUrl);
    }).catch(()=>{});
    return ()=>{active=false;if(loadedUrl)URL.revokeObjectURL(loadedUrl);};
  },[]);
  useEffect(()=>{if(user&&token&&tab==='customers')load()},[tab,user,token]);
  useEffect(()=>{if(user&&token&&tab==='home'){apiFetch('/home/business-snapshot').then(snapshot=>setData(previous=>({...previous,homeBusiness:snapshot}))).catch(error=>notify('Home business snapshot refresh failed: '+error.message));}},[tab,user,token]);
  useEffect(()=>{if(tab==='settings'&&user&&['admin','developer'].includes(String(user.role||'').toLowerCase())){Promise.all([apiFetch('/auth/users'),apiFetch('/settings/working-weekdays')]).then(([accounts,working])=>{setAuthUsers(accounts);setWorkingWeekdays(working.weekdays||[0,1,2,3,4,6])}).catch(e=>notify(e.message))}},[tab,user,token]);
  const notify=(s)=>{setNotice(s);setTimeout(()=>setNotice(''),3500)};
  const saveClockMode=mode=>{
    const normalized=String(mode||'').trim().toLowerCase();
    if(!['digital','analog'].includes(normalized))return;
    setClockMode(normalized);
    localStorage.setItem('rsc_web_clock_mode',normalized);
  };
  const uploadCustomWallpaper=async event=>{
    const file=event.target.files?.[0];event.target.value='';
    if(!file)return;
    const supported=/\.(png|jpe?g|webp|bmp)$/i.test(file.name)||['image/png','image/jpeg','image/webp','image/bmp'].includes(file.type);
    if(!supported){notify('Choose a PNG, JPG, WEBP or BMP image.');return;}
    if(file.size>15*1024*1024){notify('Custom wallpaper must be 15 MB or smaller.');return;}
    const previewUrl=URL.createObjectURL(file);
    try{
      const image=new Image();
      await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('The selected image could not be opened.'));image.src=previewUrl;});
      if(!image.naturalWidth||!image.naturalHeight)throw new Error('The selected image is invalid.');
      setAppearanceBusy(true);
      await writeCustomWallpaper(file);
      setCustomWallpaperUrl(previous=>{if(previous)URL.revokeObjectURL(previous);return previewUrl;});
      setCustomWallpaperName(file.name);
      localStorage.setItem('rsc_web_custom_wallpaper_name',file.name);
      setWallpaper('Custom Image');
      notify('Custom wallpaper saved in this browser.');
    }catch(error){URL.revokeObjectURL(previewUrl);notify(error.message||'Could not save custom wallpaper.');}
    finally{setAppearanceBusy(false);}
  };
  const resetCustomWallpaper=async()=>{
    setAppearanceBusy(true);
    try{
      await deleteCustomWallpaper();
      setCustomWallpaperUrl(previous=>{if(previous)URL.revokeObjectURL(previous);return '';});
      setCustomWallpaperName('');
      localStorage.removeItem('rsc_web_custom_wallpaper_name');
      setWallpaper('Ambient Glow');
      notify('Wallpaper reset to Ambient Glow.');
    }catch(error){notify(error.message||'Could not reset wallpaper.');}
    finally{setAppearanceBusy(false);}
  };
  const submitLogin=async(e)=>{
    e.preventDefault();setError('');setBusy(true);
    try{
      const r=await fetch(API+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username.trim(),password:login.password})});
      const j=await r.json().catch(()=>({}));
      if(!r.ok){
        const failure=new Error(j.detail||j.error||('Sign-in request failed ('+r.status+').'));
        failure.status=r.status;
        failure.retryAfter=r.headers.get('Retry-After')||'';
        throw failure;
      }
      if(!j.token||!j.user)throw new Error('The server returned an incomplete sign-in response. Please retry.');
      localStorage.setItem('rsc_auth_token',j.token);setToken(j.token);setUser(j.user);notify('Signed in');
    }catch(e){
      let message=e.message||'Could not sign in.';
      if(e.status===429){
        const retry=String(e.retryAfter||'').trim();
        let wait='';
        if(/^\\d+$/.test(retry))wait=' Wait '+retry+' seconds before trying again.';
        else if(retry){const until=Date.parse(retry);if(Number.isFinite(until)){const seconds=Math.max(1,Math.ceil((until-Date.now())/1000));wait=' Wait about '+seconds+' seconds before trying again.';}}
        message='The sign-in service is temporarily rate-limiting requests.'+wait+' Avoid repeated attempts; retry after the indicated wait.';
      }else if(e.status===401){
        try{
          const statusResponse=await fetch(API+'/auth/status',{cache:'no-store'});
          const status=await statusResponse.json();
          if(status.user_count===0)message+=' The web database reports no active accounts; the customer snapshot must be restored before sign-in.';
          else if(Array.isArray(status.usernames)&&status.usernames.length)message+=' Account usernames are case-sensitive: '+status.usernames.join(' / ')+'.';
          if(status.sync&&status.sync.configured===false)message+=' Encrypted database sync is not configured on the web backend.';
          else if(status.pull&&status.pull.ok===false)message+=' The latest customer database snapshot has not been verified on the web backend.';
        }catch{}
      }
      setError(message);
    }finally{setBusy(false)}
  };
  const submitRegistration=async(e)=>{e.preventDefault();setError('');setAuthNotice('');if(login.password!==authProfile.confirm_password){setError('Passwords do not match');return;}setBusy(true);try{const r=await fetch(API+'/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username,display_name:authProfile.display_name,password:login.password,security_question:authProfile.security_question,security_answer:authProfile.security_answer})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Account registration failed');setAuthNotice(j.message||'Account request submitted for Admin approval.');setAuthMode('login');setLogin(p=>({...p,password:''}));setAuthProfile(p=>({...p,confirm_password:'',security_answer:''}));}catch(e){setError(e.message)}finally{setBusy(false)}};
  const findRecoveryQuestion=async()=>{setError('');setRecoveryReady(false);setRecoveryQuestion('');try{const r=await fetch(API+'/auth/recovery-question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Could not find a recovery question');setRecoveryQuestion(j.security_question);setRecoveryReady(true);}catch(e){setError(e.message)}};
  const submitPasswordReset=async(e)=>{e.preventDefault();setError('');if(login.password!==authProfile.confirm_password){setError('Passwords do not match');return;}setBusy(true);try{const r=await fetch(API+'/auth/password-reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username,security_answer:authProfile.security_answer,new_password:login.password})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Password reset failed');setAuthNotice(j.message||'Password reset successfully. Sign in again.');setAuthMode('login');setLogin(p=>({...p,password:''}));setAuthProfile(p=>({...p,confirm_password:'',security_answer:''}));setRecoveryReady(false);}catch(e){setError(e.message)}finally{setBusy(false)}};
  const submitPasswordChange=async(e)=>{e.preventDefault();setError('');if(passwordChange.new_password!==passwordChange.confirm_password){setError('Passwords do not match');return;}if(passwordChange.new_password.length<8||!/[A-Za-z]/.test(passwordChange.new_password)||!/[0-9]/.test(passwordChange.new_password)){setError('Use at least 8 characters, including a letter and a number.');return;}setBusy(true);try{const r=await fetch(API+'/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username,current_password:passwordChange.current_password,new_password:passwordChange.new_password})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Password change failed');setAuthNotice(j.message||'Password changed. Sign in again.');setAuthMode('login');setLogin(p=>({...p,password:''}));setPasswordChange({current_password:'',new_password:'',confirm_password:''});}catch(e){setError(e.message)}finally{setBusy(false)}};
  const toggleAccountActive=async(account)=>{try{await apiFetch('/auth/users/'+account.id+'/active',{method:'PATCH',body:JSON.stringify({active:!account.active})});setAuthUsers(rows=>rows.map(r=>r.id===account.id?{...r,active:!account.active}:r));notify('Account status updated');}catch(e){notify(e.message)}};
  const createManagedAccount=async(event)=>{
    event.preventDefault();
    try{
      const payload={
        ...newAccount,
        employee_id: newAccount.employee_id ? Number(newAccount.employee_id) : null
      };
      await apiFetch('/auth/users',{method:'POST',body:JSON.stringify(payload)});
      const rows=await apiFetch('/auth/users');
      setAuthUsers(rows);
      setNewAccount({username:'',display_name:'',role:'Employee',employee_id:'',password:'',security_question:'What was the name of your first school?',security_answer:''});
      notify('Account created and activated');
    }catch(e){notify(e.message)}
  };
  const changeAccountRole=async(account,role)=>{if(role===account.role)return;setAccountRoleDrafts(p=>({...p,[account.id]:role}));try{await apiFetch('/auth/users/'+account.id+'/role',{method:'PATCH',body:JSON.stringify({role})});setAuthUsers(rows=>rows.map(r=>r.id===account.id?{...r,role}:r));setAccountRoleDrafts(p=>({...p,[account.id]:role}));notify('Role updated for '+account.username);if(Number(account.id)===Number(user?.id))logout();}catch(e){setAccountRoleDrafts(p=>({...p,[account.id]:account.role}));notify(e.message)}};
  const saveManagedAccountPassword=async(account)=>{const {password,confirm}=accountPasswordDraft;if(password!==confirm){notify('Passwords do not match');return;}if(password.length<8||!/[A-Za-z]/.test(password)||!/[0-9]/.test(password)){notify('Use at least 8 characters with a letter and a number');return;}try{await apiFetch('/auth/users/'+account.id+'/password-reset',{method:'POST',body:JSON.stringify({new_password:password})});setAccountPasswordResetTarget(null);setAccountPasswordDraft({password:'',confirm:''});notify('Password reset for '+account.username);if(Number(account.id)===Number(user?.id))logout();}catch(e){notify(e.message)}};
  const saveWorkingWeekdays=async()=>{setWorkingWeekdaysBusy(true);try{const result=await apiFetch('/settings/working-weekdays',{method:'PUT',body:JSON.stringify({weekdays:workingWeekdays})});setWorkingWeekdays(result.weekdays||workingWeekdays);await load(data.attendance.date||today());notify('Working days saved. Sunday is always a working day.')}catch(e){notify(e.message)}finally{setWorkingWeekdaysBusy(false)}};
  const importStoreWorkbook=async()=>{if(!canAdminEmployees||!storeWorkbook)return;setStoreImportBusy(true);try{const payload=new FormData();payload.append('file',storeWorkbook);const response=await fetch(API+'/customers/import',{method:'POST',headers:{Authorization:'Bearer '+token},body:payload});const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(body.detail||'Store workbook import failed');setStoreWorkbook(null);await load();notify('Workbook merged: '+body.inserted+' new, '+body.duplicates_enriched_or_matched+' matched or enriched. Existing records were retained.');}catch(error){notify(error.message)}finally{setStoreImportBusy(false)}};
  const importDashboardWorkbook=async()=>{if(!canAdminEmployees||!dashboardWorkbook)return;setDashboardImportBusy(true);try{const payload=new FormData();payload.append('file',dashboardWorkbook);const response=await fetch(API+'/customers/dashboard-import',{method:'POST',headers:{Authorization:'Bearer '+token},body:payload});const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(body.detail||'Regional dashboard import failed');setDashboardWorkbook(null);await load();notify('Regional benchmark imported for '+body.territories+' territories. Store records were not changed.');}catch(error){notify(error.message)}finally{setDashboardImportBusy(false)}};
  const clearStoreExclusions=()=>{
    setProspectExcludeFilter('none');
    setProspectExcludeKind('all');
    setProspectExcludeState('all');
    setProspectExcludeName('');
    setProspectExcludeDistrict('');
    setProspectExcludeKeywords('');
    setProspectPage(1);
  };
  const changeScrapeCategory=value=>{
    setScrapeCategory(value);
    setScrapeQuery(value==='Gym'?'gym fitness centre health club':value==='Gyms which sell products also'?'gym supplement counter protein bar sports nutrition':value==='All Categories'?'supplement store gym nutrition protein':'supplement store sports nutrition whey protein');
  };
  const downloadStoreExport=async(format)=>{try{const params=new URLSearchParams({format});if(prospectStateFilter!=='all')params.set('state',prospectStateFilter);if(prospectKindFilter!=='all')params.set('kind',prospectKindFilter);if(prospectWebsiteFilter!=='all')params.set('website',prospectWebsiteFilter);if(prospectVerificationFilter!=='all')params.set('verification',prospectVerificationFilter);if(prospectContactFilter!=='all')params.set('contact',prospectContactFilter);if(prospectExcludeFilter!=='none')params.set('exclude',prospectExcludeFilter);if(prospectExcludeKind!=='all')params.set('exclude_kind',prospectExcludeKind);if(prospectExcludeState!=='all')params.set('exclude_state',prospectExcludeState);if(prospectExcludeName.trim())params.set('exclude_name',prospectExcludeName.trim());if(prospectExcludeDistrict.trim())params.set('exclude_district',prospectExcludeDistrict.trim());if(prospectExcludeKeywords.trim())params.set('exclude_keywords',prospectExcludeKeywords.trim());if(query.trim())params.set('q',query.trim());const response=await fetch(API+'/customers/export?'+params.toString(),{headers:{Authorization:'Bearer '+token}});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Store Directory export failed')}const blob=await response.blob();const url=window.URL.createObjectURL(blob);const anchor=document.createElement('a');const disposition=response.headers.get('content-disposition')||'';const match=disposition.match(/filename=\"?([^\";]+)\"?/i);anchor.href=url;anchor.download=match?.[1]||('stores_directory.'+format);document.body.appendChild(anchor);anchor.click();anchor.remove();window.URL.revokeObjectURL(url);notify(format.toUpperCase()+' export downloaded');}catch(error){notify(error.message)}};
  const downloadRegionalExport=async(format)=>{try{const params=new URLSearchParams({format});if(regionalTerritoryFilter!=='all')params.set('territory_type',regionalTerritoryFilter);const response=await fetch(API+'/customers/regional-export?'+params.toString(),{headers:{Authorization:'Bearer '+token}});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Regional export failed')}const blob=await response.blob();const url=window.URL.createObjectURL(blob);const anchor=document.createElement('a');const disposition=response.headers.get('content-disposition')||'';const match=disposition.match(/filename="?([^";]+)"?/i);anchor.href=url;anchor.download=match?.[1]||('regional_dashboard.'+format);document.body.appendChild(anchor);anchor.click();anchor.remove();window.setTimeout(()=>window.URL.revokeObjectURL(url),1000);notify('Regional '+format.toUpperCase()+' export downloaded');}catch(error){notify(error.message)}};
  const openStorePrintPreview=()=>{const popup=window.open('','_blank');if(!popup){notify('Allow pop-ups to open the Store Directory print preview.');return;}const rows=prospectRows.map(row=>'<tr><td>'+escapeHtml(row.state)+'</td><td>'+escapeHtml(row.city)+'<br>'+escapeHtml(row.area)+'</td><td><b>'+escapeHtml(row.business_name)+'</b></td><td>'+escapeHtml(row.business_category)+'</td><td>'+escapeHtml(row.phone)+'</td><td>'+escapeHtml(row.address)+'</td><td>'+escapeHtml(row.maps)+'</td></tr>').join('');popup.document.open();popup.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Raw Strength Store Directory</title><style>body{font-family:Arial,sans-serif;color:#0f172a;padding:24px}h1{font-size:20px}p{color:#475569}button{padding:8px 14px;margin:10px 0}table{width:100%;border-collapse:collapse;font-size:11px}th,td{border:1px solid #cbd5e1;padding:6px;text-align:left;vertical-align:top}th{background:#1e293b;color:white}tr:nth-child(even){background:#f8fafc}@media print{button{display:none}body{padding:0}}</style></head><body><h1>RAW STRENGTH CALISTHENICS — STORE DIRECTORY</h1><p>Generated '+escapeHtml(new Date().toLocaleString())+' · '+prospectRows.length+' filtered records</p><button onclick="window.print()">Print / Save as PDF</button><table><thead><tr><th>State</th><th>City / Area</th><th>Business Name</th><th>Category</th><th>Phone</th><th>Full Address</th><th>Google Maps</th></tr></thead><tbody>'+rows+'</tbody></table></body></html>');popup.document.close();popup.focus();};
  const openRegionalPrintPreview=()=>{const popup=window.open('','_blank');if(!popup){notify('Allow pop-ups to open the Regional Dashboard print preview.');return;}const rows=regionalRows.map(row=>'<tr><td>'+escapeHtml(row.state)+'</td><td>'+escapeHtml(row.territory_type)+'</td><td>'+row.web_leads+'</td><td>'+row.workbook_leads+'</td><td>'+row.stores+'</td><td>'+row.gyms+'</td><td>'+(row.dashboard_stores??'—')+'</td><td>'+(row.variance==null?'—':(row.variance>0?'+':'')+row.variance)+'</td></tr>').join('');popup.document.open();popup.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Raw Strength Regional Dashboard</title><style>body{font-family:Arial,sans-serif;color:#0f172a;padding:24px}h1{font-size:20px}p{color:#475569}button{padding:8px 14px;margin:10px 0}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #cbd5e1;padding:7px;text-align:left}th{background:#1e293b;color:white}tr:nth-child(even){background:#f8fafc}@media print{button{display:none}body{padding:0}}</style></head><body><h1>RAW STRENGTH CALISTHENICS — REGIONAL DASHBOARD AUDIT</h1><p>Generated '+escapeHtml(new Date().toLocaleString())+' · '+regionalRows.length+' territories</p><button onclick="window.print()">Print / Save as PDF</button><table><thead><tr><th>State / UT / Island</th><th>Territory Type</th><th>Web leads</th><th>Workbook leads</th><th>All stores</th><th>All gyms</th><th>Dashboard target</th><th>Variance</th></tr></thead><tbody>'+rows+'</tbody></table></body></html>');popup.document.close();popup.focus();};
  const logout=()=>{
    const activeToken=token||localStorage.getItem('rsc_auth_token')||'';
    if(activeToken){
      fetch(API+'/auth/logout',{
        method:'POST',
        headers:{Authorization:'Bearer '+activeToken},
        keepalive:true
      }).catch(()=>{});
    }
    localStorage.removeItem('rsc_auth_token');
    setToken('');
    setUser(null);
    setData({dashboard:null,employees:[],employeeGroups:[],tasks:[],attendance:{date:today(),roster:[],remarks_options:[]},attendanceSummary:{rows:[]},holidays:[],products:[],services:[],orders:[],members:[],prospects:[],messages:[],print:null,archive:[],db:null});
    setAttendanceDrafts({});
    setSelectedAttendanceIds([]);
  };
  const set=(key,value)=>setForm(p=>({...p,[key]:value}));
  const post=async(path,payload)=>{try{const result=await apiFetch(path,{method:'POST',body:JSON.stringify(payload)});if(path==='/attendance/mark'){const selected=data.attendance.date||today();const [refreshed,summary]=await Promise.all([apiFetch('/attendance?work_date='+encodeURIComponent(selected)),apiFetch('/attendance/summary?work_date='+encodeURIComponent(selected))]);setData(p=>({...p,attendance:refreshed,attendanceSummary:summary}));setAttendanceDrafts(previous=>{const next={...previous};delete next[String(payload?.employee_id)];return next;});}else{await load(data.attendance.date||today());}notify(result?.duplicate?'Existing store matched; no duplicate was created.':'Saved successfully');return result;}catch(e){notify(e.message);throw e;}};
  const del=async(path)=>{if(!window.confirm('Delete this record?'))return;await apiFetch(path,{method:'DELETE'});await load();notify('Record deleted')};
  const saveEdit=async()=>{if(!editRecord)return;const {editType,id,...payload}=editRecord;const path=editType==='prospects'?'/customers/prospects/'+id:'/'+editType+'/'+id;try{await apiFetch(path,{method:editType==='prospects'?'PATCH':'PUT',body:JSON.stringify(payload)});setEditRecord(null);await load();notify('Changes saved');}catch(e){notify(e.message)}};
  const downloadEmployeesCsv=async()=>{
    try{
      const response=await fetch(API+'/employees/export.csv',{headers:{Authorization:'Bearer '+token}});
      if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Employee CSV export failed');}
      const blob=await response.blob();
      const url=window.URL.createObjectURL(blob);
      const anchor=document.createElement('a');
      const disposition=response.headers.get('content-disposition')||'';
      const match=disposition.match(/filename="?([^";]+)"?/i);
      anchor.href=url;anchor.download=match?.[1]||'employees.csv';
      document.body.appendChild(anchor);anchor.click();anchor.remove();
      window.setTimeout(()=>window.URL.revokeObjectURL(url),1000);
      notify('Employee list exported');
    }catch(error){notify(error.message)}
  };
  const exposeAllProofLinks=async()=>{
    if(!window.confirm('This will expose full proof links for all employees across all tasks and default reports. Proceed?'))return;
    try{
      const result=await apiFetch('/settings/expose-all-links',{method:'POST'});
      notify('Full proof links enabled across '+result.updated+' tasks.');
      await load();
    }catch(error){notify(error.message)}
  };
  const syncGoogleSheets=async()=>{
    setGoogleSheetsBusy(true);
    setGoogleSheetsStatus('');
    try{
      const result=await apiFetch('/settings/google-sheets-sync',{
        method:'POST',
        body:JSON.stringify({developer_password:googleSheetsPassword})
      });
      setGoogleSheetsStatus(result.message||'Google Sheets sync completed.');
      if(result.status==='synced'){
        notify('Google Sheets master workbook merged: '+result.updated+' records.');
        await load();
      }else{
        notify(result.message||'Google Sheets is unavailable; local records were preserved.');
      }
    }catch(error){
      setGoogleSheetsStatus(error.message);
      notify(error.message);
    }finally{
      setGoogleSheetsBusy(false);
      setGoogleSheetsPassword('');
    }
  };
  const downloadDatabaseBackup=async()=>{
    try{
      const response=await fetch(API+'/web-database/export',{headers:{Authorization:'Bearer '+token}});
      if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Database backup download failed');}
      const blob=await response.blob();
      const url=window.URL.createObjectURL(blob);
      const anchor=document.createElement('a');
      const disposition=response.headers.get('content-disposition')||'';
      const match=disposition.match(/filename="?([^";]+)"?/i);
      anchor.href=url;anchor.download=match?.[1]||'RawStrength-Web-Database.db';
      document.body.appendChild(anchor);anchor.click();anchor.remove();window.URL.revokeObjectURL(url);
      notify('Database backup downloaded');
    }catch(error){notify(error.message)}
  };
  const restoreDatabaseBackup=async()=>{
    if(!canAdminEmployees){notify('Only Admin or Developer can restore a database backup.');return;}
    if(!restoreFile)return;
    if(!window.confirm('Restore this database backup? The current web database will be backed up first. You will need to sign in again.'))return;
    setRestoreBusy(true);
    try{
      const payload=new FormData();payload.append('file',restoreFile);
      const response=await fetch(API+'/web-database/import',{method:'POST',headers:{Authorization:'Bearer '+token},body:payload});
      const body=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(body.detail||'Database restore failed');
      setRestoreFile(null);
      notify(body.message||'Database restored. Sign in again.');
      logout();
    }catch(error){notify(error.message)}
    finally{setRestoreBusy(false)}
  };
  const filtered=(items,keys)=>items.filter(x=>keys.some(k=>String(x[k]??'').toLowerCase().includes(query.toLowerCase())));
  const isEmployee = String(user?.role || '').toLowerCase() === 'employee';
  const canEditEmployees=['hr','admin','developer'].includes(String(user?.role||'').toLowerCase());
  const canAdminEmployees=['admin','developer'].includes(String(user?.role||'').toLowerCase());
  const isDeveloperSyncUser=String(user?.username||'').trim()!=='Admin'
    && !String(user?.username||'').toLowerCase().includes('taruna')
    && !String(user?.display_name||'').toLowerCase().includes('taruna')
    && (String(user?.username||'').trim()==='admin'||String(user?.role||'').trim().toLowerCase()==='developer');
  const employeeRows=useMemo(()=>{
    const term=query.trim().toLowerCase();
    let rows=(data.employees||[]).filter(e=>{
      const haystack=['id','employee_code','name','department','designation','phone','email','joining_date','notes'].map(k=>String(e[k]??'')).join(' ').toLowerCase();
      if(term&&!haystack.includes(term))return false;
      if(employeeDepartment==='all')return true;
      const dept=String(e.department||'').trim().toLowerCase();
      if(employeeDepartment==='General')return !dept||['general','unassigned','default'].includes(dept);
      return dept===employeeDepartment.toLowerCase();
    });
    if(employeeSort==='department')rows.sort((a,b)=>String(a.department||'General').localeCompare(String(b.department||'General'))||Number(a.id)-Number(b.id));
    else if(employeeSort==='name')rows.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));
    else if(employeeSort==='custom')rows.sort((a,b)=>(Number(a.display_order)||0)-(Number(b.display_order)||0)||Number(a.id)-Number(b.id));
    else rows.sort((a,b)=>Number(a.id)-Number(b.id));
    return rows;
  },[data.employees,query,employeeDepartment,employeeSort]);
  const prospectRows=useMemo(()=>{
    const term=query.trim().toLowerCase();
    const excludeTerms=prospectExcludeKeywords.split(',').map(value=>value.trim().toLowerCase()).filter(Boolean);
    const usable=value=>{const text=String(value??'').trim().toLowerCase();return Boolean(text)&&!['n/a','na','none','null','-'].includes(text);};
    return (data.prospects||[]).filter(p=>{
      const haystack=Object.values(p).map(value=>String(value??'')).join(' ').toLowerCase();
      if(term&&!term.split(/\s+/).every(word=>haystack.includes(word)))return false;
      if(prospectStateFilter!=='all'&&!String(p.state||'').split(',').some(value=>value.trim().toLowerCase()===prospectStateFilter.toLowerCase()))return false;
      const hasContact=usable(p.phone)||usable(p.email||p.email_address);
      if(prospectContactFilter==='has'&&!hasContact)return false;
      if(prospectContactFilter==='missing'&&hasContact)return false;
      const hasWebsite=usable(p.website);
      if(prospectWebsiteFilter==='has'&&!hasWebsite)return false;
      if(prospectWebsiteFilter==='missing'&&hasWebsite)return false;
      const verified=['1','yes','y','true','verified'].includes(String(p.verified||'').trim().toLowerCase());
      if(prospectVerificationFilter==='verified'&&!verified)return false;
      if(prospectVerificationFilter==='pending'&&verified)return false;
      const recordKind=String(p.kind||'Store').trim().toLowerCase();
      const category=String(p.business_category||'').toLowerCase();
      const businessName=String(p.business_name||p.name||'').toLowerCase();
      if(prospectKindFilter==='pure product selling stores'){
        const evidenceBlob=[p.business_name||p.name,p.business_category,p.source_status,p.notes].map(value=>String(value||'')).join(' ');
        const addressValue=String(p.address||'').trim();
        const mapsValue=String(p.maps||'').trim().toLowerCase();
        const productEvidence=/\b(supplement|sports nutrition|nutrition retailer|protein|creatine|whey|sports retailer)\b/i.test(evidenceBlob);
        const fullAddress=addressValue.length>=20&&/\b\d{6}\b/.test(addressValue);
        const hasMapsLink=mapsValue.startsWith('https://www.google.com/maps/')||mapsValue.startsWith('https://maps.google.com/')||mapsValue.startsWith('https://maps.app.goo.gl/');
        const negativeEvidence=/\b(pharmacy|chemist|medical|druggist|drug|ayurved|ayurvedic|herbal|herbalife|homeopath|homeopathic|health\s*kart)\b/i.test(evidenceBlob+' '+addressValue);
        if(!['store','supplement store','pure product selling store'].includes(recordKind)||!productEvidence||!fullAddress||!hasMapsLink||negativeEvidence)return false;
      }else if(prospectKindFilter==='store'){
        if(!['store','supplement store','pure product selling store'].includes(recordKind))return false;
      }else if(['gym','gyms'].includes(prospectKindFilter)){
        if(!['gym','gyms'].includes(recordKind))return false;
      }else if(['gyms which sell products also','gym + store','gyms which sell products'].includes(prospectKindFilter)){
        const hybridKind=['gym + store','gym which sells products','gym + store (hybrid)'].includes(recordKind);
        const categoryHasProducts=category.includes('product')||(category.includes('gym')&&['supplement','nutrition','counter','pro-shop','protein','shake'].some(word=>category.includes(word)));
        if(!hybridKind&&!categoryHasProducts)return false;
      }else if(prospectKindFilter!=='all'&&recordKind!==prospectKindFilter.toLowerCase())return false;
      if(prospectExcludeFilter==='missing_contact'&&!hasContact)return false;
      if(prospectExcludeFilter==='missing_website'&&!hasWebsite)return false;
      if(prospectExcludeFilter==='unverified'&&!verified)return false;
      if(prospectExcludeFilter==='gym_wellness_herbal_healthkart'){
        const isGym=['gym','gyms','gym + store','gym which sells products','gym + store (hybrid)'].includes(recordKind)||category.includes('gym')||businessName.includes('gym')||category.includes('fitness cent');
        const isWellness=haystack.includes('wellness');
        const isHerbal=['herbal','herbalife','ayurved','homeopath'].some(word=>haystack.includes(word));
        const isHealthKart=haystack.includes('healthkart');
        if(isGym||isWellness||isHerbal||isHealthKart)return false;
      }
      if(prospectExcludeKind!=='all'){
        const excludedKind=prospectExcludeKind.trim().toLowerCase();
        let excluded=false;
        if(excludedKind==='pure product selling stores')excluded=['store','supplement store','pure product selling store'].includes(recordKind)&&recordKind!=='gym + store';
        else if(['gym','gyms'].includes(excludedKind))excluded=['gym','gyms'].includes(recordKind);
        else if(excludedKind==='gyms which sell products also')excluded=['gym + store','gym which sells products','gym + store (hybrid)'].includes(recordKind)||category.includes('product')||(category.includes('gym')&&['supplement','nutrition','counter','pro-shop','protein','shake'].some(word=>category.includes(word)));
        else excluded=recordKind===excludedKind||category.includes(excludedKind);
        if(excluded)return false;
      }
      if(prospectExcludeState!=='all'&&String(p.state||'').split(',').some(value=>value.trim().toLowerCase()===prospectExcludeState.toLowerCase()))return false;
      if(prospectExcludeName.trim()&&businessName.includes(prospectExcludeName.trim().toLowerCase()))return false;
      const districtBlob=[p.city,p.area,p.district].map(value=>String(value||'')).join(' ').toLowerCase();
      if(prospectExcludeDistrict.trim()&&districtBlob.includes(prospectExcludeDistrict.trim().toLowerCase()))return false;
      if(excludeTerms.some(word=>haystack.includes(word)))return false;
      return true;
    });
  },[data.prospects,query,prospectStateFilter,prospectKindFilter,prospectWebsiteFilter,prospectVerificationFilter,prospectContactFilter,prospectExcludeFilter,prospectExcludeKind,prospectExcludeState,prospectExcludeName,prospectExcludeDistrict,prospectExcludeKeywords]);
  const prospectPageSize=100;
  const prospectPageCount=Math.max(1,Math.ceil(prospectRows.length/prospectPageSize));
  const visibleProspectRows=prospectRows.slice((prospectPage-1)*prospectPageSize,prospectPage*prospectPageSize);
  const regionalRows=useMemo(()=>{const rows=regionalSummary.rows||[];return rows.filter(row=>regionalTerritoryFilter==='all'||row.territory_type===regionalTerritoryFilter)},[regionalSummary,regionalTerritoryFilter]);
  useEffect(()=>{setProspectPage(1)},[query,prospectStateFilter,prospectKindFilter,prospectWebsiteFilter,prospectVerificationFilter,prospectContactFilter,prospectExcludeFilter,prospectExcludeKind,prospectExcludeState,prospectExcludeName,prospectExcludeDistrict,prospectExcludeKeywords]);
  useEffect(()=>{setProspectPage(page=>Math.min(page,prospectPageCount))},[prospectPageCount]);
  const selectedEmployee=(data.employees||[]).find(e=>Number(e.id)===Number(employeeSelectedId))||null;
  const saveNewEmployee=async e=>{
    e.preventDefault();
    if(!canEditEmployees){notify('HR, Admin or Developer permission is required.');return;}
    try{
      await apiFetch('/employees',{method:'POST',body:JSON.stringify(employeeForm)});
      setEmployeeForm({name:'',employee_code:'',department:'',designation:'',phone:'',email:'',joining_date:'',notes:''});
      await load();
      notify('Employee added successfully');
    }catch(err){notify(err.message)}
  };
  const updateEmployeeStatus=async()=>{
    if(!selectedEmployee)return;
    try{await apiFetch('/employees/'+selectedEmployee.id+'/status',{method:'PATCH',body:JSON.stringify({active:!Boolean(selectedEmployee.active)})});await load();notify('Employee status updated')}
    catch(err){notify(err.message)}
  };
  const deleteEmployeePermanently=async()=>{
    if(!selectedEmployee)return;
    if(!window.confirm('Permanently delete '+selectedEmployee.name+'? A safety database backup will be created first. Their tasks and attendance will also be removed.'))return;
    try{const result=await apiFetch('/employees/'+selectedEmployee.id+'/permanent',{method:'DELETE'});setEmployeeSelectedId(null);await load();notify('Employee deleted. Safety backup: '+result.backup_file)}
    catch(err){notify(err.message)}
  };
  const moveEmployee=async direction=>{
    if(!selectedEmployee)return;
    const ordered=[...(data.employees||[])].sort((a,b)=>(Number(a.display_order)||0)-(Number(b.display_order)||0)||Number(a.id)-Number(b.id));
    const index=ordered.findIndex(e=>Number(e.id)===Number(selectedEmployee.id)),target=index+direction;
    if(index<0||target<0||target>=ordered.length)return;
    [ordered[index],ordered[target]]=[ordered[target],ordered[index]];
    const items=ordered.map((e,i)=>({id:Number(e.id),display_order:(i+1)*10,department:e.department||''}));
    try{await apiFetch('/employee-directory/reorder',{method:'PUT',body:JSON.stringify({items})});setEmployeeSort('custom');await load();notify('Employee order updated')}
    catch(err){notify(err.message)}
  };
  const moveEmployeeToGroup=async()=>{
    if(!selectedEmployee||!moveToGroup)return;
    const department=moveToGroup==='General'?'':moveToGroup;
    try{await apiFetch('/employee-directory/reorder',{method:'PUT',body:JSON.stringify({items:[{id:Number(selectedEmployee.id),display_order:Number(selectedEmployee.display_order)||0,department}]})});setMoveToGroup('');await load();notify('Employee moved to section')}
    catch(err){notify(err.message)}
  };
  const createEmployeeGroup=async e=>{
    e.preventDefault();const name=groupNameDraft.trim();if(!name)return;
    try{await apiFetch('/employee-groups',{method:'POST',body:JSON.stringify({name})});setGroupNameDraft('');await load();setGroupSelected(name);setGroupRenameDraft(name);notify('Section created')}
    catch(err){notify(err.message)}
  };
  const renameEmployeeGroup=async()=>{
    if(!groupSelected||!groupRenameDraft.trim())return;
    try{const name=groupRenameDraft.trim();await apiFetch('/employee-groups',{method:'PATCH',body:JSON.stringify({old_name:groupSelected,new_name:name})});await load();setGroupSelected(name);setGroupRenameDraft(name);notify('Section renamed')}
    catch(err){notify(err.message)}
  };
  const deleteEmployeeGroup=async()=>{
    if(!groupSelected||!window.confirm('Delete section '+groupSelected+'? Employees will become General / Unassigned.'))return;
    try{await apiFetch('/employee-groups',{method:'DELETE',body:JSON.stringify({name:groupSelected})});setGroupSelected('');setGroupRenameDraft('');await load();notify('Section deleted')}
    catch(err){notify(err.message)}
  };
  const reorderEmployeeGroup=async direction=>{
    const groups=[...(data.employeeGroups||[])],index=groups.findIndex(g=>g.name===groupSelected),target=index+direction;
    if(index<0||target<0||target>=groups.length)return;
    [groups[index],groups[target]]=[groups[target],groups[index]];
    try{await apiFetch('/employee-groups/order',{method:'PUT',body:JSON.stringify({group_names:groups.map(g=>g.name)})});await load();setGroupSelected(groups[target].name);setGroupRenameDraft(groups[target].name);notify('Section order updated')}
    catch(err){notify(err.message)}
  };
  const selectedAttendanceDate=data.attendance.date||today();
  const selectedAttendanceHoliday=(data.holidays||[]).find(h=>h.holiday_date===selectedAttendanceDate);
  const attendanceIsHoliday=Boolean(selectedAttendanceHoliday);
  const visibleAttendanceRows=(data.attendance.roster||[]).filter(r=>{
    if(isEmployee && user?.employee_id && Number(r.employee_id) !== Number(user.employee_id)) return false;
    return attendanceFilter==='all'||String(r.employee_id)===String(attendanceFilter);
  });
  const attendanceDraftFor=r=>({...r,...(attendanceDrafts[r.employee_id]||{})});
  const updateAttendanceDraft=(r,key,value)=>setAttendanceDrafts(prev=>({...prev,[r.employee_id]:{...(prev[r.employee_id]||r),[key]:value}}));
  const toggleAttendanceSelection=id=>setSelectedAttendanceIds(prev=>prev.includes(Number(id))?prev.filter(x=>x!==Number(id)):[...prev,Number(id)]);
  const selectVisibleAttendance=()=>{const ids=visibleAttendanceRows.map(r=>Number(r.employee_id));setSelectedAttendanceIds(prev=>ids.every(id=>prev.includes(id))?prev.filter(id=>!ids.includes(id)):[...new Set([...prev,...ids])])};
  const attendanceNetHours=(checkIn,checkOut,breakMinutes=0)=>{if(!checkIn||!checkOut)return '—';const [ih,im]=checkIn.split(':').map(Number),[oh,om]=checkOut.split(':').map(Number);if([ih,im,oh,om].some(Number.isNaN))return '—';let minutes=(oh*60+om)-(ih*60+im);if(minutes<0)minutes+=1440;minutes=Math.max(0,minutes-Math.max(0,Number(breakMinutes)||0));return (minutes/60).toFixed(2)};
  const flushAttendanceDrafts=async(workDate=selectedAttendanceDate)=>{
    const pending=Object.entries(attendanceDrafts);
    if(!pending.length)return 0;
    const rowsById=new Map((data.attendance.roster||[]).map(row=>[String(row.employee_id),row]));
    for(const [employeeId,changes] of pending){
      const row=rowsById.get(String(employeeId));
      if(!row)throw new Error('Could not find employee '+employeeId+' in the current attendance roster.');
      const draft={...row,...changes};
      await apiFetch('/attendance/mark',{method:'POST',body:JSON.stringify({
        employee_id:Number(employeeId),work_date:workDate,
        attendance_status:draft.attendance_status||'Unmarked',
        check_in:draft.check_in||'',check_out:draft.check_out||'',
        break_minutes:Number(draft.break_minutes||0),
        attendance_note:draft.attendance_note||''
      })});
    }
    return pending.length;
  };
  const refreshAttendanceDate=async workDate=>{
    const [attendance,summary]=await Promise.all([
      apiFetch('/attendance?work_date='+encodeURIComponent(workDate)),
      apiFetch('/attendance/summary?work_date='+encodeURIComponent(workDate))
    ]);
    setData(previous=>({...previous,attendance,attendanceSummary:summary}));
  };
  const saveAttendanceDraft=async r=>{
    if(attendanceBusy)return;
    setAttendanceBusy(true);
    try{
      const draft=attendanceDraftFor(r);
      await apiFetch('/attendance/mark',{method:'POST',body:JSON.stringify({
        employee_id:Number(r.employee_id),work_date:selectedAttendanceDate,
        attendance_status:draft.attendance_status||'Unmarked',
        check_in:draft.check_in||'',check_out:draft.check_out||'',
        break_minutes:Number(draft.break_minutes||0),
        attendance_note:draft.attendance_note||''
      })});
      await refreshAttendanceDate(selectedAttendanceDate);
      setAttendanceDrafts(previous=>{const next={...previous};delete next[r.employee_id];return next;});
      notify('Attendance saved for '+r.name);
    }catch(error){notify(error.message);}
    finally{setAttendanceBusy(false);}
  };
  const saveAllAttendanceDrafts=async()=>{
    if(attendanceBusy)return;
    const pendingCount=Object.keys(attendanceDrafts).length;
    if(!pendingCount)return;
    setAttendanceBusy(true);
    try{
      await flushAttendanceDrafts(selectedAttendanceDate);
      await refreshAttendanceDate(selectedAttendanceDate);
      setAttendanceDrafts({});
      notify('Saved attendance for '+pendingCount+' employees.');
    }catch(error){notify('Attendance was not fully saved: '+error.message);}
    finally{setAttendanceBusy(false);}
  };
  const applyAttendanceBulk=async()=>{
    if(!selectedAttendanceIds.length||attendanceIsHoliday||attendanceBusy)return;
    setAttendanceBusy(true);
    try{
      await flushAttendanceDrafts(selectedAttendanceDate);
      const result=await apiFetch('/attendance/bulk-edit',{method:'POST',body:JSON.stringify({work_date:selectedAttendanceDate,employee_ids:selectedAttendanceIds,...bulkAttendance})});
      await refreshAttendanceDate(selectedAttendanceDate);
      setAttendanceDrafts({});
      notify('Updated attendance for '+result.updated+' employees');
    }catch(error){notify(error.message);}
    finally{setAttendanceBusy(false);}
  };
  const resolveAttendanceToolbarTarget=()=>{
    if(selectedAttendanceIds.length>1)throw new Error('Choose one employee for this action, or use Bulk edit selected.');
    const selectedId=selectedAttendanceIds.length===1?Number(selectedAttendanceIds[0]):attendanceFilter!=='all'?Number(attendanceFilter):null;
    const row=selectedId?(data.attendance.roster||[]).find(item=>Number(item.employee_id)===selectedId):visibleAttendanceRows.length===1?visibleAttendanceRows[0]:null;
    if(!row)throw new Error('Select one employee with the row checkbox or choose one in Filter employee.');
    return row;
  };
  const attendanceIsPresentStatus=status=>['present','late check-in','late check-out','on time','balanced hours','overtime','short hours','early departure'].includes(String(status||'').trim().toLowerCase());
  const isValidAttendanceTime=value=>/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(String(value||'').trim());
  const saveAttendanceToolbarUpdate=async(row,changes,actionLabel)=>{
    if(attendanceBusy||attendanceIsHoliday)return false;
    setAttendanceBusy(true);
    try{
      await flushAttendanceDrafts(selectedAttendanceDate);
      const draft=attendanceDraftFor(row);
      await apiFetch('/attendance/mark',{method:'POST',body:JSON.stringify({
        employee_id:Number(row.employee_id),work_date:selectedAttendanceDate,
        attendance_status:changes.attendance_status??draft.attendance_status??'Unmarked',
        check_in:changes.check_in??draft.check_in??'',
        check_out:changes.check_out??draft.check_out??'',
        break_minutes:Number(draft.break_minutes||0),
        attendance_note:changes.attendance_note??draft.attendance_note??''
      })});
      await refreshAttendanceDate(selectedAttendanceDate);
      setAttendanceDrafts({});
      notify(actionLabel+' saved for '+row.name);
      return true;
    }catch(error){notify(error.message);return false;}
    finally{setAttendanceBusy(false);}
  };
  const runAttendanceStatusAction=async status=>{
    let row;
    try{row=resolveAttendanceToolbarTarget();}catch(error){notify(error.message);return;}
    const changes={attendance_status:status};
    if(['Absent','Leave','Unmarked'].includes(status)){changes.check_in='';changes.check_out='';}
    await saveAttendanceToolbarUpdate(row,changes,status);
  };
  const runAttendanceTimeAction=async action=>{
    let row;
    try{row=resolveAttendanceToolbarTarget();}catch(error){notify(error.message);return;}
    const draft=attendanceDraftFor(row);
    const now=new Date();
    const defaultTime=String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0');
    if(action==='check-in'){
      const entered=window.prompt('Check-in time (HH:MM):',defaultTime);
      if(entered===null||!entered.trim())return;
      const time=entered.trim();
      if(!isValidAttendanceTime(time)){notify('Enter check-in time in 24-hour HH:MM format, for example 09:30.');return;}
      const status=attendanceIsPresentStatus(draft.attendance_status)?draft.attendance_status:'Present';
      await saveAttendanceToolbarUpdate(row,{attendance_status:status,check_in:time},'Check-in');
      return;
    }
    if(action==='check-out'){
      const checkIn=String(draft.check_in||'').trim();
      if(!isValidAttendanceTime(checkIn)){notify('Record a valid check-in before recording check-out.');return;}
      const entered=window.prompt('Check-out time (HH:MM):',defaultTime);
      if(entered===null||!entered.trim())return;
      const time=entered.trim();
      if(!isValidAttendanceTime(time)){notify('Enter check-out time in 24-hour HH:MM format, for example 18:00.');return;}
      const status=attendanceIsPresentStatus(draft.attendance_status)?draft.attendance_status:'Present';
      await saveAttendanceToolbarUpdate(row,{attendance_status:status,check_in:checkIn,check_out:time},'Check-out');
      return;
    }
    if(action==='edit-times'){
      const enteredIn=window.prompt('Edit check-in time (HH:MM):',draft.check_in||'');
      if(enteredIn===null)return;
      const enteredOut=window.prompt('Edit check-out time (HH:MM):',draft.check_out||'');
      if(enteredOut===null)return;
      const checkIn=enteredIn.trim(),checkOut=enteredOut.trim();
      if(checkIn&&!isValidAttendanceTime(checkIn)){notify('Check-in must use 24-hour HH:MM format.');return;}
      if(checkOut&&!isValidAttendanceTime(checkOut)){notify('Check-out must use 24-hour HH:MM format.');return;}
      if(checkOut&&!checkIn){notify('A check-out time requires a check-in time.');return;}
      const status=attendanceIsPresentStatus(draft.attendance_status)?draft.attendance_status:'Present';
      await saveAttendanceToolbarUpdate(row,{attendance_status:status,check_in:checkIn,check_out:checkOut},'Attendance times');
      return;
    }
    if(action==='remarks'){
      setAttendanceRemarksTarget(row);
      setAttendanceRemarksDraft(draft.attendance_note||'');
    }
  };
  const employeeOptions=data.employees.map(e=><option key={e.id} value={e.id}>{e.name}</option>);
  const visibleNavItems = useMemo(() => {
    if (isEmployee) {
      return navItems.filter(([id]) => ['home', 'tasks', 'attendance', 'chat'].includes(id));
    }
    return navItems;
  }, [isEmployee]);

  useEffect(() => {
    if (isEmployee && !['home', 'tasks', 'attendance', 'chat'].includes(tab)) {
      setTab('home');
    }
  }, [isEmployee, tab]);

  const heading=visibleNavItems.find(x=>x[0]===tab)?.[1]||'Home';


  if (storeRoute) return <Storefront onBack={() => { window.location.hash = ''; setStoreRoute(false); setTab('home'); }} />;

  if(!checked)return <div className="grid min-h-screen place-items-center bg-[#080d18] text-cyan-300">Loading…</div>;
  if(!user)return <div className="login-screen grid min-h-screen place-items-center bg-[#080d18] p-4 text-white"><div className="w-full max-w-md rounded-3xl border border-cyan-400/20 bg-slate-900/90 p-6 sm:p-8 shadow-2xl"><img src={brandLogo} className="mb-5 h-16 w-16 rounded-xl object-contain" alt="Raw Strength"/><h1 className="text-xl font-black">Raw Strength Calisthenics</h1><p className="mb-5 mt-1 text-sm text-slate-400">Employee Audit Manager · {authMode==='login'?'Sign in':authMode==='register'?'Create account':authMode==='change'?'Change password':'Reset password'}</p>{authNotice&&<p className="mb-4 rounded-lg border border-cyan-400/20 bg-cyan-950/40 p-3 text-sm text-cyan-200">{authNotice}</p>}{error&&<p className="mb-4 rounded-lg bg-rose-950 p-3 text-sm text-rose-300">{error}</p>}{authMode==='login'&&<form onSubmit={submitLogin}><label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>setLogin(p=>({...p,username:e.target.value}))} autoComplete="username" required/><span className="mt-1 block text-[11px] leading-relaxed text-slate-500">Use the exact account capitalization: customer <strong className="text-slate-300">Admin</strong>; developer/test <strong className="text-slate-300">admin</strong>. These are separate accounts.</span></label><label className="mb-5 block text-xs text-slate-400">Password<span className="mt-1 flex gap-2"><input className={field} type={showPassword?'text':'password'} value={login.password} onChange={e=>setLogin(p=>({...p,password:e.target.value}))} autoComplete="current-password" required/><button type="button" className="shrink-0 rounded-lg border border-white/10 px-3 text-xs text-cyan-200" onClick={()=>setShowPassword(v=>!v)}>{showPassword?'Hide':'Show'}</button></span></label><button className={btn+' w-full'} disabled={busy}>{busy?'Signing in…':'Sign in'}</button><div className="mt-5 flex flex-wrap justify-between gap-3 text-sm"><button type="button" className="text-cyan-300" onClick={()=>{setError('');setAuthNotice('');setAuthMode('forgot');setRecoveryReady(false)}}>Forgot password?</button><button type="button" className="text-cyan-300" onClick={()=>{setError('');setAuthNotice('');setAuthMode('change');setPasswordChange({current_password:'',new_password:'',confirm_password:''})}}>Change password</button><button type="button" className="text-cyan-300" onClick={()=>{setError('');setAuthNotice('');setAuthMode('register')}}>Create new account</button></div></form>}{authMode==='register'&&<form onSubmit={submitRegistration}><label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>setLogin(p=>({...p,username:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">Display name<input className={field+' mt-1'} value={authProfile.display_name} onChange={e=>setAuthProfile(p=>({...p,display_name:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">Password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={login.password} onChange={e=>setLogin(p=>({...p,password:e.target.value}))} required minLength={8}/></label><label className="mb-3 block text-xs text-slate-400">Confirm password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={authProfile.confirm_password} onChange={e=>setAuthProfile(p=>({...p,confirm_password:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">Recovery question<select className={field+' mt-1'} value={authProfile.security_question} onChange={e=>setAuthProfile(p=>({...p,security_question:e.target.value}))}>{['What was the name of your first school?','What is the name of the city where you were born?','What was your childhood nickname?','What is the name of your first teacher?','What was the first concert or live event you attended?'].map(q=><option key={q}>{q}</option>)}</select></label><label className="mb-5 block text-xs text-slate-400">Recovery answer<input className={field+' mt-1'} value={authProfile.security_answer} onChange={e=>setAuthProfile(p=>({...p,security_answer:e.target.value}))} required/></label><button className={btn+' w-full'} disabled={busy}>{busy?'Submitting…':'Create account'}</button><button type="button" className="mt-4 w-full text-sm text-cyan-300" onClick={()=>{setError('');setAuthMode('login')}}>Back to sign in</button><p className="mt-3 text-xs text-slate-500">New accounts require Admin approval before they can sign in.</p></form>}{authMode==='forgot'&&<form onSubmit={submitPasswordReset}><label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>{setLogin(p=>({...p,username:e.target.value}));setRecoveryReady(false)}} required/></label>{!recoveryReady?<button type="button" className={btn+' w-full'} onClick={findRecoveryQuestion}>Find recovery question</button>:<><div className="mb-3 rounded-lg bg-slate-950 p-3 text-sm text-cyan-200">{recoveryQuestion}</div><label className="mb-3 block text-xs text-slate-400">Recovery answer<input className={field+' mt-1'} value={authProfile.security_answer} onChange={e=>setAuthProfile(p=>({...p,security_answer:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">New password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={login.password} onChange={e=>setLogin(p=>({...p,password:e.target.value}))} required minLength={8}/></label><label className="mb-5 block text-xs text-slate-400">Confirm new password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={authProfile.confirm_password} onChange={e=>setAuthProfile(p=>({...p,confirm_password:e.target.value}))} required/></label><button className={btn+' w-full'} disabled={busy}>{busy?'Resetting…':'Reset password'}</button></>}<button type="button" className="mt-4 w-full text-sm text-cyan-300" onClick={()=>{setError('');setAuthMode('login')}}>Back to sign in</button></form>}{authMode==='change'&&<form onSubmit={submitPasswordChange}>
  <label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>setLogin(p=>({...p,username:e.target.value}))} autoComplete="username" required/></label>
  <label className="mb-3 block text-xs text-slate-400">Current password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={passwordChange.current_password} onChange={e=>setPasswordChange(p=>({...p,current_password:e.target.value}))} autoComplete="current-password" required/></label>
  <label className="mb-3 block text-xs text-slate-400">New password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={passwordChange.new_password} onChange={e=>setPasswordChange(p=>({...p,new_password:e.target.value}))} autoComplete="new-password" minLength={8} required/></label>
  <label className="mb-5 block text-xs text-slate-400">Confirm new password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={passwordChange.confirm_password} onChange={e=>setPasswordChange(p=>({...p,confirm_password:e.target.value}))} autoComplete="new-password" minLength={8} required/></label>
  <button className={btn+' w-full'} disabled={busy}>{busy?'Changing…':'Change password'}</button>
  <button type="button" className="mt-4 w-full text-sm text-cyan-300" onClick={()=>{setError('');setAuthMode('login')}}>Back to sign in</button>
</form>}</div></div>;

  return <div className="webapp-root flex h-screen min-h-0 overflow-hidden bg-[#080d18] text-slate-100">
    {groupManagerOpen&&<div className="fixed inset-0 z-[95] grid place-items-center overflow-y-auto bg-black/75 p-4"><section className="my-6 w-full max-w-3xl rounded-2xl border border-cyan-400/20 bg-slate-900 p-5 shadow-2xl">
      <div className="mb-4 flex items-center justify-between"><div><h2 className="font-bold text-white">Manage Employee Sections & Groups</h2><p className="mt-1 text-xs text-slate-400">Create, rename, reorder and remove employee sections.</p></div><button className="text-slate-400" onClick={()=>setGroupManagerOpen(false)}>Close</button></div>
      <form className="mb-4 flex flex-wrap gap-2" onSubmit={createEmployeeGroup}><input className={field+' min-w-0 flex-1'} placeholder="New section name" value={groupNameDraft} onChange={e=>setGroupNameDraft(e.target.value)} required/><button className={btn}><Plus size={15}/> Add Section</button></form>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3"><h3 className="mb-3 text-sm font-bold text-white">Sections ({data.employeeGroups.length})</h3><div className="max-h-72 space-y-1 overflow-y-auto">{data.employeeGroups.map(g=><button key={g.name} onClick={()=>{setGroupSelected(g.name);setGroupRenameDraft(g.name)}} className={'flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm '+(groupSelected===g.name?'bg-cyan-400/15 text-cyan-200':'text-slate-300 hover:bg-white/5')}><span>{g.name}</span><span className="text-xs text-slate-500">{g.employee_count}</span></button>)}{!data.employeeGroups.length&&<p className="text-xs text-slate-500">No sections found.</p>}</div></div>
        <div className="space-y-3 rounded-xl border border-white/10 bg-slate-950/60 p-3"><h3 className="text-sm font-bold text-white">Selected section</h3><select className={field} value={groupSelected} onChange={e=>{setGroupSelected(e.target.value);setGroupRenameDraft(e.target.value)}}><option value="">Select section</option>{data.employeeGroups.map(g=><option key={g.name} value={g.name}>{g.name}</option>)}</select><input className={field} value={groupRenameDraft} onChange={e=>setGroupRenameDraft(e.target.value)} placeholder="Section name"/><div className="flex flex-wrap gap-2"><button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!groupSelected} onClick={()=>reorderEmployeeGroup(-1)}>Move Up</button><button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!groupSelected} onClick={()=>reorderEmployeeGroup(1)}>Move Down</button><button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!groupSelected||!groupRenameDraft.trim()} onClick={renameEmployeeGroup}>Rename</button><button className="rounded-lg border border-rose-400/20 px-3 py-2 text-sm text-rose-300 disabled:opacity-40" disabled={!groupSelected} onClick={deleteEmployeeGroup}>Delete</button></div><p className="text-xs text-slate-500">Deleting a section moves its employees to General / Unassigned. Historical task department labels remain unchanged.</p></div>
      </div>
      <div className="mt-5 flex justify-end"><button className="rounded-lg border border-white/10 px-4 py-2 text-sm" onClick={()=>setGroupManagerOpen(false)}>Done</button></div>
    </section></div>}
    {editRecord&&<div className="fixed inset-0 z-[100] grid place-items-center overflow-y-auto bg-black/70 p-4"><section className="my-6 w-full max-w-3xl rounded-2xl border border-cyan-400/20 bg-slate-900 p-5 shadow-2xl"><div className="mb-4 flex items-center justify-between"><h2 className="font-bold text-white">Edit {editRecord.editType==='employees'?'employee':editRecord.editType==='prospects'?'store / prospect':'task'}</h2><button className="text-slate-400" onClick={()=>setEditRecord(null)}>Close</button></div><div className="grid gap-3 sm:grid-cols-2">{(editRecord.editType==='employees'?['name','employee_code','department','designation','phone','email','joining_date','notes','active']:editRecord.editType==='prospects'?['business_name','business_category','kind','state','city','area','contact_person','phone','email','address','website','maps','followup_date','call_time','connection','verified','response','source_status','notes']:['title','employee_id','task_date','department','details','due_time','priority','status','progress','target_qty','actual_qty','next_action','proof_url','proof_note','manager_note','expose_link']).map(k=><label key={k} className="block text-xs text-slate-400"><span className="mb-1 block">{k.replaceAll('_',' ')}</span>{k==='employee_id'?<select className={field} value={editRecord[k]??''} onChange={e=>setEditRecord(p=>({...p,[k]:Number(e.target.value)}))}><option value="">Select employee</option>{data.employees.map(e=><option key={e.id} value={e.id}>{e.name}</option>)}</select>:['details','notes','proof_note','manager_note','next_action','address'].includes(k)?<textarea className={field} rows="2" value={editRecord[k]??''} onChange={e=>setEditRecord(p=>({...p,[k]:e.target.value}))}/>:k==='active'?<select className={field} value={Number(editRecord[k]??1)} onChange={e=>setEditRecord(p=>({...p,[k]:Number(e.target.value)}))}><option value="1">Active</option><option value="0">Inactive</option></select>:k==='status'?<select className={field} value={editRecord[k]??'Not started'} onChange={e=>setEditRecord(p=>({...p,[k]:e.target.value}))}>{['Not started','In progress','Partially completed','Submitted','Completed','Blocked','Pending review','Pending','Cancelled'].map(v=><option key={v}>{v}</option>)}</select>:<input className={field} type={['task_date','joining_date','followup_date'].includes(k)?'date':k==='call_time'?'time':['website','maps'].includes(k)?'url':'text'} value={editRecord[k]??''} onChange={e=>setEditRecord(p=>({...p,[k]:['progress','expose_link','active'].includes(k)?Number(e.target.value):e.target.value}))}/>}</label>)}</div><div className="mt-5 flex justify-end gap-2"><button className="rounded-lg border border-white/10 px-4 py-2 text-sm" onClick={()=>setEditRecord(null)}>Cancel</button><button className={btn} onClick={saveEdit}>Save changes</button></div></section></div>}
    {notice&&<div className="fixed right-4 top-4 z-[90] rounded-xl border border-cyan-400/30 bg-slate-900 px-4 py-3 text-sm text-cyan-200">{notice}</div>}
    {sidebar&&<button aria-label="Close menu" onClick={()=>setSidebar(false)} className="fixed inset-0 z-40 bg-black/60 md:hidden"/>}
    <aside className={`fixed inset-y-0 left-0 z-50 flex ${sidebarCollapsed?'w-16':'w-56'} flex-col border-r border-white/10 bg-slate-950/95 transition-all duration-200 md:static md:translate-x-0 ${sidebar?'translate-x-0':'-translate-x-full'}`}>
      <div className="p-3 border-b border-white/10">
        <button
          type="button"
          onClick={()=>setSidebarCollapsed(c=>!c)}
          className="flex w-full items-center justify-between rounded-lg border border-white/10 bg-white/5 px-2.5 py-2 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition"
          title="Collapse or expand navigation"
        >
          <span className="text-sm">☰</span>
          {!sidebarCollapsed && <span className="font-bold tracking-wide">Collapse menu</span>}
        </button>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {visibleNavItems.map(([id,label,Icon])=>{
          const isActive = tab === id;
          return (
            <button
              key={id}
              onClick={()=>{setTab(id);setSidebar(false)}}
              title={label}
              className={`flex w-full items-center ${sidebarCollapsed ? 'justify-center px-1' : 'gap-2.5 px-3'} py-2.5 rounded-lg text-left text-xs font-semibold transition ${
                isActive
                  ? 'border-l-4 border-l-cyan-400 bg-cyan-400/15 text-cyan-200 font-bold shadow-sm'
                  : 'border-l-4 border-l-transparent text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {sidebarCollapsed ? (
                <span className="text-base" title={label}>{label.split(' ')[0]}</span>
              ) : (
                <span className="truncate">{label}</span>
              )}
            </button>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-3">
        {!sidebarCollapsed && (
          <div className="mb-2 min-w-0">
            <p className="truncate text-xs font-bold text-white">{user.display_name||user.username}</p>
            <p className="text-[11px] text-cyan-300 font-semibold">{user.role}</p>
          </div>
        )}
        <a
          href="https://github.com/yalangisexter-ux/audit-report/releases/latest/download/RawStrengthEmployeeAuditManager-Setup.exe"
          target="_blank"
          rel="noopener noreferrer"
          className={`mb-2 flex items-center ${sidebarCollapsed ? 'justify-center w-full' : 'gap-2'} text-xs font-semibold text-purple-300 hover:text-purple-200`}
          title="Download Windows Desktop App (.exe)"
        >
          <Download size={14} /> {!sidebarCollapsed && <span>Download Desktop (.exe)</span>}
        </a>
        <button onClick={logout} className={`flex items-center ${sidebarCollapsed ? 'justify-center w-full' : 'gap-2'} text-xs font-semibold text-rose-300 hover:text-rose-200`} title="Sign out">
          <LogOut size={14}/> {!sidebarCollapsed && <span>Sign out</span>}
        </button>
      </div>
    </aside>
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="flex min-h-[88px] sm:min-h-[96px] shrink-0 items-center justify-between gap-2 sm:gap-3 border-b border-white/10 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 px-3 sm:px-4 py-2 shadow-lg overflow-hidden">
        <div className="flex shrink-0 items-center gap-2.5 sm:gap-3">
          <button onClick={()=>setSidebar(true)} className="rounded-lg border border-white/10 p-2 md:hidden text-slate-300 hover:text-white shrink-0">
            <Menu size={18}/>
          </button>
          <div className="relative rounded-xl p-[2px] bg-gradient-to-r from-cyan-400 via-indigo-500 to-purple-500 shadow-lg shadow-cyan-500/10 shrink-0">
            <div className="h-12 w-12 sm:h-16 sm:w-16 md:h-20 md:w-20 rounded-[10px] bg-slate-950/90 flex items-center justify-center p-1 sm:p-1.5">
              <img src={brandLogo} alt="Raw Strength Calisthenics" className="h-full w-full object-contain" />
            </div>
          </div>
          <div className="shrink-0 flex flex-col justify-center">
            <h1 className="text-sm sm:text-lg md:text-xl lg:text-2xl font-black tracking-tight text-white whitespace-nowrap select-none" style={{ whiteSpace: 'nowrap' }}>
              Raw Strength Calisthenics
            </h1>
            <p className="mt-0.5 text-[9px] sm:text-[11px] md:text-xs font-extrabold tracking-[0.14em] uppercase text-cyan-300 whitespace-nowrap select-none" style={{ whiteSpace: 'nowrap' }}>
              EXECUTIVE AUDIT &nbsp;•&nbsp; OPERATIONS OS &nbsp;•&nbsp; v1.3.82
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2.5 ml-auto">
          {/* Day / Night mode instant toggle matching desktop EXE benchmark */}
          <button
            type="button"
            onClick={()=>setTheme(theme==='night'?'day':'night')}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-bold transition shadow-sm ${theme==='night' ? 'border-amber-400/40 bg-amber-400/15 text-amber-200 hover:bg-amber-400/25' : 'border-sky-400/40 bg-sky-500/20 text-sky-100 hover:bg-sky-500/30'}`}
            title={theme==='night' ? "Switch to Day mode" : "Switch to Night mode"}
          >
            {theme==='night' ? '☀️ Day mode' : '🌙 Night mode'}
          </button>

          <button
            type="button"
            onClick={()=>{window.location.hash='#store';setStoreRoute(true);}}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/40 bg-cyan-400/15 px-2.5 py-1.5 text-xs font-bold text-cyan-200 hover:bg-cyan-400/25 transition"
            title="Open online customer storefront"
          >
            🛍️ Storefront ↗
          </button>

          <button
            type="button"
            onClick={()=>load()}
            title="Continuous Cloud Sync is Active. Data is continuously encrypted and synchronized automatically in the background. Click to check for updates now."
            className="hidden 2xl:inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/50 bg-gradient-to-b from-emerald-500/20 to-emerald-600/30 px-3 py-1.5 text-xs font-bold text-emerald-100 hover:from-emerald-500/30 hover:to-emerald-600/40 transition shadow-sm"
          >
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" /> Auto-Synced
          </button>

          <a
            href="https://github.com/yalangisexter-ux/audit-report/releases/latest/download/RawStrengthEmployeeAuditManager-Setup.exe"
            target="_blank"
            rel="noopener noreferrer"
            title="Download the official Windows Desktop Application (.exe installer)"
            className="hidden 2xl:inline-flex items-center gap-1.5 rounded-lg border border-purple-400/40 bg-purple-500/20 px-3 py-1.5 text-xs font-bold text-purple-200 hover:bg-purple-500/30 transition shadow-sm"
          >
            <Download size={13} className="text-purple-300" /> Windows (.exe)
          </a>

          <div className="hidden xl:flex items-center gap-2">
            <select
              aria-label="Application theme"
              className="max-w-28 rounded-lg border border-white/10 bg-slate-900 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-400"
              value={theme}
              onChange={e=>setTheme(e.target.value)}
            >
              {APPEARANCE_THEMES.map(value=><option key={value} value={value}>{value[0].toUpperCase()+value.slice(1)}</option>)}
            </select>
          </div>

          <div className="flex items-center gap-1.5 rounded-xl border border-indigo-500/30 bg-slate-950/80 p-1 px-2 shadow-inner">
            <HeaderClock clockMode={clockMode} onToggleMode={()=>saveClockMode(clockMode==='digital'?'analog':'digital')}/>
            <button
              type="button"
              onClick={()=>saveClockMode(clockMode==='digital'?'analog':'digital')}
              className="rounded bg-white/10 px-1.5 py-1 text-xs text-white hover:bg-white/20"
              title="Switch clock mode (Digital / Analog)"
            >
              🕒
            </button>
          </div>

          <button
            onClick={()=>load()}
            className="rounded-lg border border-white/10 p-2 text-cyan-300 hover:bg-white/5"
            title="Refresh all data"
          >
            <RefreshCw size={16} className={busy?'animate-spin':''}/>
          </button>
        </div>
      </header>
      <main className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3 sm:p-5">
        {tab==='home'&&<HomeWorkspace user={user} business={data.homeBusiness} theme={theme} onThemeChange={setTheme} wallpaper={wallpaper} wallpaperStyles={WALLPAPER_STYLES} onWallpaperChange={setWallpaper} onCustomWallpaperUpload={uploadCustomWallpaper} canRollback={canAdminEmployees} onNavigate={setTab}/>}
        {tab==='dashboard'&&<>
          <div className="rounded-2xl border border-cyan-400/25 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-4 shadow-xl">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><p className="text-sm font-black tracking-wider text-white">⚡ OPERATIONS COMMAND // REAL-TIME WORKFORCE AUDIT</p><p className="mt-1 text-xs text-slate-400">{data.dashboard?.today||today()} · Workforce and task telemetry</p></div>
              <span className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-xs font-bold text-emerald-300">● REAL-TIME AUDIT METRICS ACTIVE</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            {[
              ['TOTAL EMPLOYEES',data.dashboard?.kpis?.total_employees??data.employees.length,'Active roster','employees'],
              ['PRESENT TODAY',data.dashboard?.kpis?.present_today??0,'Verified on-site','attendance'],
              ['ABSENT TODAY',data.dashboard?.kpis?.absent_today??0,'Attendance records','attendance'],
              ['OPEN TASKS',data.dashboard?.kpis?.open_tasks??0,'Active work items','tasks'],
              ["TODAY'S CHECK-INS",data.dashboard?.kpis?.checkins_today??0,'Clocked in','attendance']
            ].map(([label,value,subtitle,target])=><button type="button" key={label} onClick={()=>setTab(target)} className={card+' text-left transition hover:border-cyan-400/40'}>
              <p className="text-[11px] font-extrabold tracking-wide text-slate-400">{label}</p><p className="mt-2 text-3xl font-black tabular-nums text-cyan-300">{value}</p><p className="mt-1 text-[11px] font-semibold text-slate-500">{subtitle}</p>
            </button>)}
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Panel title="Quick Actions">
              <div className="flex flex-wrap gap-2">
                {[
                  ['employees','➕ Add Employee'],
                  ['tasks','✓ Assign Task'],
                  ['attendance','▦ Mark Attendance'],
                  ['customers','🏪 Store Directory'],
                  ['reports','▤ Print Center']
                ].map(([target,label])=><button type="button" key={target} onClick={()=>setTab(target)} className={btn}>{label}</button>)}
              </div>
            </Panel>
            <Panel title="Recent Employees" actions={<button type="button" onClick={()=>setTab('employees')} className="text-xs font-semibold text-cyan-300">View directory</button>}>
              <div className="overflow-x-auto"><table className="w-full min-w-[430px] text-left text-sm">
                <thead className="text-[11px] uppercase text-slate-500"><tr>{['#','Employee ID','Name','Role','Status'].map(label=><th key={label} className="border-b border-white/10 px-2 py-2">{label}</th>)}</tr></thead>
                <tbody>{(data.dashboard?.recent_employees||[]).map((employee,index)=><tr key={employee.id} className="border-b border-white/5 text-slate-300">
                  <td className="px-2 py-2">{index+1}</td><td className="px-2 py-2">{employee.employee_code||'—'}</td><td className="px-2 py-2 font-semibold text-white">{employee.name}</td><td className="px-2 py-2">{employee.designation||'—'}</td><td className="px-2 py-2 text-emerald-300">{employee.active?'Active':'Inactive'}</td>
                </tr>)}</tbody>
              </table>{!(data.dashboard?.recent_employees||[]).length&&<p className="py-5 text-center text-sm text-slate-500">No active employees found.</p>}</div>
            </Panel>
            <Panel title="Today's Tasks" actions={<button type="button" onClick={()=>setTab('tasks')} className="text-xs font-semibold text-cyan-300">Open Task Manager</button>}>
              <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-sm">
                <thead className="text-[11px] uppercase text-slate-500"><tr>{['Employee','Task','Status','Progress','Due'].map(label=><th key={label} className="border-b border-white/10 px-2 py-2">{label}</th>)}</tr></thead>
                <tbody>{(data.dashboard?.today_tasks||[]).map(task=>{const progress=Math.max(0,Math.min(100,Number(task.progress)||0));return <tr key={task.id} className="border-b border-white/5 text-slate-300">
                  <td className="px-2 py-3">{task.employee_name||'—'}</td><td className="max-w-[180px] whitespace-normal px-2 py-3 font-semibold text-white">{task.title||'—'}</td><td className="px-2 py-3">{task.status||'Not selected'}</td><td className="min-w-[110px] px-2 py-3"><div className="h-2 overflow-hidden rounded-full bg-slate-700"><div className="h-full rounded-full bg-cyan-400" style={{width:progress+'%'}}/></div><span className="mt-1 block text-[10px] tabular-nums text-slate-400">{progress}%</span></td><td className="px-2 py-3">{task.due_time||'—'}</td>
                </tr>})}</tbody>
              </table>{!(data.dashboard?.today_tasks||[]).length&&<p className="py-5 text-center text-sm text-slate-500">No tasks scheduled for today.</p>}</div>
            </Panel>
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Panel title="Today's Attendance" actions={<button type="button" onClick={()=>setTab('attendance')} className="text-xs font-semibold text-cyan-300">Open calendar</button>}>
              <div className="rounded-xl bg-slate-950/70 p-4">
                <div className="flex items-center justify-between gap-3"><span className="text-sm font-bold text-white">Attendance gauge</span><span className="text-2xl font-black text-emerald-300">{data.dashboard?.kpis?.attendance_rate??0}%</span></div>
                <div className="mt-3 h-3 overflow-hidden rounded-full bg-slate-700"><div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400" style={{width:Math.max(0,Math.min(100,Number(data.dashboard?.kpis?.attendance_rate)||0))+'%'}}/></div>
                <p className="mt-3 whitespace-pre-line text-xs leading-6 text-slate-400">{data.dashboard?.attendance_summary||'Attendance summary is not available yet.'}</p>
              </div>
              <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[340px] text-left text-sm">
                <thead className="text-[11px] uppercase text-slate-500"><tr>{['Employee','Status','Check-in'].map(label=><th key={label} className="border-b border-white/10 px-2 py-2">{label}</th>)}</tr></thead>
                <tbody>{(data.dashboard?.attendance_roster||[]).map(row=><tr key={row.employee_id} className="border-b border-white/5 text-slate-300">
                  <td className="px-2 py-2 font-semibold text-white">{row.name}</td><td className="px-2 py-2">{row.status}</td><td className="px-2 py-2 tabular-nums">{row.check_in||'—'}</td>
                </tr>)}</tbody>
              </table></div>
            </Panel>
            <Panel title="Employee Productivity" actions={<span className="text-xs text-slate-500">70% tasks · 30% attendance</span>}>
              <div className="space-y-4">
                {(data.dashboard?.productivity||[]).map(employee=>{const score=Math.max(0,Math.min(100,Number(employee.score)||0));return <div key={employee.employee_id}>
                  <div className="flex items-center justify-between gap-3"><span className="min-w-0 truncate text-sm font-semibold text-white">{employee.name}</span><span className="text-sm font-black tabular-nums text-cyan-300">{score}%</span></div>
                  <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-700"><div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" style={{width:score+'%'}}/></div>
                  <p className="mt-1 text-[10px] text-slate-500">{employee.present_count}/{employee.attendance_eligible_days} eligible attendance days · {employee.completed}/{employee.task_count} completed tasks · Since {employee.tracking_start}</p>
                </div>})}
                {!(data.dashboard?.productivity||[]).length&&<p className="py-5 text-center text-sm text-slate-500">Productivity data is not available yet.</p>}
              </div>
            </Panel>
            <Panel title="Productivity Summary">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Average score</p><p className="mt-1 text-2xl font-black text-cyan-300">{data.dashboard?.kpis?.avg_productivity??0}%</p></div>
                <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Completed today</p><p className="mt-1 text-2xl font-black text-emerald-300">{data.dashboard?.kpis?.completed_tasks??0}</p></div>
                <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">On leave</p><p className="mt-1 text-2xl font-black text-violet-300">{data.dashboard?.kpis?.leave_today??0}</p></div>
                <div className="rounded-xl bg-slate-950/70 p-3"><p className="text-xs text-slate-500">Not checked</p><p className="mt-1 text-2xl font-black text-amber-300">{data.dashboard?.kpis?.not_checked_today??0}</p></div>
              </div>
            </Panel>
          </div>
        </>}
        {tab==='employees'&&<>
          {canEditEmployees&&<Panel title="Add employee">
            <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={saveNewEmployee}>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Employee name *</span><input className={field} required value={employeeForm.name} onChange={e=>setEmployeeForm(p=>({...p,name:e.target.value}))}/></label>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Employee ID *</span><input className={field} required value={employeeForm.employee_code} onChange={e=>setEmployeeForm(p=>({...p,employee_code:e.target.value}))}/></label>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Section / Department</span><input className={field} list="employee-group-options" value={employeeForm.department} onChange={e=>setEmployeeForm(p=>({...p,department:e.target.value}))}/><datalist id="employee-group-options">{data.employeeGroups.map(g=><option key={g.name} value={g.name}/>)}</datalist></label>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Job title / Designation</span><input className={field} value={employeeForm.designation} onChange={e=>setEmployeeForm(p=>({...p,designation:e.target.value}))}/></label>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Phone</span><input className={field} value={employeeForm.phone} onChange={e=>setEmployeeForm(p=>({...p,phone:e.target.value}))}/></label>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Email</span><input className={field} type="email" value={employeeForm.email} onChange={e=>setEmployeeForm(p=>({...p,email:e.target.value}))}/></label>
              <label className="block space-y-1"><span className="text-xs font-semibold text-slate-400">Joining date</span><input className={field} type="date" value={employeeForm.joining_date} onChange={e=>setEmployeeForm(p=>({...p,joining_date:e.target.value}))}/></label>
              <label className="block space-y-1 sm:col-span-2"><span className="text-xs font-semibold text-slate-400">Notes</span><textarea className={field} rows="2" value={employeeForm.notes} onChange={e=>setEmployeeForm(p=>({...p,notes:e.target.value}))}/></label>
              <div className="sm:col-span-2 xl:col-span-3"><button className={btn} disabled={busy}><Plus size={16}/> Add employee</button></div>
            </form>
          </Panel>}
          <Panel title={'Employee Directory · '+employeeRows.length+' shown / '+data.employees.length+' total'} actions={<button onClick={()=>load()} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-cyan-200">Refresh</button>}>
            <div className="mb-4 grid gap-3 md:grid-cols-3">
              <input className={field} placeholder="Search name, ID, department, role, phone, email or notes" value={query} onChange={e=>setQuery(e.target.value)}/>
              <select className={field} value={employeeDepartment} onChange={e=>setEmployeeDepartment(e.target.value)}><option value="all">All departments / groups</option><option value="General">General / Unassigned</option>{data.employeeGroups.filter(g=>g.name.toLowerCase()!=='general').map(g=><option key={g.name} value={g.name}>{g.name} ({g.employee_count})</option>)}</select>
              <select className={field} value={employeeSort} onChange={e=>setEmployeeSort(e.target.value)}><option value="serial">Serial Number / ID</option><option value="department">Department / Group</option><option value="name">Name (A-Z)</option><option value="custom">Custom Order</option></select>
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {canAdminEmployees&&<button className={btn} onClick={()=>{const first=data.employeeGroups[0]?.name||'';setGroupSelected(first);setGroupRenameDraft(first);setGroupManagerOpen(true)}}>Manage Sections</button>}
              {canAdminEmployees&&<button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!selectedEmployee} onClick={()=>moveEmployee(-1)}>Move Up</button>}
              {canAdminEmployees&&<button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!selectedEmployee} onClick={()=>moveEmployee(1)}>Move Down</button>}
              {canAdminEmployees&&<><select className={field+' w-auto min-w-44'} value={moveToGroup} onChange={e=>setMoveToGroup(e.target.value)}><option value="">Move selected to section…</option><option value="General">General / Unassigned</option>{data.employeeGroups.map(g=><option key={g.name} value={g.name}>{g.name}</option>)}</select><button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!selectedEmployee||!moveToGroup} onClick={moveEmployeeToGroup}>Move to Section</button></>}
              {canEditEmployees&&<button className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={!selectedEmployee} onClick={()=>selectedEmployee&&setEditRecord({...selectedEmployee,editType:'employees'})}>Edit Selected</button>}
              {canEditEmployees&&<button className="rounded-lg border border-amber-400/20 px-3 py-2 text-sm text-amber-200 disabled:opacity-40" disabled={!selectedEmployee} onClick={updateEmployeeStatus}>{selectedEmployee?.active?'Deactivate':'Activate'}</button>}
              {canAdminEmployees&&<button className="rounded-lg border border-rose-400/20 px-3 py-2 text-sm text-rose-300 disabled:opacity-40" disabled={!selectedEmployee} onClick={deleteEmployeePermanently}>Delete Employee</button>}
              {selectedEmployee&&<span className="text-xs text-slate-500">Selected: {selectedEmployee.name}</span>}
            </div>
            <div className="overflow-x-auto"><table className="w-full min-w-[1040px] text-left text-sm">
              <thead className="text-xs uppercase text-slate-500"><tr>{['ID','Employee ID','Name','Department / Group','Job title','Phone','Email','Joining date','Status','Actions'].map(label=><th key={label} className="border-b border-white/10 px-3 py-3">{label}</th>)}</tr></thead>
              <tbody>{employeeRows.map(e=><tr key={e.id} onClick={()=>setEmployeeSelectedId(e.id)} onDoubleClick={()=>canEditEmployees&&setEditRecord({...e,editType:'employees'})} className={'cursor-pointer border-b border-white/5 text-slate-300 '+(Number(employeeSelectedId)===Number(e.id)?'bg-cyan-400/10':'hover:bg-white/[0.03]')}>
                <td className="px-3 py-3">{e.id}</td><td className="px-3 py-3">{e.employee_code||'—'}</td><td className="px-3 py-3 font-semibold text-white">{e.name}</td><td className="px-3 py-3">{e.department||'General'}</td><td className="px-3 py-3">{e.designation||'—'}</td><td className="px-3 py-3">{e.phone||'—'}</td><td className="px-3 py-3">{e.email||'—'}</td><td className="px-3 py-3">{e.joining_date||'—'}</td><td className="px-3 py-3"><span className={e.active?'text-emerald-300':'text-amber-300'}>{e.active?'Active':'Inactive'}</span></td>
                <td className="px-3 py-3"><button className="text-cyan-300 disabled:opacity-40" disabled={!canEditEmployees} onClick={event=>{event.stopPropagation();setEmployeeSelectedId(e.id);setEditRecord({...e,editType:'employees'})}}>Edit</button></td>
              </tr>)}</tbody></table>{!employeeRows.length&&<p className="py-6 text-center text-sm text-slate-500">No employees match the selected search and filters.</p>}</div>
          </Panel>
        </>}
        {tab==='tasks'&&<TaskManager tasks={data.tasks} employees={data.employees} user={user} apiFetch={apiFetch} onReload={()=>load()} notify={notify}/>}
        {tab==='tracker'&&<TaskManager tasks={data.tasks} employees={data.employees} user={user} apiFetch={apiFetch} onReload={()=>load()} notify={notify} mode="tracker"/>}
        {tab==='settings'&&canAdminEmployees&&<Panel title="Working week">
          <p className="mb-3 text-sm text-slate-400">Choose the working weekdays used by attendance and productivity totals. Sunday is always a working day and cannot be disabled.</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map((day,index)=><label key={day} className="flex items-center gap-2 rounded-lg border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-slate-200"><input type="checkbox" checked={workingWeekdays.includes(index)} disabled={index===6} onChange={event=>setWorkingWeekdays(previous=>{const next=new Set(previous);if(event.target.checked)next.add(index);else next.delete(index);next.add(6);return [...next].sort((a,b)=>a-b)})}/>{day}{index===6&&<span className="ml-auto text-xs text-cyan-300">Required</span>}</label>)}</div>
          <button type="button" className={btn+' mt-3'} disabled={workingWeekdaysBusy} onClick={saveWorkingWeekdays}>{workingWeekdaysBusy?'Saving…':'Save working days'}</button>
        </Panel>}
        {tab==='settings'&&canAdminEmployees&&<Panel title="User account management">
          <p className="mb-3 text-sm text-slate-400">Create active accounts for employees or staff, map accounts to employee records, assign roles and reset passwords. Passwords are stored using PBKDF2 hashing.</p>
          <form className="mb-4 grid gap-3 rounded-xl border border-white/10 bg-slate-950/40 p-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={createManagedAccount}>
            <label className="text-xs text-slate-400">Username<input className={field+' mt-1'} value={newAccount.username} onChange={e=>setNewAccount(p=>({...p,username:e.target.value}))} maxLength={64} required/></label>
            <label className="text-xs text-slate-400">Display name<input className={field+' mt-1'} value={newAccount.display_name} onChange={e=>setNewAccount(p=>({...p,display_name:e.target.value}))} maxLength={100} required/></label>
            <label className="text-xs text-slate-400">Role / access level<select className={field+' mt-1'} value={newAccount.role} onChange={e=>setNewAccount(p=>({...p,role:e.target.value}))}>{['Employee','Staff','HR','Admin','Developer'].map(role=><option key={role} value={role} disabled={role==='Developer'&&String(user?.role||'').toLowerCase()!=='developer'}>{role}</option>)}</select></label>
            <label className="text-xs text-slate-400">Map to Employee<select className={field+' mt-1'} value={newAccount.employee_id||''} onChange={e=>{const empId=e.target.value;const emp=data.employees.find(x=>String(x.id)===String(empId));setNewAccount(p=>({...p,employee_id:empId,display_name:p.display_name&&p.display_name!==p.username?p.display_name:(emp?emp.name:p.display_name)}));}}><option value="">None / Unmapped</option>{data.employees.map(emp=><option key={emp.id} value={emp.id}>{emp.name} ({emp.employee_code||'EMP'+emp.id})</option>)}</select></label>
            <label className="text-xs text-slate-400">Initial password<input className={field+' mt-1'} type="password" autoComplete="new-password" minLength={8} value={newAccount.password} onChange={e=>setNewAccount(p=>({...p,password:e.target.value}))} required/></label>
            <label className="text-xs text-slate-400">Recovery question<select className={field+' mt-1'} value={newAccount.security_question} onChange={e=>setNewAccount(p=>({...p,security_question:e.target.value}))}>{['What was the name of your first school?','What is the name of the city where you were born?','What was your childhood nickname?','What is the name of your first teacher?','What was the first concert or live event you attended?'].map(q=><option key={q}>{q}</option>)}</select></label>
            <label className="text-xs text-slate-400 sm:col-span-2 xl:col-span-3">Recovery answer<input className={field+' mt-1'} type="password" autoComplete="off" value={newAccount.security_answer} onChange={e=>setNewAccount(p=>({...p,security_answer:e.target.value}))} required/></label>
            <button className={btn+' sm:col-span-2 xl:col-span-3'}><Plus size={16}/> Create active account</button>
          </form>
          <div className="overflow-x-auto"><table className="w-full min-w-[1100px] text-sm"><thead><tr className="text-left text-xs text-slate-500"><th className="p-2">Username</th><th className="p-2">Display name</th><th className="p-2">Role / access</th><th className="p-2">Mapped Employee</th><th className="p-2">Status</th><th className="p-2">Created</th><th className="p-2">Actions</th></tr></thead><tbody>{authUsers.map(a=>{const protectedDeveloper=String(a.role||'').toLowerCase()==='developer'&&String(user?.role||'').toLowerCase()!=='developer';return <tr key={a.id} className="border-t border-white/5 align-top"><td className="p-2 font-mono text-xs">{a.username}</td><td className="p-2">{a.display_name}</td><td className="p-2"><select className={field+' min-w-28'} value={accountRoleDrafts[a.id]??a.role} disabled={protectedDeveloper} onChange={e=>changeAccountRole(a,e.target.value)}>{['Employee','Staff','HR','Admin','Developer'].map(role=><option key={role} value={role} disabled={role==='Developer'&&String(user?.role||'').toLowerCase()!=='developer'}>{role}</option>)}</select></td><td className="p-2"><div className="font-semibold text-cyan-200">{a.employee_name?`${a.employee_name} (${a.employee_code||'EMP'+a.employee_id})`:'—'}</div><select className="mt-1 rounded border border-white/10 bg-slate-950 px-2 py-1 text-xs text-slate-300" value={a.employee_id||''} onChange={async e=>{const nextId=e.target.value?Number(e.target.value):null;try{await apiFetch('/auth/users/'+a.id+'/mapping',{method:'PATCH',body:JSON.stringify({employee_id:nextId})});const found=data.employees.find(x=>Number(x.id)===nextId);setAuthUsers(rows=>rows.map(r=>r.id===a.id?{...r,employee_id:nextId,employee_name:found?found.name:null,employee_code:found?found.employee_code:null}:r));notify('Employee mapping updated for '+a.username);}catch(err){notify(err.message);}}}><option value="">Unmapped</option>{data.employees.map(emp=><option key={emp.id} value={emp.id}>{emp.name}</option>)}</select></td><td className="p-2">{a.active?'Active':'Pending / disabled'}</td><td className="p-2 text-xs text-slate-400">{String(a.created_at||'').slice(0,10)||'—'}</td><td className="p-2"><div className="flex flex-wrap gap-2"><button type="button" className="rounded-md border border-white/10 px-3 py-1 text-xs text-cyan-200 disabled:opacity-40" disabled={protectedDeveloper||(Number(a.id)===Number(user?.id)&&Boolean(a.active))} onClick={()=>toggleAccountActive(a)}>{a.active?'Deactivate':'Activate'}</button><button type="button" className="rounded-md border border-white/10 px-3 py-1 text-xs text-amber-200 disabled:opacity-40" disabled={protectedDeveloper} onClick={()=>{setAccountPasswordResetTarget(accountPasswordResetTarget===a.id?null:a.id);setAccountPasswordDraft({password:'',confirm:''})}}>Reset password</button></div>{accountPasswordResetTarget===a.id&&<div className="mt-2 grid min-w-56 gap-2 rounded-lg border border-white/10 bg-slate-950 p-2"><input className={field} type="password" autoComplete="new-password" placeholder="New password (8+ chars)" value={accountPasswordDraft.password} onChange={e=>setAccountPasswordDraft(p=>({...p,password:e.target.value}))}/><input className={field} type="password" autoComplete="new-password" placeholder="Confirm new password" value={accountPasswordDraft.confirm} onChange={e=>setAccountPasswordDraft(p=>({...p,confirm:e.target.value}))}/><div className="flex gap-2"><button type="button" className={btn+' px-3 py-2'} onClick={()=>saveManagedAccountPassword(a)}>Save password</button><button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300" onClick={()=>{setAccountPasswordResetTarget(null);setAccountPasswordDraft({password:'',confirm:''})}}>Cancel</button></div></div>}</td></tr>})}</tbody></table>{!authUsers.length&&<p className="py-5 text-center text-sm text-slate-500">No account records available.</p>}</div>
        </Panel>}
        {tab==='attendance'&&<><Panel title="Daily attendance"><div className="mb-3 flex flex-wrap items-end gap-3"><label className="text-xs text-slate-400">Work date<input className={field+' mt-1'} type="date" value={selectedAttendanceDate} disabled={attendanceBusy||Boolean(attendanceRemarksTarget)} onChange={async e=>{
            const selectedDate=e.target.value;
            if(!selectedDate||selectedDate===selectedAttendanceDate||attendanceBusy)return;
            setAttendanceBusy(true);
            try{
              const pendingCount=await flushAttendanceDrafts(selectedAttendanceDate);
              const [attendance,summary]=await Promise.all([
                apiFetch('/attendance?work_date='+encodeURIComponent(selectedDate)),
                apiFetch('/attendance/summary?work_date='+encodeURIComponent(selectedDate))
              ]);
              setData(previous=>({...previous,attendance,attendanceSummary:summary}));
              setAttendanceDrafts({});
              setSelectedAttendanceIds([]);
              if(pendingCount)notify('Saved '+pendingCount+' pending attendance changes before changing date.');
            }catch(error){notify('Could not change attendance date: '+error.message);}
            finally{setAttendanceBusy(false);}
          }}/></label>{isEmployee ? (
            <div className="rounded-lg border border-cyan-400/30 bg-cyan-950/40 px-3 py-1.5 text-xs text-cyan-200">
              <span className="block text-[10px] uppercase text-slate-400">Employee Record</span>
              <span className="font-bold">{user.employee_name || user.display_name || user.username}</span>
            </div>
          ) : (
            <label className="text-xs text-slate-400">Filter employee<select className={field+' mt-1 min-w-52'} value={attendanceFilter} onChange={e=>{setAttendanceFilter(e.target.value);setSelectedAttendanceIds([])}}><option value="all">All employees</option>{data.employees.map(e=><option key={e.id} value={e.id}>{e.name}</option>)}</select></label>
          )}<button type="button" className="rounded-lg border border-white/10 px-3 py-2.5 text-sm text-cyan-200" onClick={selectVisibleAttendance}>{visibleAttendanceRows.length>0&&visibleAttendanceRows.every(r=>selectedAttendanceIds.includes(Number(r.employee_id)))?'Clear visible selection':'Select all visible'}</button><span className="text-xs text-slate-500">{selectedAttendanceIds.length} selected</span>{Object.keys(attendanceDrafts).length>0&&<button type="button" className="rounded-lg border border-cyan-400/30 px-3 py-2.5 text-sm text-cyan-200 disabled:opacity-40" disabled={attendanceBusy||attendanceIsHoliday} onClick={saveAllAttendanceDrafts}>Save all {Object.keys(attendanceDrafts).length} pending</button>}</div><div className="mb-3 flex flex-wrap items-center gap-2">
<span className="mr-1 text-xs font-semibold text-slate-400">Desktop attendance actions:</span>
<button type="button" className="rounded-lg border border-emerald-400/30 px-3 py-2 text-sm text-emerald-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceStatusAction('Present')}>● Present</button>
<button type="button" className="rounded-lg border border-rose-400/30 px-3 py-2 text-sm text-rose-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceStatusAction('Absent')}>● Absent</button>
<button type="button" className="rounded-lg border border-amber-400/30 px-3 py-2 text-sm text-amber-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceStatusAction('Leave')}>● Leave</button>
<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceTimeAction('check-in')}>Check In</button>
<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceTimeAction('check-out')}>Check Out</button>
<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceTimeAction('edit-times')}>Edit Times</button>
<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-sm text-cyan-200 disabled:opacity-40" disabled={attendanceIsHoliday||attendanceBusy} onClick={()=>runAttendanceTimeAction('remarks')}>Remarks</button>
<span className="text-xs text-slate-500">Choose one employee by checkbox or filter for these actions.</span>
</div>{attendanceRemarksTarget&&<div className="fixed inset-0 z-[80] grid place-items-center bg-black/75 p-4" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget){setAttendanceRemarksTarget(null);setAttendanceRemarksDraft('');}}}><section className="w-full max-w-lg rounded-2xl border border-cyan-400/30 bg-slate-900 p-5 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="attendance-remarks-title"><h3 id="attendance-remarks-title" className="text-lg font-bold text-white">Attendance Remarks</h3><p className="mt-1 text-sm text-slate-400">Select a preset or type remarks for {selectedAttendanceDate} · {attendanceRemarksTarget.name}</p><label className="mt-4 block space-y-1 text-xs font-semibold text-slate-400">Remarks<input autoFocus list="attendance-remark-presets" className={field} value={attendanceRemarksDraft} placeholder="Select preset or type remarks" onChange={event=>setAttendanceRemarksDraft(event.target.value)}/><datalist id="attendance-remark-presets">{(data.attendance.remarks_options||[]).map((option,index)=><option key={index} value={option}/>)}</datalist></label><div className="mt-5 flex justify-end gap-2"><button type="button" className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300" onClick={()=>{setAttendanceRemarksTarget(null);setAttendanceRemarksDraft('');}}>Cancel</button><button type="button" className={btn} disabled={attendanceBusy} onClick={async()=>{const target=attendanceRemarksTarget;if(!target)return;const saved=await saveAttendanceToolbarUpdate(target,{attendance_note:attendanceRemarksDraft.trim()},'Attendance remarks');if(saved){setAttendanceRemarksTarget(null);setAttendanceRemarksDraft('');}}}>Save remarks</button></div></section></div>}{attendanceIsHoliday&&<p className="mb-3 rounded-lg border border-amber-400/30 bg-amber-950/40 p-3 text-sm text-amber-200">Holiday: {selectedAttendanceHoliday.holiday_name||'Declared holiday'} — attendance editing is disabled for this date.</p>}<div className="overflow-x-auto"><table className="w-full min-w-[1120px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="p-2">Select</th><th className="p-2">Employee</th><th className="p-2">Date</th><th className="p-2">Attendance status</th><th className="p-2">Check-in</th><th className="p-2">Check-out</th><th className="p-2">Net hours</th><th className="p-2">Remarks</th><th className="p-2">Action</th></tr></thead><tbody>{visibleAttendanceRows.map(r=>{const draft=attendanceDraftFor(r);return <tr key={r.employee_id} className="border-t border-white/5 text-slate-300"><td className="p-2"><input aria-label={'Select '+r.name} type="checkbox" checked={selectedAttendanceIds.includes(Number(r.employee_id))} onChange={()=>toggleAttendanceSelection(r.employee_id)} disabled={attendanceIsHoliday}/></td><td className="p-2 font-semibold text-white">{r.name}<div className="text-xs text-slate-500">{r.department||'—'}</div></td><td className="p-2 text-xs text-slate-400">{selectedAttendanceDate}</td><td className="p-2"><select className={field+' min-w-32'} value={attendanceIsHoliday?'Holiday':(['Unmarked','Present','Absent','Leave'].includes(draft.attendance_status)?draft.attendance_status:'Unmarked')} disabled={attendanceIsHoliday} onChange={e=>{const status=e.target.value;setAttendanceDrafts(prev=>({...prev,[r.employee_id]:{...(prev[r.employee_id]||r),attendance_status:status,...(['Absent','Leave','Unmarked'].includes(status)?{check_in:'',check_out:''}:{})}}))}}>{(attendanceIsHoliday?['Holiday']:['Unmarked','Present','Absent','Leave']).map(s=><option key={s}>{s}</option>)}</select></td><td className="p-2"><input className={field+' w-28'} type="time" value={draft.check_in||''} disabled={attendanceIsHoliday||['Absent','Leave','Unmarked'].includes(draft.attendance_status)} onChange={e=>updateAttendanceDraft(r,'check_in',e.target.value)}/></td><td className="p-2"><input className={field+' w-28'} type="time" value={draft.check_out||''} disabled={attendanceIsHoliday||['Absent','Leave','Unmarked'].includes(draft.attendance_status)} onChange={e=>updateAttendanceDraft(r,'check_out',e.target.value)}/></td><td className="p-2 whitespace-nowrap text-cyan-200">{attendanceNetHours(draft.check_in,draft.check_out,draft.break_minutes)}</td><td className="p-2"><input className={field+' min-w-48'} value={draft.attendance_note||''} disabled={attendanceIsHoliday} placeholder="Attendance remarks" onChange={e=>updateAttendanceDraft(r,'attendance_note',e.target.value)}/></td><td className="p-2"><button className={btn+' px-3 py-2'} disabled={attendanceIsHoliday||attendanceBusy||!attendanceDrafts[r.employee_id]} onClick={()=>saveAttendanceDraft(r)}>{attendanceBusy?'Saving…':'Save'}</button></td></tr>})}</tbody></table>{!visibleAttendanceRows.length&&<p className="py-6 text-center text-sm text-slate-500">No employees found.</p>}</div></Panel>{!isEmployee&&<Panel title="Bulk edit selected employees"><p className="mb-3 text-sm text-slate-400">Only checked fields are changed. Unchecked values remain untouched.</p><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_status} onChange={e=>setBulkAttendance(p=>({...p,apply_status:e.target.checked}))}/> Apply status</span><select className={field} value={bulkAttendance.status} onChange={e=>setBulkAttendance(p=>({...p,status:e.target.value}))}>{['Present','Absent','Leave','Unmarked'].map(s=><option key={s}>{s}</option>)}</select></label><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_check_in} onChange={e=>setBulkAttendance(p=>({...p,apply_check_in:e.target.checked}))}/> Apply check-in</span><input className={field} type="time" value={bulkAttendance.check_in} onChange={e=>setBulkAttendance(p=>({...p,check_in:e.target.value}))}/></label><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_check_out} onChange={e=>setBulkAttendance(p=>({...p,apply_check_out:e.target.checked}))}/> Apply check-out</span><input className={field} type="time" value={bulkAttendance.check_out} onChange={e=>setBulkAttendance(p=>({...p,check_out:e.target.value}))}/></label><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_remarks} onChange={e=>setBulkAttendance(p=>({...p,apply_remarks:e.target.checked}))}/> Apply remarks</span><input className={field} value={bulkAttendance.remarks} onChange={e=>setBulkAttendance(p=>({...p,remarks:e.target.value}))} placeholder="Remarks (blank clears)"/></label></div><div className="mt-4 flex flex-wrap items-center gap-3"><button className={btn} disabled={!selectedAttendanceIds.length||attendanceIsHoliday||!Object.entries(bulkAttendance).some(([k,v])=>k.startsWith('apply_')&&v)} onClick={applyAttendanceBulk}>Apply to {selectedAttendanceIds.length} selected</button><button className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300" onClick={()=>setBulkAttendance({apply_status:false,status:'Present',apply_check_in:false,check_in:'',apply_check_out:false,check_out:'',apply_remarks:false,remarks:''})}>Reset bulk fields</button></div></Panel>}<Panel title="Attendance totals & period summary"><p className="mb-3 text-xs text-slate-500">Totals exclude declared holidays and non-working weekdays. Work days are counted through the selected date.</p><Rows items={data.attendanceSummary?.rows||[]} keys={['employee_name','start_date','work_days','present','absent','leave','holidays','total_present']}/></Panel><Panel title="Company holidays">{canAdminEmployees?<form className="grid gap-3 sm:grid-cols-3" onSubmit={async e=>{e.preventDefault();try{await post('/holidays',holidayForm);setHolidayForm({holiday_date:today(),holiday_name:''})}catch{}}}><label className="text-xs text-slate-400">Date<input className={field+' mt-1'} type="date" value={holidayForm.holiday_date} onChange={e=>setHolidayForm(p=>({...p,holiday_date:e.target.value}))} required/></label><label className="text-xs text-slate-400">Holiday name<input className={field+' mt-1'} value={holidayForm.holiday_name} onChange={e=>setHolidayForm(p=>({...p,holiday_name:e.target.value}))} required/></label><button className={btn+' self-end'}><Plus size={16}/> Declare holiday</button></form>:<p className="mb-3 text-xs text-slate-500">Holiday declarations are managed by Admin or Developer accounts.</p>}<Rows items={data.holidays||[]} keys={['holiday_date','holiday_name','created_at']} onDelete={canAdminEmployees ? (h=>del('/holidays/'+h.holiday_date)) : undefined}/></Panel></>}{tab==='business'&&<BusinessTracking apiFetch={apiFetch} employees={data.employees} notify={notify}/>}
        {tab==='customers'&&<><Panel title="Store Directory · Workbook import, regional coverage & exports"><div className="grid gap-4 xl:grid-cols-2"><div className="rounded-xl border border-white/10 bg-slate-950/50 p-3"><h3 className="mb-2 text-sm font-bold text-white">Merge Store Directory workbook</h3><p className="mb-3 text-xs text-slate-400">Admin / Developer only · .xlsx up to 50 MB. Existing customer IDs, notes, follow-ups and records are merged, not deleted or replaced.</p><input className={field+' mb-3'} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={!canAdminEmployees||storeImportBusy} onChange={e=>setStoreWorkbook(e.target.files?.[0]||null)}/><button type="button" className={btn} disabled={!canAdminEmployees||!storeWorkbook||storeImportBusy} onClick={importStoreWorkbook}>{storeImportBusy?'Importing and merging…':'Import and merge workbook'}</button></div><div className="rounded-xl border border-white/10 bg-slate-950/50 p-3"><h3 className="mb-2 text-sm font-bold text-white">Import regional benchmark workbook</h3><p className="mb-3 text-xs text-slate-400">Admin / Developer only · Updates benchmark counts only. It does not alter Store Directory records.</p><input className={field+' mb-3'} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={!canAdminEmployees||dashboardImportBusy} onChange={e=>setDashboardWorkbook(e.target.files?.[0]||null)}/><button type="button" className={btn} disabled={!canAdminEmployees||!dashboardWorkbook||dashboardImportBusy} onClick={importDashboardWorkbook}>{dashboardImportBusy?'Importing benchmark…':'Import regional benchmark'}</button></div></div><div className="mt-4 flex flex-wrap items-center gap-2"><span className="mr-2 text-xs font-semibold text-slate-400">Export filtered Store Directory:</span>{['csv','xlsx','pdf','docx'].map(format=><button type="button" key={format} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={()=>downloadStoreExport(format)}>{format.toUpperCase()}</button>)}<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={openStorePrintPreview}>Print Preview</button></div><div className="mt-4 flex flex-wrap items-center gap-2"><span className="mr-2 text-xs font-semibold text-slate-400">Regional dashboard export:</span>{['csv','xlsx','pdf'].map(format=><button type="button" key={format} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={()=>downloadRegionalExport(format)}>{format.toUpperCase()}</button>)}<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={openRegionalPrintPreview}>Print Preview</button></div><div className="mt-4"><div className="mb-2 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold text-white">Regional coverage</h3><span className="text-xs text-slate-400">{regionalRows.length} territories · {regionalSummary.totals?.customer_records||0} customer records</span></div><div className="mb-3 flex flex-wrap items-center gap-2"><select className={field+' w-auto min-w-56'} value={regionalTerritoryFilter} onChange={e=>setRegionalTerritoryFilter(e.target.value)}><option value="all">All 36 regions</option><option value="State">28 States</option><option value="Union Territory">6 Union Territories</option><option value="Island Territory">2 Island Territories</option></select><span className="text-xs text-slate-500">Export and print actions use this territory filter.</span></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="text-slate-500"><tr>{['State / UT','Type','Web leads','Workbook leads','Stores','Gyms','Dashboard stores','Variance'].map(label=><th key={label} className="border-b border-white/10 px-2 py-2">{label}</th>)}</tr></thead><tbody>{regionalRows.map(row=><tr key={row.state} className="border-b border-white/5 text-slate-300"><td className="px-2 py-2 font-semibold text-white">{row.state}</td><td className="px-2 py-2">{row.territory_type}</td><td className="px-2 py-2">{row.web_leads}</td><td className="px-2 py-2">{row.workbook_leads}</td><td className="px-2 py-2">{row.stores}</td><td className="px-2 py-2">{row.gyms}</td><td className="px-2 py-2">{row.dashboard_stores??'—'}</td><td className="px-2 py-2">{row.variance==null?'—':(row.variance>0?'+':'')+row.variance}</td></tr>)}</tbody></table>{!(regionalSummary.rows||[]).length&&<p className="py-4 text-center text-xs text-slate-500">Regional coverage will appear when Store Directory records or a dashboard benchmark are available.</p>}</div></div></Panel><Panel title="Store Directory · Web scraping"><form className="grid gap-3 sm:grid-cols-4" onSubmit={async e=>{e.preventDefault();if(scrapeBusy)return;setScrapeBusy(true);setScrapeStatus('Starting evidence-based public merchant search…');try{const started=await apiFetch('/customers/scrape',{method:'POST',body:JSON.stringify({state:scrapeState,category:scrapeCategory,query:scrapeQuery,max_results:30,deep_scrape:true})});let status;for(let i=0;i<300;i++){await new Promise(r=>setTimeout(r,1200));status=await apiFetch('/customers/scrape/'+started.job_id);setScrapeStatus(status.status==='running'?'Searching public merchant pages and checking address evidence…':status.status==='completed'?'Completed. Found '+status.found+' evidence-backed leads.':'Scraping failed: '+(status.error||'Unknown error'));if(status.status!=='running')break;}if(status?.status==='completed'){await load();notify('Store Directory updated: '+status.found+' leads found');}else if(status?.status==='running')setScrapeStatus('Search is still running. Refresh the directory shortly.');}catch(err){setScrapeStatus(err.message);notify(err.message)}finally{setScrapeBusy(false)}}}><label className="text-xs text-slate-400">Scraping region<select className={field+' mt-1'} value={scrapeState} onChange={e=>setScrapeState(e.target.value)}><option value="">All India</option><optgroup label="28 States"><option>Andhra Pradesh</option><option>Arunachal Pradesh</option><option>Assam</option><option>Bihar</option><option>Chhattisgarh</option><option>Goa</option><option>Gujarat</option><option>Haryana</option><option>Himachal Pradesh</option><option>Jharkhand</option><option>Karnataka</option><option>Kerala</option><option>Madhya Pradesh</option><option>Maharashtra</option><option>Manipur</option><option>Meghalaya</option><option>Mizoram</option><option>Nagaland</option><option>Odisha</option><option>Punjab</option><option>Rajasthan</option><option>Sikkim</option><option>Tamil Nadu</option><option>Telangana</option><option>Tripura</option><option>Uttar Pradesh</option><option>Uttarakhand</option><option>West Bengal</option></optgroup><optgroup label="6 Union Territories"><option>Chandigarh</option><option>Dadra and Nagar Haveli and Daman and Diu</option><option>Delhi</option><option>Jammu and Kashmir</option><option>Ladakh</option><option>Puducherry</option></optgroup><optgroup label="2 Island Territories"><option>Andaman and Nicobar Islands</option><option>Lakshadweep</option></optgroup></select></label><label className="text-xs text-slate-400">Business type<select className={field+' mt-1'} value={scrapeCategory} onChange={e=>changeScrapeCategory(e.target.value)}><option>Pure Product Selling Stores</option><option>Gym</option><option>Gyms which sell products also</option><option>All Categories</option></select></label><label className="text-xs text-slate-400 sm:col-span-2">Search terms<input className={field+' mt-1'} value={scrapeQuery} onChange={e=>setScrapeQuery(e.target.value)}/></label><button className={btn+' sm:col-span-4'} disabled={scrapeBusy}><Globe size={16}/>{scrapeBusy?'Searching public websites…':'Start deep web scraping'}</button></form>{scrapeStatus&&<p className="mt-3 rounded-lg bg-slate-950 p-3 text-sm text-cyan-200">{scrapeStatus}</p>}<p className="mt-2 text-xs text-slate-500">Only public merchant pages are inspected. Leads are deduplicated and marked unverified until direct confirmation; no synthetic contact details are generated.</p></Panel><Panel title="Add store / prospect"><form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={async e=>{e.preventDefault();const result=await post('/customers/prospects',form);if(result?.success)setForm(p=>({...p,business_name:'',business_category:'',kind:'Store',area:'',city:'',state:'',contact_person:'',phone:'',email:'',address:'',website:'',maps:'',followup_date:'',call_time:'',connection:'',verified:'No',response:'',notes:''}));}}><FormInput label="Business / store name" name="business_name" form={form} onChange={set} required/><FormInput label="Business category" name="business_category" form={form} onChange={set}/><FormInput label="Record type" name="kind" form={form} onChange={set} placeholder="Store / Gym / Hybrid"/><FormInput label="Area / locality" name="area" form={form} onChange={set}/><FormInput label="City" name="city" form={form} onChange={set} required/><FormInput label="State / UT" name="state" form={form} onChange={set} required/><FormInput label="Contact person" name="contact_person" form={form} onChange={set}/><FormInput label="Phone" name="phone" form={form} onChange={set}/><FormInput label="Email" name="email" form={form} onChange={set} type="email"/><FormInput label="Full postal address" name="address" form={form} onChange={set}/><FormInput label="Official website" name="website" form={form} onChange={set} type="url"/><FormInput label="Google Maps URL (optional)" name="maps" form={form} onChange={set} type="url"/><FormInput label="Follow-up date" name="followup_date" form={form} onChange={set} type="date"/><FormInput label="Call time" name="call_time" form={form} onChange={set} type="time"/><FormInput label="Connection / outcome" name="connection" form={form} onChange={set}/><FormInput label="Verification" name="verified" form={form} onChange={set} placeholder="Yes / No"/><FormInput label="Response" name="response" form={form} onChange={set}/><FormInput label="Notes" name="notes" form={form} onChange={set}/><button className={btn+' sm:col-span-2 xl:col-span-3'}><Plus size={16}/> Add prospect</button></form><p className="mt-2 text-xs text-slate-500">If a direct Maps URL is not supplied, the directory generates a Google Maps search link from the business name and postal address. City and state identify the store branch for duplicate checking.</p></Panel><Panel title={`Store directory · ${data.prospects.length} records`}><div className="mb-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-6"><input className={field} placeholder="Search business, address, contact, phone, email or website" value={query} onChange={e=>setQuery(e.target.value)}/><select className={field} value={prospectKindFilter} onChange={e=>setProspectKindFilter(e.target.value)}><option value="all">All record types</option>{Array.from(new Set(['Pure Product Selling Stores','Gym','Gyms which sell products also',...(data.prospects||[]).map(p=>String(p.kind||'Store').trim()).filter(Boolean)])).sort().map(k=><option key={k} value={k.toLowerCase()}>{k}</option>)}</select><select className={field} value={prospectStateFilter} onChange={e=>setProspectStateFilter(e.target.value)}><option value="all">All states / UTs</option>{Array.from(new Set((data.prospects||[]).flatMap(p=>String(p.state||'').split(',').map(value=>value.trim()).filter(Boolean)))).sort().map(s=><option key={s} value={s}>{s}</option>)}</select><select className={field} value={prospectContactFilter} onChange={e=>setProspectContactFilter(e.target.value)}><option value="all">All contacts</option><option value="has">Has phone / email</option><option value="missing">Missing contact</option></select><select className={field} value={prospectWebsiteFilter} onChange={e=>setProspectWebsiteFilter(e.target.value)}><option value="all">All website status</option><option value="has">Has website</option><option value="missing">Missing website</option></select><select className={field} value={prospectVerificationFilter} onChange={e=>setProspectVerificationFilter(e.target.value)}><option value="all">All verification states</option><option value="verified">Verified</option><option value="pending">Unverified</option></select></div><div className="mb-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-6"><select className={field} value={prospectExcludeFilter} onChange={e=>setProspectExcludeFilter(e.target.value)}><option value="none">Exclude: none</option><option value="gym_wellness_herbal_healthkart">Exclude gyms / wellness / herbal / HealthKart</option><option value="missing_contact">Exclude missing phone / email</option><option value="missing_website">Exclude missing website</option><option value="unverified">Exclude unverified leads</option></select><select className={field} value={prospectExcludeKind} onChange={e=>setProspectExcludeKind(e.target.value)}><option value="all">Exclude category: none</option>{Array.from(new Set(['Pure Product Selling Stores','Gym','Gyms which sell products also',...(data.prospects||[]).map(p=>String(p.kind||'Store').trim()).filter(Boolean)])).sort().map(k=><option key={k} value={k}>{'Exclude: '+k}</option>)}</select><select className={field} value={prospectExcludeState} onChange={e=>setProspectExcludeState(e.target.value)}><option value="all">Exclude state: none</option>{Array.from(new Set((data.prospects||[]).flatMap(p=>String(p.state||'').split(',').map(value=>value.trim()).filter(Boolean)))).sort().map(s=><option key={s} value={s}>{'Exclude: '+s}</option>)}</select><input className={field} placeholder="Exclude business name…" value={prospectExcludeName} onChange={e=>setProspectExcludeName(e.target.value)}/><input className={field} placeholder="Exclude city / district…" value={prospectExcludeDistrict} onChange={e=>setProspectExcludeDistrict(e.target.value)}/><input className={field} placeholder="Exclude keywords (comma-separated)…" value={prospectExcludeKeywords} onChange={e=>setProspectExcludeKeywords(e.target.value)}/><button type="button" className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-100 hover:bg-red-500/20" onClick={clearStoreExclusions}>Clear exclusions</button></div>{busy&&data.prospects.length===0&&<p className="mb-3 text-sm text-cyan-200">Loading the complete Store Directory…</p>}<Rows items={visibleProspectRows} keys={['business_name','business_category','kind','area','city','state','address','phone','email','website','maps','followup_date','call_time','connection','verified','response','source_status']} onEdit={canAdminEmployees?(p=>setEditRecord({...p,editType:'prospects'})):undefined} onDelete={canAdminEmployees?(p=>del('/customers/prospects/'+p.id)):undefined}/><div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400"><span>Showing {prospectRows.length?((prospectPage-1)*prospectPageSize+1):0}–{Math.min(prospectPage*prospectPageSize,prospectRows.length)} of {prospectRows.length} stores · Page {prospectPage} of {prospectPageCount}</span><div className="flex gap-2"><button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 disabled:opacity-40" disabled={prospectPage<=1} onClick={()=>setProspectPage(page=>Math.max(1,page-1))}>Previous</button><button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 disabled:opacity-40" disabled={prospectPage>=prospectPageCount} onClick={()=>setProspectPage(page=>Math.min(prospectPageCount,page+1))}>Next</button></div></div></Panel><Panel title="Memberships"><form className="grid gap-3 sm:grid-cols-3" onSubmit={e=>{e.preventDefault();post('/business/members',{full_name:form.full_name,plan_name:form.plan_name,status:'Active'})}}><FormInput label="Member name" name="full_name" form={form} onChange={set}/><FormInput label="Plan" name="plan_name" form={form} onChange={set}/><button className={btn+' self-end'}><Plus size={16}/> Add member</button></form><Rows items={data.members} keys={['full_name','status','plan_name','phone','start_date','end_date']}/></Panel></>}
        {tab==='reports'&&<PrintCenter employees={data.employees} archive={data.archive} apiFetch={apiFetch} notify={notify} onOpenArchive={()=>setTab('archive')}/>}
        {tab==='archive'&&<ArchiveManager items={data.archive} employees={data.employees} apiFetch={apiFetch} notify={notify} refresh={load} isAdmin={canAdminEmployees} token={token}/>}
        {tab==='chat'&&<Panel title="Live Chat"><LiveChat messages={data.messages} user={user} onSendGeneral={async content=>{await post('/chat/messages',{channel:'general',content,sender_name:user.display_name||user.username})}}/></Panel>}
        {tab==='settings'&&canAdminEmployees&&<Panel title="Google Sheets master sync">
          <p className="mb-3 text-sm text-slate-400">Pull the current desktop master workbook and merge it into this web database. Matching records are updated from the workbook; local-only records are not deleted. This is a pull operation, not an upload to Google Sheets.</p>
          {isDeveloperSyncUser&&<label className="mb-3 block max-w-md text-xs text-slate-400">Developer password (required for lowercase developer account)
            <input className={field+' mt-1'} type="password" autoComplete="current-password" value={googleSheetsPassword} onChange={e=>setGoogleSheetsPassword(e.target.value)} placeholder="Enter developer password"/>
          </label>}
          <button type="button" className={btn} disabled={googleSheetsBusy||(isDeveloperSyncUser&&!googleSheetsPassword.trim())} onClick={syncGoogleSheets}>{googleSheetsBusy?'Syncing master workbook…':'Sync Google Sheets'}</button>
          {googleSheetsStatus&&<p role="status" className="mt-3 rounded-lg bg-slate-950 p-3 text-sm text-cyan-200">{googleSheetsStatus}</p>}
          <p className="mt-2 text-xs text-slate-500">Customer Admin sync does not require a developer password. Developer sync authorization is checked for each request and is never stored.</p>
        </Panel>}
        {tab==='settings'&&<Panel title="Appearance & wallpaper">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block space-y-2 text-xs font-semibold text-slate-400">Theme
              <select className={field} value={theme} onChange={e=>setTheme(e.target.value)}>{APPEARANCE_THEMES.map(value=><option key={value} value={value}>{value[0].toUpperCase()+value.slice(1)}</option>)}</select>
            </label>
            <label className="block space-y-2 text-xs font-semibold text-slate-400">Live wallpaper
              <select className={field} value={wallpaper} onChange={e=>setWallpaper(e.target.value)}>{WALLPAPER_STYLES.map(value=><option key={value} value={value}>{value}</option>)}</select>
            </label>
            <label className="block space-y-2 text-xs font-semibold text-slate-400">Clock display mode
              <select aria-label="Clock display mode" className={field} value={clockMode} onChange={e=>saveClockMode(e.target.value)}>
                <option value="digital">Digital</option><option value="analog">Analog</option>
              </select>
            </label>
            <label className="block space-y-2 text-xs font-semibold text-slate-400">Custom wallpaper · PNG, JPG, WEBP or BMP · 15 MB max
              <input className={field} type="file" accept=".png,.jpg,.jpeg,.webp,.bmp,image/png,image/jpeg,image/webp,image/bmp" disabled={appearanceBusy} onChange={uploadCustomWallpaper}/>
              <span className="block font-normal text-slate-500">{customWallpaperName?'Saved in this browser: '+customWallpaperName:'No custom image selected.'}</span>
            </label>
            <div className="flex flex-wrap items-end gap-2">
              <button type="button" className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-cyan-200 disabled:opacity-50" disabled={appearanceBusy} onClick={resetCustomWallpaper}>{appearanceBusy?'Saving…':'Reset wallpaper'}</button>
              <span className="text-xs text-slate-500">Theme and wallpaper remain local to this browser. Clock display mode is stored in this browser, matching the Windows desktop's per-installation preference.</span>
            </div>
          </div>
        </Panel>}
        {tab==='settings'&&<><Panel title="Employee data actions"><div className="flex flex-wrap gap-2"><button type="button" className={btn} onClick={downloadEmployeesCsv}>Export employees CSV</button><button type="button" className={btn} onClick={exposeAllProofLinks}>Expose all proof links</button></div><p className="mt-2 text-xs text-slate-500">CSV includes active and inactive employee records. Global exposure enables full proof URLs for every task and the default reports.</p></Panel><Panel title="Account"><p className="text-sm">Signed in as <b>{user.display_name||user.username}</b> · {user.role}</p><button className="mt-3 rounded-lg border border-white/10 px-4 py-2 text-sm text-rose-300" onClick={logout}>Sign out</button></Panel><Panel title="Database and encrypted sync"><div className="mb-3 grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-slate-950 p-3"><p className="text-xs text-slate-500">Database</p><p className="mt-1 text-sm font-semibold">{data.db?.database_connected?'Connected':'Unavailable'}</p><p className="text-xs text-slate-500">{data.db?.database_name||'Waiting for status'}</p></div><div className="rounded-lg bg-slate-950 p-3"><p className="text-xs text-slate-500">Database size</p><p className="mt-1 text-sm font-semibold">{data.db?.database_size_bytes!=null?(data.db.database_size_bytes/1024/1024).toFixed(2)+' MB':'—'}</p><p className="text-xs text-slate-500">Integrity: {data.db?.database_integrity||'Unknown'}</p></div><div className="rounded-lg bg-slate-950 p-3"><p className="text-xs text-slate-500">Encrypted sync</p><p className="mt-1 text-sm font-semibold">{data.db?.sync?.status||'Status unavailable'}</p><p className="text-xs text-slate-500">{data.db?.sync?.configured?'Configured':'Not configured'}</p></div></div><pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(data.db?.counts||{},null,2)}</pre><div className="mt-3 flex flex-wrap gap-2"><button className={btn} onClick={downloadDatabaseBackup}><Download size={16}/> Download database backup</button><button className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm text-cyan-200 disabled:opacity-50" disabled={Boolean(data.db?.sync?.busy)} onClick={async()=>{try{const r=await apiFetch('/system/sync-now',{method:'POST'});notify(r.success?'Encrypted sync completed':(r.error||r.status||'Sync did not complete'));await load()}catch(e){notify(e.message)}}}><RefreshCw size={16}/> Sync Now</button></div>{canAdminEmployees&&<div className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/5 p-3"><label className="block text-xs text-slate-300">Restore database backup (Admin / Developer)<input className={field+' mt-2'} type="file" accept=".db,.sqlite,.sqlite3" onChange={e=>setRestoreFile(e.target.files?.[0]||null)}/></label><button className="mt-3 inline-flex items-center gap-2 rounded-lg border border-rose-400/30 px-4 py-2.5 text-sm text-rose-200 disabled:opacity-40" disabled={!restoreFile||restoreBusy} onClick={restoreDatabaseBackup}><Upload size={16}/>{restoreBusy?'Validating and restoring…':'Restore selected backup'}</button><p className="mt-2 text-xs text-slate-500">The server validates the SQLite file and creates a safety backup before replacement. Account names and password hashes in the restored database are preserved; browser sessions are cleared.</p></div>}</Panel></>}
              {tab==='settings'&&<UpdateCenter apiFetch={apiFetch} notify={notify} canRollback={canAdminEmployees} card={card} field={field} btn={btn}/>}
</main>
    </div>
  </div>;
}
