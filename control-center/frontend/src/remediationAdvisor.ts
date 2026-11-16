import type { IncidentRCAResponse } from './api/types'
import { assessEvidenceQuality } from './evidenceQuality'

export type EvidenceStatus =
  | 'MISSING_ROOT_EVENT'
  | 'INCOMPLETE_EVIDENCE'
  | 'CONFLICTING_EVIDENCE'
  | 'UNVERIFIED_CAUSALITY'
  | 'REVIEW_REQUIRED'

export interface RemediationRecommendation {
  type: 'FURTHER_INVESTIGATION'
  evidenceStatus: EvidenceStatus
  title: string
  rationale: string
  risk: 'LOW'
  confidence: 'UNDETERMINED'
  preconditions: string[]
  executionAllowed: false
  approvalStatus: 'NOT_REQUESTED'
}

export function evaluateRemediation(
  rca: IncidentRCAResponse
): RemediationRecommendation {
  const evidence = assessEvidenceQuality(rca)
  const assessment = rca.assessment

  let evidenceStatus: EvidenceStatus
  let title: string
  let rationale: string

  if (evidence.quality === 'MISSING') {
    evidenceStatus = 'MISSING_ROOT_EVENT'
    title = 'Locate and validate the root event'
    rationale =
      'The declared root event is not available in the RCA evidence.'
  } else if (evidence.quality === 'PARTIAL') {
    evidenceStatus = 'INCOMPLETE_EVIDENCE'
    title = 'Retrieve complete incident evidence'
    rationale =
      'The RCA evidence collections are truncated.'
  } else if (
    assessment?.limitations?.some(
      item => /\bconflict(?:ing)?\b|\bcontradict(?:ory|ion|ions)?\b/i.test(item)
    )
  ) {
    evidenceStatus = 'CONFLICTING_EVIDENCE'
    title = 'Investigate conflicting evidence'
    rationale =
      'The RCA assessment reports conflicting or contradictory evidence.'
  } else if (assessment?.causality_verified !== true) {
    evidenceStatus = 'UNVERIFIED_CAUSALITY'
    title = 'Validate the declared root event'
    rationale =
      'Root event causality has not been independently verified.'
  } else {
    evidenceStatus = 'REVIEW_REQUIRED'
    title = 'Review causal evidence before remediation'
    rationale =
      'The RCA reports verified causality, but this does not authorize execution.'
  }

  return {
    type: 'FURTHER_INVESTIGATION',
    evidenceStatus,
    title,
    rationale,
    risk: 'LOW',
    confidence: 'UNDETERMINED',
    preconditions: [
      'Review incident evidence and source provenance',
      'Validate event chronology',
      'Correlate independent evidence sources',
      'Assess operational impact before any action',
    ],
    executionAllowed: false,
    approvalStatus: 'NOT_REQUESTED',
  }
}
