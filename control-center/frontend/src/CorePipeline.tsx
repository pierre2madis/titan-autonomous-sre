import { useEffect, useState } from "react";
import "./CorePipeline.css";
import { useLanguage } from "./i18n/LanguageContext";

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

function formatDate(value: string | null, locale: string, noObservation: string): string {
  if (!value) return noObservation;
  return new Date(value).toLocaleString(locale);
}

export default function CorePipeline() {
  const { t, locale } = useLanguage();
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
          <h2>{t('Core Pipeline')}</h2>
          <p>{t('PostgreSQL evidence · Read-only')}</p>
        </div>

        <span className="titan-pipeline-status" data-health-status={error ? "UNKNOWN" : data?.status ?? "UNKNOWN"}>
          {error ? t('UNAVAILABLE') : data?.status ?? t('LOADING')}
        </span>
      </div>

      {error && (
        <p className="titan-pipeline-error">
          {t('Evidence refresh failed')}: {error}
        </p>
      )}

      {data && (
        <>
          <div className="titan-pipeline-grid">
            <div>
              <span>{t('Events')}</span>
              <strong>{data.events.total}</strong>
            </div>

            <div>
              <span>{t('Pending outbox')}</span>
              <strong>{data.outbox.pending}</strong>
            </div>

            <div>
              <span>{t('Transitions')}</span>
              <strong>{data.transition_inbox.total}</strong>
            </div>

            <div>
              <span>{t('Open incidents')}</span>
              <strong>{data.incidents.unresolved}</strong>
            </div>
          </div>

          <div className="titan-pipeline-details">
            <p>{data.reason}</p>

            <dl>
              <dt>{t('Activity')}</dt>
              <dd>{data.activity}</dd>

              <dt>{t('Worker liveness')}</dt>
              <dd>{data.worker_liveness}</dd>

              <dt>{t('Outbox overdue')}</dt>
              <dd>
                {data.outbox.backlog_overdue ? "YES" : "NO"}
              </dd>

              <dt>{t('Last event')}</dt>
              <dd>
                {formatDate(data.events.last_received_at, locale, t('No observation'))}
              </dd>

              <dt>{t('Last publication')}</dt>
              <dd>
                {formatDate(data.outbox.last_published_at, locale, t('No observation'))}
              </dd>

              <dt>{t('Last transition')}</dt>
              <dd>
                {formatDate(data.transition_inbox.last_received_at, locale, t('No observation'))}
              </dd>
            </dl>
          </div>

          <footer className="titan-pipeline-footer">
            {t('Updated')}: {formatDate(data.checked_at, locale, t('No observation'))}
            {" · "}{t('Auto-refresh: 15s')}
          </footer>
        </>
      )}
    </section>
  );
}
