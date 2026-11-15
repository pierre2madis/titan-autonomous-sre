import type { IncidentRCAResponse } from './api/types'
import { evaluateRemediation } from './remediationAdvisor'

export default function RemediationAdvisor({
  data,
}: {
  data: IncidentRCAResponse
}) {
  const recommendation = evaluateRemediation(data)

  return (
    <section
      className="panel"
      aria-label="Remediation Advisor"
      style={{ marginTop: 20 }}
    >
      <div className="panel-header">
        <h2>Remediation Advisor</h2>
        <span>Proposal only · No execution</span>
      </div>

      <div className="details">
        <h3>{recommendation.title}</h3>

        <p>{recommendation.rationale}</p>

        <p>
          <strong>Recommendation:</strong>{' '}
          {recommendation.type}
        </p>

        <p>
          <strong>Risk:</strong>{' '}
          {recommendation.risk}
        </p>

        <p>
          <strong>Confidence:</strong>{' '}
          {recommendation.confidence}
        </p>

        <p>
          <strong>Approval:</strong>{' '}
          {recommendation.approvalStatus}
        </p>

        <p>
          <strong>Execution:</strong>{' '}
          {recommendation.executionAllowed
            ? 'Allowed'
            : 'Blocked'}
        </p>

        <h3>Required investigation</h3>

        <ul>
          {recommendation.preconditions.map(item => (
            <li key={item}>{item}</li>
          ))}
        </ul>

        <p>
          <strong>Evidence limitations:</strong>
        </p>

        <ul>
          {data.assessment.limitations.map(
            (limitation, index) => (
              <li key={index}>{limitation}</li>
            )
          )}
        </ul>
      </div>
    </section>
  )
}
