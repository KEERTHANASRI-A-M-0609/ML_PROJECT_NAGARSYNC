import { useState } from 'react'
import Sidebar from './Sidebar.jsx'
import TopBar from './TopBar.jsx'
import { useLive } from '../hooks/useLive.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function AppShell({ user, onLogout, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { meta } = useLive()
  const { t, lang } = useLanguage()

  return (
    <div className="ns-shell">
      <Sidebar user={user} mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      <div className="ns-main-wrapper">
        <TopBar user={user} onLogout={onLogout} onToggleSidebar={() => setMobileOpen(!mobileOpen)} />
        {meta?.data_mode === 'simulated_demo' && (
          <div className="ns-banner">
            <span><strong>{t.banner?.demoTitle || 'Demo data mode:'}</strong> {t.banner?.demoText || 'Tamil Nadu telemetry, leak signals, and risk scores shown here are calibrated demo data for decision support.'}</span>
            <span style={{ padding: '2px 8px', borderRadius: 999, background: '#fff', border: '1px solid #fcd34d', fontSize: '0.7rem', fontWeight: 800 }}>DEMO DATA</span>
          </div>
        )}
        <main className="ns-content">{children}</main>
        <footer className="ns-app-footer" role="contentinfo">
          <div>
            <strong>NagarSync Enterprise</strong> <span style={{ margin: '0 6px', color: '#A2C2E2' }}>|</span>
            <span>{lang === 'ta' ? 'தமிழ்நாடு உள்கட்டமைப்பு புலனாய்வு மற்றும் ஒருங்கிணைந்த குடிமை சேவைகள்' : 'Tamil Nadu infrastructure intelligence and coordinated civic services'}</span>
          </div>
          <div className="ns-app-footer-links">
            <a href="/map">GIS</a>
            <a href="/directory">Directory</a>
            <a href="/public">Community</a>
            <span style={{ color: '#B0B0B0' }}>© 2026 NagarSync</span>
          </div>
        </footer>
      </div>
    </div>
  )
}
