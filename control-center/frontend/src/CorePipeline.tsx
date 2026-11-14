import { useEffect, useState } from "react";
import "./CorePipeline.css";

type PipelineData = {
  status: string;
  reason: string;
  activity: string;
  checked_at: string;
  worker_liveness: string;
  events: {
    total: number;
    last_received_at: string | null;
  };
  outbox: {
    pending: number;
    pending_retried: number;
    oldest_pending_age_seconds: number | null;
    backlog_overdue: boolean;
    last_published_at: string | null;
  };
  transition_inbox: {
    total: number;
    last_received_at: string | null;
  };
  incidents: {
    total: number;
    unresolved: number;
  };
};

function formatDate(value: string | null): string {
  if (!value) return "No observation";
  return new Date(value).toLocaleString();
}

export default function CorePipeline() {
  const [data, setData] = useState<PipelineData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function refresh() {
      try {
        const response = await fetch(
          "/api/v1/platform/pipeline",
          {
            cache: "no-store",
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const result: PipelineData = await response.json();

        if (active) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Pipeline API unavailable"
          );
        }
      }
    }

    void refresh();

    const timer = window.setInterval(() => {
      void refresh();
    }, 15000);

    return () => {
      active = false;
      window.clearInterval(timer);
      controller.abort();
    };
  }, []);

  return (
    <section className="titan-pipeline">
      <div className="titan-pipeline-header">
        <div>
          <h2>Core Pipeline</h2>
          <p>PostgreSQL evidence · Read-only</p>
        </div>

        <span className="titan-pipeline-status">
          {error ? "UNAVAILABLE" : data?.status ?? "LOADING"}
        </span>
      </div>

      {error && (
        <p className="titan-pipeline-error">
          Evidence refresh failed: {error}
        </p>
      )}

      {data && (
        <>
          <div className="titan-pipeline-grid">
            <div>
              <span>Events</span>
              <strong>{data.events.total}</strong>
            </div>

            <div>
              <span>Pending outbox</span>
              <strong>{data.outbox.pending}</strong>
            </div>

            <div>
              <span>Transitions</span>
              <strong>{data.transition_inbox.total}</strong>
            </div>

            <div>
              <span>Open incidents</span>
              <strong>{data.incidents.unresolved}</strong>
            </div>
          </div>

          <div className="titan-pipeline-details">
            <p>{data.reason}</p>

            <dl>
              <dt>Activity</dt>
              <dd>{data.activity}</dd>

              <dt>Worker liveness</dt>
              <dd>{data.worker_liveness}</dd>

              <dt>Outbox overdue</dt>
              <dd>
                {data.outbox.backlog_overdue ? "YES" : "NO"}
              </dd>

              <dt>Last event</dt>
              <dd>
                {formatDate(data.events.last_received_at)}
              </dd>

              <dt>Last publication</dt>
              <dd>
                {formatDate(data.outbox.last_published_at)}
              </dd>

              <dt>Last transition</dt>
              <dd>
                {formatDate(data.transition_inbox.last_received_at)}
              </dd>
            </dl>
          </div>

          <footer className="titan-pipeline-footer">
            Updated: {formatDate(data.checked_at)}
            {" · "}Auto-refresh: 15s
          </footer>
        </>
      )}
    </section>
  );
}
