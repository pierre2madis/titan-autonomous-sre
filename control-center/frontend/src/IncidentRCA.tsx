import { useEffect, useState } from 'react'
import { titanAPI } from './api/client'
import EvidenceProvenance from './EvidenceProvenance'
import RemediationAdvisor from './RemediationAdvisor'
import type { IncidentRCAResponse } from './api/types'
import { useLanguage } from './i18n/LanguageContext'



export default function IncidentRCA({ incidentId }: { incidentId: string }) {
  const { t } = useLanguage()
  const [data, setData] = useState<IncidentRCAResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    setData(null)
    setError(null)
    titanAPI.rca(incidentId)
      .then(result => { if (active) setData(result) })
      .catch(err => { if (active) setError(String(err)) })
    return () => { active = false }
  }, [incidentId])
  return (
    <section className="panel" style={{ marginTop: 20 }} aria-label={t('Incident RCA')}>
      <div className="panel-header"><h2>{t('Incident RCA')}</h2><span>{t('Observed evidence · read-only')}</span></div>
      <div className="details">
        {error && <p className="error" role="alert">{error}</p>}
        {!data && !error && <p className="empty">{t('Loading RCA evidence...')}</p>}
        {data && <EvidenceProvenance data={data} />}
        {data && <RemediationAdvisor data={data} />}
      </div>
    </section>
  )
}
