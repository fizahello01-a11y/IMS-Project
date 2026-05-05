// src/components/Layout.tsx
import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from 'react-query'
import { healthApi } from '../api'

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { data: health } = useQuery('health', healthApi.get, { refetchInterval: 10_000 })
  const { data: metrics } = useQuery('metrics', healthApi.metrics, { refetchInterval: 5_000 })

  const isOk = health?.status === 'ok'

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: 220, background: 'var(--bg2)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', padding: '20px 0', flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ padding: '0 20px 24px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
            ⚡ IMS
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            Incident Management
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ padding: '16px 12px', flex: 1 }}>
          {[
            { to: '/', label: '📊 Dashboard', exact: true },
          ].map(({ to, label, exact }) => {
            const active = exact ? location.pathname === to : location.pathname.startsWith(to)
            return (
              <Link key={to} to={to} style={{
                display: 'block', padding: '8px 12px', borderRadius: 6,
                color: active ? 'var(--accent)' : 'var(--muted)',
                background: active ? 'rgba(88,166,255,0.1)' : 'transparent',
                marginBottom: 2, fontWeight: active ? 500 : 400,
                transition: 'all 0.1s',
              }}>{label}</Link>
            )
          })}
        </nav>

        {/* System status */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            System Status
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: isOk ? 'var(--resolved)' : 'var(--p0)',
              boxShadow: isOk ? '0 0 6px var(--resolved)' : '0 0 6px var(--p0)',
            }} className={isOk ? '' : 'pulse'} />
            <span style={{ fontSize: 12, color: 'var(--text)' }}>
              {isOk ? 'All systems operational' : 'Degraded'}
            </span>
          </div>
          {metrics && (
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              {(metrics.signals_per_sec || 0).toFixed(1)} signals/sec
            </div>
          )}
          <a href="http://localhost:8000/docs" target="_blank" style={{ fontSize: 11, color: 'var(--accent)', display: 'block', marginTop: 8 }}>
            API Docs →
          </a>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main style={{ flex: 1, overflow: 'auto' }}>
        {children}
      </main>
    </div>
  )
}
