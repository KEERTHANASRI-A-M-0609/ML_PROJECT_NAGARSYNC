import { NavLink } from 'react-router-dom'
import {
  Layers, LayoutDashboard, Map, AlertTriangle, ClipboardList, Cpu, Wrench,
  FolderGit2, BarChart3, ShieldCheck, FileCheck2, Users, Search, Radio, FileText, Camera, Building2, Landmark, UserSearch, HeartHandshake
} from 'lucide-react'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function Sidebar({ user, mobileOpen, onCloseMobile }) {
  const role = user?.role || 'citizen'
  const { t } = useLanguage()
  const itemClass = ({ isActive }) => `ns-nav-item ${isActive ? 'active' : ''}`

  return (
    <aside className={`ns-sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="ns-sidebar-header">
        <div className="ns-sidebar-brand-mark"><Layers size={20} /></div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="ns-sidebar-brand-title">NagarSync</span>
            <span style={{ fontSize: '0.62rem', padding: '2px 6px', background: 'rgba(255,255,255,0.16)', color: '#fff', fontWeight: 800, borderRadius: 6 }}>AI</span>
          </div>
          <div className="ns-sidebar-brand-sub">{t.brandSub || 'CIVIC INFRASTRUCTURE OS'}</div>
        </div>
      </div>

      <nav className="ns-sidebar-nav" onClick={onCloseMobile}>
        <span className="ns-sidebar-section-title">{t.nav?.corePlatform || 'CORE PLATFORM'}</span>
        {(role === 'admin' || role === 'field_worker') && <NavLink to="/dashboard" className={itemClass}><LayoutDashboard size={16} /><span>{t.nav?.command || 'Command Center'}</span></NavLink>}
        <NavLink to="/map" className={itemClass}><Map size={16} /><span>{t.nav?.map || 'Spatial GIS Map'}</span></NavLink>
        {(role === 'admin' || role === 'field_worker') && <NavLink to="/inspector" className={itemClass}><Search size={16} /><span>{t.nav?.assets || 'Asset Inspector'}</span></NavLink>}
        <NavLink to="/public" className={itemClass}><ClipboardList size={16} /><span>{role === 'citizen' ? (t.nav?.citizenPortal || 'Community Forum') : (t.nav?.issues || 'Area Forum & Updates')}</span></NavLink>
        {role === 'citizen' && <NavLink to="/report" className={itemClass}><Camera size={16} /><span>{t.nav?.reportIssue || 'Report an Issue'}</span></NavLink>}

        <span className="ns-sidebar-section-title">DISTRICT INTELLIGENCE</span>
        <NavLink to="/directory" className={itemClass}><Landmark size={16} /><span>{t.nav?.directory || 'District Directory'}</span></NavLink>
        <NavLink to="/directory/find-local-officer" className={itemClass}><UserSearch size={16} /><span>{t.nav?.findOfficer || 'Find Local Officer'}</span></NavLink>
        <NavLink to="/directory/officers" className={itemClass}><Users size={16} /><span>{t.nav?.officers || 'Officer Directory'}</span></NavLink>
        <NavLink to="/directory/offices" className={itemClass}><Building2 size={16} /><span>{t.nav?.offices || 'Office Locator'}</span></NavLink>
        <NavLink to="/directory/services" className={itemClass}><HeartHandshake size={16} /><span>{t.nav?.services || 'Public Services'}</span></NavLink>

        {(role === 'admin' || role === 'field_worker') && (
          <>
            <span className="ns-sidebar-section-title">{t.nav?.mlIntelligence || 'AI INTELLIGENCE'}</span>
            {role === 'admin' && <NavLink to="/planner" className={itemClass}><Cpu size={16} /><span>{t.nav?.planner || 'DigOnce Planner'}</span></NavLink>}
            {role === 'admin' && <NavLink to="/attention" className={itemClass}><AlertTriangle size={16} /><span>{t.nav?.hotspots || 'Risk Hotspots'}</span></NavLink>}
            <NavLink to="/leaks" className={itemClass}><Radio size={16} /><span>{t.nav?.sensors || 'Sensors & Telemetry'}</span></NavLink>
            {role === 'admin' && <NavLink to="/experiments" className={itemClass}><BarChart3 size={16} /><span>{t.nav?.modelLab || 'Model Lab'}</span></NavLink>}
          </>
        )}

        <span className="ns-sidebar-section-title">{t.nav?.operations || 'OPERATIONS'}</span>
        {(role === 'admin' || role === 'field_worker') && <NavLink to="/field" className={itemClass}><Wrench size={16} /><span>{t.nav?.maintenance || 'Maintenance Orders'}</span></NavLink>}
        <NavLink to="/governance" className={itemClass}><FolderGit2 size={16} /><span>{t.nav?.devProjects || 'Capital Works & Governance'}</span></NavLink>

        {role === 'admin' && (
          <>
            <span className="ns-sidebar-section-title">{t.nav?.administration || 'ADMINISTRATION'}</span>
            <NavLink to="/admin" className={itemClass}><ShieldCheck size={16} /><span>{t.nav?.authorityConsole || 'Operations Console'}</span></NavLink>
            <NavLink to="/admin/records" className={itemClass}><FileCheck2 size={16} /><span>{t.nav?.records || 'Manage Records'}</span></NavLink>
            <NavLink to="/admin/wards" className={itemClass}><Users size={16} /><span>{t.nav?.wardKpi || 'Zone Performance'}</span></NavLink>
            <NavLink to="/admin/audit" className={itemClass}><FileText size={16} /><span>{t.nav?.audit || 'Audit Logs'}</span></NavLink>
          </>
        )}
      </nav>

      <div className="ns-sidebar-footer">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <strong>Enterprise v3.0</strong>
          <span style={{ padding: '2px 7px', borderRadius: 999, background: 'rgba(255,255,255,0.14)', fontSize: '0.65rem', fontWeight: 800 }}>{t.enterpriseTag || 'AURORA'}</span>
        </div>
        <span>Predictive, coordinated, transparent civic ops</span>
      </div>
    </aside>
  )
}
