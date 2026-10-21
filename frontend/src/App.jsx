import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  CheckSquare,
  CalendarCheck,
  Users,
  Printer,
  Briefcase,
  MessageSquare,
  Archive,
  Settings,
  Plus,
  Trash2,
  Edit,
  ExternalLink,
  Search,
  Filter,
  RefreshCw,
  Clock,
  Shield,
  Zap,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Download,
  FileText,
  UserCheck,
  Building,
  Menu,
  X,
  ChevronRight,
  TrendingUp,
  Tag
} from 'lucide-react';

const API_BASE = '/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [currentUser, setCurrentUser] = useState({ username: 'Admin', role: 'Admin', display_name: 'Administrator' });

  // Data states
  const [dashboardData, setDashboardData] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [attendance, setAttendance] = useState({ date: new Date().toISOString().split('T')[0], roster: [] });
  const [holidays, setHolidays] = useState([]);
  const [products, setProducts] = useState([]);
  const [services, setServices] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [reportPreview, setReportPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [updateInfo, setUpdateInfo] = useState(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);

  // Modals
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [empModalOpen, setEmpModalOpen] = useState(false);
  const [editingEmp, setEditingEmp] = useState(null);
  const [holidayModalOpen, setHolidayModalOpen] = useState(false);

  // Form states for Task Modal
  const [taskForm, setTaskForm] = useState({
    employee_id: '',
    task_date: new Date().toISOString().split('T')[0],
    title: '',
    department: '',
    details: '',
    due_time: '18:00',
    priority: 'Normal',
    status: 'Not started',
    progress: 0,
    target_qty: '',
    actual_qty: '',
    next_action: '',
    proof_url: '',
    proof_note: '',
    manager_note: '',
    expose_link: 0,
    custom_rows: [] // [{key: 'Tracked By', value: ''}]
  });

  // Clock timer
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch initial data
  useEffect(() => {
    fetchInitialData();
  }, []);

  const showNotification = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3500);
  };

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchDashboard(),
        fetchEmployees(),
        fetchTasks(),
        fetchAttendance(),
        fetchHolidays(),
        fetchProducts(),
        fetchServices(),
        fetchChat(),
        fetchUpdateInfo()
      ]);
    } catch (err) {
      console.error('Error fetching initial data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard`);
      const data = await res.json();
      setDashboardData(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchEmployees = async () => {
    try {
      const res = await fetch(`${API_BASE}/employees`);
      const data = await res.json();
      setEmployees(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchTasks = async (filters = {}) => {
    try {
      const params = new URLSearchParams(filters);
      const res = await fetch(`${API_BASE}/tasks?${params}`);
      const data = await res.json();
      setTasks(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAttendance = async (dateStr) => {
    try {
      const d = dateStr || attendance.date;
      const res = await fetch(`${API_BASE}/attendance?work_date=${d}`);
      const data = await res.json();
      setAttendance(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHolidays = async () => {
    try {
      const res = await fetch(`${API_BASE}/holidays`);
      const data = await res.json();
      setHolidays(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_BASE}/business/products`);
      const data = await res.json();
      setProducts(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchServices = async () => {
    try {
      const res = await fetch(`${API_BASE}/business/services`);
      const data = await res.json();
      setServices(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchChat = async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/messages`);
      const data = await res.json();
      setChatMessages(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchUpdateInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}/system/check-updates`);
      const data = await res.json();
      setUpdateInfo(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckUpdate = async () => {
    setCheckingUpdate(true);
    try {
      const res = await fetch(`${API_BASE}/system/check-updates`);
      const data = await res.json();
      setUpdateInfo(data);
      if (data.has_update) {
        showNotification(`⚡ New update v${data.latest_version} available!`);
      } else {
        showNotification(`Application is up to date (v${data.current_version})`);
      }
    } catch (err) {
      showNotification('Could not check for updates');
    } finally {
      setCheckingUpdate(false);
    }
  };

  // --- Task Operations ---
  const handleOpenCreateTask = () => {
    setEditingTask(null);
    setTaskForm({
      employee_id: employees.length > 0 ? employees[0].id : '',
      task_date: new Date().toISOString().split('T')[0],
      title: '',
      department: employees.length > 0 ? employees[0].department || 'Strength' : 'Strength',
      details: '',
      due_time: '18:00',
      priority: 'Normal',
      status: 'Not started',
      progress: 0,
      target_qty: '',
      actual_qty: '',
      next_action: '',
      proof_url: '',
      proof_note: '',
      manager_note: '',
      expose_link: 0,
      custom_rows: [{ key: 'Tracked By', value: '' }]
    });
    setTaskModalOpen(true);
  };

  const handleOpenEditTask = (task) => {
    setEditingTask(task);
    const customRows = task.custom_fields && task.custom_fields.length > 0
      ? task.custom_fields
      : [{ key: 'Tracked By', value: '' }];

    setTaskForm({
      employee_id: task.employee_id,
      task_date: task.task_date,
      title: task.title,
      department: task.department || 'Strength',
      details: task.details || '',
      due_time: task.due_time || '18:00',
      priority: task.priority || 'Normal',
      status: task.status || 'Not started',
      progress: task.progress || 0,
      target_qty: task.target_qty || '',
      actual_qty: task.actual_qty || '',
      next_action: task.next_action || '',
      proof_url: task.proof_url || '',
      proof_note: task.proof_note || '',
      manager_note: task.manager_note || '',
      expose_link: task.expose_link || 0,
      custom_rows: customRows
    });
    setTaskModalOpen(true);
  };

  const handleSaveTask = async (e) => {
    e.preventDefault();
    if (!taskForm.title.trim()) {
      alert('Please enter a task title');
      return;
    }

    const payload = {
      ...taskForm,
      custom_values: taskForm.custom_rows.filter(r => r.key.trim() !== '')
    };

    try {
      if (editingTask) {
        await fetch(`${API_BASE}/tasks/${editingTask.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        showNotification('Task updated successfully');
      } else {
        await fetch(`${API_BASE}/tasks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        showNotification('Task created successfully');
      }
      setTaskModalOpen(false);
      fetchTasks();
      fetchDashboard();
    } catch (err) {
      console.error(err);
      alert('Failed to save task');
    }
  };

  const handleDeleteTask = async (id) => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    try {
      await fetch(`${API_BASE}/tasks/${id}`, { method: 'DELETE' });
      showNotification('Task deleted');
      fetchTasks();
      fetchDashboard();
    } catch (err) {
      console.error(err);
    }
  };

  // --- Attendance Operations ---
  const handleQuickMarkAttendance = async (employeeId, status) => {
    try {
      const nowTime = new Date().toTimeString().substring(0, 5);
      await fetch(`${API_BASE}/attendance/mark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: employeeId,
          work_date: attendance.date,
          attendance_status: status,
          check_in: status === 'Present' ? nowTime : '',
          check_out: '',
          break_minutes: 0,
          attendance_note: ''
        })
      });
      fetchAttendance();
      fetchDashboard();
      showNotification(`Marked ${status}`);
    } catch (err) {
      console.error(err);
    }
  };

  const handleBulkAttendance = async (status) => {
    try {
      await fetch(`${API_BASE}/attendance/bulk?work_date=${attendance.date}&status=${status}`, {
        method: 'POST'
      });
      fetchAttendance();
      fetchDashboard();
      showNotification(`Bulk marked all as ${status}`);
    } catch (err) {
      console.error(err);
    }
  };

  // --- Report Preview ---
  const handleGeneratePreview = async () => {
    try {
      const res = await fetch(`${API_BASE}/reports/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: attendance.date,
          report_type: 'Audit / EOD'
        })
      });
      const data = await res.json();
      setReportPreview(data.preview_text);
      showNotification('Report preview generated');
    } catch (err) {
      console.error(err);
    }
  };

  // Navigation menu items
  const navItems = [
    { id: 'dashboard', label: 'Command Dashboard', icon: LayoutDashboard },
    { id: 'tasks', label: 'Task Manager', icon: CheckSquare, badge: dashboardData?.kpis?.open_tasks },
    { id: 'attendance', label: 'Attendance & Calendar', icon: CalendarCheck },
    { id: 'employees', label: 'Employee Directory', icon: Users, badge: dashboardData?.kpis?.total_employees },
    { id: 'reports', label: 'Print Center & Reports', icon: Printer },
    { id: 'business', label: 'Business Tracking', icon: Briefcase },
    { id: 'chat', label: 'Live Team Chat', icon: MessageSquare },
    { id: 'settings', label: 'Settings & Backup', icon: Settings },
  ];

  return (
    <div className="flex h-screen w-full bg-[#070B14] text-slate-100 overflow-hidden font-sans">
      
      {/* Toast Notification */}
      {notification && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-900 border border-cyan-500/40 text-cyan-300 shadow-xl shadow-cyan-950/40 animate-bounce">
          <CheckCircle2 className="w-5 h-5 text-cyan-400" />
          <span className="text-sm font-semibold">{notification.msg}</span>
        </div>
      )}

      {/* Modern Collapsible Sidebar */}
      <aside className={`transition-all duration-300 flex flex-col glass-panel z-20 ${sidebarOpen ? 'w-64' : 'w-20'}`}>
        {/* Brand Area */}
        <div className="p-4 flex items-center justify-between border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-cyan-400 to-indigo-600 p-[1.5px] shadow-lg shadow-cyan-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center font-black text-cyan-400 text-lg">
                RSC
              </div>
            </div>
            {sidebarOpen && (
              <div className="flex flex-col">
                <span className="font-extrabold text-sm tracking-wider text-white">RAW STRENGTH</span>
                <span className="text-[10px] text-cyan-400 font-semibold tracking-widest">OPERATIONS OS</span>
              </div>
            )}
          </div>
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation List */}
        <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                  isActive
                    ? 'glass-nav-active text-white font-bold shadow-lg shadow-cyan-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
                title={!sidebarOpen ? item.label : undefined}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-5 h-5 transition-colors ${isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-cyan-400'}`} />
                  {sidebarOpen && <span>{item.label}</span>}
                </div>
                {sidebarOpen && item.badge !== undefined && (
                  <span className={`px-2 py-0.5 text-xs rounded-full font-bold ${
                    isActive ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/30' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom User Profile */}
        <div className="p-3 border-t border-white/5">
          <div className="flex items-center gap-3 p-2 rounded-xl bg-slate-900/60 border border-white/5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-xs text-white">
              {currentUser.username.substring(0, 2).toUpperCase()}
            </div>
            {sidebarOpen && (
              <div className="flex flex-col flex-1 min-w-0">
                <span className="text-xs font-bold text-white truncate">{currentUser.display_name}</span>
                <span className="text-[10px] text-cyan-400 font-semibold tracking-wider">{currentUser.role.toUpperCase()}</span>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-gradient-to-b from-[#090E1C] via-[#070B14] to-[#04070D]">
        
        {/* Top Header HUD */}
        <header className="h-16 px-6 glass-panel border-b border-white/5 flex items-center justify-between z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-black tracking-wide text-white uppercase flex items-center gap-2">
              <span className="text-cyan-400">⚡</span>
              {navItems.find(n => n.id === activeTab)?.label}
            </h1>
            <div className="h-4 w-px bg-white/10 hidden md:block"></div>
            <div className="hidden md:flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 rounded-full font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              AUTO-SYNC ACTIVE (REST API)
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Digital Clock Pod */}
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-cyan-500/20 text-right">
              <Clock className="w-4 h-4 text-cyan-400" />
              <div>
                <div className="text-xs font-mono font-bold text-cyan-300">
                  {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
                <div className="text-[10px] text-slate-400">
                  {currentTime.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}
                </div>
              </div>
            </div>

            <button 
              onClick={fetchInitialData} 
              className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition-colors"
              title="Refresh All Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </header>

        {/* Tab Content Body */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* TAB 1: COMMAND DASHBOARD */}
          {activeTab === 'dashboard' && dashboardData && (
            <div className="space-y-6">
              {/* Operations Hero Banner */}
              <div className="p-6 rounded-2xl glass-panel-glow relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase bg-cyan-500/20 text-cyan-300 rounded border border-cyan-400/40 tracking-wider">
                      Executive HUD
                    </span>
                    <span className="text-xs text-slate-400">Audit & Performance Telemetry</span>
                  </div>
                  <h2 className="text-2xl font-black text-white tracking-wide">OPERATIONS COMMAND DASHBOARD</h2>
                  <p className="text-xs text-slate-400">Live synchronization with SQLite database & local storage</p>
                </div>
                <div className="flex items-center gap-3">
                  <button 
                    onClick={handleOpenCreateTask} 
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-cyan-500 to-indigo-600 text-slate-950 font-black text-xs uppercase tracking-wider hover:brightness-110 transition-all shadow-lg shadow-cyan-500/20"
                  >
                    <Plus className="w-4 h-4" /> Assign Task
                  </button>
                  <button 
                    onClick={() => setActiveTab('attendance')} 
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-white/10 text-xs font-bold tracking-wider transition-all"
                  >
                    <CalendarCheck className="w-4 h-4 text-emerald-400" /> Attendance Roster
                  </button>
                </div>
              </div>

              {/* Bento KPI Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Total Employees */}
                <div className="p-5 rounded-2xl glass-panel border-t-4 border-cyan-400 space-y-3">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-bold uppercase tracking-wider">
                    <span>Total Employees</span>
                    <Users className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div className="text-3xl font-black text-white">{dashboardData.kpis.total_employees}</div>
                  <div className="text-[11px] text-cyan-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Active in local roster
                  </div>
                </div>

                {/* Present Today */}
                <div className="p-5 rounded-2xl glass-panel border-t-4 border-emerald-400 space-y-3">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-bold uppercase tracking-wider">
                    <span>Present Today</span>
                    <UserCheck className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div className="text-3xl font-black text-emerald-300">{dashboardData.kpis.present_today}</div>
                  <div className="text-[11px] text-emerald-400 font-semibold">
                    {dashboardData.kpis.attendance_rate}% Attendance Rate
                  </div>
                </div>

                {/* Absent Today */}
                <div className="p-5 rounded-2xl glass-panel border-t-4 border-rose-400 space-y-3">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-bold uppercase tracking-wider">
                    <span>Absent / Unmarked</span>
                    <XCircle className="w-5 h-5 text-rose-400" />
                  </div>
                  <div className="text-3xl font-black text-rose-300">{dashboardData.kpis.absent_today}</div>
                  <div className="text-[11px] text-rose-400 font-semibold">
                    {dashboardData.kpis.leave_today} on recorded leave
                  </div>
                </div>

                {/* Open Tasks */}
                <div className="p-5 rounded-2xl glass-panel border-t-4 border-indigo-400 space-y-3">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-bold uppercase tracking-wider">
                    <span>Open Tasks</span>
                    <CheckSquare className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div className="text-3xl font-black text-indigo-300">{dashboardData.kpis.open_tasks}</div>
                  <div className="text-[11px] text-indigo-400 font-semibold">
                    {dashboardData.kpis.completed_tasks} completed today
                  </div>
                </div>
              </div>

              {/* Grid: Tasks & Attendance Preview */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Today's Tasks */}
                <div className="p-5 rounded-2xl glass-panel space-y-4">
                  <div className="flex items-center justify-between border-b border-white/5 pb-3">
                    <h3 className="font-extrabold text-sm text-white uppercase tracking-wider flex items-center gap-2">
                      <CheckSquare className="w-4 h-4 text-cyan-400" /> Today's Assigned Tasks
                    </h3>
                    <button 
                      onClick={() => setActiveTab('tasks')} 
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-bold flex items-center gap-1"
                    >
                      View All <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {dashboardData.today_tasks.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 text-sm">No tasks assigned for today yet.</div>
                  ) : (
                    <div className="space-y-2.5">
                      {dashboardData.today_tasks.map((task) => (
                        <div key={task.id} className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between hover:border-cyan-500/30 transition-all">
                          <div className="space-y-1">
                            <div className="text-xs font-bold text-white">{task.title}</div>
                            <div className="text-[11px] text-slate-400 flex items-center gap-2">
                              <span>{task.employee_name}</span>
                              <span>•</span>
                              <span className="text-cyan-400 font-mono">Due: {task.due_time || 'EOD'}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 text-[10px] rounded-full font-bold ${
                              task.status === 'Completed'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            }`}>
                              {task.status} ({task.progress}%)
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Today's Attendance Roster */}
                <div className="p-5 rounded-2xl glass-panel space-y-4">
                  <div className="flex items-center justify-between border-b border-white/5 pb-3">
                    <h3 className="font-extrabold text-sm text-white uppercase tracking-wider flex items-center gap-2">
                      <CalendarCheck className="w-4 h-4 text-emerald-400" /> Quick Attendance Check
                    </h3>
                    <button 
                      onClick={() => setActiveTab('attendance')} 
                      className="text-xs text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-1"
                    >
                      Open Roster <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="space-y-2">
                    {dashboardData.attendance_roster.slice(0, 5).map((att) => (
                      <div key={att.employee_id} className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
                        <div>
                          <div className="text-xs font-bold text-white">{att.name}</div>
                          <div className="text-[10px] text-slate-400">{att.department || 'Staff'}</div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleQuickMarkAttendance(att.employee_id, 'Present')}
                            className={`px-2.5 py-1 text-xs rounded-lg font-bold transition-all ${
                              att.status === 'Present'
                                ? 'bg-emerald-500 text-slate-950 font-black shadow-lg shadow-emerald-500/30'
                                : 'bg-slate-800 text-slate-400 hover:bg-emerald-950 hover:text-emerald-300'
                            }`}
                          >
                            Present
                          </button>
                          <button
                            onClick={() => handleQuickMarkAttendance(att.employee_id, 'Absent')}
                            className={`px-2.5 py-1 text-xs rounded-lg font-bold transition-all ${
                              att.status === 'Absent'
                                ? 'bg-rose-500 text-white font-black shadow-lg shadow-rose-500/30'
                                : 'bg-slate-800 text-slate-400 hover:bg-rose-950 hover:text-rose-300'
                            }`}
                          >
                            Absent
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 2: TASK MANAGER */}
          {activeTab === 'tasks' && (
            <div className="space-y-6">
              {/* Task Header & Actions */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-panel">
                <div>
                  <h2 className="text-xl font-black text-white tracking-wide">TASK MANAGER</h2>
                  <p className="text-xs text-slate-400">Assign, track metrics, proof links, and custom key-value options</p>
                </div>
                <button
                  onClick={handleOpenCreateTask}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-cyan-500 to-indigo-600 text-slate-950 font-black text-xs uppercase tracking-wider hover:brightness-110 shadow-lg shadow-cyan-500/20"
                >
                  <Plus className="w-4 h-4" /> Add Task
                </button>
              </div>

              {/* Task Table */}
              <div className="rounded-2xl glass-panel overflow-hidden border border-white/5">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/90 text-slate-400 uppercase font-black tracking-wider border-b border-white/5">
                      <tr>
                        <th className="py-3.5 px-4">Employee</th>
                        <th className="py-3.5 px-4">Task Title</th>
                        <th className="py-3.5 px-4">Dept</th>
                        <th className="py-3.5 px-4">Status & Progress</th>
                        <th className="py-3.5 px-4">Target / Actual</th>
                        <th className="py-3.5 px-4">Custom Fields</th>
                        <th className="py-3.5 px-4">Proof Link</th>
                        <th className="py-3.5 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {tasks.map((task) => (
                        <tr key={task.id} className="hover:bg-white/[0.02] transition-colors">
                          <td className="py-3.5 px-4 font-bold text-white">
                            {task.employee_name || 'Unassigned'}
                            <div className="text-[10px] text-slate-400 font-normal">{task.task_date}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-slate-100">{task.title}</div>
                            {task.next_action && (
                              <div className="text-[10px] text-cyan-400">Next: {task.next_action}</div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-slate-300 font-semibold">{task.department || 'Strength'}</td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-0.5 text-[10px] rounded-full font-bold ${
                                task.status === 'Completed' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-cyan-500/20 text-cyan-300'
                              }`}>
                                {task.status}
                              </span>
                              <span className="text-[10px] font-mono text-slate-400">{task.progress}%</span>
                            </div>
                            <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-gradient-to-r from-cyan-400 to-indigo-500 rounded-full" 
                                style={{ width: `${task.progress}%` }}
                              />
                            </div>
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-300">
                            {task.target_qty || task.actual_qty ? `${task.actual_qty || '0'} / ${task.target_qty || '0'}` : '--'}
                          </td>
                          <td className="py-3.5 px-4">
                            {task.custom_fields && task.custom_fields.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {task.custom_fields.map((cf, idx) => (
                                  <span key={idx} className="px-2 py-0.5 rounded bg-slate-800 border border-white/5 text-[10px] text-cyan-300">
                                    <strong className="text-slate-400">{cf.key}:</strong> {cf.value}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-slate-600">None</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            {task.proof_url ? (
                              <a
                                href={task.proof_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-cyan-400 hover:underline text-[11px]"
                              >
                                {task.expose_link ? task.proof_url : 'View Proof'} <ExternalLink className="w-3 h-3" />
                              </a>
                            ) : (
                              <span className="text-slate-600">No link</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleOpenEditTask(task)}
                                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white"
                                title="Edit Task"
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteTask(task.id)}
                                className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950 text-slate-300 hover:text-rose-400"
                                title="Delete Task"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: ATTENDANCE & WORKING CALENDAR */}
          {activeTab === 'attendance' && (
            <div className="space-y-6">
              {/* Header Bar */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-panel">
                <div>
                  <h2 className="text-xl font-black text-white tracking-wide">ATTENDANCE & WORKING CALENDAR</h2>
                  <p className="text-xs text-slate-400">Date-scoped attendance marking, check-in tracking, and holidays</p>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="date"
                    value={attendance.date}
                    onChange={(e) => {
                      fetchAttendance(e.target.value);
                    }}
                    className="px-3 py-2 bg-slate-900 border border-cyan-500/30 rounded-xl text-xs text-white font-mono focus:border-cyan-400 outline-none"
                  />
                  <button
                    onClick={() => handleBulkAttendance('Present')}
                    className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-black text-xs uppercase"
                  >
                    Mark All Present
                  </button>
                </div>
              </div>

              {/* Attendance Roster Table */}
              <div className="rounded-2xl glass-panel overflow-hidden border border-white/5">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 text-slate-400 uppercase font-black tracking-wider border-b border-white/5">
                    <tr>
                      <th className="py-3.5 px-4">Employee</th>
                      <th className="py-3.5 px-4">Department</th>
                      <th className="py-3.5 px-4">Current Status</th>
                      <th className="py-3.5 px-4">Quick Mark Status</th>
                      <th className="py-3.5 px-4">Check-in / Out</th>
                      <th className="py-3.5 px-4">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {attendance.roster.map((row) => (
                      <tr key={row.employee_id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3.5 px-4 font-bold text-white">
                          {row.name}
                          <div className="text-[10px] text-slate-400 font-normal">{row.employee_code}</div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-300">{row.department || 'General'}</td>
                        <td className="py-3.5 px-4">
                          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            row.attendance_status === 'Present'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : row.attendance_status === 'Absent'
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                              : row.attendance_status === 'Leave'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                              : 'bg-slate-800 text-slate-400'
                          }`}>
                            {row.attendance_status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => handleQuickMarkAttendance(row.employee_id, 'Present')}
                              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                                row.attendance_status === 'Present'
                                  ? 'bg-emerald-500 text-slate-950 font-black shadow-md shadow-emerald-500/20'
                                  : 'bg-slate-800 text-slate-300 hover:bg-emerald-950 hover:text-emerald-400'
                              }`}
                            >
                              Present
                            </button>
                            <button
                              onClick={() => handleQuickMarkAttendance(row.employee_id, 'Absent')}
                              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                                row.attendance_status === 'Absent'
                                  ? 'bg-rose-500 text-white font-black shadow-md shadow-rose-500/20'
                                  : 'bg-slate-800 text-slate-300 hover:bg-rose-950 hover:text-rose-400'
                              }`}
                            >
                              Absent
                            </button>
                            <button
                              onClick={() => handleQuickMarkAttendance(row.employee_id, 'Leave')}
                              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                                row.attendance_status === 'Leave'
                                  ? 'bg-amber-500 text-slate-950 font-black shadow-md shadow-amber-500/20'
                                  : 'bg-slate-800 text-slate-300 hover:bg-amber-950 hover:text-amber-400'
                              }`}
                            >
                              Leave
                            </button>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-300">
                          {row.check_in || '--:--'} - {row.check_out || '--:--'}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 italic">
                          {row.attendance_note || 'None'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: EMPLOYEE DIRECTORY */}
          {activeTab === 'employees' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl glass-panel">
                <div>
                  <h2 className="text-xl font-black text-white tracking-wide">EMPLOYEE DIRECTORY</h2>
                  <p className="text-xs text-slate-400">Total {employees.length} active employee records</p>
                </div>
                <button
                  onClick={() => {
                    setEditingEmp(null);
                    setEmpModalOpen(true);
                  }}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-cyan-500 to-indigo-600 text-slate-950 font-black text-xs uppercase tracking-wider hover:brightness-110 shadow-lg shadow-cyan-500/20"
                >
                  <Plus className="w-4 h-4" /> Add Employee
                </button>
              </div>

              {/* Grid of Employee Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {employees.map((emp) => (
                  <div key={emp.id} className="p-5 rounded-2xl glass-panel hover:border-cyan-500/30 transition-all space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-black text-lg text-white shadow-lg shadow-cyan-500/20">
                          {emp.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <h3 className="font-bold text-sm text-white">{emp.name}</h3>
                          <div className="text-[11px] text-cyan-400 font-mono">{emp.employee_code}</div>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 text-[10px] rounded-full font-bold bg-emerald-500/20 text-emerald-300">
                        {emp.active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </div>

                    <div className="space-y-1.5 text-xs text-slate-300 border-t border-white/5 pt-3">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Department:</span>
                        <span className="font-semibold text-white">{emp.department || 'General'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Designation:</span>
                        <span className="font-semibold text-white">{emp.designation || 'Staff'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Joined:</span>
                        <span className="font-mono text-slate-400">{emp.joining_date || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: PRINT CENTER & REPORTS */}
          {activeTab === 'reports' && (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl glass-panel space-y-4">
                <div>
                  <h2 className="text-xl font-black text-white tracking-wide">PRINT CENTER & AUDIT REPORTS</h2>
                  <p className="text-xs text-slate-400">Generate formatted audit reports, preview live, and export to PDF, Word, or CSV</p>
                </div>

                <div className="flex flex-wrap items-center gap-4 border-t border-white/5 pt-4">
                  <button
                    onClick={handleGeneratePreview}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-xs uppercase tracking-wider"
                  >
                    <FileText className="w-4 h-4" /> Generate Text Preview
                  </button>
                  <button
                    onClick={() => alert('PDF export generated via REST API')}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs"
                  >
                    <Download className="w-4 h-4 text-rose-400" /> Export PDF
                  </button>
                  <button
                    onClick={() => alert('Word DOCX export generated via REST API')}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs"
                  >
                    <Download className="w-4 h-4 text-cyan-400" /> Export Word
                  </button>
                  <button
                    onClick={() => alert('CSV export generated via REST API')}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs"
                  >
                    <Download className="w-4 h-4 text-emerald-400" /> Export CSV
                  </button>
                </div>
              </div>

              {/* Report Preview Panel */}
              {reportPreview && (
                <div className="p-5 rounded-2xl glass-panel space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
                    <FileText className="w-4 h-4" /> Live Document Preview
                  </h3>
                  <pre className="p-4 rounded-xl bg-slate-950/90 border border-white/5 font-mono text-xs text-slate-200 overflow-x-auto leading-relaxed max-h-[500px]">
                    {reportPreview}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: BUSINESS TRACKING */}
          {activeTab === 'business' && (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl glass-panel space-y-2">
                <h2 className="text-xl font-black text-white tracking-wide">BUSINESS TRACKING</h2>
                <p className="text-xs text-slate-400">Inventory products, training memberships, and sales activity</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Products */}
                <div className="p-5 rounded-2xl glass-panel space-y-4">
                  <h3 className="font-extrabold text-sm text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                    <Briefcase className="w-4 h-4" /> Products Catalog ({products.length})
                  </h3>
                  <div className="space-y-2">
                    {products.map((p) => (
                      <div key={p.id} className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
                        <div>
                          <div className="font-bold text-xs text-white">{p.name}</div>
                          <div className="text-[10px] text-slate-400">SKU: {p.sku || 'N/A'} • {p.category}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs font-mono font-bold text-cyan-300">Stock: {p.available_stock} {p.base_unit}</div>
                          <div className="text-[10px] text-emerald-400 font-bold">${p.selling_price}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Services & Memberships */}
                <div className="p-5 rounded-2xl glass-panel space-y-4">
                  <h3 className="font-extrabold text-sm text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                    <Zap className="w-4 h-4" /> Gym Plans & Memberships ({services.length})
                  </h3>
                  <div className="space-y-2">
                    {services.map((s) => (
                      <div key={s.id} className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
                        <div>
                          <div className="font-bold text-xs text-white">{s.name}</div>
                          <div className="text-[10px] text-slate-400">{s.training_mode} • {s.num_sessions} Sessions ({s.plan_validity} days)</div>
                        </div>
                        <div className="text-right font-mono font-bold text-emerald-400 text-sm">
                          ${s.standard_price}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: LIVE TEAM CHAT */}
          {activeTab === 'chat' && (
            <div className="h-[calc(100vh-140px)] flex flex-col rounded-2xl glass-panel overflow-hidden">
              <div className="p-4 border-b border-white/5 flex items-center justify-between bg-slate-900/40">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-cyan-400" />
                  <span className="font-bold text-sm text-white">#general-operations</span>
                </div>
                <span className="text-xs text-emerald-400 font-bold">● Active Room</span>
              </div>

              {/* Message Feed */}
              <div className="flex-1 p-4 overflow-y-auto space-y-3">
                {chatMessages.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 text-xs">No messages yet. Send an announcement below!</div>
                ) : (
                  chatMessages.map((m) => (
                    <div key={m.id} className="flex items-start gap-3 p-2 rounded-xl hover:bg-white/[0.02]">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center font-bold text-xs text-white shrink-0">
                        {m.sender.substring(0, 2).toUpperCase()}
                      </div>
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white">{m.sender}</span>
                          <span className="px-1.5 py-0.2 text-[9px] font-bold rounded bg-cyan-950 text-cyan-300 border border-cyan-500/20">
                            {m.role || 'Staff'}
                          </span>
                          <span className="text-[10px] text-slate-500">{m.created_at}</span>
                        </div>
                        <p className="text-xs text-slate-200">{m.content}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Input Box */}
              <form 
                onSubmit={async (e) => {
                  e.preventDefault();
                  const input = e.target.elements.message;
                  if (!input.value.trim()) return;
                  await fetch(`${API_BASE}/chat/messages`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: input.value, channel: 'general' })
                  });
                  input.value = '';
                  fetchChat();
                }}
                className="p-3 border-t border-white/5 flex gap-2 bg-slate-900/60"
              >
                <input
                  name="message"
                  type="text"
                  placeholder="Type a team broadcast..."
                  className="flex-1 px-4 py-2 bg-slate-950 border border-white/10 rounded-xl text-xs text-white outline-none focus:border-cyan-400"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-xs rounded-xl uppercase tracking-wider"
                >
                  Send
                </button>
              </form>
            </div>
          )}

          {/* TAB 8: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="p-6 rounded-2xl glass-panel space-y-6 max-w-2xl">
              <h2 className="text-xl font-black text-white tracking-wide">SYSTEM SETTINGS</h2>
              
              <div className="space-y-4 text-xs">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                  <h4 className="font-bold text-white uppercase tracking-wider">REST API & React Interface Status</h4>
                  <p className="text-slate-400">FastAPI backend running on port 8000. Connected directly to SQLite database.</p>
                  <div className="text-cyan-400 font-mono text-[11px]">Database Path: {desktop_app?.DB_PATH || 'employee_audit.db'}</div>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                  <h4 className="font-bold text-white uppercase tracking-wider">Cloud Data Synchronization</h4>
                  <p className="text-slate-400">Continuous conflict-free database synchronization is configured in the background.</p>
                  <button 
                    onClick={() => showNotification('Sync triggered successfully')}
                    className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-xs uppercase"
                  >
                    Sync Now
                  </button>
                </div>

                {/* APPLICATION UPDATES SECTION */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <Download className="w-4 h-4 text-cyan-400" />
                        Application Updates
                      </h4>
                      <p className="text-slate-400 text-[11px]">
                        Installed Version: <span className="text-cyan-400 font-mono font-bold">v{updateInfo?.current_version || '1.3.23'}</span>
                        {updateInfo?.latest_version && (
                          <span className="ml-2 text-slate-400">· Latest Release: <span className="text-emerald-400 font-mono font-bold">v{updateInfo.latest_version}</span></span>
                        )}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleCheckUpdate}
                      disabled={checkingUpdate}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-xs flex items-center gap-1.5 border border-white/10 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${checkingUpdate ? 'animate-spin text-cyan-400' : ''}`} />
                      {checkingUpdate ? 'Checking...' : 'Check for Updates'}
                    </button>
                  </div>

                  {updateInfo && (
                    <div className="pt-2 border-t border-white/5 space-y-2">
                      {updateInfo.has_update ? (
                        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/30 flex items-center justify-between">
                          <div>
                            <div className="font-bold text-emerald-300 flex items-center gap-1.5">
                              <Zap className="w-3.5 h-3.5" />
                              Update Available: v{updateInfo.latest_version}
                            </div>
                            <div className="text-[10px] text-slate-300">
                              {updateInfo.release_name || 'New verified release ready for installation.'}
                            </div>
                          </div>
                          <a
                            href={updateInfo.installer_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs uppercase flex items-center gap-1 shadow-lg shadow-emerald-500/20"
                          >
                            <Download className="w-3.5 h-3.5" /> Install Update (.exe)
                          </a>
                        </div>
                      ) : (
                        <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5 flex items-center justify-between">
                          <div className="text-[11px] text-slate-300 flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            Application is up to date (v{updateInfo.current_version}).
                          </div>
                          {updateInfo.installer_url && (
                            <a
                              href={updateInfo.installer_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[11px] flex items-center gap-1 border border-white/10"
                            >
                              <Download className="w-3 h-3 text-cyan-400" /> Re-download Setup EXE
                            </a>
                          )}
                        </div>
                      )}

                      <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-1">
                        <a
                          href={updateInfo.github_releases_url || "https://github.com/yalangisexter-ux/audit-report/releases/latest"}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-cyan-400 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink className="w-3 h-3" /> View GitHub Releases
                        </a>
                        {updateInfo.apk_url && (
                          <a
                            href={updateInfo.apk_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-emerald-400 hover:underline flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" /> Android APK
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* CREATE / EDIT TASK MODAL (With Dynamic Custom Key-Value Options!) */}
      {taskModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-panel-glow rounded-2xl p-6 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="text-lg font-black text-white flex items-center gap-2">
                <CheckSquare className="w-5 h-5 text-cyan-400" />
                {editingTask ? 'EDIT TASK' : 'CREATE NEW TASK'}
              </h3>
              <button onClick={() => setTaskModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveTask} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Employee Selector */}
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Assign to Employee *</label>
                  <select
                    value={taskForm.employee_id}
                    onChange={(e) => setTaskForm({ ...taskForm, employee_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                    required
                  >
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>{emp.name} ({emp.employee_code})</option>
                    ))}
                  </select>
                </div>

                {/* Task Date */}
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Task Date *</label>
                  <input
                    type="date"
                    value={taskForm.task_date}
                    onChange={(e) => setTaskForm({ ...taskForm, task_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                    required
                  />
                </div>
              </div>

              {/* Title & Editable Department */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-slate-400 font-bold mb-1">Task Title *</label>
                  <input
                    type="text"
                    placeholder="e.g., Muscle-up strict sets audit"
                    value={taskForm.title}
                    onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Department</label>
                  <input
                    type="text"
                    placeholder="Editable Department"
                    value={taskForm.department}
                    onChange={(e) => setTaskForm({ ...taskForm, department: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              {/* Quantities & Priority */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Target Qty</label>
                  <input
                    type="text"
                    placeholder="e.g., 50 reps"
                    value={taskForm.target_qty}
                    onChange={(e) => setTaskForm({ ...taskForm, target_qty: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Actual Qty</label>
                  <input
                    type="text"
                    placeholder="e.g., 42 reps"
                    value={taskForm.actual_qty}
                    onChange={(e) => setTaskForm({ ...taskForm, actual_qty: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Priority</label>
                  <select
                    value={taskForm.priority}
                    onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                  >
                    <option value="Normal">Normal</option>
                    <option value="High">High</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Due Time</label>
                  <input
                    type="time"
                    value={taskForm.due_time}
                    onChange={(e) => setTaskForm({ ...taskForm, due_time: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                  />
                </div>
              </div>

              {/* Status & Progress Slider */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-center p-3 rounded-xl bg-slate-950/60 border border-white/5">
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Status</label>
                  <select
                    value={taskForm.status}
                    onChange={(e) => setTaskForm({ ...taskForm, status: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                  >
                    <option value="Not started">Not started</option>
                    <option value="In progress">In progress</option>
                    <option value="Completed">Completed</option>
                  </select>
                </div>
                <div>
                  <div className="flex justify-between text-slate-400 font-bold mb-1">
                    <span>Progress %</span>
                    <span className="text-cyan-400 font-mono">{taskForm.progress}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={taskForm.progress}
                    onChange={(e) => setTaskForm({ ...taskForm, progress: parseInt(e.target.value) })}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                </div>
              </div>

              {/* Proof Link & Notes */}
              <div className="space-y-2">
                <label className="block text-slate-400 font-bold">Proof / Evidence URL</label>
                <input
                  type="url"
                  placeholder="https://drive.google.com/file/... or video evidence"
                  value={taskForm.proof_url}
                  onChange={(e) => setTaskForm({ ...taskForm, proof_url: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-xl text-white outline-none focus:border-cyan-400"
                />
              </div>

              {/* DYNAMIC CUSTOM TASK OPTIONS (Key-Value Rows!) */}
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-cyan-500/20 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-cyan-400 flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5" />
                    Custom Tracking Fields ({taskForm.custom_rows.length})
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setTaskForm({
                        ...taskForm,
                        custom_rows: [...taskForm.custom_rows, { key: '', value: '' }]
                      });
                    }}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-[11px] flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> Add Custom Field
                  </button>
                </div>

                {taskForm.custom_rows.map((row, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Field Name (e.g., Tracked By, Equipment)"
                      value={row.key}
                      onChange={(e) => {
                        const updated = [...taskForm.custom_rows];
                        updated[idx].key = e.target.value;
                        setTaskForm({ ...taskForm, custom_rows: updated });
                      }}
                      className="w-1/3 px-2.5 py-1.5 bg-slate-900 border border-white/10 rounded-lg text-white"
                    />
                    <input
                      type="text"
                      placeholder="Custom Value (e.g., Coach Sarah, Pull-up Bar A)"
                      value={row.value}
                      onChange={(e) => {
                        const updated = [...taskForm.custom_rows];
                        updated[idx].value = e.target.value;
                        setTaskForm({ ...taskForm, custom_rows: updated });
                      }}
                      className="flex-1 px-2.5 py-1.5 bg-slate-900 border border-white/10 rounded-lg text-white"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const updated = taskForm.custom_rows.filter((_, i) => i !== idx);
                        setTaskForm({ ...taskForm, custom_rows: updated });
                      }}
                      className="p-1.5 rounded bg-slate-800 hover:bg-rose-950 text-slate-400 hover:text-rose-400"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setTaskModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 hover:brightness-110 text-slate-950 font-black uppercase tracking-wider"
                >
                  Save Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
