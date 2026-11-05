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

const API = '/api';
const today = () => { const d = new Date(); return [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-'); };
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const navItems = [
  ['home','Home',LayoutDashboard],['dashboard','Dashboard',LayoutDashboard],
  ['employees','Employees',Users],['tasks','Task Manager',CheckSquare],
  ['tracker','Employee Tracker',ClipboardList],['attendance','Attendance',CalendarCheck],
  ['reports','Print Center',Printer],['archive','EOD Archive',Archive],
  ['business','Business Tracking',Briefcase],['customers','Store Directory',Store],
  ['chat','Live Chat',MessageCircle],['settings','Settings & Backup',Settings]
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

export default function App() {
  const [tab,setTab]=useState('home'),[sidebar,setSidebar]=useState(true);
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
  const [newAccount,setNewAccount]=useState({username:'',display_name:'',role:'Staff',password:'',security_question:'What was the name of your first school?',security_answer:''});
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const [data,setData]=useState({dashboard:null,employees:[],employeeGroups:[],tasks:[],attendance:{date:today(),roster:[]},attendanceSummary:{rows:[]},holidays:[],products:[],services:[],orders:[],members:[],prospects:[],messages:[],print:null,archive:[],db:null});
  const [query,setQuery]=useState('');
  const [prospectStateFilter,setProspectStateFilter]=useState('all');
  const [prospectKindFilter,setProspectKindFilter]=useState('all');
  const [prospectWebsiteFilter,setProspectWebsiteFilter]=useState('all');
  const [prospectVerificationFilter,setProspectVerificationFilter]=useState('all');
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
  const [selectedAttendanceIds,setSelectedAttendanceIds]=useState([]);
  const [bulkAttendance,setBulkAttendance]=useState({apply_status:false,status:'Present',apply_check_in:false,check_in:'',apply_check_out:false,check_out:'',apply_remarks:false,remarks:''});
  const [form,setForm]=useState({name:'',employee_code:'',department:'',designation:'',phone:'',email:'',title:'',task_date:today(),employee_id:'',priority:'Normal',status:'Not started',details:'',sku:'',category:'General',brand:'',base_unit:'PCS',opening_stock:0,received_qty:0,reorder_level:0,selling_price:0,training_mode:'In-Person',standard_price:0,customer_name:'',order_value:0,full_name:'',plan_name:'',business_name:'',business_category:'',kind:'Store',area:'',city:'',state:'',contact_person:'',address:'',website:'',maps:'',followup_date:'',call_time:'',connection:'',verified:'No',response:'',notes:'',content:'',channel:'general'});
  const [report,setReport]=useState({date:today(),report_type:'Audit / EOD',employee_id:''});
  const [reportText,setReportText]=useState('');
  const [editRecord,setEditRecord]=useState(null);
  const [holidayForm,setHolidayForm]=useState({holiday_date:today(),holiday_name:''});
  const [scrapeState,setScrapeState]=useState('');
  const [scrapeQuery,setScrapeQuery]=useState('sports nutrition supplement stores');
  const [scrapeBusy,setScrapeBusy]=useState(false);
  const [scrapeStatus,setScrapeStatus]=useState('');
  const [restoreFile,setRestoreFile]=useState(null),[restoreBusy,setRestoreBusy]=useState(false);
  const [workingWeekdays,setWorkingWeekdays]=useState([0,1,2,3,4,6]),[workingWeekdaysBusy,setWorkingWeekdaysBusy]=useState(false);
  const [theme,setTheme]=useState(()=>{const saved=localStorage.getItem('rsc_web_theme')||'night';return APPEARANCE_THEMES.includes(saved)?saved:'night';});
  const [wallpaper,setWallpaper]=useState(()=>{const saved=localStorage.getItem('rsc_web_wallpaper')||'Galaxy';return WALLPAPER_STYLES.includes(saved)?saved:'Galaxy';});
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
      ['dashboard','/dashboard',null],['employees','/employees?active_only=false',[]],['employeeGroups','/employee-groups',[]],['tasks','/tasks',[]],
      ['attendance','/attendance?work_date='+encodeURIComponent(selectedAttendanceDate),{date:selectedAttendanceDate,roster:[]}],
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
    setData(prev=>({...prev,...nextData}));setAttendanceDrafts({});setSelectedAttendanceIds([]);setBusy(false);
  };
  useEffect(()=>{(async()=>{if(!token){setChecked(true);return;}try{const r=await fetch(API+'/auth/me',{headers:{Authorization:'Bearer '+token}});if(!r.ok)throw 0;const j=await r.json();setUser(j.user);setChecked(true);}catch{localStorage.removeItem('rsc_auth_token');setToken('');setUser(null);setChecked(true);}})()},[]);
  useEffect(()=>{if(user&&token)load()},[user,token]);
  useEffect(()=>{
    document.documentElement.dataset.rscTheme=theme;
    document.body.dataset.rscTheme=theme;
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
  useEffect(()=>{if(tab==='settings'&&user&&['admin','developer'].includes(String(user.role||'').toLowerCase())){Promise.all([apiFetch('/auth/users'),apiFetch('/settings/working-weekdays')]).then(([accounts,working])=>{setAuthUsers(accounts);setWorkingWeekdays(working.weekdays||[0,1,2,3,4,6])}).catch(e=>notify(e.message))}},[tab,user,token]);
  const notify=(s)=>{setNotice(s);setTimeout(()=>setNotice(''),3500)};
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
  const submitLogin=async(e)=>{e.preventDefault();setError('');setBusy(true);try{const r=await fetch(API+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(login)});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Invalid username or password');localStorage.setItem('rsc_auth_token',j.token);setToken(j.token);setUser(j.user);notify('Signed in');}catch(e){let message=e.message;try{const s=await fetch(API+'/auth/status').then(x=>x.json());if(Array.isArray(s.usernames)&&s.usernames.length)message+=' Available account username(s): '+s.usernames.join(', ')+'.';}catch{}setError(message)}finally{setBusy(false)}};
  const submitRegistration=async(e)=>{e.preventDefault();setError('');setAuthNotice('');if(login.password!==authProfile.confirm_password){setError('Passwords do not match');return;}setBusy(true);try{const r=await fetch(API+'/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username,display_name:authProfile.display_name,password:login.password,security_question:authProfile.security_question,security_answer:authProfile.security_answer})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Account registration failed');setAuthNotice(j.message||'Account request submitted for Admin approval.');setAuthMode('login');setLogin(p=>({...p,password:''}));setAuthProfile(p=>({...p,confirm_password:'',security_answer:''}));}catch(e){setError(e.message)}finally{setBusy(false)}};
  const findRecoveryQuestion=async()=>{setError('');setRecoveryReady(false);setRecoveryQuestion('');try{const r=await fetch(API+'/auth/recovery-question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Could not find a recovery question');setRecoveryQuestion(j.security_question);setRecoveryReady(true);}catch(e){setError(e.message)}};
  const submitPasswordReset=async(e)=>{e.preventDefault();setError('');if(login.password!==authProfile.confirm_password){setError('Passwords do not match');return;}setBusy(true);try{const r=await fetch(API+'/auth/password-reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username,security_answer:authProfile.security_answer,new_password:login.password})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Password reset failed');setAuthNotice(j.message||'Password reset successfully. Sign in again.');setAuthMode('login');setLogin(p=>({...p,password:''}));setAuthProfile(p=>({...p,confirm_password:'',security_answer:''}));setRecoveryReady(false);}catch(e){setError(e.message)}finally{setBusy(false)}};
  const submitPasswordChange=async(e)=>{e.preventDefault();setError('');if(passwordChange.new_password!==passwordChange.confirm_password){setError('Passwords do not match');return;}if(passwordChange.new_password.length<8||!/[A-Za-z]/.test(passwordChange.new_password)||!/[0-9]/.test(passwordChange.new_password)){setError('Use at least 8 characters, including a letter and a number.');return;}setBusy(true);try{const r=await fetch(API+'/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:login.username,current_password:passwordChange.current_password,new_password:passwordChange.new_password})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Password change failed');setAuthNotice(j.message||'Password changed. Sign in again.');setAuthMode('login');setLogin(p=>({...p,password:''}));setPasswordChange({current_password:'',new_password:'',confirm_password:''});}catch(e){setError(e.message)}finally{setBusy(false)}};
  const toggleAccountActive=async(account)=>{try{await apiFetch('/auth/users/'+account.id+'/active',{method:'PATCH',body:JSON.stringify({active:!account.active})});setAuthUsers(rows=>rows.map(r=>r.id===account.id?{...r,active:!account.active}:r));notify('Account status updated');}catch(e){notify(e.message)}};
  const createManagedAccount=async(event)=>{event.preventDefault();try{await apiFetch('/auth/users',{method:'POST',body:JSON.stringify(newAccount)});const rows=await apiFetch('/auth/users');setAuthUsers(rows);setNewAccount({username:'',display_name:'',role:'Staff',password:'',security_question:'What was the name of your first school?',security_answer:''});notify('Account created and activated');}catch(e){notify(e.message)}};
  const changeAccountRole=async(account,role)=>{if(role===account.role)return;setAccountRoleDrafts(p=>({...p,[account.id]:role}));try{await apiFetch('/auth/users/'+account.id+'/role',{method:'PATCH',body:JSON.stringify({role})});setAuthUsers(rows=>rows.map(r=>r.id===account.id?{...r,role}:r));setAccountRoleDrafts(p=>({...p,[account.id]:role}));notify('Role updated for '+account.username);if(Number(account.id)===Number(user?.id))logout();}catch(e){setAccountRoleDrafts(p=>({...p,[account.id]:account.role}));notify(e.message)}};
  const saveManagedAccountPassword=async(account)=>{const {password,confirm}=accountPasswordDraft;if(password!==confirm){notify('Passwords do not match');return;}if(password.length<8||!/[A-Za-z]/.test(password)||!/[0-9]/.test(password)){notify('Use at least 8 characters with a letter and a number');return;}try{await apiFetch('/auth/users/'+account.id+'/password-reset',{method:'POST',body:JSON.stringify({new_password:password})});setAccountPasswordResetTarget(null);setAccountPasswordDraft({password:'',confirm:''});notify('Password reset for '+account.username);if(Number(account.id)===Number(user?.id))logout();}catch(e){notify(e.message)}};
  const saveWorkingWeekdays=async()=>{setWorkingWeekdaysBusy(true);try{const result=await apiFetch('/settings/working-weekdays',{method:'PUT',body:JSON.stringify({weekdays:workingWeekdays})});setWorkingWeekdays(result.weekdays||workingWeekdays);await load(data.attendance.date||today());notify('Working days saved. Sunday is always a working day.')}catch(e){notify(e.message)}finally{setWorkingWeekdaysBusy(false)}};
  const importStoreWorkbook=async()=>{if(!canAdminEmployees||!storeWorkbook)return;setStoreImportBusy(true);try{const payload=new FormData();payload.append('file',storeWorkbook);const response=await fetch(API+'/customers/import',{method:'POST',headers:{Authorization:'Bearer '+token},body:payload});const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(body.detail||'Store workbook import failed');setStoreWorkbook(null);await load();notify('Workbook merged: '+body.inserted+' new, '+body.duplicates_enriched_or_matched+' matched or enriched. Existing records were retained.');}catch(error){notify(error.message)}finally{setStoreImportBusy(false)}};
  const importDashboardWorkbook=async()=>{if(!canAdminEmployees||!dashboardWorkbook)return;setDashboardImportBusy(true);try{const payload=new FormData();payload.append('file',dashboardWorkbook);const response=await fetch(API+'/customers/dashboard-import',{method:'POST',headers:{Authorization:'Bearer '+token},body:payload});const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(body.detail||'Regional dashboard import failed');setDashboardWorkbook(null);await load();notify('Regional benchmark imported for '+body.territories+' territories. Store records were not changed.');}catch(error){notify(error.message)}finally{setDashboardImportBusy(false)}};
  const downloadStoreExport=async(format)=>{try{const params=new URLSearchParams({format});if(prospectStateFilter!=='all')params.set('state',prospectStateFilter);if(prospectKindFilter!=='all')params.set('kind',prospectKindFilter);if(prospectWebsiteFilter!=='all')params.set('website',prospectWebsiteFilter);if(prospectVerificationFilter!=='all')params.set('verification',prospectVerificationFilter);if(query.trim())params.set('q',query.trim());const response=await fetch(API+'/customers/export?'+params.toString(),{headers:{Authorization:'Bearer '+token}});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Store Directory export failed')}const blob=await response.blob();const url=window.URL.createObjectURL(blob);const anchor=document.createElement('a');const disposition=response.headers.get('content-disposition')||'';const match=disposition.match(/filename="?([^";]+)"?/i);anchor.href=url;anchor.download=match?.[1]||('stores_directory.'+format);document.body.appendChild(anchor);anchor.click();anchor.remove();window.URL.revokeObjectURL(url);notify(format.toUpperCase()+' export downloaded');}catch(error){notify(error.message)}};
  const downloadRegionalExport=async(format)=>{try{const params=new URLSearchParams({format});if(regionalTerritoryFilter!=='all')params.set('territory_type',regionalTerritoryFilter);const response=await fetch(API+'/customers/regional-export?'+params.toString(),{headers:{Authorization:'Bearer '+token}});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.detail||'Regional export failed')}const blob=await response.blob();const url=window.URL.createObjectURL(blob);const anchor=document.createElement('a');const disposition=response.headers.get('content-disposition')||'';const match=disposition.match(/filename="?([^";]+)"?/i);anchor.href=url;anchor.download=match?.[1]||('regional_dashboard.'+format);document.body.appendChild(anchor);anchor.click();anchor.remove();window.setTimeout(()=>window.URL.revokeObjectURL(url),1000);notify('Regional '+format.toUpperCase()+' export downloaded');}catch(error){notify(error.message)}};
  const openStorePrintPreview=()=>{const popup=window.open('','_blank');if(!popup){notify('Allow pop-ups to open the Store Directory print preview.');return;}const rows=prospectRows.map(row=>'<tr><td>'+escapeHtml(row.state)+'</td><td>'+escapeHtml(row.city)+'<br>'+escapeHtml(row.area)+'</td><td><b>'+escapeHtml(row.business_name)+'</b></td><td>'+escapeHtml(row.business_category)+'</td><td>'+escapeHtml(row.phone)+'</td><td>'+escapeHtml(row.address)+'</td><td>'+escapeHtml(row.maps)+'</td></tr>').join('');popup.document.open();popup.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Raw Strength Store Directory</title><style>body{font-family:Arial,sans-serif;color:#0f172a;padding:24px}h1{font-size:20px}p{color:#475569}button{padding:8px 14px;margin:10px 0}table{width:100%;border-collapse:collapse;font-size:11px}th,td{border:1px solid #cbd5e1;padding:6px;text-align:left;vertical-align:top}th{background:#1e293b;color:white}tr:nth-child(even){background:#f8fafc}@media print{button{display:none}body{padding:0}}</style></head><body><h1>RAW STRENGTH CALISTHENICS — STORE DIRECTORY</h1><p>Generated '+escapeHtml(new Date().toLocaleString())+' · '+prospectRows.length+' filtered records</p><button onclick="window.print()">Print / Save as PDF</button><table><thead><tr><th>State</th><th>City / Area</th><th>Business Name</th><th>Category</th><th>Phone</th><th>Full Address</th><th>Google Maps</th></tr></thead><tbody>'+rows+'</tbody></table></body></html>');popup.document.close();popup.focus();};
  const openRegionalPrintPreview=()=>{const popup=window.open('','_blank');if(!popup){notify('Allow pop-ups to open the Regional Dashboard print preview.');return;}const rows=regionalRows.map(row=>'<tr><td>'+escapeHtml(row.state)+'</td><td>'+escapeHtml(row.territory_type)+'</td><td>'+row.web_leads+'</td><td>'+row.workbook_leads+'</td><td>'+row.stores+'</td><td>'+row.gyms+'</td><td>'+(row.dashboard_stores??'—')+'</td><td>'+(row.variance==null?'—':(row.variance>0?'+':'')+row.variance)+'</td></tr>').join('');popup.document.open();popup.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Raw Strength Regional Dashboard</title><style>body{font-family:Arial,sans-serif;color:#0f172a;padding:24px}h1{font-size:20px}p{color:#475569}button{padding:8px 14px;margin:10px 0}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #cbd5e1;padding:7px;text-align:left}th{background:#1e293b;color:white}tr:nth-child(even){background:#f8fafc}@media print{button{display:none}body{padding:0}}</style></head><body><h1>RAW STRENGTH CALISTHENICS — REGIONAL DASHBOARD AUDIT</h1><p>Generated '+escapeHtml(new Date().toLocaleString())+' · '+regionalRows.length+' territories</p><button onclick="window.print()">Print / Save as PDF</button><table><thead><tr><th>State / UT / Island</th><th>Territory Type</th><th>Web leads</th><th>Workbook leads</th><th>All stores</th><th>All gyms</th><th>Dashboard target</th><th>Variance</th></tr></thead><tbody>'+rows+'</tbody></table></body></html>');popup.document.close();popup.focus();};
  const logout=()=>{localStorage.removeItem('rsc_auth_token');setToken('');setUser(null);setData({dashboard:null,employees:[],employeeGroups:[],tasks:[],attendance:{date:today(),roster:[]},attendanceSummary:{rows:[]},holidays:[],products:[],services:[],orders:[],members:[],prospects:[],messages:[],print:null,archive:[],db:null});setAttendanceDrafts({});setSelectedAttendanceIds([])};
  const set=(key,value)=>setForm(p=>({...p,[key]:value}));
  const post=async(path,payload)=>{try{const result=await apiFetch(path,{method:'POST',body:JSON.stringify(payload)});if(path==='/attendance/mark'){const selected=data.attendance.date||today();const [refreshed,summary]=await Promise.all([apiFetch('/attendance?work_date='+encodeURIComponent(selected)),apiFetch('/attendance/summary?work_date='+encodeURIComponent(selected))]);setData(p=>({...p,attendance:refreshed,attendanceSummary:summary}));setAttendanceDrafts({});}else{await load(data.attendance.date||today());}notify(result?.duplicate?'Existing store matched; no duplicate was created.':'Saved successfully');return result;}catch(e){notify(e.message);throw e;}};
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
    return (data.prospects||[]).filter(p=>{
      const haystack=['business_name','business_category','kind','area','city','state','contact_person','phone','email','address','website','maps','followup_date','call_time','connection','verified','response','source_status','notes'].map(k=>String(p[k]??'')).join(' ').toLowerCase();
      if(term&&!haystack.includes(term))return false;
      if(prospectStateFilter!=='all'&&String(p.state||'').trim().toLowerCase()!==prospectStateFilter.toLowerCase())return false;
      if(prospectKindFilter!=='all'&&String(p.kind||'Store').trim().toLowerCase()!==prospectKindFilter.toLowerCase())return false;
      const hasWebsite=Boolean(String(p.website||'').trim());
      if(prospectWebsiteFilter==='has'&&!hasWebsite)return false;
      if(prospectWebsiteFilter==='missing'&&hasWebsite)return false;
      const verified=['yes','y','true','verified'].includes(String(p.verified||'').trim().toLowerCase())||String(p.source_status||'').toLowerCase().includes('verified');
      if(prospectVerificationFilter==='verified'&&!verified)return false;
      if(prospectVerificationFilter==='pending'&&verified)return false;
      return true;
    });
  },[data.prospects,query,prospectStateFilter,prospectKindFilter,prospectWebsiteFilter,prospectVerificationFilter]);
  const prospectPageSize=100;
  const prospectPageCount=Math.max(1,Math.ceil(prospectRows.length/prospectPageSize));
  const visibleProspectRows=prospectRows.slice((prospectPage-1)*prospectPageSize,prospectPage*prospectPageSize);
  const regionalRows=useMemo(()=>{const rows=regionalSummary.rows||[];return rows.filter(row=>regionalTerritoryFilter==='all'||row.territory_type===regionalTerritoryFilter)},[regionalSummary,regionalTerritoryFilter]);
  useEffect(()=>{setProspectPage(1)},[query,prospectStateFilter,prospectKindFilter,prospectWebsiteFilter,prospectVerificationFilter]);
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
  const visibleAttendanceRows=(data.attendance.roster||[]).filter(r=>attendanceFilter==='all'||String(r.employee_id)===String(attendanceFilter));
  const attendanceDraftFor=r=>({...r,...(attendanceDrafts[r.employee_id]||{})});
  const updateAttendanceDraft=(r,key,value)=>setAttendanceDrafts(prev=>({...prev,[r.employee_id]:{...(prev[r.employee_id]||r),[key]:value}}));
  const toggleAttendanceSelection=id=>setSelectedAttendanceIds(prev=>prev.includes(Number(id))?prev.filter(x=>x!==Number(id)):[...prev,Number(id)]);
  const selectVisibleAttendance=()=>{const ids=visibleAttendanceRows.map(r=>Number(r.employee_id));setSelectedAttendanceIds(prev=>ids.every(id=>prev.includes(id))?prev.filter(id=>!ids.includes(id)):[...new Set([...prev,...ids])])};
  const attendanceNetHours=(checkIn,checkOut,breakMinutes=0)=>{if(!checkIn||!checkOut)return '—';const [ih,im]=checkIn.split(':').map(Number),[oh,om]=checkOut.split(':').map(Number);if([ih,im,oh,om].some(Number.isNaN))return '—';let minutes=(oh*60+om)-(ih*60+im);if(minutes<0)minutes+=1440;minutes=Math.max(0,minutes-Math.max(0,Number(breakMinutes)||0));return (minutes/60).toFixed(2)};
  const saveAttendanceDraft=async r=>{const draft=attendanceDraftFor(r);await post('/attendance/mark',{employee_id:Number(r.employee_id),work_date:selectedAttendanceDate,attendance_status:draft.attendance_status||'Unmarked',check_in:draft.check_in||'',check_out:draft.check_out||'',break_minutes:Number(draft.break_minutes||0),attendance_note:draft.attendance_note||''})};
  const applyAttendanceBulk=async()=>{if(!selectedAttendanceIds.length||attendanceIsHoliday)return;try{const result=await apiFetch('/attendance/bulk-edit',{method:'POST',body:JSON.stringify({work_date:selectedAttendanceDate,employee_ids:selectedAttendanceIds,...bulkAttendance})});await load(selectedAttendanceDate);notify('Updated attendance for '+result.updated+' employees');}catch(e){notify(e.message)}};
  const employeeOptions=data.employees.map(e=><option key={e.id} value={e.id}>{e.name}</option>);
  const heading=navItems.find(x=>x[0]===tab)?.[1]||'Home';
  const Panel=({title,children,actions})=><section className={card}><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 className="font-bold text-white">{title}</h2>{actions}</div>{children}</section>;
  const Input=({label,name,type='text',placeholder='',required=false})=><label className="block min-w-0 space-y-1"><span className="text-xs font-semibold text-slate-400">{label}</span><input className={field} type={type} required={required} value={form[name]??''} placeholder={placeholder} onChange={e=>set(name,type==='number'?Number(e.target.value):e.target.value)}/></label>;
  const Select=({label,name,options})=><label className="block min-w-0 space-y-1"><span className="text-xs font-semibold text-slate-400">{label}</span><select className={field} value={form[name]??''} onChange={e=>set(name,e.target.value)}>{options.map(o=><option key={o[0]} value={o[0]}>{o[1]}</option>)}</select></label>;
  const Rows=({items,keys,onDelete,onEdit})=><div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr>{keys.map(k=><th className="border-b border-white/10 px-3 py-3" key={k}>{k.replaceAll('_',' ')}</th>)}{(onDelete||onEdit)&&<th className="border-b border-white/10 px-3 py-3">Actions</th>}</tr></thead><tbody>{items.map((x,i)=><tr key={x.id??i} className="border-b border-white/5 text-slate-300">{keys.map(k=><td className={'px-3 py-3 '+(k==='address'?'max-w-[280px] whitespace-normal':'')} key={k}>{['maps','website'].includes(k)&&/^https?:\/\//i.test(String(x[k]||''))?<a className="text-cyan-300 underline underline-offset-2" href={String(x[k])} target="_blank" rel="noopener noreferrer">{k==='maps'?'Open Maps':'Open website'}</a>:String(x[k]??'—')}</td>)}{(onDelete||onEdit)&&<td className="px-3 py-3"><div className="flex gap-3">{onEdit&&<button className="text-cyan-300" onClick={()=>onEdit(x)}>Edit</button>}{onDelete&&<button className="text-rose-300" onClick={()=>onDelete(x)} aria-label="Delete"><Trash2 size={16}/></button>}</div></td>}</tr>)}</tbody></table>{!items.length&&<p className="py-6 text-center text-sm text-slate-500">No records found.</p>}</div>;

  if(!checked)return <div className="grid min-h-screen place-items-center bg-[#080d18] text-cyan-300">Loading…</div>;
  if(!user)return <div className="login-screen grid min-h-screen place-items-center bg-[#080d18] p-4 text-white"><div className="w-full max-w-md rounded-3xl border border-cyan-400/20 bg-slate-900/90 p-6 sm:p-8 shadow-2xl"><img src={brandLogo} className="mb-5 h-16 w-16 rounded-xl object-contain" alt="Raw Strength"/><h1 className="text-xl font-black">Raw Strength Calisthenics</h1><p className="mb-5 mt-1 text-sm text-slate-400">Employee Audit Manager · {authMode==='login'?'Sign in':authMode==='register'?'Create account':authMode==='change'?'Change password':'Reset password'}</p>{authNotice&&<p className="mb-4 rounded-lg border border-cyan-400/20 bg-cyan-950/40 p-3 text-sm text-cyan-200">{authNotice}</p>}{error&&<p className="mb-4 rounded-lg bg-rose-950 p-3 text-sm text-rose-300">{error}</p>}{authMode==='login'&&<form onSubmit={submitLogin}><label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>setLogin(p=>({...p,username:e.target.value}))} autoComplete="username" required/></label><label className="mb-5 block text-xs text-slate-400">Password<span className="mt-1 flex gap-2"><input className={field} type={showPassword?'text':'password'} value={login.password} onChange={e=>setLogin(p=>({...p,password:e.target.value}))} autoComplete="current-password" required/><button type="button" className="shrink-0 rounded-lg border border-white/10 px-3 text-xs text-cyan-200" onClick={()=>setShowPassword(v=>!v)}>{showPassword?'Hide':'Show'}</button></span></label><button className={btn+' w-full'} disabled={busy}>{busy?'Signing in…':'Sign in'}</button><div className="mt-5 flex flex-wrap justify-between gap-3 text-sm"><button type="button" className="text-cyan-300" onClick={()=>{setError('');setAuthNotice('');setAuthMode('forgot');setRecoveryReady(false)}}>Forgot password?</button><button type="button" className="text-cyan-300" onClick={()=>{setError('');setAuthNotice('');setAuthMode('change');setPasswordChange({current_password:'',new_password:'',confirm_password:''})}}>Change password</button><button type="button" className="text-cyan-300" onClick={()=>{setError('');setAuthNotice('');setAuthMode('register')}}>Create new account</button></div></form>}{authMode==='register'&&<form onSubmit={submitRegistration}><label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>setLogin(p=>({...p,username:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">Display name<input className={field+' mt-1'} value={authProfile.display_name} onChange={e=>setAuthProfile(p=>({...p,display_name:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">Password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={login.password} onChange={e=>setLogin(p=>({...p,password:e.target.value}))} required minLength={8}/></label><label className="mb-3 block text-xs text-slate-400">Confirm password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={authProfile.confirm_password} onChange={e=>setAuthProfile(p=>({...p,confirm_password:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">Recovery question<select className={field+' mt-1'} value={authProfile.security_question} onChange={e=>setAuthProfile(p=>({...p,security_question:e.target.value}))}>{['What was the name of your first school?','What is the name of the city where you were born?','What was your childhood nickname?','What is the name of your first teacher?','What was the first concert or live event you attended?'].map(q=><option key={q}>{q}</option>)}</select></label><label className="mb-5 block text-xs text-slate-400">Recovery answer<input className={field+' mt-1'} value={authProfile.security_answer} onChange={e=>setAuthProfile(p=>({...p,security_answer:e.target.value}))} required/></label><button className={btn+' w-full'} disabled={busy}>{busy?'Submitting…':'Create account'}</button><button type="button" className="mt-4 w-full text-sm text-cyan-300" onClick={()=>{setError('');setAuthMode('login')}}>Back to sign in</button><p className="mt-3 text-xs text-slate-500">New accounts require Admin approval before they can sign in.</p></form>}{authMode==='forgot'&&<form onSubmit={submitPasswordReset}><label className="mb-3 block text-xs text-slate-400">Username<input className={field+' mt-1'} value={login.username} onChange={e=>{setLogin(p=>({...p,username:e.target.value}));setRecoveryReady(false)}} required/></label>{!recoveryReady?<button type="button" className={btn+' w-full'} onClick={findRecoveryQuestion}>Find recovery question</button>:<><div className="mb-3 rounded-lg bg-slate-950 p-3 text-sm text-cyan-200">{recoveryQuestion}</div><label className="mb-3 block text-xs text-slate-400">Recovery answer<input className={field+' mt-1'} value={authProfile.security_answer} onChange={e=>setAuthProfile(p=>({...p,security_answer:e.target.value}))} required/></label><label className="mb-3 block text-xs text-slate-400">New password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={login.password} onChange={e=>setLogin(p=>({...p,password:e.target.value}))} required minLength={8}/></label><label className="mb-5 block text-xs text-slate-400">Confirm new password<input className={field+' mt-1'} type={showPassword?'text':'password'} value={authProfile.confirm_password} onChange={e=>setAuthProfile(p=>({...p,confirm_password:e.target.value}))} required/></label><button className={btn+' w-full'} disabled={busy}>{busy?'Resetting…':'Reset password'}</button></>}<button type="button" className="mt-4 w-full text-sm text-cyan-300" onClick={()=>{setError('');setAuthMode('login')}}>Back to sign in</button></form>}{authMode==='change'&&<form onSubmit={submitPasswordChange}>
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
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/10 bg-slate-950/95 transition-transform md:static md:translate-x-0 ${sidebar?'translate-x-0':'-translate-x-full'}`}>
      <div className="flex items-center gap-3 border-b border-white/10 p-4"><img src={brandLogo} className="h-10 w-10 rounded-lg object-contain" alt=""/><div><b className="text-sm">RAW STRENGTH</b><p className="text-[10px] tracking-widest text-cyan-400">CALISTHENICS</p></div><button className="ml-auto md:hidden" onClick={()=>setSidebar(false)}>✕</button></div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">{navItems.map(([id,label,Icon])=><button key={id} onClick={()=>{setTab(id);setSidebar(false)}} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm ${tab===id?'border border-cyan-400/30 bg-cyan-400/10 text-cyan-200':'text-slate-400 hover:bg-white/5'}`}><Icon size={18}/>{label}</button>)}</nav>
      <div className="border-t border-white/10 p-4"><p className="truncate text-sm font-bold">{user.display_name||user.username}</p><p className="text-xs text-slate-500">{user.role}</p><button onClick={logout} className="mt-3 flex items-center gap-2 text-xs text-rose-300"><LogOut size={14}/> Sign out</button></div>
    </aside>
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/10 bg-slate-950/50 px-4"><div className="flex min-w-0 items-center gap-3"><button onClick={()=>setSidebar(true)} className="rounded-lg border border-white/10 p-2 md:hidden"><Menu size={18}/></button><div><h1 className="truncate text-sm font-black uppercase tracking-wide">{heading}</h1><p className="text-[10px] text-slate-500">Employee Audit Manager · Operations</p></div></div><div className="flex items-center gap-2"><select aria-label="Application theme" className="hidden lg:block max-w-28 rounded-lg border border-white/10 bg-slate-900 px-2 py-2 text-xs text-slate-200" value={theme} onChange={e=>setTheme(e.target.value)}>{APPEARANCE_THEMES.map(value=><option key={value} value={value}>{value[0].toUpperCase()+value.slice(1)}</option>)}</select><select aria-label="Live wallpaper" className="hidden xl:block max-w-40 rounded-lg border border-white/10 bg-slate-900 px-2 py-2 text-xs text-slate-200" value={wallpaper} onChange={e=>setWallpaper(e.target.value)}>{WALLPAPER_STYLES.map(value=><option key={value} value={value}>{value}</option>)}</select><span className="hidden text-xs text-cyan-300 sm:inline">{new Date().toLocaleString()}</span><button onClick={()=>load()} className="rounded-lg border border-white/10 p-2 text-cyan-300" title="Refresh"><RefreshCw size={16} className={busy?'animate-spin':''}/></button></div></header>
      <main className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3 sm:p-5">
        {(tab==='home'||tab==='dashboard')&&<><div className="grid grid-cols-2 gap-3 xl:grid-cols-4">{[['Employees',data.dashboard?.kpis?.total_employees??data.employees.length],['Present today',data.dashboard?.kpis?.present_today??0],['Open tasks',data.dashboard?.kpis?.open_tasks??0],['Completed',data.dashboard?.kpis?.completed_tasks??0]].map(([l,v])=><div className={card} key={l}><p className="text-xs text-slate-400">{l}</p><p className="mt-2 text-3xl font-black text-cyan-300">{v}</p></div>)}</div><Panel title="Today's work"><Rows items={data.dashboard?.today_tasks||data.tasks.slice(0,8)} keys={['title','employee_name','status','task_date','priority']}/></Panel><Panel title="Quick actions"><div className="flex flex-wrap gap-2">{[['employees','Add employee'],['tasks','Create task'],['attendance','Mark attendance'],['reports','Generate report']].map(([t,l])=><button key={t} onClick={()=>setTab(t)} className={btn}>{l}</button>)}</div></Panel></>}
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
          <p className="mb-3 text-sm text-slate-400">Create active accounts, approve registrations, assign roles and reset passwords. Passwords are stored using the same PBKDF2 hashing as the Windows application.</p>
          <form className="mb-4 grid gap-3 rounded-xl border border-white/10 bg-slate-950/40 p-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={createManagedAccount}>
            <label className="text-xs text-slate-400">Username<input className={field+' mt-1'} value={newAccount.username} onChange={e=>setNewAccount(p=>({...p,username:e.target.value}))} maxLength={64} required/></label>
            <label className="text-xs text-slate-400">Display name<input className={field+' mt-1'} value={newAccount.display_name} onChange={e=>setNewAccount(p=>({...p,display_name:e.target.value}))} maxLength={100} required/></label>
            <label className="text-xs text-slate-400">Role / access level<select className={field+' mt-1'} value={newAccount.role} onChange={e=>setNewAccount(p=>({...p,role:e.target.value}))}>{['Staff','HR','Admin','Developer'].map(role=><option key={role} value={role} disabled={role==='Developer'&&String(user?.role||'').toLowerCase()!=='developer'}>{role}</option>)}</select></label>
            <label className="text-xs text-slate-400">Initial password<input className={field+' mt-1'} type="password" autoComplete="new-password" minLength={8} value={newAccount.password} onChange={e=>setNewAccount(p=>({...p,password:e.target.value}))} required/></label>
            <label className="text-xs text-slate-400">Recovery question<select className={field+' mt-1'} value={newAccount.security_question} onChange={e=>setNewAccount(p=>({...p,security_question:e.target.value}))}>{['What was the name of your first school?','What is the name of the city where you were born?','What was your childhood nickname?','What is the name of your first teacher?','What was the first concert or live event you attended?'].map(q=><option key={q}>{q}</option>)}</select></label>
            <label className="text-xs text-slate-400">Recovery answer<input className={field+' mt-1'} type="password" autoComplete="off" value={newAccount.security_answer} onChange={e=>setNewAccount(p=>({...p,security_answer:e.target.value}))} required/></label>
            <button className={btn+' sm:col-span-2 xl:col-span-3'}><Plus size={16}/> Create active account</button>
          </form>
          <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-sm"><thead><tr className="text-left text-xs text-slate-500"><th className="p-2">Username</th><th className="p-2">Display name</th><th className="p-2">Role / access</th><th className="p-2">Status</th><th className="p-2">Created</th><th className="p-2">Actions</th></tr></thead><tbody>{authUsers.map(a=>{const protectedDeveloper=String(a.role||'').toLowerCase()==='developer'&&String(user?.role||'').toLowerCase()!=='developer';return <tr key={a.id} className="border-t border-white/5 align-top"><td className="p-2">{a.username}</td><td className="p-2">{a.display_name}</td><td className="p-2"><select className={field+' min-w-28'} value={accountRoleDrafts[a.id]??a.role} disabled={protectedDeveloper} onChange={e=>changeAccountRole(a,e.target.value)}>{['Staff','HR','Admin','Developer'].map(role=><option key={role} value={role} disabled={role==='Developer'&&String(user?.role||'').toLowerCase()!=='developer'}>{role}</option>)}</select></td><td className="p-2">{a.active?'Active':'Pending / disabled'}</td><td className="p-2 text-xs text-slate-400">{String(a.created_at||'').slice(0,10)||'—'}</td><td className="p-2"><div className="flex flex-wrap gap-2"><button type="button" className="rounded-md border border-white/10 px-3 py-1 text-xs text-cyan-200 disabled:opacity-40" disabled={protectedDeveloper||(Number(a.id)===Number(user?.id)&&Boolean(a.active))} onClick={()=>toggleAccountActive(a)}>{a.active?'Deactivate':'Activate'}</button><button type="button" className="rounded-md border border-white/10 px-3 py-1 text-xs text-amber-200 disabled:opacity-40" disabled={protectedDeveloper} onClick={()=>{setAccountPasswordResetTarget(accountPasswordResetTarget===a.id?null:a.id);setAccountPasswordDraft({password:'',confirm:''})}}>Reset password</button></div>{accountPasswordResetTarget===a.id&&<div className="mt-2 grid min-w-56 gap-2 rounded-lg border border-white/10 bg-slate-950 p-2"><input className={field} type="password" autoComplete="new-password" placeholder="New password (8+ chars)" value={accountPasswordDraft.password} onChange={e=>setAccountPasswordDraft(p=>({...p,password:e.target.value}))}/><input className={field} type="password" autoComplete="new-password" placeholder="Confirm new password" value={accountPasswordDraft.confirm} onChange={e=>setAccountPasswordDraft(p=>({...p,confirm:e.target.value}))}/><div className="flex gap-2"><button type="button" className={btn+' px-3 py-2'} onClick={()=>saveManagedAccountPassword(a)}>Save password</button><button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300" onClick={()=>{setAccountPasswordResetTarget(null);setAccountPasswordDraft({password:'',confirm:''})}}>Cancel</button></div></div>}</td></tr>})}</tbody></table>{!authUsers.length&&<p className="py-5 text-center text-sm text-slate-500">No account records available.</p>}</div>
        </Panel>}
        {tab==='attendance'&&<><Panel title="Daily attendance"><div className="mb-3 flex flex-wrap items-end gap-3"><label className="text-xs text-slate-400">Work date<input className={field+' mt-1'} type="date" value={selectedAttendanceDate} onChange={async e=>{const selectedDate=e.target.value;if(!selectedDate)return;try{const [a,s]=await Promise.all([apiFetch('/attendance?work_date='+encodeURIComponent(selectedDate)),apiFetch('/attendance/summary?work_date='+encodeURIComponent(selectedDate))]);setData(p=>({...p,attendance:a,attendanceSummary:s}));setAttendanceDrafts({});setSelectedAttendanceIds([])}catch(err){notify(err.message)}}}/></label><label className="text-xs text-slate-400">Filter employee<select className={field+' mt-1 min-w-52'} value={attendanceFilter} onChange={e=>{setAttendanceFilter(e.target.value);setSelectedAttendanceIds([])}}><option value="all">All employees</option>{data.employees.map(e=><option key={e.id} value={e.id}>{e.name}</option>)}</select></label><button type="button" className="rounded-lg border border-white/10 px-3 py-2.5 text-sm text-cyan-200" onClick={selectVisibleAttendance}>{visibleAttendanceRows.length>0&&visibleAttendanceRows.every(r=>selectedAttendanceIds.includes(Number(r.employee_id)))?'Clear visible selection':'Select all visible'}</button><span className="text-xs text-slate-500">{selectedAttendanceIds.length} selected</span></div>{attendanceIsHoliday&&<p className="mb-3 rounded-lg border border-amber-400/30 bg-amber-950/40 p-3 text-sm text-amber-200">Holiday: {selectedAttendanceHoliday.holiday_name||'Declared holiday'} — attendance editing is disabled for this date.</p>}<div className="overflow-x-auto"><table className="w-full min-w-[1120px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="p-2">Select</th><th className="p-2">Employee</th><th className="p-2">Date</th><th className="p-2">Attendance status</th><th className="p-2">Check-in</th><th className="p-2">Check-out</th><th className="p-2">Net hours</th><th className="p-2">Remarks</th><th className="p-2">Action</th></tr></thead><tbody>{visibleAttendanceRows.map(r=>{const draft=attendanceDraftFor(r);return <tr key={r.employee_id} className="border-t border-white/5 text-slate-300"><td className="p-2"><input aria-label={'Select '+r.name} type="checkbox" checked={selectedAttendanceIds.includes(Number(r.employee_id))} onChange={()=>toggleAttendanceSelection(r.employee_id)} disabled={attendanceIsHoliday}/></td><td className="p-2 font-semibold text-white">{r.name}<div className="text-xs text-slate-500">{r.department||'—'}</div></td><td className="p-2 text-xs text-slate-400">{selectedAttendanceDate}</td><td className="p-2"><select className={field+' min-w-32'} value={['Unmarked','Present','Absent','Leave'].includes(draft.attendance_status)?draft.attendance_status:'Unmarked'} disabled={attendanceIsHoliday} onChange={e=>{const status=e.target.value;setAttendanceDrafts(prev=>({...prev,[r.employee_id]:{...(prev[r.employee_id]||r),attendance_status:status,...(['Absent','Leave','Unmarked'].includes(status)?{check_in:'',check_out:''}:{})}}))}}>{['Unmarked','Present','Absent','Leave'].map(s=><option key={s}>{s}</option>)}</select></td><td className="p-2"><input className={field+' w-28'} type="time" value={draft.check_in||''} disabled={attendanceIsHoliday||['Absent','Leave','Unmarked'].includes(draft.attendance_status)} onChange={e=>updateAttendanceDraft(r,'check_in',e.target.value)}/></td><td className="p-2"><input className={field+' w-28'} type="time" value={draft.check_out||''} disabled={attendanceIsHoliday||['Absent','Leave','Unmarked'].includes(draft.attendance_status)} onChange={e=>updateAttendanceDraft(r,'check_out',e.target.value)}/></td><td className="p-2 whitespace-nowrap text-cyan-200">{attendanceNetHours(draft.check_in,draft.check_out,draft.break_minutes)}</td><td className="p-2"><input className={field+' min-w-48'} value={draft.attendance_note||''} disabled={attendanceIsHoliday} placeholder="Attendance remarks" onChange={e=>updateAttendanceDraft(r,'attendance_note',e.target.value)}/></td><td className="p-2"><button className={btn+' px-3 py-2'} disabled={attendanceIsHoliday||!attendanceDrafts[r.employee_id]} onClick={()=>saveAttendanceDraft(r)}>Save</button></td></tr>})}</tbody></table>{!visibleAttendanceRows.length&&<p className="py-6 text-center text-sm text-slate-500">No employees found.</p>}</div></Panel><Panel title="Bulk edit selected employees"><p className="mb-3 text-sm text-slate-400">Only checked fields are changed. Unchecked values remain untouched.</p><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_status} onChange={e=>setBulkAttendance(p=>({...p,apply_status:e.target.checked}))}/> Apply status</span><select className={field} value={bulkAttendance.status} onChange={e=>setBulkAttendance(p=>({...p,status:e.target.value}))}>{['Present','Absent','Leave','Unmarked'].map(s=><option key={s}>{s}</option>)}</select></label><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_check_in} onChange={e=>setBulkAttendance(p=>({...p,apply_check_in:e.target.checked}))}/> Apply check-in</span><input className={field} type="time" value={bulkAttendance.check_in} onChange={e=>setBulkAttendance(p=>({...p,check_in:e.target.value}))}/></label><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_check_out} onChange={e=>setBulkAttendance(p=>({...p,apply_check_out:e.target.checked}))}/> Apply check-out</span><input className={field} type="time" value={bulkAttendance.check_out} onChange={e=>setBulkAttendance(p=>({...p,check_out:e.target.value}))}/></label><label className="space-y-2 text-xs text-slate-400"><span className="flex items-center gap-2"><input type="checkbox" checked={bulkAttendance.apply_remarks} onChange={e=>setBulkAttendance(p=>({...p,apply_remarks:e.target.checked}))}/> Apply remarks</span><input className={field} value={bulkAttendance.remarks} onChange={e=>setBulkAttendance(p=>({...p,remarks:e.target.value}))} placeholder="Remarks (blank clears)"/></label></div><div className="mt-4 flex flex-wrap items-center gap-3"><button className={btn} disabled={!selectedAttendanceIds.length||attendanceIsHoliday||!Object.entries(bulkAttendance).some(([k,v])=>k.startsWith('apply_')&&v)} onClick={applyAttendanceBulk}>Apply to {selectedAttendanceIds.length} selected</button><button className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-slate-300" onClick={()=>setBulkAttendance({apply_status:false,status:'Present',apply_check_in:false,check_in:'',apply_check_out:false,check_out:'',apply_remarks:false,remarks:''})}>Reset bulk fields</button></div></Panel><Panel title="Attendance totals & period summary"><p className="mb-3 text-xs text-slate-500">Totals exclude declared holidays and non-working weekdays. Work days are counted through the selected date.</p><Rows items={data.attendanceSummary?.rows||[]} keys={['employee_name','start_date','work_days','present','absent','leave','holidays','total_present']}/></Panel><Panel title="Holiday declaration"><form className="grid gap-3 sm:grid-cols-3" onSubmit={async e=>{e.preventDefault();try{await post('/holidays',holidayForm);setHolidayForm({holiday_date:today(),holiday_name:''})}catch{}}}><label className="text-xs text-slate-400">Date<input className={field+' mt-1'} type="date" value={holidayForm.holiday_date} onChange={e=>setHolidayForm(p=>({...p,holiday_date:e.target.value}))} required/></label><label className="text-xs text-slate-400">Holiday name<input className={field+' mt-1'} value={holidayForm.holiday_name} onChange={e=>setHolidayForm(p=>({...p,holiday_name:e.target.value}))} required/></label><button className={btn+' self-end'}><Plus size={16}/> Declare holiday</button></form><Rows items={data.holidays||[]} keys={['holiday_date','holiday_name','created_at']} onDelete={h=>del('/holidays/'+h.holiday_date)}/></Panel></>}{tab==='business'&&<BusinessTracking apiFetch={apiFetch} employees={data.employees} notify={notify}/>}
        {tab==='customers'&&<><Panel title="Store Directory · Workbook import, regional coverage & exports"><div className="grid gap-4 xl:grid-cols-2"><div className="rounded-xl border border-white/10 bg-slate-950/50 p-3"><h3 className="mb-2 text-sm font-bold text-white">Merge Store Directory workbook</h3><p className="mb-3 text-xs text-slate-400">Admin / Developer only · .xlsx up to 50 MB. Existing customer IDs, notes, follow-ups and records are merged, not deleted or replaced.</p><input className={field+' mb-3'} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={!canAdminEmployees||storeImportBusy} onChange={e=>setStoreWorkbook(e.target.files?.[0]||null)}/><button type="button" className={btn} disabled={!canAdminEmployees||!storeWorkbook||storeImportBusy} onClick={importStoreWorkbook}>{storeImportBusy?'Importing and merging…':'Import and merge workbook'}</button></div><div className="rounded-xl border border-white/10 bg-slate-950/50 p-3"><h3 className="mb-2 text-sm font-bold text-white">Import regional benchmark workbook</h3><p className="mb-3 text-xs text-slate-400">Admin / Developer only · Updates benchmark counts only. It does not alter Store Directory records.</p><input className={field+' mb-3'} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={!canAdminEmployees||dashboardImportBusy} onChange={e=>setDashboardWorkbook(e.target.files?.[0]||null)}/><button type="button" className={btn} disabled={!canAdminEmployees||!dashboardWorkbook||dashboardImportBusy} onClick={importDashboardWorkbook}>{dashboardImportBusy?'Importing benchmark…':'Import regional benchmark'}</button></div></div><div className="mt-4 flex flex-wrap items-center gap-2"><span className="mr-2 text-xs font-semibold text-slate-400">Export filtered Store Directory:</span>{['csv','xlsx','pdf','docx'].map(format=><button type="button" key={format} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={()=>downloadStoreExport(format)}>{format.toUpperCase()}</button>)}<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={openStorePrintPreview}>Print Preview</button></div><div className="mt-4 flex flex-wrap items-center gap-2"><span className="mr-2 text-xs font-semibold text-slate-400">Regional dashboard export:</span>{['csv','xlsx','pdf'].map(format=><button type="button" key={format} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={()=>downloadRegionalExport(format)}>{format.toUpperCase()}</button>)}<button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-cyan-200" onClick={openRegionalPrintPreview}>Print Preview</button></div><div className="mt-4"><div className="mb-2 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold text-white">Regional coverage</h3><span className="text-xs text-slate-400">{regionalRows.length} territories · {regionalSummary.totals?.customer_records||0} customer records</span></div><div className="mb-3 flex flex-wrap items-center gap-2"><select className={field+' w-auto min-w-56'} value={regionalTerritoryFilter} onChange={e=>setRegionalTerritoryFilter(e.target.value)}><option value="all">All 36 regions</option><option value="State">28 States</option><option value="Union Territory">6 Union Territories</option><option value="Island Territory">2 Island Territories</option></select><span className="text-xs text-slate-500">Export and print actions use this territory filter.</span></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="text-slate-500"><tr>{['State / UT','Type','Web leads','Workbook leads','Stores','Gyms','Dashboard stores','Variance'].map(label=><th key={label} className="border-b border-white/10 px-2 py-2">{label}</th>)}</tr></thead><tbody>{regionalRows.map(row=><tr key={row.state} className="border-b border-white/5 text-slate-300"><td className="px-2 py-2 font-semibold text-white">{row.state}</td><td className="px-2 py-2">{row.territory_type}</td><td className="px-2 py-2">{row.web_leads}</td><td className="px-2 py-2">{row.workbook_leads}</td><td className="px-2 py-2">{row.stores}</td><td className="px-2 py-2">{row.gyms}</td><td className="px-2 py-2">{row.dashboard_stores??'—'}</td><td className="px-2 py-2">{row.variance==null?'—':(row.variance>0?'+':'')+row.variance}</td></tr>)}</tbody></table>{!(regionalSummary.rows||[]).length&&<p className="py-4 text-center text-xs text-slate-500">Regional coverage will appear when Store Directory records or a dashboard benchmark are available.</p>}</div></div></Panel><Panel title="Store Directory · Web scraping"><form className="grid gap-3 sm:grid-cols-3" onSubmit={async e=>{e.preventDefault();if(scrapeBusy)return;setScrapeBusy(true);setScrapeStatus('Starting evidence-based public merchant search…');try{const started=await apiFetch('/customers/scrape',{method:'POST',body:JSON.stringify({state:scrapeState,query:scrapeQuery,max_results:20,deep_scrape:true})});let status;for(let i=0;i<300;i++){await new Promise(r=>setTimeout(r,1200));status=await apiFetch('/customers/scrape/'+started.job_id);setScrapeStatus(status.status==='running'?'Searching public merchant pages and checking address evidence…':status.status==='completed'?'Completed. Found '+status.found+' evidence-backed leads.':'Scraping failed: '+(status.error||'Unknown error'));if(status.status!=='running')break;}if(status?.status==='completed'){await load();notify('Store Directory updated: '+status.found+' leads found');}else if(status?.status==='running')setScrapeStatus('Search is still running. Refresh the directory shortly.');}catch(err){setScrapeStatus(err.message);notify(err.message)}finally{setScrapeBusy(false)}}}><label className="text-xs text-slate-400">State / UT (optional)<input className={field+' mt-1'} value={scrapeState} onChange={e=>setScrapeState(e.target.value)} placeholder="e.g. Andhra Pradesh"/></label><label className="text-xs text-slate-400 sm:col-span-2">Search terms<input className={field+' mt-1'} value={scrapeQuery} onChange={e=>setScrapeQuery(e.target.value)}/></label><button className={btn+' sm:col-span-3'} disabled={scrapeBusy}><Globe size={16}/>{scrapeBusy?'Searching public websites…':'Start deep web scraping'}</button></form>{scrapeStatus&&<p className="mt-3 rounded-lg bg-slate-950 p-3 text-sm text-cyan-200">{scrapeStatus}</p>}<p className="mt-2 text-xs text-slate-500">Only public merchant pages are inspected. Leads are deduplicated and marked unverified until direct confirmation; no synthetic contact details are generated.</p></Panel><Panel title="Add store / prospect"><form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" onSubmit={async e=>{e.preventDefault();const result=await post('/customers/prospects',form);if(result?.success)setForm(p=>({...p,business_name:'',business_category:'',kind:'Store',area:'',city:'',state:'',contact_person:'',phone:'',email:'',address:'',website:'',maps:'',followup_date:'',call_time:'',connection:'',verified:'No',response:'',notes:''}));}}><Input label="Business / store name" name="business_name" required/><Input label="Business category" name="business_category"/><Input label="Record type" name="kind" placeholder="Store / Gym / Hybrid"/><Input label="Area / locality" name="area"/><Input label="City" name="city" required/><Input label="State / UT" name="state" required/><Input label="Contact person" name="contact_person"/><Input label="Phone" name="phone"/><Input label="Email" name="email" type="email"/><Input label="Full postal address" name="address"/><Input label="Official website" name="website" type="url"/><Input label="Google Maps URL (optional)" name="maps" type="url"/><Input label="Follow-up date" name="followup_date" type="date"/><Input label="Call time" name="call_time" type="time"/><Input label="Connection / outcome" name="connection"/><Input label="Verification" name="verified" placeholder="Yes / No"/><Input label="Response" name="response"/><Input label="Notes" name="notes"/><button className={btn+' sm:col-span-2 xl:col-span-3'}><Plus size={16}/> Add prospect</button></form><p className="mt-2 text-xs text-slate-500">If a direct Maps URL is not supplied, the directory generates a Google Maps search link from the business name and postal address. City and state identify the store branch for duplicate checking.</p></Panel><Panel title={`Store directory · ${data.prospects.length} records`}><div className="mb-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5"><input className={field} placeholder="Search business, address, contact, phone, email or website" value={query} onChange={e=>setQuery(e.target.value)}/><select className={field} value={prospectKindFilter} onChange={e=>setProspectKindFilter(e.target.value)}><option value="all">All record types</option>{Array.from(new Set((data.prospects||[]).map(p=>String(p.kind||'Store').trim()).filter(Boolean))).sort().map(k=><option key={k} value={k.toLowerCase()}>{k}</option>)}</select><select className={field} value={prospectStateFilter} onChange={e=>setProspectStateFilter(e.target.value)}><option value="all">All states / UTs</option>{Array.from(new Set((data.prospects||[]).map(p=>String(p.state||'').trim()).filter(Boolean))).sort().map(s=><option key={s} value={s}>{s}</option>)}</select><select className={field} value={prospectWebsiteFilter} onChange={e=>setProspectWebsiteFilter(e.target.value)}><option value="all">All website status</option><option value="has">Has website</option><option value="missing">No website</option></select><select className={field} value={prospectVerificationFilter} onChange={e=>setProspectVerificationFilter(e.target.value)}><option value="all">All verification states</option><option value="verified">Verified</option><option value="pending">Needs confirmation</option></select></div>{busy&&data.prospects.length===0&&<p className="mb-3 text-sm text-cyan-200">Loading the complete Store Directory…</p>}<Rows items={visibleProspectRows} keys={['business_name','business_category','kind','area','city','state','address','phone','email','website','maps','followup_date','call_time','connection','verified','response','source_status']} onEdit={canAdminEmployees?(p=>setEditRecord({...p,editType:'prospects'})):undefined} onDelete={canAdminEmployees?(p=>del('/customers/prospects/'+p.id)):undefined}/><div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400"><span>Showing {prospectRows.length?((prospectPage-1)*prospectPageSize+1):0}–{Math.min(prospectPage*prospectPageSize,prospectRows.length)} of {prospectRows.length} stores · Page {prospectPage} of {prospectPageCount}</span><div className="flex gap-2"><button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 disabled:opacity-40" disabled={prospectPage<=1} onClick={()=>setProspectPage(page=>Math.max(1,page-1))}>Previous</button><button type="button" className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 disabled:opacity-40" disabled={prospectPage>=prospectPageCount} onClick={()=>setProspectPage(page=>Math.min(prospectPageCount,page+1))}>Next</button></div></div></Panel><Panel title="Memberships"><form className="grid gap-3 sm:grid-cols-3" onSubmit={e=>{e.preventDefault();post('/business/members',{full_name:form.full_name,plan_name:form.plan_name,status:'Active'})}}><Input label="Member name" name="full_name"/><Input label="Plan" name="plan_name"/><button className={btn+' self-end'}><Plus size={16}/> Add member</button></form><Rows items={data.members} keys={['full_name','status','plan_name','phone','start_date','end_date']}/></Panel></>}
        {tab==='reports'&&<PrintCenter employees={data.employees} apiFetch={apiFetch} notify={notify}/>}
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
            <label className="block space-y-2 text-xs font-semibold text-slate-400">Custom wallpaper · PNG, JPG, WEBP or BMP · 15 MB max
              <input className={field} type="file" accept=".png,.jpg,.jpeg,.webp,.bmp,image/png,image/jpeg,image/webp,image/bmp" disabled={appearanceBusy} onChange={uploadCustomWallpaper}/>
              <span className="block font-normal text-slate-500">{customWallpaperName?'Saved in this browser: '+customWallpaperName:'No custom image selected.'}</span>
            </label>
            <div className="flex flex-wrap items-end gap-2">
              <button type="button" className="rounded-lg border border-white/10 px-4 py-2.5 text-sm text-cyan-200 disabled:opacity-50" disabled={appearanceBusy} onClick={resetCustomWallpaper}>{appearanceBusy?'Saving…':'Reset wallpaper'}</button>
              <span className="text-xs text-slate-500">Changes apply immediately. Appearance is stored locally in this browser and is not written to shared employee records or cloud snapshots.</span>
            </div>
          </div>
        </Panel>}
        {tab==='settings'&&<><Panel title="Employee data actions"><div className="flex flex-wrap gap-2"><button type="button" className={btn} onClick={downloadEmployeesCsv}>Export employees CSV</button><button type="button" className={btn} onClick={exposeAllProofLinks}>Expose all proof links</button></div><p className="mt-2 text-xs text-slate-500">CSV includes active and inactive employee records. Global exposure enables full proof URLs for every task and the default reports.</p></Panel><Panel title="Account"><p className="text-sm">Signed in as <b>{user.display_name||user.username}</b> · {user.role}</p><button className="mt-3 rounded-lg border border-white/10 px-4 py-2 text-sm text-rose-300" onClick={logout}>Sign out</button></Panel><Panel title="Database and encrypted sync"><div className="mb-3 grid gap-2 sm:grid-cols-3"><div className="rounded-lg bg-slate-950 p-3"><p className="text-xs text-slate-500">Database</p><p className="mt-1 text-sm font-semibold">{data.db?.database_connected?'Connected':'Unavailable'}</p><p className="text-xs text-slate-500">{data.db?.database_name||'Waiting for status'}</p></div><div className="rounded-lg bg-slate-950 p-3"><p className="text-xs text-slate-500">Database size</p><p className="mt-1 text-sm font-semibold">{data.db?.database_size_bytes!=null?(data.db.database_size_bytes/1024/1024).toFixed(2)+' MB':'—'}</p><p className="text-xs text-slate-500">Integrity: {data.db?.database_integrity||'Unknown'}</p></div><div className="rounded-lg bg-slate-950 p-3"><p className="text-xs text-slate-500">Encrypted sync</p><p className="mt-1 text-sm font-semibold">{data.db?.sync?.status||'Status unavailable'}</p><p className="text-xs text-slate-500">{data.db?.sync?.configured?'Configured':'Not configured'}</p></div></div><pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(data.db?.counts||{},null,2)}</pre><div className="mt-3 flex flex-wrap gap-2"><button className={btn} onClick={downloadDatabaseBackup}><Download size={16}/> Download database backup</button><button className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm text-cyan-200 disabled:opacity-50" disabled={Boolean(data.db?.sync?.busy)} onClick={async()=>{try{const r=await apiFetch('/system/sync-now',{method:'POST'});notify(r.success?'Encrypted sync completed':(r.error||r.status||'Sync did not complete'));await load()}catch(e){notify(e.message)}}}><RefreshCw size={16}/> Sync Now</button></div>{canAdminEmployees&&<div className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/5 p-3"><label className="block text-xs text-slate-300">Restore database backup (Admin / Developer)<input className={field+' mt-2'} type="file" accept=".db,.sqlite,.sqlite3" onChange={e=>setRestoreFile(e.target.files?.[0]||null)}/></label><button className="mt-3 inline-flex items-center gap-2 rounded-lg border border-rose-400/30 px-4 py-2.5 text-sm text-rose-200 disabled:opacity-40" disabled={!restoreFile||restoreBusy} onClick={restoreDatabaseBackup}><Upload size={16}/>{restoreBusy?'Validating and restoring…':'Restore selected backup'}</button><p className="mt-2 text-xs text-slate-500">The server validates the SQLite file and creates a safety backup before replacement. Account names and password hashes in the restored database are preserved; browser sessions are cleared.</p></div>}</Panel></>}
      </main>
    </div>
  </div>;
}
