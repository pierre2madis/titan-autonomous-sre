import PipelineCorrelation from "./PipelineCorrelation";
import WorkerHealth from "./WorkerHealth";
import CorePipeline from "./CorePipeline";
import PlatformHealth from './PlatformHealth'
import { useCallback, useEffect, useState } from 'react'
import { titanAPI } from './api/client'
import type { Incident, Timeline } from './api/types'
import IncidentRCA from './IncidentRCA'
import IncidentLifecycle from './IncidentLifecycle'
import OperationalIncidents from './OperationalIncidents'
import './App.css'
import { useLanguage, LanguageSwitcher } from './i18n/LanguageContext'
import ThemeControls from './ThemeControls'

function formatDate(value: string | null, locale: string): string {
  if (!value) return '—'
  return new Date(value).toLocaleString(locale)
}

function App() {
  const { t, locale } = useLanguage()
  type View = 'overview' | 'incidents' | 'evidence' | 'health' | 'automation'
  const [view, setView] = useState<View>('overview')
  const navigation: { id: View; icon: string; label: string }[] = [
    { id: 'overview', icon: '◉', label: 'Overview' },
    { id: 'incidents', icon: '▤', label: 'Incidents' },
    { id: 'evidence', icon: '◇', label: 'Evidence Explorer' },
    { id: 'health', icon: '▣', label: 'Platform Health' },
    { id: 'automation', icon: '⚙', label: 'Automation' },
  ]
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selected, setSelected] = useState<Incident | null>(null)
  const handleOperationalSelection = useCallback((id: string) => {
    setSelected(current => {
      if (current?.incident_id === id) return current
      return incidents.find(item => item.incident_id === id) ?? null
    })
  }, [incidents])
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

        <nav aria-label={t('Navigation')}>
          {navigation.map(item => (
            <button key={item.id} type="button"
              className={view === item.id ? 'nav-active' : ''}
              aria-current={view === item.id ? 'page' : undefined}
              onClick={() => setView(item.id)}>
              <span aria-hidden="true">{item.icon}</span> {t(item.label)}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          {t('READ-ONLY MODE')}
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{view === 'overview' ? t('Operations Overview') : t(navigation.find(item => item.id === view)?.label ?? 'Overview')}</h1>
            <p>{t('TITAN Autonomous SRE Platform')}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}><ThemeControls /><LanguageSwitcher /><span className="environment">LAB · V0.2</span></div>
        </header>

        {view === 'overview' && <section className="metrics">
          <div className="metric-card">
            <span>{t('Total incidents')}</span>
            <strong>{incidents.length}</strong>
            <small>{t('Current API page')}</small>
          </div>

          <div className="metric-card">
            <span>{t('Active incidents')}</span>
            <strong>
              {incidents.filter(i =>
                !['RESOLVED', 'CLOSED'].includes(i.state)
              ).length}
            </strong>
            <small>{t('Unresolved in current page')}</small>
          </div>

          <div className="metric-card">
            <span>{t('Platform mode')}</span>
            <strong className="mode">OBSERVE</strong>
            <small>{t('No remediation controls')}</small>
          </div>
        </section>}

        {(view === 'overview' || view === 'incidents') && <>
        {loading && <p>{t('Loading incidents...')}</p>}
        {error && <div className="error">{error}</div>}

        <section className="workspace">
          <div className="panel">
            <div className="panel-header">
              <h2>{t('Incidents')}</h2>
              <span>{incidents.length} {t('loaded')}</span>
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
              <p className="empty">{t('No incidents found.')}</p>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>{t('Incident Investigation')}</h2>
              <span>PostgreSQL + Kafka Inbox</span>
            </div>

            {selected ? (
              <div className="details">
                <h3>{selected.incident_id}</h3>
                <span className="state">{selected.state}</span>

                <dl>
                  <dt>{t('Severity')}</dt>
                  <dd>{selected.severity}</dd>
                  <dt>{t('Root event')}</dt>
                  <dd>{selected.root_event_id}</dd>
                  <dt>{t('Opened')}</dt>
                  <dd>{formatDate(selected.opened_at, locale)}</dd>
                  <dt>{t('Updated')}</dt>
                  <dd>{formatDate(selected.updated_at, locale)}</dd>
                </dl>

                <h3>{t('Transition Timeline')}</h3>

                {timeline?.items.map(item => (
                  <div className="timeline-item" key={item.event_id}>
                    <strong>{item.transition_id}</strong>
                    <span>{formatDate(item.received_at, locale)}</span>
                    <small>
                      {item.topic} · partition {item.partition_id}
                      {' · '}offset {item.kafka_offset}
                    </small>
                  </div>
                ))}

                {timeline && timeline.items.length === 0 && (
                  <p className="empty">{t('No transitions recorded.')}</p>
                )}

                {!timeline && (
                  <p className="empty">{t('Loading timeline...')}</p>
                )}
              </div>
            ) : (
              <p className="empty">{t('Select an incident.')}</p>
            )}
          </div>
        </section>

        {view === 'incidents' && selected && <IncidentRCA incidentId={selected.incident_id} />}
        </>}
        {view === 'incidents' && <OperationalIncidents selectedIncidentId={selected?.incident_id ?? ""} onSelectIncident={handleOperationalSelection} />}
        {view === 'incidents' && <IncidentLifecycle />}
        {view === 'evidence' && <section className="panel titan-view-panel">
          <div className="panel-header"><h2>{t('Evidence Explorer')}</h2><span>{t('READ-ONLY MODE')}</span></div>
          <div className="details">
            <p>{t('Evidence explorer description')}</p>
            <label htmlFor="titan-evidence-incident">{t('Incidents')}</label>
            <select id="titan-evidence-incident" className="titan-view-select"
              value={selected?.incident_id ?? ''}
              onChange={event => setSelected(incidents.find(i => i.incident_id === event.target.value) ?? null)}>
              {incidents.length === 0 && <option value="">{t('No incidents found.')}</option>}
              {incidents.map(i => <option key={i.incident_id} value={i.incident_id}>{i.incident_id}</option>)}
            </select>
            {selected && <IncidentRCA incidentId={selected.incident_id} />}
          </div>
        </section>}
        {view === 'health' && <>
          <PlatformHealth />
          <CorePipeline />
          <WorkerHealth />
          <PipelineCorrelation />
        </>}
        {view === 'automation' && <section className="panel titan-view-panel">
          <div className="panel-header"><h2>{t('Automation')}</h2><span>{t('READ-ONLY MODE')}</span></div>
          <div className="details"><p>{t('Automation placeholder')}</p></div>
        </section>}

        <footer>
          TITAN Control Center V0.2 · {t('Read-only MVP')} ·
          {t('Evidence-driven Autonomous SRE')}
        </footer>
      </main>
    </div>
  )
}

export default App
