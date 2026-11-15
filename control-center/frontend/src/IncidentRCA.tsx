import { useEffect, useState } from 'react'
import { titanAPI } from './api/client'
import EvidenceProvenance from './EvidenceProvenance'
import type { IncidentRCAResponse } from './api/types'
import { useLanguage } from './i18n/LanguageContext'


function chronologicalTransitions<T extends {
  received_at: string | null
  event_id: string
  transition_id: string
}>(items: T[]): T[] {
  const timestamp = (value: string | null): number => {
    if (!value) return Number.POSITIVE_INFINITY
    const parsed = Date.parse(value)
    return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY
  }

  return [...items].sort((a, b) => {
    const timeA = timestamp(a.received_at)
    const timeB = timestamp(b.received_at)

    if (timeA !== timeB) {
      if (timeA === Number.POSITIVE_INFINITY) return 1
      if (timeB === Number.POSITIVE_INFINITY) return -1
      return timeA - timeB
    }

    return (
      a.transition_id.localeCompare(b.transition_id) ||
      a.event_id.localeCompare(b.event_id)
    )
  })
}

export default function IncidentRCA({ incidentId }: { incidentId: string }) {
  const { t, displayValue, locale } = useLanguage()
  const [data, setData] = useState<IncidentRCAResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    setData(null)
    setError(null)
    titanAPI.rca(incidentId)
      .then(result => { if (active) setData(result) })
      .catch(err => { if (active) setError(String(err)) })
    return () => { active = false }
  }, [incidentId])
  return (
    <section className="panel" style={{ marginTop: 20 }} aria-label={t('Incident RCA')}>
      <div className="panel-header"><h2>{t('Incident RCA')}</h2><span>{t('Observed evidence · read-only')}</span></div>
      <div className="details">
        {error && <p className="error" role="alert">{error}</p>}
        {!data && !error && <p className="empty">{t('Loading RCA evidence...')}</p>}
        {data && <>
          <h3>{t('Assessment')}</h3>
          <p><strong>{displayValue(data.assessment.classification)}</strong> · {t('Confidence')}: {displayValue(data.assessment.confidence)}</p>
          <p>{t('Causality verified')}: {t(data.assessment.causality_verified ? 'Yes' : 'No')}</p>
          <h3>{t('Observed facts')}</h3>
          <dl>
            <dt>{t('Declared root event')}</dt><dd>{data.observed_facts.declared_root_event_id || t('No')}</dd>
            <dt>{t('Root event record found')}</dt><dd>{t(data.observed_facts.root_event_found ? 'Yes' : 'No')}</dd>
            <dt>{t('Related events returned')}</dt><dd>{data.observed_facts.related_event_count_returned}</dd>
            <dt>{t('Transitions returned')}</dt><dd>{data.observed_facts.transition_count_returned}</dd>
          </dl>
          {data.root_event && <p>{t('Referenced event')}: {data.root_event.event_id} · {data.root_event.source} · {data.root_event.event_type}</p>}
          <h3>{t('Related events (correlation only)')}</h3>
          {data.related_events.length === 0 && <p className="empty">{t('No related events found.')}</p>}
          {data.related_events.map(e => <div className="timeline-item" key={e.event_id}>
            <strong>{e.event_id}</strong><span>{e.source} · {e.event_type} · {e.host ?? t('unknown host')}</span>
            <small>{e.observed_at ?? t('No observation timestamp')}</small>
          </div>)}
          {data.limits.events_truncated && <p>{t('Event results truncated.')}</p>}
          <h3>{t('Transitions')}</h3>
          {data.transitions.length === 0 && <p className="empty">{t('No transitions found.')}</p>}
          {chronologicalTransitions(data.transitions).map(tr => <div className="timeline-item" key={tr.event_id}>
            <strong>{tr.transition_id}</strong><span>{tr.received_at ? new Date(tr.received_at).toLocaleString(locale) : '—'}</span>
          </div>)}
          {data.limits.transitions_truncated && <p>{t('Transition results truncated.')}</p>}
          <EvidenceProvenance data={data} />
          <h3>{t('Evidence limitations')}</h3>
          <ul>{data.assessment.limitations.map(s => <li key={s}>{t(s)}</li>)}</ul>
        </>}
      </div>
    </section>
  )
}
