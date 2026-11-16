import { useEffect, useState } from "react";

const EVENT_IDS = [
  "TITAN-RECOVERY-002",
  "TITAN-RECOVERY-001",
  "TITAN-E2E-001",
  "TITAN-R6-09F-05-001",
];

type IntegrationEvidenceRecord = {
  event_id: string;
  source: string;
  event_type: string;
  host: string;
  observed_at: string;
  classification: string;
  verification_status: string;
  review_only: boolean;
  causality_verified: boolean;
  remediation_allowed: boolean;
};

type EvidenceState = {
  eventId: string;
  status: "loading" | "ready" | "error";
  data?: IntegrationEvidenceRecord;
  message?: string;
};

function isSafeEvidence(
  data: IntegrationEvidenceRecord,
  eventId: string
): boolean {
  return (
    data.event_id === eventId &&
    data.source === "TITAN" &&
    data.classification === "TEST_UNVERIFIED" &&
    data.verification_status === "UNVERIFIED" &&
    data.review_only === true &&
    data.causality_verified === false &&
    data.remediation_allowed === false
  );
}

export default function IntegrationEvidence() {
  const [records, setRecords] = useState<EvidenceState[]>(
    EVENT_IDS.map((eventId) => ({
      eventId,
      status: "loading",
    }))
  );

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      const results = await Promise.all(
        EVENT_IDS.map(async (eventId): Promise<EvidenceState> => {
          try {
            const response = await fetch(
              `/api/v1/evidence/integration/${encodeURIComponent(eventId)}`,
              { signal: controller.signal }
            );

            if (!response.ok) {
              return {
                eventId,
                status: "error",
                message: `HTTP ${response.status}`,
              };
            }

            const data =
              (await response.json()) as IntegrationEvidenceRecord;

            if (!isSafeEvidence(data, eventId)) {
              return {
                eventId,
                status: "error",
                message: "Evidence safety validation failed",
              };
            }

            return {
              eventId,
              status: "ready",
              data,
            };
          } catch (error) {
            return {
              eventId,
              status: "error",
              message:
                error instanceof Error
                  ? error.message
                  : "Request failed",
            };
          }
        })
      );

      if (!controller.signal.aborted) {
        setRecords(results);
      }
    }

    void load();

    return () => controller.abort();
  }, []);

  return (
    <section aria-labelledby="integration-evidence-title">
      <h2 id="integration-evidence-title">
        Integration Evidence
      </h2>

      <p>
        Synthetic and integration test records. These records
        are unverified, review-only, and cannot authorize
        automated remediation.
      </p>

      {records.map((record) => (
        <article key={record.eventId}>
          <h3>{record.eventId}</h3>

          {record.status === "loading" && (
            <p>Loading integration evidence...</p>
          )}

          {record.status === "error" && (
            <p role="alert">
              Evidence unavailable: {record.message}
            </p>
          )}

          {record.status === "ready" && record.data && (
            <dl>
              <dt>Source</dt>
              <dd>{record.data.source}</dd>

              <dt>Type</dt>
              <dd>{record.data.event_type}</dd>

              <dt>Host</dt>
              <dd>{record.data.host}</dd>

              <dt>Observed</dt>
              <dd>{record.data.observed_at}</dd>

              <dt>Classification</dt>
              <dd>{record.data.classification}</dd>

              <dt>Verification</dt>
              <dd>{record.data.verification_status}</dd>

              <dt>Review only</dt>
              <dd>YES</dd>

              <dt>Causality verified</dt>
              <dd>NO</dd>

              <dt>Remediation allowed</dt>
              <dd>NO</dd>
            </dl>
          )}
        </article>
      ))}
    </section>
  );
}
