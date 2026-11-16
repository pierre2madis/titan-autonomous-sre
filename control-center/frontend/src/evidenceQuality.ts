import type { IncidentRCAResponse } from './api/types'

export type EvidenceQuality =
  | 'MISSING'
  | 'PARTIAL'
  | 'UNVERIFIED'
  | 'CORROBORATED'

export interface EvidenceQualityAssessment {
  quality: EvidenceQuality
  independentCorroboration: boolean
  rootEventAvailable: boolean
  collectionsComplete: boolean
  limitations: string[]
}

export function assessEvidenceQuality(
  rca: IncidentRCAResponse
): EvidenceQualityAssessment {
  const rootEventAvailable =
    rca.observed_facts?.root_event_found === true &&
    rca.root_event !== null &&
    rca.root_event !== undefined

  const collectionsComplete =
    rca.limits?.events_truncated === false &&
    rca.limits?.transitions_truncated === false

  let quality: EvidenceQuality

  if (!rootEventAvailable) {
    quality = 'MISSING'
  } else if (!collectionsComplete) {
    quality = 'PARTIAL'
  } else {
    // The current RCA contract does not provide
    // independent corroboration evidence.
    quality = 'UNVERIFIED'
  }

  return {
    quality,
    independentCorroboration: false,
    rootEventAvailable,
    collectionsComplete,
    limitations: rca.assessment?.limitations ?? [],
  }
}
