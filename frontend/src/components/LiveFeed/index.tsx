// src/components/LiveFeed/index.tsx
import { useQuery } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { incidentsApi } from '../../api'
import { Incident, Priority, IncidentStatus } from '../../types'

const priorityOrder: Record<Priority, number> = { P0: 0, P1: 1, P2: 2, P3: 3 }

function PriorityBadge({ p }: { p: Priority }) {
  return <span className={`badge badge-${p.toLowerCase()}`}>{p}</span>
}

function StatusDot({ s }: { s: IncidentStatus }) {
  const map: Record<IncidentStatus, string> = {
    OPEN:          'var(--open)',
    INVESTIGATING: 'var(--invest)',
    RESOLVED:      'var(--resolved)',
    CLOSED:        'var(--closed)',
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: map[s], flexShrink: 0 }} />
      <span style={{ fontSize: 12, color: 'var(--muted)' }}>{s}</span>
    </div>
  )
}

export default function LiveFeed() {
  const { data: incidents = [], isLoading, error, isFetching } = useQuery(
    'incidents',
    () => incidentsApi.list(),
    { refetchInterval: 5_000 }
  )
  const navigate = useNavigate()

  const sorted = [...incidents].sort(
    (a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]
  )

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 32, color: 'var(--muted)' }}>
      <div className="spinner" /> Loading incidents…
    </div>
  )

  if (error) return (
    <div style={{ padding: 32, color: 'var(--p0)' }}>
      ⚠ Could not connect to backend. Is it running?
    </div>
  )

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Active Incidents</h2>
          {isFetching && <div className="spinner" style={{ width: 14, height: 14, borderWidth: 1.5 }} />}
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          {sorted.length} total · auto-refreshes every 5s
        </div>
      </div>

      {sorted.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--muted)' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>✅</div>
          <div>No incidents. All systems nominal.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sorted.map((inc) => (
            <IncidentRow key={inc.id} incident={inc} onClick={() => navigate(`/incidents/${inc.id}`)} />
          ))}
        </div>
      )}
    </div>
  )
}

function IncidentRow({ incident: inc, onClick }: { incident: Incident; onClick: () => void }) {
  const age = formatDistanceToNow(new Date(inc.created_at), { addSuffix: true })

  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--bg2)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${inc.priority === 'P0' ? 'var(--p0)' : inc.priority === 'P1' ? 'var(--p1)' : inc.priority === 'P2' ? 'var(--p2)' : 'var(--p3)'}`,
        borderRadius: 'var(--radius-lg)',
        padding: '14px 18px',
        cursor: 'pointer',
        display: 'grid',
        gridTemplateColumns: '80px 1fr auto',
        gap: 16,
        alignItems: 'center',
        transition: 'background 0.1s, border-color 0.1s',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg3)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg2)')}
    >
      <PriorityBadge p={inc.priority} />

      <div>
        <div style={{ fontWeight: 500, marginBottom: 4, fontSize: 14 }}>{inc.title}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12, color: 'var(--muted)' }}>
          <StatusDot s={inc.status} />
          <span>🖥 {inc.component_id}</span>
          <span>📡 {inc.signal_count} signals</span>
          <span>🕐 {age}</span>
        </div>
      </div>

      <div style={{ color: 'var(--muted)', fontSize: 18 }}>›</div>
    </div>
  )
}
