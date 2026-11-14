import { useEffect, useState } from "react";
import "./PipelineCorrelation.css";

type Worker = {
  group_id: string;
  group_state?: string;
  status: string;
  lag: number | null;
};

type CorrelationResponse = {
  service: string;
  assessment?: {
    health_status: string;
    activity_state: string;
    confidence: string;
    worker_liveness: string;
    summary: string;
  };
  status: string;
  mode: string;
  checked_at: string;
  reasons: string[];
  evidence: string[];
  pipeline: {
    outbox: {
      pending: number;
      backlog_overdue: boolean;
    };
  };
  workers: {
    groups: Worker[];
  };
};

export default function PipelineCorrelation() {
  const [data, setData] =
    useState<CorrelationResponse | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let controller: AbortController | null = null;

    async function refresh() {
      controller?.abort();
      controller = new AbortController();

      try {
        const response = await fetch(
          "/api/v1/platform/correlation",
          {
            cache: "no-store",
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const result: CorrelationResponse =
          await response.json();

        if (active) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (
          active &&
          !(
            err instanceof DOMException &&
            err.name === "AbortError"
          )
        ) {
          setError(
            err instanceof Error
              ? err.message
              : "Correlation API unavailable"
          );
        }
      }
    }

    void refresh();

    const timer = window.setInterval(
      () => void refresh(),
      15000
    );

    return () => {
      active = false;
      window.clearInterval(timer);
      controller?.abort();
    };
  }, []);

  return (
    <section className="titan-correlation">
      <header className="titan-correlation-header">
        <div>
          <h2>Pipeline Correlation</h2>
          <p>
            PostgreSQL + Kafka + Worker Evidence
          </p>
        </div>

        <span className="titan-correlation-status">
          {error
            ? "UNAVAILABLE"
            : data?.status ?? "LOADING"}
        </span>
      </header>

      {error && (
        <p className="titan-correlation-error">
          Evidence refresh failed: {error}
        </p>
      )}

      {data && (
        <>
          {data.assessment && (
            <div className="titan-assessment">
              <p className="titan-assessment-summary">
                {data.assessment.summary}
              </p>
              <div className="titan-assessment-facts">
                <span>
                  Health: {data.assessment.health_status}
                </span>
                <span>
                  Activity: {data.assessment.activity_state}
                </span>
                <span>
                  Confidence: {data.assessment.confidence}
                </span>
                <span>
                  Liveness: {data.assessment.worker_liveness}
                </span>
              </div>
            </div>
          )}

          <div className="titan-correlation-metrics">
            <div>
              <small>Outbox pending</small>
              <strong>
                {data.pipeline.outbox.pending}
              </strong>
            </div>

            <div>
              <small>Consumer groups</small>
              <strong>
                {data.workers.groups.length}
              </strong>
            </div>

            <div>
              <small>Total consumer lag</small>
              <strong>
                {data.workers.groups.some(
                  (group) => group.lag === null
                )
                  ? "UNKNOWN"
                  : data.workers.groups.reduce(
                      (total, group) =>
                        total + (group.lag ?? 0),
                      0
                    )}
              </strong>
            </div>
          </div>

          <div className="titan-correlation-details">
            <div>
              <h3>Diagnostic reasons</h3>
              <ul>
                {data.reasons.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
            </div>

            <div>
              <h3>Evidence</h3>
              <ul>
                {data.evidence.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <footer className="titan-correlation-footer">
            Updated:{" "}
            {new Date(
              data.checked_at
            ).toLocaleString()}
            {" · "}Read-only
            {" · "}Refresh 15s
          </footer>
        </>
      )}
    </section>
  );
}
