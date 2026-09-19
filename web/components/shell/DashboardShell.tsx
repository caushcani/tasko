'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bell, Menu, Search, Settings2 } from 'lucide-react'
import { CommandPalette } from './CommandPalette'
import { GlobalHotkeys } from './GlobalHotkeys'
import { isNavItemActive, NAV_ITEMS, titleFor, type NavItem } from './nav-items'

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  if (!item.href) {
    return (
      <button className="nav-item" disabled aria-disabled="true" title="Not built yet">
        <item.icon size={17} />
        <span>{item.label}</span>
      </button>
    )
  }
  return (
    <Link href={item.href} className={`nav-item ${active ? 'active' : ''}`}>
      <item.icon size={17} />
      <span>{item.label}</span>
    </Link>
  )
}

// The sidebar + topbar chrome every dashboard page shares. Lives in the root
// layout so `/`, `/tasks`, etc. only ever render their own content — see
// app/layout.tsx.
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [mobileNav, setMobileNav] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const pathname = usePathname()
  const title = titleFor(pathname)

  return (
    <main className="app-shell">
      <GlobalHotkeys />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />

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
          {NAV_ITEMS.filter((item) => item.group === 'monitor').map((item) => (
            <NavLink item={item} active={isNavItemActive(item, pathname)} key={item.label} />
          ))}
          <p className="nav-label nav-label-spaced">Manage</p>
          {NAV_ITEMS.filter((item) => item.group === 'manage').map((item) => (
            <NavLink item={item} active={isNavItemActive(item, pathname)} key={item.label} />
          ))}
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
            <button className="search-box" onClick={() => setPaletteOpen(true)}>
              <Search size={16} />
              <span>Search tasks...</span>
              <kbd>⌘ K</kbd>
            </button>
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
