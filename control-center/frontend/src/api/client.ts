import type { Incident, IncidentList, Timeline } from './types'

async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`API request failed: HTTP ${response.status}`)
  }

  return response.json() as Promise<T>
}

export const titanAPI = {
  incidents: () =>
    getJSON<IncidentList>('/api/v1/incidents?limit=50'),

  incident: (id: string) =>
    getJSON<Incident>(
      `/api/v1/incidents/${encodeURIComponent(id)}`
    ),

  timeline: (id: string) =>
    getJSON<Timeline>(
      `/api/v1/incidents/${encodeURIComponent(id)}/timeline`
    ),
}
