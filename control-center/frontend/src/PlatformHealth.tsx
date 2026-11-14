import { useEffect, useState } from 'react'
import './PlatformHealth.css'
import { useLanguage } from './i18n/LanguageContext'

type Status = 'UP' | 'DOWN' | 'DEGRADED' | 'UNKNOWN'

interface ComponentHealth {
  name: string
  status: Status
  check: string
  reason: string
  checked_at: string
}

interface PlatformHealthResponse {
  service: string
  status: Status
  mode: string
  checked_at: string
  components: ComponentHealth[]
}

export default function PlatformHealth() {
  const { t, locale } = useLanguage()
  const [data, setData] = useState<PlatformHealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const refresh = async () => {
      try {
        const response = await fetch('/api/v1/platform/health', {
          cache: 'no-store',
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const result = await response.json() as PlatformHealthResponse

        if (active) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (active) {
          setError(String(err))
          setData(null)
        }
      }
    }

    void refresh()

    const timer = window.setInterval(() => {
      void refresh()
    }, 15000)

    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  return (
    <section className="platform-health">
      <div className="health-heading">
        <h2>{t('Platform Health')}</h2>
        <span>{t('Automatic refresh: 15s')}</span>
      </div>

      {error && (
        <div className="health-error">
          {t('Health API unavailable')}: {error}
        </div>
      )}

      {data && (
        <>
          <div className="health-summary">
            <strong>{t('Overall')}: {data.status}</strong>
            <span>{t('Mode')}: {data.mode}</span>
            <span>
              {t('Checked')}: {new Date(data.checked_at).toLocaleString(locale)}
            </span>
          </div>

          <div className="health-grid">
            {data.components.map(item => (
              <article className="health-card" key={item.name}>
                <div className="health-card-header">
                  <strong>{item.name}</strong>
                  <span className={`health-status status-${item.status}`} data-health-status={item.status}>
                    {item.status}
                  </span>
                </div>

                <p>{item.reason}</p>
                <small>{item.check}</small>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
