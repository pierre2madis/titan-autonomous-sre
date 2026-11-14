import PipelineCorrelation from "./PipelineCorrelation";
import WorkerHealth from "./WorkerHealth";
import CorePipeline from "./CorePipeline";
import PlatformHealth from './PlatformHealth'
import { useEffect, useState } from 'react'
import { titanAPI } from './api/client'
import type { Incident, Timeline } from './api/types'
import './App.css'

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selected, setSelected] = useState<Incident | null>(null)
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    titanAPI.incidents()
      .then(data => {
        setIncidents(data.items)
        if (data.items.length > 0) {
          setSelected(data.items[0])
        }
      })
      .catch(err => setError(String(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selected) return

    setTimeline(null)

    titanAPI.timeline(selected.incident_id)
      .then(setTimeline)
      .catch(err => setError(String(err)))
  }, [selected])

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">◆</span>
          <div>
            <strong>TITAN</strong>
            <small>CONTROL CENTER</small>
          </div>
        </div>

        <nav>
          <div className="nav-active">◉ Overview</div>
          <div>▤ Incidents</div>
          <div>◇ Evidence Explorer</div>
          <div>▣ Platform Health</div>
          <div>⚙ Automation</div>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          READ-ONLY MODE
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>Operations Overview</h1>
            <p>TITAN Autonomous SRE Platform</p>
          </div>
          <span className="environment">LAB · V0.1</span>
        </header>

        <section className="metrics">
          <div className="metric-card">
            <span>Total incidents</span>
            <strong>{incidents.length}</strong>
            <small>Current API page</small>
          </div>

          <div className="metric-card">
            <span>Active incidents</span>
            <strong>
              {incidents.filter(i =>
                !['RESOLVED', 'CLOSED'].includes(i.state)
              ).length}
            </strong>
            <small>Unresolved in current page</small>
          </div>

          <div className="metric-card">
            <span>Platform mode</span>
            <strong className="mode">OBSERVE</strong>
            <small>No remediation controls</small>
          </div>
        </section>

        {loading && <p>Loading incidents...</p>}
        {error && <div className="error">{error}</div>}

        <section className="workspace">
          <div className="panel">
            <div className="panel-header">
              <h2>Incidents</h2>
              <span>{incidents.length} loaded</span>
            </div>

            {incidents.map(incident => (
              <button
                key={incident.incident_id}
                className={
                  'incident-row ' +
                  (selected?.incident_id === incident.incident_id
                    ? 'selected' : '')
                }
                onClick={() => {
                  setSelected(incident)
                  setError(null)
                }}
              >
                <strong>{incident.incident_id}</strong>
                <span>{incident.correlation_key}</span>
                <span className="state">{incident.state}</span>
              </button>
            ))}

            {!loading && incidents.length === 0 && (
              <p className="empty">No incidents found.</p>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Incident Investigation</h2>
              <span>PostgreSQL + Kafka Inbox</span>
            </div>

            {selected ? (
              <div className="details">
                <h3>{selected.incident_id}</h3>
                <span className="state">{selected.state}</span>

                <dl>
                  <dt>Severity</dt>
                  <dd>{selected.severity}</dd>
                  <dt>Root event</dt>
                  <dd>{selected.root_event_id}</dd>
                  <dt>Opened</dt>
                  <dd>{formatDate(selected.opened_at)}</dd>
                  <dt>Updated</dt>
                  <dd>{formatDate(selected.updated_at)}</dd>
                </dl>

                <h3>Transition Timeline</h3>

                {timeline?.items.map(item => (
                  <div className="timeline-item" key={item.event_id}>
                    <strong>{item.transition_id}</strong>
                    <span>{formatDate(item.received_at)}</span>
                    <small>
                      {item.topic} · partition {item.partition_id}
                      {' · '}offset {item.kafka_offset}
                    </small>
                  </div>
                ))}

                {timeline && timeline.items.length === 0 && (
                  <p className="empty">No transitions recorded.</p>
                )}

                {!timeline && (
                  <p className="empty">Loading timeline...</p>
                )}
              </div>
            ) : (
              <p className="empty">Select an incident.</p>
            )}
          </div>
        </section>

        <PlatformHealth />
      <CorePipeline />
      <WorkerHealth />
      <PipelineCorrelation />

        <footer>
          TITAN Control Center V0.1 · Read-only MVP ·
          Evidence-driven Autonomous SRE
        </footer>
      </main>
    </div>
  )
}

export default App
