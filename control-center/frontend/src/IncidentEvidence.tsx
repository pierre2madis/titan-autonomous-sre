import { useEffect, useState } from 'react'

interface Artifact {
  role: string
  sha256: string
  size_bytes: number
  verification_status: string
}

interface IncidentEvidenceResponse {
  mode: string
  incident_id: string
  verification_status: string
  review_only: boolean
  causality_verified: boolean
  remediation_allowed: boolean
  correlation: {
    correlation_key: string
    declared_event_count: number
    individual_event_records_available: boolean
    root_event_id: string
    root_event_policy: string
    independent_corroboration: boolean
  }
  artifacts: Artifact[]
  limitations: string[]
}

export default function IncidentEvidence({
  incidentId
}: {
  incidentId: string
}) {
  const [data, setData] =
    useState<IncidentEvidenceResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    setData(null)
    setError(null)
    setLoading(true)

    async function load() {
      try {
        const response = await fetch(
          `/api/v1/incidents/${encodeURIComponent(incidentId)}/evidence`,
          {
            method: 'GET',
            signal: controller.signal,
            headers: { Accept: 'application/json' }
          }
        )

        if (!response.ok) {
          throw new Error(`Evidence API HTTP ${response.status}`)
        }

        const result: IncidentEvidenceResponse =
          await response.json()

        if (
          result.incident_id !== incidentId ||
          result.mode !== 'OFFLINE_READ_ONLY' ||
          result.review_only !== true ||
          result.causality_verified !== false ||
          result.remediation_allowed !== false ||
          !Array.isArray(result.artifacts) ||
          !Array.isArray(result.limitations) ||
          !result.correlation
        ) {
          throw new Error('Unexpected evidence API contract')
        }

        if (!controller.signal.aborted) {
          setData(result)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : String(err)
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => controller.abort()
  }, [incidentId])

  return (
    <section
      className="panel"
      style={{ marginTop: 20 }}
      aria-label="Incident Evidence"
    >
      <div className="panel-header">
        <h2>Incident Evidence</h2>
        <span>OFFLINE · READ ONLY</span>
      </div>

      <div className="details">
        <h3>{incidentId}</h3>

        {loading && <p role="status">Loading evidence...</p>}
        {error && <p className="error" role="alert">{error}</p>}

        {data && (
          <>
            <dl>
              <dt>Verification status</dt>
              <dd>{data.verification_status}</dd>

              <dt>Mode</dt>
              <dd>{data.mode}</dd>

              <dt>Correlation key</dt>
              <dd>{data.correlation.correlation_key}</dd>

              <dt>Declared correlated events</dt>
              <dd>{data.correlation.declared_event_count}</dd>

              <dt>Individual event records available</dt>
              <dd>
                {data.correlation.individual_event_records_available
                  ? 'Yes' : 'No'}
              </dd>

              <dt>Declared root event</dt>
              <dd>{data.correlation.root_event_id}</dd>

              <dt>Root event policy</dt>
              <dd>{data.correlation.root_event_policy}</dd>

              <dt>Independent corroboration</dt>
              <dd>
                {data.correlation.independent_corroboration
                  ? 'Yes' : 'No'}
              </dd>

              <dt>Causality verified</dt>
              <dd>No</dd>

              <dt>Remediation</dt>
              <dd>DISABLED</dd>
            </dl>

            <h3>Evidence artifacts ({data.artifacts.length})</h3>

            {data.artifacts.map((artifact, index) => (
              <div
                className="timeline-item"
                key={`${artifact.role}-${index}`}
              >
                <strong>{artifact.role}</strong>
                <p>Status: {artifact.verification_status}</p>
                <p>Size: {artifact.size_bytes} bytes</p>
                <p style={{ overflowWrap: 'anywhere' }}>
                  SHA-256: <code>{artifact.sha256}</code>
                </p>
              </div>
            ))}

            <h3>Evidence limitations</h3>
            <ul>
              {data.limitations.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>

            <p role="status">
              Offline evidence is for review only.
              It does not establish verified causality
              or authorize remediation.
            </p>
          </>
        )}
      </div>
    </section>
  )
}
