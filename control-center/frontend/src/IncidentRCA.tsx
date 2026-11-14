import { useEffect, useState } from 'react'
import { titanAPI } from './api/client'
import type { IncidentRCAResponse } from './api/types'

export default function IncidentRCA({ incidentId }: { incidentId: string }) {
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
    <section className="panel" style={{ marginTop: 20 }} aria-label="Incident RCA">
      <div className="panel-header"><h2>Incident RCA</h2><span>Observed evidence · read-only</span></div>
      <div className="details">
        {error && <p className="error" role="alert">{error}</p>}
        {!data && !error && <p className="empty">Loading RCA evidence...</p>}
        {data && <>
          <h3>Assessment</h3>
          <p><strong>{data.assessment.classification}</strong> · Confidence: {data.assessment.confidence}</p>
          <p>Causality verified: {data.assessment.causality_verified ? 'Yes' : 'No'}</p>
          <h3>Observed facts</h3>
          <dl>
            <dt>Declared root event</dt><dd>{data.observed_facts.declared_root_event_id || 'None'}</dd>
            <dt>Root event record found</dt><dd>{data.observed_facts.root_event_found ? 'Yes' : 'No'}</dd>
            <dt>Related events returned</dt><dd>{data.observed_facts.related_event_count_returned}</dd>
            <dt>Transitions returned</dt><dd>{data.observed_facts.transition_count_returned}</dd>
          </dl>
          {data.root_event && <p>Referenced event: {data.root_event.event_id} · {data.root_event.source} · {data.root_event.event_type}</p>}
          <h3>Related events (correlation only)</h3>
          {data.related_events.length === 0 && <p className="empty">No related events found.</p>}
          {data.related_events.map(e => <div className="timeline-item" key={e.event_id}>
            <strong>{e.event_id}</strong><span>{e.source} · {e.event_type} · {e.host ?? 'unknown host'}</span>
            <small>{e.observed_at ?? 'No observation timestamp'}</small>
          </div>)}
          {data.limits.events_truncated && <p>Event results truncated.</p>}
          <h3>Transitions</h3>
          {data.transitions.length === 0 && <p className="empty">No transitions found.</p>}
          {data.transitions.map(t => <div className="timeline-item" key={t.event_id}>
            <strong>{t.transition_id}</strong><span>{t.received_at}</span>
          </div>)}
          {data.limits.transitions_truncated && <p>Transition results truncated.</p>}
          <h3>Evidence limitations</h3>
          <ul>{data.assessment.limitations.map(s => <li key={s}>{s}</li>)}</ul>
        </>}
      </div>
    </section>
  )
}
