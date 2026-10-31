import React, { useState, useEffect } from 'react';
import brandLogo from '../../assets/raw_strength_brand_hud.png';
import {
  LayoutDashboard, CheckSquare, CalendarCheck, Users, Printer, Briefcase,
  Settings, RefreshCw, CheckCircle2, Menu, LogOut, Eye, EyeOff
} from 'lucide-react';

const API_BASE = '/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(() => typeof window !== 'undefined' && window.matchMedia('(min-width: 768px)').matches);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [currentUser, setCurrentUser] = useState(null);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('rsc_auth_token') || '');
  const [authChecked, setAuthChecked] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [loginBusy, setLoginBusy] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [attendance, setAttendance] = useState({ date: new Date().toISOString().split('T')[0], roster: [] });
  const [products, setProducts] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    (async () => {
      const token = localStorage.getItem('rsc_auth_token') || '';
      if (!token) { setAuthChecked(true); return; }
      try {
        const res = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error('session');
        const data = await res.json();
        setAuthToken(token);
        window.__rsc_token = token;
        setCurrentUser(data.user);
        setAuthChecked(true);
        loadAll(token);
      } catch {
        localStorage.removeItem('rsc_auth_token');
        setAuthToken('');
        setCurrentUser(null);
        setAuthChecked(true);
      }
    })();
  }, []);

  const apiFetch = async (url, options = {}) => {
    const token = authToken || window.__rsc_token || localStorage.getItem('rsc_auth_token') || '';
    const headers = { ...(options.headers || {}) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      localStorage.removeItem('rsc_auth_token');
      window.__rsc_token = '';
      setAuthToken('');
      setCurrentUser(null);
    }
    return res;
  };

  const showNotification = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  };

  const loadAll = async (tokenOverride) => {
    if (tokenOverride) window.__rsc_token = tokenOverride;
    setLoading(true);
    try {
      const [d, e, t, a, p, s] = await Promise.all([
        apiFetch(`${API_BASE}/dashboard`).then(r => r.ok ? r.json() : null),
        apiFetch(`${API_BASE}/employees`).then(r => r.ok ? r.json() : []),
        apiFetch(`${API_BASE}/tasks`).then(r => r.ok ? r.json() : []),
        apiFetch(`${API_BASE}/attendance?work_date=${new Date().toISOString().slice(0, 10)}`).then(r => r.ok ? r.json() : { date: '', roster: [] }),
        apiFetch(`${API_BASE}/business/products`).then(r => r.ok ? r.json() : []),
        apiFetch(`${API_BASE}/business/services`).then(r => r.ok ? r.json() : []),
      ]);
      setDashboardData(d);
      setEmployees(Array.isArray(e) ? e : []);
      setTasks(Array.isArray(t) ? t : []);
      setAttendance(a || { date: '', roster: [] });
      setProducts(Array.isArray(p) ? p : []);
      setServices(Array.isArray(s) ? s : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginBusy(true);
    setLoginError('');
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Invalid username or password');
      localStorage.setItem('rsc_auth_token', data.token);
      window.__rsc_token = data.token;
      setAuthToken(data.token);
      setCurrentUser(data.user);
      await loadAll(data.token);
      showNotification('Signed in');
    } catch (err) {
      setLoginError(err.message || 'Login failed');
    } finally {
      setLoginBusy(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('rsc_auth_token');
    window.__rsc_token = '';
    setAuthToken('');
    setCurrentUser(null);
  };

  const kpis = dashboardData?.kpis || {};
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'tasks', label: 'Task Manager', icon: CheckSquare, badge: kpis.open_tasks ?? tasks.length },
    { id: 'attendance', label: 'Attendance', icon: CalendarCheck },
    { id: 'employees', label: 'Employees', icon: Users, badge: kpis.total_employees ?? employees.length },
    { id: 'business', label: 'Business / Products', icon: Briefcase },
    { id: 'reports', label: 'Reports', icon: Printer },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  if (!authChecked) {
    return <div className="min-h-screen bg-[#070B14] text-cyan-300 flex items-center justify-center text-sm font-semibold">Loading…</div>;
  }

  if (!currentUser || !authToken) {
    return (
      <div className="min-h-screen bg-[#070B14] text-slate-100 flex items-center justify-center p-6">
        <form onSubmit={handleLogin} className="w-full max-w-lg rounded-3xl border border-cyan-400/20 bg-slate-900/90 p-6 sm:p-9 shadow-2xl shadow-black/40">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-400 to-indigo-600 p-[1.5px]">
              <img src={brandLogo} alt="Raw Strength Calisthenics" className="w-full h-full rounded-[10px] object-contain" />
            </div>
            <div>
              <h1 className="text-lg font-extrabold text-white break-words">Raw Strength Calisthenics</h1>
              <p className="text-xs text-slate-400">Employee Audit Manager · Sign in</p>
            </div>
          </div>
          <p className="text-sm text-slate-400 mb-5 break-words">Use the same username and password as the desktop app.</p>
          {loginError && <div className="mb-4 text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg px-3 py-2 break-words">{loginError}</div>}
          <label className="block text-xs font-semibold text-slate-400 mb-1">Username</label>
          <input className="w-full mb-4 rounded-lg bg-slate-950 border border-white/10 px-3 py-2.5 text-sm outline-none focus:border-cyan-400"
            value={loginForm.username} onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })} required autoComplete="username" />
          <label className="block text-xs font-semibold text-slate-400 mb-1">Password</label>
          <div className="relative mb-6">
            <input type={showPassword ? 'text' : 'password'} className="w-full rounded-lg bg-slate-950 border border-white/10 px-3 py-3 pr-20 text-base outline-none focus:border-cyan-400"
              value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} required autoComplete="current-password" />
            <button type="button" onClick={() => setShowPassword((visible) => !visible)}
              aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}
              className="absolute inset-y-0 right-2 my-auto h-10 min-w-16 rounded-lg border border-cyan-400/30 bg-slate-900 px-3 text-sm font-bold text-cyan-300 hover:border-cyan-400/70 focus:outline-none focus:ring-2 focus:ring-cyan-400/50">
              {showPassword ? <><EyeOff className="inline w-4 h-4 mr-1" />Hide</> : <><Eye className="inline w-4 h-4 mr-1" />Show</>}
            </button>
          </div>
          <button type="submit" disabled={loginBusy}
            className="w-full rounded-lg bg-gradient-to-r from-cyan-400 to-indigo-500 text-slate-950 font-bold py-2.5 text-sm disabled:opacity-60 min-h-[44px]">
            {loginBusy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="webapp-shell flex h-screen w-full bg-[#070B14] text-slate-100 overflow-hidden">
      {notification && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-900 border border-cyan-500/40 text-cyan-300 shadow-xl">
          <CheckCircle2 className="w-5 h-5" /><span className="text-sm font-semibold break-words">{notification}</span>
        </div>
      )}

      <aside className={`webapp-sidebar transition-all duration-300 flex flex-col border-r border-white/5 bg-slate-950/80 z-20 ${sidebarOpen ? 'w-64' : 'w-16'}`}>
        <div className="p-4 flex items-center justify-between border-b border-white/5">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 shrink-0 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-400 to-indigo-600 p-[1.5px]">
              <img src={brandLogo} alt="Raw Strength Calisthenics" className="w-full h-full rounded-[10px] object-contain" />
            </div>
            {sidebarOpen && (
              <div className="min-w-0">
                <div className="font-extrabold text-sm text-white truncate">RAW STRENGTH</div>
                <div className="text-[10px] text-cyan-400 font-semibold tracking-widest">CALISTHENICS</div>
              </div>
            )}
          </div>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400"><Menu className="w-5 h-5" /></button>
        </div>
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button key={item.id} onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium min-h-[40px] ${active ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-400/40' : 'text-slate-400 hover:bg-white/5'}`}>
                <Icon className="w-5 h-5 shrink-0" />
                {sidebarOpen && <span className="truncate flex-1 text-left">{item.label}</span>}
                {sidebarOpen && item.badge !== undefined && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800">{item.badge}</span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="p-3 border-t border-white/5">
          <div className="flex items-center gap-3 p-2 rounded-xl bg-slate-900/60 min-w-0">
            <div className="w-8 h-8 shrink-0 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-xs">
              {(currentUser?.username || 'U').slice(0, 2).toUpperCase()}
            </div>
            {sidebarOpen && (
              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold text-white truncate">{currentUser?.display_name || currentUser?.username}</div>
                <div className="text-[10px] text-cyan-400">{(currentUser?.role || '').toUpperCase()}</div>
                <button type="button" onClick={handleLogout} className="text-[10px] text-cyan-400/80 hover:text-cyan-300 flex items-center gap-1 mt-0.5">
                  <LogOut className="w-3 h-3" /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      <div className="webapp-content flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="h-14 px-4 border-b border-white/5 flex items-center justify-between bg-slate-950/50">
          <button type="button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation" className="mobile-menu-button p-2 rounded-lg bg-slate-900 border border-white/10 text-cyan-300"><Menu className="w-5 h-5" /></button><h1 className="text-base font-black text-white uppercase truncate">{navItems.find(n => n.id === activeTab)?.label}</h1>
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-xs font-mono text-cyan-300">{currentTime.toLocaleTimeString()}</div>
            <button onClick={() => loadAll()} className="p-2 rounded-lg bg-slate-900 border border-white/10 hover:border-cyan-400/40" title="Refresh">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </header>

        <main className="webapp-main flex-1 overflow-y-auto p-3 sm:p-4 space-y-4 min-w-0">
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                ['Employees', kpis.total_employees ?? employees.length],
                ['Present today', kpis.present_today ?? 0],
                ['Open tasks', kpis.open_tasks ?? 0],
                ['Completed', kpis.completed_tasks ?? 0],
              ].map(([label, val]) => (
                <div key={label} className="rounded-xl border border-white/10 bg-slate-900/60 p-4 min-w-0">
                  <div className="text-xs text-slate-400 truncate">{label}</div>
                  <div className="text-2xl font-black text-cyan-300 mt-1">{val}</div>
                </div>
              ))}
              <div className="col-span-2 md:col-span-4 rounded-xl border border-white/10 bg-slate-900/40 p-4">
                <div className="text-sm font-bold text-white mb-2">Today's tasks</div>
                {(dashboardData?.today_tasks || tasks.slice(0, 6)).length === 0 && <p className="text-sm text-slate-500">No tasks yet.</p>}
                <ul className="space-y-2">
                  {(dashboardData?.today_tasks || tasks.slice(0, 6)).map((t, i) => (
                    <li key={t.id || i} className="text-sm text-slate-300 border-b border-white/5 pb-2 break-words">
                      <span className="font-semibold text-white">{t.title}</span>
                      <span className="text-slate-500"> · {t.status} · {t.employee_name || ''}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'tasks' && (
            <div className="space-y-2">
              <div className="text-sm text-slate-400 mb-2">{tasks.length} tasks</div>
              {tasks.map((t) => (
                <div key={t.id} className="rounded-xl border border-white/10 bg-slate-900/50 p-3 min-w-0">
                  <div className="font-semibold text-white break-words">{t.title}</div>
                  <div className="text-xs text-slate-400 mt-1 break-words">{t.employee_name || '—'} · {t.status} · {t.task_date} · {t.priority}</div>
                  {t.details && <div className="text-xs text-slate-500 mt-1 break-words whitespace-pre-wrap">{t.details}</div>}
                </div>
              ))}
              {tasks.length === 0 && <p className="text-slate-500 text-sm">No tasks found.</p>}
            </div>
          )}

          {activeTab === 'attendance' && (
            <div className="space-y-2">
              <div className="text-sm text-slate-400">Date: {attendance.date || '—'}</div>
              {(attendance.roster || []).map((r, i) => (
                <div key={r.employee_id || i} className="rounded-xl border border-white/10 bg-slate-900/50 p-3 flex justify-between gap-3 min-w-0">
                  <div className="min-w-0">
                    <div className="font-semibold text-white truncate">{r.name}</div>
                    <div className="text-xs text-slate-400">{r.department || ''} · {r.employee_code || ''}</div>
                  </div>
                  <div className="text-sm font-bold text-cyan-300 shrink-0">{r.status || r.attendance_status || 'Unmarked'}</div>
                </div>
              ))}
              {(attendance.roster || []).length === 0 && <p className="text-slate-500 text-sm">No attendance rows.</p>}
            </div>
          )}

          {activeTab === 'employees' && (
            <div className="space-y-2">
              {employees.map((e) => (
                <div key={e.id} className="rounded-xl border border-white/10 bg-slate-900/50 p-3 min-w-0">
                  <div className="font-semibold text-white break-words">{e.name}</div>
                  <div className="text-xs text-slate-400 break-words">{e.employee_code} · {e.department} · {e.designation}</div>
                  <div className="text-xs text-slate-500 break-words">{e.phone} {e.email}</div>
                </div>
              ))}
              {employees.length === 0 && <p className="text-slate-500 text-sm">No employees.</p>}
            </div>
          )}

          {activeTab === 'business' && (
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <h2 className="font-bold text-white mb-2">Products ({products.length})</h2>
                {products.map((p) => (
                  <div key={p.id} className="rounded-xl border border-white/10 bg-slate-900/50 p-3 mb-2 min-w-0">
                    <div className="font-semibold text-white break-words">{p.name}</div>
                    <div className="text-xs text-slate-400 break-words">SKU {p.sku || '—'} · {p.category}</div>
                  </div>
                ))}
                {products.length === 0 && <p className="text-slate-500 text-sm">No products.</p>}
              </div>
              <div>
                <h2 className="font-bold text-white mb-2">Services / Plans ({services.length})</h2>
                {services.map((s) => (
                  <div key={s.id} className="rounded-xl border border-white/10 bg-slate-900/50 p-3 mb-2 min-w-0">
                    <div className="font-semibold text-white break-words">{s.name}</div>
                    <div className="text-xs text-slate-400 break-words">{s.category} · {s.training_mode} · ₹{s.standard_price}</div>
                  </div>
                ))}
                {services.length === 0 && <p className="text-slate-500 text-sm">No services.</p>}
              </div>
            </div>
          )}

          {activeTab === 'reports' && (
            <div className="rounded-xl border border-white/10 bg-slate-900/50 p-4 text-sm text-slate-400 break-words">
              Full PDF export matches the desktop Print Center. Web report APIs are under /api/reports.
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="rounded-xl border border-white/10 bg-slate-900/50 p-4 space-y-2 text-sm text-slate-300">
              <div className="font-bold text-white">Signed in as {currentUser?.display_name || currentUser?.username}</div>
              <div className="text-slate-400 break-words">Role: {currentUser?.role}</div>
              <div className="text-slate-400 break-words">Web uses the same login users when the cloud DB snapshot is pulled. Customer prospects and full invoicing expand in follow-up updates.</div>
              <button type="button" onClick={handleLogout} className="mt-2 px-4 py-2 rounded-lg bg-slate-800 border border-white/10 text-cyan-300 min-h-[40px]">Sign out</button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
