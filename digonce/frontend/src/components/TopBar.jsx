import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Building2, LogOut, Radio, Languages } from 'lucide-react'
import NotificationBell from './NotificationBell.jsx'
import { Badge } from './ui/Primitives.jsx'
import { useLive } from '../hooks/useLive.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'

const ZONES = [
  'All Metro Zones (Statewide Overview)',
  'Zone 1 - North Metro Sector',
  'Zone 2 - Central Business District',
  'Zone 3 - Southern Tech Corridor',
  'Zone 4 - Industrial Arterials',
  'Zone 5 - Western Suburbs'
]

export default function TopBar({ user, onLogout, onToggleSidebar }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { connected, tick } = useLive()
  const { lang, setLang, t } = useLanguage()
  const [zone, setZone] = useState(ZONES[0])

  const role = user?.role || 'citizen'
  const roleBadgeVariant = role === 'admin' ? 'navy' : role === 'field_worker' ? 'gold' : 'ocean'
  const roleDisplay = role === 'admin' ? (t.roles?.admin || 'ADMIN') : role === 'field_worker' ? (t.roles?.field || 'FIELD ENGINEER') : (t.roles?.citizen || 'CITIZEN')
  const pathParts = location.pathname.split('/').filter(Boolean)
  const breadcrumb = pathParts.length === 0 ? (lang === 'ta' ? 'முகப்பு' : 'Home') : pathParts.map((p) => p.replace(/-/g, ' ')).join(' / ')

  return (
    <header className="ns-topbar">
      <div className="ns-topbar-left">
        <button type="button" onClick={onToggleSidebar} className="ns-btn ns-btn-secondary ns-btn-sm" aria-label="Toggle Navigation" style={{ padding: 6 }}>
          <Menu size={18} />
        </button>
        <span className="ns-breadcrumb">NagarSync / <strong style={{ textTransform: 'capitalize' }}>{breadcrumb}</strong></span>
        <div className="ns-zone-select">
          <Building2 size={13} />
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            {ZONES.map((z) => <option key={z} value={z}>{z}</option>)}
          </select>
        </div>
      </div>

      <div className="ns-topbar-right">
        <button type="button" className="ns-btn ns-btn-secondary ns-btn-sm" onClick={() => setLang(lang === 'en' ? 'ta' : 'en')} title={lang === 'en' ? 'Switch to Tamil' : 'Switch to English'} style={{ gap: 6 }}>
          <Languages size={14} />
          <span>{lang === 'en' ? 'தமிழ்' : 'English'}</span>
        </button>
        <div className={`ns-status-pill ${connected ? 'active' : 'standby'}`} title={connected ? `${t.telemetryLive || 'Telemetry synchronized'} (${tick})` : (t.telemetryOffline || 'Telemetry standby')}>
          <Radio size={13} />
          <span>{connected ? `${t.telemetryLive || 'TELEMETRY SYNCHRONIZED'} · ${tick}` : (t.telemetryOffline || 'TELEMETRY STANDBY')}</span>
        </div>
        <NotificationBell user={user} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', borderLeft: '1px solid var(--ns-border)', paddingLeft: '0.75rem' }}>
          <Badge variant={roleBadgeVariant}>{roleDisplay}</Badge>
          <span style={{ fontSize: '0.82rem', fontWeight: 700 }}>{user?.name || user?.email?.split('@')[0] || 'User'}</span>
          <button type="button" onClick={() => { onLogout(); navigate('/login') }} title={lang === 'ta' ? 'வெளியேறு' : 'Sign out'} style={{ background: 'none', border: 'none', color: 'var(--ns-muted)', cursor: 'pointer', padding: 4 }}>
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  )
}
