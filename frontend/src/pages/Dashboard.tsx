// src/pages/Dashboard.tsx
import { useQuery } from 'react-query'
import LiveFeed from '../components/LiveFeed'
import { healthApi, incidentsApi } from '../api'

function MetricCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {label}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: incidents = [] } = useQuery('incidents', incidentsApi.list, { refetchInterval: 5_000 })
  const { data: metrics } = useQuery('metrics', healthApi.metrics, { refetchInterval: 5_000 })

  const open        = incidents.filter(i => i.status !== 'CLOSED').length
  const p0          = incidents.filter(i => i.priority === 'P0' && i.status !== 'CLOSED').length
  const investigating = incidents.filter(i => i.status === 'INVESTIGATING').length
  const rate        = (metrics?.signals_per_sec || 0).toFixed(1)

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Incident Dashboard</h1>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Real-time view of all active incidents. Click any row to investigate.
        </p>
      </div>

      {/* Metrics row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        <MetricCard label="Active Incidents" value={open} color={open > 0 ? 'var(--p1)' : 'var(--resolved)'} />
        <MetricCard label="P0 Critical"      value={p0}  color={p0  > 0 ? 'var(--p0)' : 'var(--resolved)'} />
        <MetricCard label="Investigating"    value={investigating} />
        <MetricCard label="Signals / sec"    value={rate} color="var(--accent)" />
      </div>

      {/* Live feed */}
      <LiveFeed />
    </div>
  )
}
