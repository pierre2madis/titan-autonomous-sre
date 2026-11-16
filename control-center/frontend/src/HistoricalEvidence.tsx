import { useEffect, useState } from "react";

const EVENT_ID =
  "EVT-LINUX-CPU-172196eb5c05fceaf30e8a8701f05b7f";

type HistoricalEvidenceResponse = {
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
  provenance: {
    kind: string;
    historical: boolean;
    verified: boolean;
    synthetic_status: string;
  };
  payload: Record<string, unknown>;
};

type EvidenceState =
  | { status: "loading" }
  | { status: "available"; data: HistoricalEvidenceResponse }
  | { status: "not_found" }
  | { status: "policy_violation" }
  | { status: "unavailable" };

export default function HistoricalEvidence() {
  const [state, setState] = useState<EvidenceState>({
    status: "loading",
  });

  useEffect(() => {
    const controller = new AbortController();

    async function loadEvidence() {
      try {
        const response = await fetch(
          `/api/v1/evidence/historical/${encodeURIComponent(EVENT_ID)}`,
          {
            signal: controller.signal,
            headers: { Accept: "application/json" },
          }
        );

        if (response.status === 404) {
          setState({ status: "not_found" });
          return;
        }

        if (response.status === 409) {
          setState({ status: "policy_violation" });
          return;
        }

        if (!response.ok) {
          setState({ status: "unavailable" });
          return;
        }

        const data =
          (await response.json()) as HistoricalEvidenceResponse;

        if (
          data.event_id !== EVENT_ID ||
          data.verification_status !== "UNVERIFIED" ||
          data.review_only !== true ||
          data.causality_verified !== false ||
          data.remediation_allowed !== false ||
          data.provenance?.kind !== "UNVERIFIED" ||
          data.provenance?.historical !== true ||
          data.provenance?.verified !== false ||
          data.provenance?.synthetic_status !== "NOT_ESTABLISHED"
        ) {
          setState({ status: "policy_violation" });
          return;
        }

        setState({ status: "available", data });
      } catch (error) {
        if (controller.signal.aborted) return;
        setState({ status: "unavailable" });
      }
    }

    void loadEvidence();

    return () => controller.abort();
  }, []);

  return (
    <section aria-labelledby="historical-evidence-title">
      <h2 id="historical-evidence-title">
        Historical Evidence
      </h2>

      <p>
        Read-only historical observations. These records do not
        establish verified causality or authorize remediation.
      </p>

      {state.status === "loading" && (
        <p role="status">Loading historical evidence...</p>
      )}

      {state.status === "not_found" && (
        <p role="status">
          Historical evidence not found for the requested
          event identifier.
        </p>
      )}

      {state.status === "policy_violation" && (
        <p role="alert">
          Evidence policy violation. The record cannot be
          presented as trusted historical evidence.
        </p>
      )}

      {state.status === "unavailable" && (
        <p role="alert">
          Historical evidence service unavailable.
        </p>
      )}

      {state.status === "available" && (
        <div>
          <p>
            <strong>Event:</strong> {state.data.event_id}
          </p>

          <p>
            <strong>Host:</strong> {state.data.host}
          </p>

          <p>
            <strong>Source:</strong> {state.data.source}
          </p>

          <p>
            <strong>Observed at:</strong>{" "}
            {state.data.observed_at}
          </p>

          <p>
            <strong>Verification:</strong>{" "}
            {state.data.verification_status}
          </p>

          <p>
            <strong>Classification:</strong>{" "}
            {state.data.classification}
          </p>

          <p>
            <strong>Historical:</strong> Yes
          </p>

          <p>
            <strong>Review only:</strong> Yes
          </p>

          <p>
            <strong>Causality verified:</strong> No
          </p>

          <p>
            <strong>Remediation allowed:</strong> No
          </p>
        </div>
      )}
    </section>
  );
}
