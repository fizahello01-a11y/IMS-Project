// src/components/RCAForm/index.tsx
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { useState } from 'react'
import { RCACreateForm, ROOT_CAUSE_CATEGORIES } from '../../types'
import { incidentsApi } from '../../api'

const schema = z.object({
  incident_start:      z.date({ required_error: 'Start time is required' }),
  incident_end:        z.date({ required_error: 'End time is required' }),
  root_cause_category: z.string().min(1, 'Select a root cause category'),
  fix_applied:         z.string().min(10, 'Describe the fix (min 10 characters)'),
  prevention_steps:    z.string().min(10, 'Describe prevention steps (min 10 characters)'),
}).refine(d => d.incident_end > d.incident_start, {
  message: 'End time must be after start time',
  path: ['incident_end'],
})

const field = {
  label: (text: string, required = true) => (
    <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
      {text}{required && <span style={{ color: 'var(--p0)', marginLeft: 3 }}>*</span>}
    </label>
  ),
  error: (msg?: string) => msg ? (
    <p style={{ fontSize: 12, color: 'var(--p0)', marginTop: 4 }}>{msg}</p>
  ) : null,
}

interface Props {
  incidentId: string
  existingRca?: any
  onSuccess: () => void
}

export default function RCAForm({ incidentId, existingRca, onSuccess }: Props) {
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const { register, control, handleSubmit, formState: { errors } } = useForm<RCACreateForm>({
    resolver: zodResolver(schema),
    defaultValues: existingRca ? {
      incident_start:      new Date(existingRca.incident_start),
      incident_end:        new Date(existingRca.incident_end),
      root_cause_category: existingRca.root_cause_category,
      fix_applied:         existingRca.fix_applied,
      prevention_steps:    existingRca.prevention_steps,
    } : {},
  })

  const onSubmit = async (data: RCACreateForm) => {
    setSubmitting(true)
    setApiError(null)
    try {
      await incidentsApi.submitRCA(incidentId, data)
      setSuccess(true)
      setTimeout(onSuccess, 800)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      if (typeof detail === 'object' && detail?.errors) {
        setApiError(detail.errors.join('; '))
      } else {
        setApiError(typeof detail === 'string' ? detail : 'Submission failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (success) return (
    <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--resolved)' }}>
      <div style={{ fontSize: 32, marginBottom: 8 }}>✅</div>
      <div style={{ fontWeight: 500 }}>RCA submitted successfully</div>
    </div>
  )

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: -4 }}>Root Cause Analysis</h3>

      {/* Time range */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          {field.label('Incident Start')}
          <Controller name="incident_start" control={control} render={({ field: f }) => (
            <DatePicker
              selected={f.value}
              onChange={f.onChange}
              showTimeSelect
              dateFormat="yyyy-MM-dd HH:mm"
              placeholderText="Select start time"
              customInput={<input style={{ background: 'var(--bg3)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 12px', width: '100%' }} />}
            />
          )} />
          {field.error(errors.incident_start?.message)}
        </div>
        <div>
          {field.label('Incident End')}
          <Controller name="incident_end" control={control} render={({ field: f }) => (
            <DatePicker
              selected={f.value}
              onChange={f.onChange}
              showTimeSelect
              dateFormat="yyyy-MM-dd HH:mm"
              placeholderText="Select end time"
              customInput={<input style={{ background: 'var(--bg3)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 12px', width: '100%' }} />}
            />
          )} />
          {field.error(errors.incident_end?.message)}
        </div>
      </div>

      {/* Root cause category */}
      <div>
        {field.label('Root Cause Category')}
        <select {...register('root_cause_category')}>
          <option value="">— Select category —</option>
          {ROOT_CAUSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {field.error(errors.root_cause_category?.message)}
      </div>

      {/* Fix applied */}
      <div>
        {field.label('Fix Applied')}
        <textarea
          {...register('fix_applied')}
          rows={4}
          placeholder="Describe what was done to resolve the incident…"
          style={{ resize: 'vertical' }}
        />
        {field.error(errors.fix_applied?.message)}
      </div>

      {/* Prevention steps */}
      <div>
        {field.label('Prevention Steps')}
        <textarea
          {...register('prevention_steps')}
          rows={4}
          placeholder="What will be done to prevent this from happening again…"
          style={{ resize: 'vertical' }}
        />
        {field.error(errors.prevention_steps?.message)}
      </div>

      {/* API error */}
      {apiError && (
        <div style={{ background: 'rgba(255,123,114,0.1)', border: '1px solid rgba(255,123,114,0.3)', borderRadius: 8, padding: '12px 16px', color: 'var(--p0)', fontSize: 13 }}>
          ⚠ {apiError}
        </div>
      )}

      <button type="submit" className="btn btn-primary" disabled={submitting} style={{ alignSelf: 'flex-start' }}>
        {submitting ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 1.5 }} /> Submitting…</> : '💾 Submit RCA'}
      </button>
    </form>
  )
}
