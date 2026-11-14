import { useEffect, useState } from "react";
import "./WorkerHealth.css";

type Partition = {
  partition: number;
  committed?: number;
  low?: number;
  high?: number;
  lag?: number | null;
  error?: string;
};

type ConsumerGroup = {
  group_id: string;
  topic: string;
  group_state?: string;
  status: string;
  reason: string;
  lag: number | null;
  partitions: Partition[];
};

type WorkerHealthData = {
  service: string;
  status: string;
  mode: string;
  checked_at: string;
  groups: ConsumerGroup[];
};

export default function WorkerHealth() {
  const [data, setData] = useState<WorkerHealthData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let controller: AbortController | null = null;

    async function refresh() {
      if (controller) controller.abort();
      controller = new AbortController();

      try {
        const response = await fetch(
          "/api/v1/platform/workers",
          {
            cache: "no-store",
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const result: WorkerHealthData = await response.json();

        if (active) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (active && !(err instanceof DOMException &&
                        err.name === "AbortError")) {
          setError(
            err instanceof Error
              ? err.message
              : "Worker Health API unavailable"
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
      controller?.abort();
    };
  }, []);

  return (
    <section className="titan-workers">
      <header className="titan-workers-header">
        <div>
          <h2>Worker Health</h2>
          <p>Kafka consumer groups · Read-only</p>
        </div>
        <span className="titan-workers-overall">
          {error ? "UNAVAILABLE" : data?.status ?? "LOADING"}
        </span>
      </header>

      {error && (
        <p className="titan-workers-error">
          Evidence refresh failed: {error}
        </p>
      )}

      {data && (
        <>
          <div className="titan-workers-grid">
            {data.groups.map((group) => (
              <article
                className="titan-worker-card"
                key={group.group_id}
              >
                <div className="titan-worker-top">
                  <strong>{group.group_id}</strong>
                  <span>{group.status}</span>
                </div>

                <p className="titan-worker-topic">
                  {group.topic}
                </p>

                <div className="titan-worker-metrics">
                  <div>
                    <small>Group state</small>
                    <strong>
                      {group.group_state ?? "UNKNOWN"}
                    </strong>
                  </div>

                  <div>
                    <small>Consumer lag</small>
                    <strong>
                      {group.lag ?? "UNKNOWN"}
                    </strong>
                  </div>
                </div>

                <p className="titan-worker-reason">
                  {group.reason}
                </p>

                <div className="titan-worker-partitions">
                  {group.partitions.map((partition) => (
                    <p key={partition.partition}>
                      Partition {partition.partition}
                      {" · "}Committed {partition.committed ?? "N/A"}
                      {" · "}High {partition.high ?? "N/A"}
                      {" · "}Lag {partition.lag ?? "UNKNOWN"}
                    </p>
                  ))}
                </div>
              </article>
            ))}
          </div>

          <footer className="titan-workers-footer">
            Updated: {new Date(data.checked_at).toLocaleString()}
            {" · "}Auto-refresh: 15s
          </footer>
        </>
      )}
    </section>
  );
}
