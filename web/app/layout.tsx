import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { DashboardShell } from '@/components/shell/DashboardShell'
import { Providers } from './providers'
import './globals.css'

export const metadata: Metadata = {
  title: 'Tasko — Taskiq fleet monitoring',
  description: 'A self-hosted dashboard for Taskiq workers, queues, throughput, and task health.',
  icons: {
    // One mark, not a light/dark pair — the dashboard itself has no light
    // theme (globals.css is dark-only), and the icon's own dark background
    // reads fine in either browser chrome anyway.
    icon: [
      { url: '/icon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0b1014',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-background">
      <body className="antialiased">
        <Providers>
          <DashboardShell>{children}</DashboardShell>
        </Providers>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
