'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bell, Menu, Search, Settings2 } from 'lucide-react'
import { isNavItemActive, NAV_ITEMS, titleFor } from './nav-items'

// The sidebar + topbar chrome every dashboard page shares. Lives in the root
// layout so `/`, `/tasks`, etc. only ever render their own content — see
// app/layout.tsx.
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [mobileNav, setMobileNav] = useState(false)
  const pathname = usePathname()
  const title = titleFor(pathname)

  return (
    <main className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'mobile-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">
            <span />
            <span />
            <span />
          </div>
          <span>
            tasko<span className="brand-dot">.</span>
          </span>
        </div>
        <nav className="primary-nav" aria-label="Main navigation">
          <p className="nav-label">Monitor</p>
          {NAV_ITEMS.map((item) =>
            item.href ? (
              <Link
                href={item.href}
                className={`nav-item ${isNavItemActive(item, pathname) ? 'active' : ''}`}
                key={item.label}
              >
                <item.icon size={17} />
                <span>{item.label}</span>
              </Link>
            ) : (
              <button
                className="nav-item"
                key={item.label}
                disabled
                aria-disabled="true"
                title="Not built yet"
              >
                <item.icon size={17} />
                <span>{item.label}</span>
              </button>
            ),
          )}
          <p className="nav-label nav-label-spaced">Manage</p>
          <button className="nav-item" disabled aria-disabled="true" title="Not built yet">
            <Bell size={17} />
            <span>Alerts</span>
          </button>
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item" disabled aria-disabled="true" title="Not built yet">
            <Settings2 size={17} />
            <span>Settings</span>
          </button>
          <div className="user-row connection-row">
            <span className="conn-dot" />
            <div>
              <strong>tasko-core</strong>
              <small>localhost:8000</small>
            </div>
          </div>
        </div>
      </aside>

      <section className="content-area">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileNav(!mobileNav)}
            aria-label="Toggle navigation"
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumbs">
            <span>Tasko</span>
            <span>/</span>
            <strong>{title}</strong>
          </div>
          <div className="top-actions">
            <div className="search-box">
              <Search size={16} />
              <span>Search tasks...</span>
              <kbd>⌘ K</kbd>
            </div>
            <button className="icon-button" aria-label="Notifications" disabled>
              <Bell size={18} />
            </button>
          </div>
        </header>
        <div className="dashboard-content">{children}</div>
      </section>
    </main>
  )
}
