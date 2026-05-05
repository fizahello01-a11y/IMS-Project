// src/pages/IncidentPage.tsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { formatDistanceToNow, format } from 'date-fns'
import { incidentsApi } from '../api'
import RCAForm from '../components/RCAForm'
import { IncidentStatus, STATUS_FLOW } from '../types'

const STATUS_COLORS: Record<IncidentStatus, string> = {
  OPEN:          'var(--open)',
  INVESTIGATING: 'var(--invest)',
  RESOLVED:      'var(--resolved)',
  CLOSED:        'var(--closed)',
}

const STATUS_LABEL: Record<IncidentStatus, string> = {
  OPEN:          '🔴 Open',
  INVESTIGATING: '🟣 Investigating',
  RESOLVED:      '🟢 Resolved',
  CLOSED:        '⚫ Closed',
}

export default function IncidentPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showRCAForm, setShowRCAForm] = useState(false)
  const [transitionError, setTransitionError] = useState<string | null>(null)

  const { data: incident, isLoading } = useQuery(
    ['incident', id],
    () => incidentsApi.get(id!),
    { refetchInterval: 5_000 }
  )

  const { data: signalsData } = useQuery(
    ['signals', id],
    () => incidentsApi.getRawSignals(id!),
    { refetchInterval: 10_000 }
  )

  const transitionMutation = useMutation(
    (status: IncidentStatus) => incidentsApi.transitionStatus(id!, status),
    {
      onSuccess: () => {
        qc.invalidateQueries(['incident', id])
        qc.invalidateQueries('incidents')
        setTransitionError(null)
      },
      onError: (e: any) => {
        const detail = e?.response?.data?.detail
        if (typeof detail === 'object' && detail?.message) {
          setTransitionError(detail.message + ': ' + (detail.errors || []).join(', '))
        } else {
          setTransitionError(typeof detail === 'string' ? detail : 'Transition failed')
        }
      },
    }
  )

  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 40, color: 'var(--muted)' }}>
      <div className="spinner" /> Loading incident…
    </div>
  )

  if (!incident) return (
    <div style={{ padding: 40 }}>
      <div style={{ color: 'var(--p0)', marginBottom: 12 }}>Incident not found.</div>
      <button className="btn btn-ghost" onClick={() => navigate('/')}>← Back to Dashboard</button>
    </div>
  )

  const nextStatus = STATUS_FLOW[incident.status as IncidentStatus]
  const signals = signalsData?.signals || []

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Back */}
      <button className="btn btn-ghost" onClick={() => navigate('/')} style={{ marginBottom: 20, fontSize: 13 }}>
        ← Back to Dashboard
      </button>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 12 }}>
          <span className={`badge badge-${incident.priority.toLowerCase()}`} style={{ fontSize: 13, padding: '4px 12px' }}>
            {incident.priority}
          </span>
          <span style={{ color: STATUS_COLORS[incident.status as IncidentStatus], fontWeight: 500 }}>
            {STATUS_LABEL[incident.status as IncidentStatus]}
          </span>
        </div>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, lineHeight: 1.3 }}>
          {incident.title}
        </h1>
        <div style={{ display: 'flex', gap: 20, fontSize: 13, color: 'var(--muted)', flexWrap: 'wrap' }}>
          <span>🖥 <strong style={{ color: 'var(--text)' }}>{incident.component_id}</strong></span>
          <span>🏷 {incident.component_type}</span>
          <span>📡 {incident.signal_count} signals</span>
          <span>⏱ Created {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}</span>
          {incident.mttr_minutes && <span>🔧 MTTR: <strong style={{ color: 'var(--resolved)' }}>{incident.mttr_minutes}m</strong></span>}
        </div>
      </div>

      {/* Status transition */}
      {incident.status !== 'CLOSED' && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 12, color: 'var(--muted)' }}>
            STATUS TRANSITION
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            {(['OPEN','INVESTIGATING','RESOLVED','CLOSED'] as IncidentStatus[]).map((s, i) => (
              <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {i > 0 && <span style={{ color: 'var(--border)' }}>→</span>}
                <span style={{
                  padding: '4px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                  background: incident.status === s ? `${STATUS_COLORS[s]}20` : 'var(--bg3)',
                  color: incident.status === s ? STATUS_COLORS[s] : 'var(--muted)',
                  border: incident.status === s ? `1px solid ${STATUS_COLORS[s]}` : '1px solid var(--border)',
                }}>
                  {s}
                </span>
              </div>
            ))}
          </div>

          {nextStatus && (
            <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                className="btn btn-primary"
                onClick={() => transitionMutation.mutate(nextStatus)}
                disabled={transitionMutation.isLoading}
              >
                {transitionMutation.isLoading
                  ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 1.5 }} /> Moving…</>
                  : `→ Move to ${nextStatus}`
                }
              </button>
              {nextStatus === 'CLOSED' && !incident.rca && (
                <span style={{ fontSize: 12, color: 'var(--p2)' }}>⚠ RCA required before closing</span>
              )}
            </div>
          )}

          {transitionError && (
            <div style={{ marginTop: 12, background: 'rgba(255,123,114,0.1)', border: '1px solid rgba(255,123,114,0.3)', borderRadius: 8, padding: '10px 14px', color: 'var(--p0)', fontSize: 13 }}>
              ⚠ {transitionError}
            </div>
          )}
        </div>
      )}

      {/* Two column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Raw signals */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 12, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
            RAW SIGNALS (from MongoDB)
            <span style={{ background: 'var(--bg3)', padding: '1px 8px', borderRadius: 999, fontSize: 11 }}>
              {signals.length}
            </span>
          </div>
          <div style={{ maxHeight: 320, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {signals.length === 0 ? (
              <div style={{ color: 'var(--muted)', fontSize: 13, padding: '8px 0' }}>No signals yet</div>
            ) : signals.map((sig, i) => (
              <div key={i} style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span className="mono" style={{ color: 'var(--p1)', fontWeight: 500 }}>{sig.error_code}</span>
                  <span style={{ color: 'var(--muted)' }}>
                    {sig.received_at ? format(new Date(sig.received_at), 'HH:mm:ss') : ''}
                  </span>
                </div>
                {sig.message && <div style={{ color: 'var(--muted)' }}>{sig.message}</div>}
              </div>
            ))}
          </div>
        </div>

        {/* RCA section */}
        <div className="card">
          {incident.rca && !showRCAForm ? (
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 16, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                ROOT CAUSE ANALYSIS
                {incident.status !== 'CLOSED' && (
                  <button className="btn btn-ghost" onClick={() => setShowRCAForm(true)} style={{ fontSize: 11 }}>
                    Edit
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  { label: 'Category',           value: incident.rca.root_cause_category },
                  { label: 'Fix Applied',         value: incident.rca.fix_applied },
                  { label: 'Prevention Steps',    value: incident.rca.prevention_steps },
                  { label: 'Duration',            value: `${format(new Date(incident.rca.incident_start), 'MMM d HH:mm')} → ${format(new Date(incident.rca.incident_end), 'MMM d HH:mm')}` },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div>
              {!showRCAForm && incident.status !== 'CLOSED' && (
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>📋</div>
                  <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 16 }}>No RCA submitted yet</div>
                  <button className="btn btn-primary" onClick={() => setShowRCAForm(true)}>
                    + Submit RCA
                  </button>
                </div>
              )}
              {showRCAForm && (
                <RCAForm
                  incidentId={id!}
                  existingRca={incident.rca}
                  onSuccess={() => {
                    setShowRCAForm(false)
                    qc.invalidateQueries(['incident', id])
                  }}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
