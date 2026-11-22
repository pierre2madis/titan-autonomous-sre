import { useEffect, useState } from 'react'

type Classification =
  | 'HEALTHY'
  | 'EXPECTED_DOWN'
  | 'UNEXPECTED_DOWN'
  | 'UNKNOWN'

interface SplunkEvidence {
  mode: string
  source: string
  event_id: string
  observed_at: string
  evaluated_at: string
  age_seconds: number
  max_age_seconds: number
  fresh: boolean
  observed_classification: Classification
  classification: Classification
  incident_candidate: boolean
  evidence: {
    contract_version: string
    complete: boolean
    recognized: boolean
    expected_peer_count?: number
    observed_peer_count?: number
    missing_peers?: string[]
  }
  limitations: string[]
}

const endpoint = '/api/v1/splunk/cluster/evidence'

function statusColor(status: Classification): string {
  switch (status) {
    case 'HEALTHY':
      return '#22c55e'
    case 'EXPECTED_DOWN':
      return '#f59e0b'
    case 'UNEXPECTED_DOWN':
      return '#ef4444'
    default:
      return '#94a3b8'
  }
}

export default function SplunkClusterHealth() {
  const [data, setData] = useState<SplunkEvidence | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    async function loadEvidence() {
      try {
        const response = await fetch(endpoint, {
          signal: controller.signal,
          cache: 'no-store',
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const result = await response.json() as SplunkEvidence

        if (
          typeof result.fresh !== 'boolean' ||
          ![
            'HEALTHY',
            'EXPECTED_DOWN',
            'UNEXPECTED_DOWN',
            'UNKNOWN',
          ].includes(result.classification)
        ) {
          throw new Error('Invalid Splunk evidence response')
        }

        if (!controller.signal.aborted) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setData(null)
          setError(String(err))
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadEvidence()

    return () => controller.abort()
  }, [])

  const effectiveStatus: Classification =
    data && data.fresh ? data.classification : 'UNKNOWN'

  return (
    <section className="panel" style={{ marginBottom: 20 }}>
      <div className="panel-header">
        <h2>Splunk Cluster Health</h2>
        <span>READ-ONLY · SNAPSHOT</span>
      </div>

      {loading && <p>Loading Splunk evidence...</p>}

      {error && (
        <div className="error" role="alert">
          Splunk evidence unavailable: {error}
        </div>
      )}

      {!loading && !data && !error && (
        <p className="empty">No Splunk evidence available.</p>
      )}

      {data && (
        <div className="details">
          <h3 style={{ color: statusColor(effectiveStatus) }}>
            {effectiveStatus}
          </h3>

          <dl>
            <dt>Source</dt>
            <dd>{data.source}</dd>

            <dt>Observed classification</dt>
            <dd>{data.observed_classification}</dd>

            <dt>Effective classification</dt>
            <dd>{effectiveStatus}</dd>

            <dt>Evidence freshness</dt>
            <dd>{data.fresh ? 'FRESH' : 'STALE / INVALID'}</dd>

            <dt>Evidence age</dt>
            <dd>
              {Number.isFinite(data.age_seconds)
                ? `${data.age_seconds.toFixed(1)} seconds`
                : 'Unavailable'}
            </dd>

            <dt>Expected peers</dt>
            <dd>{data.evidence.expected_peer_count ?? 'Unknown'}</dd>

            <dt>Observed peers</dt>
            <dd>{data.evidence.observed_peer_count ?? 'Unknown'}</dd>

            <dt>Missing peers</dt>
            <dd>
              {data.evidence.missing_peers?.join(', ') || 'None reported'}
            </dd>

            <dt>Incident candidate</dt>
            <dd>
              {data.fresh && data.incident_candidate
                ? 'YES'
                : 'NO'}
            </dd>

            <dt>Observed at</dt>
            <dd>{data.observed_at}</dd>

            <dt>Event ID</dt>
            <dd>{data.event_id}</dd>
          </dl>

          {!data.fresh && (
            <p role="status" style={{ color: '#f59e0b' }}>
              Historical evidence only. Current cluster health is unknown.
            </p>
          )}

          <small>
            Snapshot-based monitoring. No live Splunk query or
            remediation is performed by this component.
          </small>
        </div>
      )}
    </section>
  )
}
