import { useEffect, useState } from 'react'

interface LifecycleResponse {
  mode: string
  incident_id: string
  event: {
    event_type: string
    incident_id: string
    correlation_key: string
    correlated_events: number
    root_event_id: string
    lifecycle_state: string
    rca_classification: string
    causality_verified: boolean
    delivery_mode: string
  }
  assessment: {
    causality_verified: boolean
    classification: string
    limitations: string[]
  }
}

const DEMO_INCIDENT_ID = 'INC-4BD65636F6FDB7A3'

export default function IncidentLifecycle() {
  const [data, setData] = useState<LifecycleResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const response = await fetch(
          `/api/v1/incidents/${encodeURIComponent(DEMO_INCIDENT_ID)}/lifecycle`,
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(
            response.status === 404
              ? 'Offline incident not found'
              : `Lifecycle API unavailable (HTTP ${response.status})`
          )
        }

        const result: LifecycleResponse = await response.json()

        if (
          result.incident_id !== DEMO_INCIDENT_ID ||
          result.mode !== 'OFFLINE_READ_ONLY' ||
          result.event?.event_type !== 'INCIDENT_CREATED' ||
          result.event?.causality_verified !== false ||
          result.assessment?.causality_verified !== false
        ) {
          throw new Error('Unexpected lifecycle contract')
        }

        setData(result)
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

  return (
    <section
      className="panel"
      style={{ marginTop: 20 }}
      aria-label="Offline Incident Lifecycle"
    >
      <div className="panel-header">
        <h2>Offline Incident Lifecycle</h2>
        <span>DEMO · READ ONLY</span>
      </div>

      <div className="details">
        {loading && <p className="empty">Loading offline incident...</p>}

        {error && <p className="error" role="alert">{error}</p>}

        {data && (
          <>
            <h3>{data.incident_id}</h3>
            <span className="state">{data.event.lifecycle_state}</span>

            <dl>
              <dt>Event type</dt>
              <dd>{data.event.event_type}</dd>

              <dt>Correlation key</dt>
              <dd>{data.event.correlation_key}</dd>

              <dt>Correlated events</dt>
              <dd>{data.event.correlated_events}</dd>

              <dt>Declared root event</dt>
              <dd>{data.event.root_event_id}</dd>

              <dt>RCA classification</dt>
              <dd>{data.assessment.classification}</dd>

              <dt>Causality verified</dt>
              <dd>{data.assessment.causality_verified ? 'Yes' : 'No'}</dd>

              <dt>Delivery mode</dt>
              <dd>{data.event.delivery_mode}</dd>
            </dl>

            <h3>Evidence limitations</h3>
            <ul>
              {data.assessment.limitations.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  )
}
