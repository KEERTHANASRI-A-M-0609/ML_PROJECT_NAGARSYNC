import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { getTranslation } from '../i18n.js'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try { return localStorage.getItem('ns_lang') === 'ta' ? 'ta' : 'en' } catch { return 'en' }
  })

  const setLang = (next) => {
    const v = next === 'ta' ? 'ta' : 'en'
    setLangState(v)
    try { localStorage.setItem('ns_lang', v) } catch {}
  }

  useEffect(() => {
    document.documentElement.lang = lang === 'ta' ? 'ta' : 'en'
  }, [lang])

  const value = useMemo(() => ({ lang, setLang, t: getTranslation(lang) }), [lang])
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) return { lang: 'en', setLang: () => {}, t: getTranslation('en') }
  return ctx
}
