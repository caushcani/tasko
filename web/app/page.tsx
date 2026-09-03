'use client'

import { useState } from 'react'
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  Boxes,
  CheckCircle2,
  Clock3,
  Command,
  Database,
  Ellipsis,
  Filter,
  Gauge,
  Layers3,
  LayoutDashboard,
  Menu,
  MoreHorizontal,
  Pause,
  Play,
  Search,
  Server,
  Settings2,
  ShieldCheck,
  TerminalSquare,
  TimerReset,
  Users,
  XCircle,
} from 'lucide-react'

const navItems = [
  { label: 'Overview', icon: LayoutDashboard, active: true },
  { label: 'Tasks', icon: Boxes },
  { label: 'Workers', icon: Server },
  { label: 'Queues', icon: Layers3 },
  { label: 'Schedules', icon: TimerReset },
]

const taskRows = [
  { name: 'sync_customer_records', queue: 'default', worker: 'worker-03', status: 'Success', duration: '1.24s', age: '12 sec ago' },
  { name: 'generate_weekly_report', queue: 'reports', worker: 'worker-01', status: 'Running', duration: '38.09s', age: '42 sec ago' },
  { name: 'send_invoice_email', queue: 'emails', worker: 'worker-02', status: 'Success', duration: '0.82s', age: '1 min ago' },
  { name: 'refresh_product_cache', queue: 'priority', worker: 'worker-04', status: 'Failed', duration: '4.61s', age: '2 min ago' },
  { name: 'rebuild_search_index', queue: 'maintenance', worker: 'worker-01', status: 'Queued', duration: '—', age: '3 min ago' },
]

function MetricCard({ label, value, delta, positive = true, icon: Icon }: { label: string; value: string; delta: string; positive?: boolean; icon: typeof Activity }) {
  return (
    <div className="metric-card">
      <div className="metric-top"><span>{label}</span><Icon size={16} /></div>
      <div className="metric-value">{value}</div>
      <div className={positive ? 'metric-delta positive' : 'metric-delta negative'}>{positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{delta}<span>vs last 24h</span></div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = { Success: 'status-success', Running: 'status-running', Failed: 'status-failed', Queued: 'status-queued' }
  const icons: Record<string, typeof CheckCircle2> = { Success: CheckCircle2, Running: Activity, Failed: XCircle, Queued: Clock3 }
  const Icon = icons[status]
  return <span className={`status-badge ${styles[status]}`}><Icon size={13} />{status}</span>
}

export default function Page() {
  const [paused, setPaused] = useState(false)
  const [activeRange, setActiveRange] = useState('24 hours')
  const [mobileNav, setMobileNav] = useState(false)

  return (
    <main className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'mobile-open' : ''}`}>
        <div className="brand"><div className="brand-mark"><span /><span /><span /></div><span>tasko<span className="brand-dot">.</span></span></div>
        <nav className="primary-nav" aria-label="Main navigation">
          <p className="nav-label">Monitor</p>
          {navItems.map((item) => <button className={`nav-item ${item.active ? 'active' : ''}`} key={item.label}><item.icon size={17} /><span>{item.label}</span>{item.label === 'Tasks' && <span className="nav-count">24</span>}</button>)}
          <p className="nav-label nav-label-spaced">Manage</p>
          <button className="nav-item"><TerminalSquare size={17} /><span>Logs</span></button>
          <button className="nav-item"><Bell size={17} /><span>Alerts</span><span className="alert-dot" /></button>
        </nav>
        <div className="sidebar-bottom"><button className="nav-item"><Settings2 size={17} /><span>Settings</span></button><div className="user-row connection-row"><span className="conn-dot" /><div><strong>tasko-core</strong><small>localhost:8000</small></div></div></div>
      </aside>

      <section className="content-area">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(!mobileNav)} aria-label="Toggle navigation"><Menu size={20} /></button><div className="breadcrumbs"><span>Tasko</span><span>/</span><strong>Overview</strong></div><div className="top-actions"><div className="search-box"><Search size={16} /><span>Search tasks...</span><kbd>⌘ K</kbd></div><button className="icon-button" aria-label="Notifications"><Bell size={18} /><i /></button></div></header>
        <div className="dashboard-content">
          <div className="page-heading"><div><div className="eyebrow"><span className="live-indicator" />Live monitoring</div><h1>Overview<span className="heading-period">.</span></h1><p>Fleet health across your Taskiq workers and queues.</p></div><div className="heading-actions"><button className="outline-button" onClick={() => setPaused(!paused)}>{paused ? <Play size={15} /> : <Pause size={15} />}{paused ? 'Resume' : 'Pause'} monitoring</button></div></div>

          <div className="metric-grid"><MetricCard label="Tasks processed" value="18,429" delta="12.8%" icon={Activity} /><MetricCard label="Success rate" value="99.2%" delta="0.4%" icon={ShieldCheck} /><MetricCard label="Avg. duration" value="1.84s" delta="8.2%" positive={false} icon={Gauge} /><MetricCard label="Active workers" value="8 / 10" delta="2 online" icon={Users} /></div>

          <div className="section-grid"><section className="panel throughput-panel"><div className="panel-heading"><div><h2>Task throughput</h2><p>Tasks completed over time</p></div><div className="range-tabs">{['1 hour', '24 hours', '7 days'].map((range) => <button key={range} className={activeRange === range ? 'selected' : ''} onClick={() => setActiveRange(range)}>{range}</button>)}</div></div><div className="chart-wrap"><div className="chart-y-labels"><span>1.2k</span><span>800</span><span>400</span><span>0</span></div><div className="chart"><div className="grid-line line-1" /><div className="grid-line line-2" /><div className="grid-line line-3" /><div className="grid-line line-4" /><svg viewBox="0 0 720 190" preserveAspectRatio="none" role="img" aria-label="Task throughput chart"><defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#55d6c2" stopOpacity=".28" /><stop offset="100%" stopColor="#55d6c2" stopOpacity="0" /></linearGradient></defs><path d="M0,145 C40,132 55,150 84,121 S125,102 150,126 S185,89 215,109 S250,87 279,96 S320,62 350,88 S385,104 409,73 S446,57 471,71 S500,47 532,66 S570,38 600,57 S635,36 660,52 S700,28 720,39 V190 H0 Z" fill="url(#area)" /><path d="M0,145 C40,132 55,150 84,121 S125,102 150,126 S185,89 215,109 S250,87 279,96 S320,62 350,88 S385,104 409,73 S446,57 471,71 S500,47 532,66 S570,38 600,57 S635,36 660,52 S700,28 720,39" fill="none" stroke="#55d6c2" strokeWidth="2.5" vectorEffect="non-scaling-stroke" /></svg><div className="chart-x-labels"><span>00:00</span><span>04:00</span><span>08:00</span><span>12:00</span><span>16:00</span><span>20:00</span><span>Now</span></div></div></div><div className="chart-legend"><span><i className="legend-dot cyan" />Completed <strong>18,429</strong></span><span><i className="legend-dot amber" />Failed <strong>146</strong></span></div></section>
            <section className="panel queue-panel"><div className="panel-heading"><div><h2>Queue health</h2><p>Current queue depth</p></div><button className="more-button" aria-label="More queue options"><Ellipsis size={19} /></button></div><div className="queue-total"><strong>2,841</strong><span>pending tasks</span><span className="queue-up"><ArrowUpRight size={14} /> 6.4%</span></div><div className="queue-list">{[['default', '1,248', '55%', 'cyan'], ['priority', '824', '29%', 'blue'], ['emails', '512', '18%', 'amber'], ['reports', '257', '9%', 'violet']].map(([name, count, percent, color]) => <div className="queue-row" key={name}><div className="queue-name"><i className={`queue-dot ${color}`} />{name}<span>{count}</span></div><div className="progress-track"><div className={`progress-fill ${color}`} style={{ width: percent }} /></div></div>)}</div><button className="text-button">View all queues <ArrowUpRight size={14} /></button></section></div>

          <section className="panel tasks-panel"><div className="panel-heading tasks-heading"><div><h2>Recent tasks</h2><p>Latest activity across the fleet</p></div><div className="table-actions"><button className="outline-button small"><Filter size={14} />Filters</button><button className="more-button"><Ellipsis size={19} /></button></div></div><div className="table-scroll"><table><thead><tr><th>Task name</th><th>Queue</th><th>Worker</th><th>Status</th><th>Duration</th><th>Started</th><th /></tr></thead><tbody>{taskRows.map((task) => <tr key={task.name}><td><span className="task-name"><span className="task-glyph">{task.status === 'Failed' ? <AlertCircle size={13} /> : <Command size={13} />}</span>{task.name}</span></td><td><span className="queue-pill">{task.queue}</span></td><td><span className="worker-cell"><span className="worker-dot" />{task.worker}</span></td><td><StatusBadge status={task.status} /></td><td className="mono">{task.duration}</td><td className="muted-cell">{task.age}</td><td><button className="row-more" aria-label={`Actions for ${task.name}`}><MoreHorizontal size={16} /></button></td></tr>)}</tbody></table></div><button className="view-tasks">View all tasks <ArrowUpRight size={14} /></button></section>

          <footer className="dashboard-footer"><span><span className="footer-dot" />All systems operational</span><span>Last updated just now</span><span className="footer-spacer" /><span><Database size={14} /> tasko-core v0.1.0</span></footer>
        </div>
      </section>
    </main>
  )
}
