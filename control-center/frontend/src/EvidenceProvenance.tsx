import type { IncidentRCAResponse, RCAEvent } from './api/types'

type Props = {
  data: IncidentRCAResponse
}

function display(value: string | null | undefined): string {
  return value || 'Not available'
}

function EvidenceRecord({
  event,
  classification,
}: {
  event: RCAEvent
  classification: string
}) {
  return (
    <div className="timeline-item">
      <strong>{event.event_id}</strong>

      <span>
        {classification} · {event.source} / {event.event_type}
      </span>

      <small>
        Host: {display(event.host)}
        {' · '}Observed: {display(event.observed_at)}
        {' · '}Received: {display(event.received_at)}
      </small>

      <small>
        Correlation key: {display(event.correlation_key)}
      </small>
    </div>
  )
}

export default function EvidenceProvenance({ data }: Props) {
  const {
    incident,
    observed_facts,
    root_event,
    related_events,
    transitions,
    assessment,
    limits,
  } = data

  return (
    <section
      className="titan-evidence-provenance"
      aria-label="Evidence Provenance"
    >
      <h3>Evidence Provenance</h3>

      <p>
        Incident: <strong>{incident.incident_id}</strong>
        {' · '}Correlation key: {display(incident.correlation_key)}
      </p>

      <h3>Declared Root Event</h3>

      <p>
        Root event reference:{' '}
        {display(observed_facts.declared_root_event_id)}
      </p>

      {root_event ? (
        <EvidenceRecord
          event={root_event}
          classification="Referenced root event"
        />
      ) : (
        <p className="empty">
          No root event record returned. A declared root event
          is not independently verified as causal.
        </p>
      )}

      <h3>Correlated Evidence</h3>

      <p>
        {related_events.length} related event records returned.
        Correlation does not establish causality.
      </p>

      {related_events.map(event => (
        <EvidenceRecord
          key={event.event_id}
          event={event}
          classification="Correlated event"
        />
      ))}

      {related_events.length === 0 && (
        <p className="empty">
          No correlated evidence returned for this incident.
        </p>
      )}

      <h3>Kafka Transition Provenance</h3>

      {transitions.map(transition => (
        <div
          className="timeline-item"
          key={`${transition.event_id}-${transition.transition_id}`}
        >
          <strong>{transition.transition_id}</strong>

          <span>
            Topic: {transition.topic}
            {' · '}Partition: {transition.partition_id}
            {' · '}Offset: {transition.kafka_offset}
          </span>

          <small>
            Event ID: {transition.event_id}
            {' · '}Received: {display(transition.received_at)}
          </small>
        </div>
      ))}

      {transitions.length === 0 && (
        <p className="empty">
          No persisted Kafka transitions returned.
        </p>
      )}

      <h3>RCA Explainability</h3>

      <dl>
        <dt>Classification</dt>
        <dd>{assessment.classification}</dd>

        <dt>Confidence</dt>
        <dd>{assessment.confidence}</dd>

        <dt>Causality verified</dt>
        <dd>{assessment.causality_verified ? 'Yes' : 'No'}</dd>

        <dt>Root event record found</dt>
        <dd>{observed_facts.root_event_found ? 'Yes' : 'No'}</dd>
      </dl>

      <h3>Evidence Completeness</h3>

      <dl>
        <dt>API collection limit</dt>
        <dd>{limits.per_collection}</dd>

        <dt>Events truncated</dt>
        <dd>{limits.events_truncated ? 'Yes' : 'No'}</dd>

        <dt>Transitions truncated</dt>
        <dd>{limits.transitions_truncated ? 'Yes' : 'No'}</dd>
      </dl>

      <h3>Assessment Limitations</h3>

      {assessment.limitations.length === 0 ? (
        <p>No additional limitations returned by the API.</p>
      ) : (
        <ul>
          {assessment.limitations.map((limitation, index) => (
            <li key={`${index}-${limitation}`}>
              {limitation}
            </li>
          ))}
        </ul>
      )}

      <p>
        <strong>Evidence policy:</strong> Observed facts and
        correlated events must not be presented as independently
        verified causal relationships.
      </p>
    </section>
  )
}
