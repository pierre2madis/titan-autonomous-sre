import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import catalogs from './translations.json'

type Language = 'en' | 'fr'
type LanguageContextValue = {
  language: Language
  locale: string
  setLanguage: (language: Language) => void
  t: (key: string) => string
  displayValue: (value: string) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)
const STORAGE_KEY = 'titan.controlCenter.language'

function initialLanguage(): Language {
  try { return window.localStorage.getItem(STORAGE_KEY) === 'fr' ? 'fr' : 'en' }
  catch { return 'en' }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(initialLanguage)
  const locale = language === 'fr' ? 'fr-FR' : 'en-US'
  useEffect(() => {
    document.documentElement.lang = language
    try { window.localStorage.setItem(STORAGE_KEY, language) } catch { /* storage disabled */ }
  }, [language])
  const t = (key: string): string => {
    const catalog = catalogs[language] as Record<string, string>
    return catalog[key] ?? key
  }
  const displayValue = (value: string): string => t(value)
  return <LanguageContext.Provider value={{ language, locale, setLanguage, t, displayValue }}>
    {children}
  </LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('LanguageProvider is missing')
  return context
}

export function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage()
  return <div role="group" aria-label="Language / Langue" style={{ display: 'flex', gap: 4 }}>
    <button type="button" aria-pressed={language === 'en'} onClick={() => setLanguage('en')}
      style={{ cursor: 'pointer', fontWeight: language === 'en' ? 700 : 400, padding: '5px 9px' }}>EN</button>
    <button type="button" aria-pressed={language === 'fr'} onClick={() => setLanguage('fr')}
      style={{ cursor: 'pointer', fontWeight: language === 'fr' ? 700 : 400, padding: '5px 9px' }}>FR</button>
  </div>
}
