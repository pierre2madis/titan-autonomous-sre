import { useEffect, useState } from 'react'

type Incident = {
  incident_id: string
  state: string
  severity: string
  correlation_key: string | null
  root_event_id: string | null
  updated_at: string | null
}

type IncidentList = {
  items: Incident[]
  mode: string
}

type RCA = {
  incident_id: string
  mode: string
  incident: Incident
  observed_facts: {
    declared_root_event_id: string | null
    root_event_found: boolean
    related_event_count_returned: number
    transition_count_returned: number
  }
  related_events: Array<{
    event_id: string
    source: string
    event_type: string
    host: string | null
    observed_at: string | null
  }>
  transitions: Array<{
    event_id: string
    transition_id: string
    topic: string
    received_at: string | null
  }>
  assessment: {
    classification: string
    confidence: string
    causality_verified: boolean
    limitations: string[]
  }
  limits: {
    events_truncated: boolean
    transitions_truncated: boolean
  }
}

export default function OperationalIncidents() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selected, setSelected] = useState('')
  const [rca, setRca] = useState<RCA | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const response = await fetch('/api/v1/incidents?limit=20', {
          signal: controller.signal,
        })

        if (!response.ok) throw new Error(`Incident API HTTP ${response.status}`)

        const result: IncidentList = await response.json()
        if (result.mode !== 'READ_ONLY' || !Array.isArray(result.items)) {
          throw new Error('Unexpected operational incident contract')
        }

        setIncidents(result.items)
        if (result.items.length > 0) {
          setSelected(result.items[0].incident_id)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : String(err))
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    void load()
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!selected) return

    const controller = new AbortController()
    setRca(null)
    setError('')

    async function loadRca() {
      try {
        const response = await fetch(
          `/api/v1/incidents/${encodeURIComponent(selected)}/rca?limit=25`,
          { signal: controller.signal }
        )

        if (!response.ok) throw new Error(`RCA API HTTP ${response.status}`)

        const result: RCA = await response.json()

        if (
          result.mode !== 'READ_ONLY' ||
          result.incident_id !== selected ||
          result.assessment?.causality_verified !== false
        ) {
          throw new Error('Unexpected operational RCA contract')
        }

        setRca(result)
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : String(err))
        }
      }
    }

    void loadRca()
    return () => controller.abort()
  }, [selected])

  return (
    <section className="panel" style={{ marginTop: 20 }}>
      <div className="panel-header">
        <h2>Operational Incident Lifecycle</h2>
        <span>POSTGRESQL · READ ONLY</span>
      </div>

      <div className="details">
        {loading && <p>Loading operational incidents...</p>}
        {error && <p className="error" role="alert">{error}</p>}

        {!loading && !error && incidents.length === 0 && (
          <p>No operational incidents available.</p>
        )}

        {incidents.length > 0 && (
          <>
            <label htmlFor="titan-operational-incident">
              Incident
            </label>
            <select
              id="titan-operational-incident"
              value={selected}
              onChange={event => setSelected(event.target.value)}
              style={{ marginLeft: 12, maxWidth: '100%' }}
            >
              {incidents.map(incident => (
                <option key={incident.incident_id} value={incident.incident_id}>
                  {incident.incident_id} — {incident.state}
                </option>
              ))}
            </select>
          </>
        )}

        {selected && !rca && !error && <p>Loading RCA evidence...</p>}

        {rca && (
          <>
            <h3>{rca.incident_id}</h3>
            <span className="state">{rca.incident.state}</span>

            <dl>
              <dt>Severity</dt>
              <dd>{rca.incident.severity}</dd>

              <dt>Correlation key</dt>
              <dd>{rca.incident.correlation_key || 'Not available'}</dd>

              <dt>Declared root event</dt>
              <dd>{rca.observed_facts.declared_root_event_id || 'None'}</dd>

              <dt>Root event found</dt>
              <dd>{rca.observed_facts.root_event_found ? 'Yes' : 'No'}</dd>

              <dt>Related events returned</dt>
              <dd>{rca.observed_facts.related_event_count_returned}</dd>

              <dt>Transitions returned</dt>
              <dd>{rca.observed_facts.transition_count_returned}</dd>

              <dt>RCA classification</dt>
              <dd>{rca.assessment.classification}</dd>

              <dt>Confidence</dt>
              <dd>{rca.assessment.confidence}</dd>

              <dt>Causality verified</dt>
              <dd>{rca.assessment.causality_verified ? 'Yes' : 'No'}</dd>
            </dl>

            <h3>Transition Timeline</h3>
            {rca.transitions.length === 0 ? (
              <p>No persisted transitions returned.</p>
            ) : (
              <ul>
                {rca.transitions.map((transition, index) => (
                  <li key={`${transition.event_id}-${index}`}>
                    {transition.received_at || 'Unknown time'} —{' '}
                    {transition.transition_id} ({transition.topic})
                  </li>
                ))}
              </ul>
            )}

            <h3>Related Evidence</h3>
            {rca.related_events.length === 0 ? (
              <p>No events matched the incident correlation key.</p>
            ) : (
              <ul>
                {rca.related_events.map(event => (
                  <li key={event.event_id}>
                    {event.event_id} — {event.source} / {event.event_type}
                  </li>
                ))}
              </ul>
            )}

            {(rca.limits.events_truncated ||
              rca.limits.transitions_truncated) && (
              <p>Evidence results are truncated by the API limit.</p>
            )}

            <h3>Evidence Limitations</h3>
            <ul>
              {rca.assessment.limitations.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
