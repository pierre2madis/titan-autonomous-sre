import type { IncidentRCAResponse } from './api/types'

export interface RemediationRecommendation {
  type: 'FURTHER_INVESTIGATION'
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
  const assessment = rca.assessment

  const causalityUnverified =
    assessment.causality_verified !== true

  return {
    type: 'FURTHER_INVESTIGATION',
    title: causalityUnverified
      ? 'Validate the declared root event'
      : 'Review evidence before remediation',
    rationale: causalityUnverified
      ? 'Root event causality has not been independently verified.'
      : 'Verified causality alone does not authorize remediation.',
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
