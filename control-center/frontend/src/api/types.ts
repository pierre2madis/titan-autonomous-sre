export interface Incident {
  incident_id: string
  correlation_key: string
  state: string
  severity: string
  root_event_id: string
  opened_at: string
  updated_at: string
  resolved_at: string | null
}

export interface IncidentList {
  items: Incident[]
  limit: number
  offset: number
  mode: string
}

export interface Transition {
  event_id: string
  transition_id: string
  incident_id: string
  topic: string
  partition_id: number
  kafka_offset: number
  received_at: string
}

export interface Timeline {
  incident_id: string
  items: Transition[]
  count: number
  mode: string
}

export interface RCAEvent {
  event_id: string
  source: string
  event_type: string
  host: string | null
  correlation_key: string | null
  observed_at: string | null
  received_at: string | null
}
export interface IncidentRCAResponse {
  incident_id: string
  mode: 'READ_ONLY'
  incident: Incident
  observed_facts: {
    declared_root_event_id: string | null
    root_event_found: boolean
    related_event_count_returned: number
    transition_count_returned: number
  }
  root_event: RCAEvent | null
  related_events: RCAEvent[]
  transitions: Transition[]
  assessment: {
    classification: string
    confidence: 'UNDETERMINED'
    causality_verified: boolean
    limitations: string[]
  }
  limits: {
    per_collection: number
    events_truncated: boolean
    transitions_truncated: boolean
  }
}
