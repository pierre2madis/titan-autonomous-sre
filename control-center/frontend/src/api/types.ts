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
