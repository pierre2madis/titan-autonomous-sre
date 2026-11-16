import type { IncidentRCAResponse, RCAEvent } from './api/types'

export interface EvidenceSourceSummary {
  source: string
  eventCount: number
  eventTypes: string[]
  hosts: string[]
}

export interface StructuredProvenance {
  totalEvents: number
  distinctSources: number
  sources: EvidenceSourceSummary[]
  missingHostCount: number
  missingObservedAtCount: number
  invalidObservedAtCount: number
  missingReceivedAtCount: number
  independentCorroboration: false
  limitations: string[]
}

function validTimestamp(value: string | null): boolean {
  return Boolean(
    value &&
    Number.isFinite(Date.parse(value))
  )
}

export function summarizeEvidenceProvenance(
  rca: IncidentRCAResponse
): StructuredProvenance {
  const events: RCAEvent[] = [
    ...(rca.root_event ? [rca.root_event] : []),
    ...rca.related_events,
  ]

  const bySource = new Map<string, {
    count: number
    eventTypes: Set<string>
    hosts: Set<string>
  }>()

  let missingHostCount = 0
  let missingObservedAtCount = 0
  let invalidObservedAtCount = 0
  let missingReceivedAtCount = 0

  for (const event of events) {
    const source = event.source || 'UNKNOWN'

    if (!bySource.has(source)) {
      bySource.set(source, {
        count: 0,
        eventTypes: new Set(),
        hosts: new Set(),
      })
    }

    const entry = bySource.get(source)!
    entry.count += 1
    entry.eventTypes.add(event.event_type)

    if (event.host) {
      entry.hosts.add(event.host)
    } else {
      missingHostCount += 1
    }

    if (!event.observed_at) {
      missingObservedAtCount += 1
    } else if (!validTimestamp(event.observed_at)) {
      invalidObservedAtCount += 1
    }

    if (!event.received_at) {
      missingReceivedAtCount += 1
    }
  }

  const sources = [...bySource.entries()]
    .map(([source, entry]) => ({
      source,
      eventCount: entry.count,
      eventTypes: [...entry.eventTypes].sort(),
      hosts: [...entry.hosts].sort(),
    }))
    .sort((a, b) => a.source.localeCompare(b.source))

  return {
    totalEvents: events.length,
    distinctSources: sources.length,
    sources,
    missingHostCount,
    missingObservedAtCount,
    invalidObservedAtCount,
    missingReceivedAtCount,
    independentCorroboration: false,
    limitations: [
      'Source diversity does not establish source independence.',
      'Event correlation does not establish causality.',
      'The current API does not expose independent corroboration evidence.',
    ],
  }
}
