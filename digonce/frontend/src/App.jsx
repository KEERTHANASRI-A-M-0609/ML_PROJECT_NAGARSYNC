import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import LoginPage from './pages/LoginPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import Dashboard from './pages/Dashboard.jsx'
import CityMap from './pages/CityMap.jsx'
import Planner from './pages/Planner.jsx'
import Experiments from './pages/Experiments.jsx'
import LeaksTraffic from './pages/LeaksTraffic.jsx'
import AssetInspector from './pages/AssetInspector.jsx'
import AgentPage from './pages/AgentPage.jsx'
import PublicPage from './pages/PublicPage.jsx'
import AdminConsole from './pages/AdminConsole.jsx'
import AdminCrudPage from './pages/AdminCrudPage.jsx'
import CitizenReport from './pages/CitizenReport.jsx'
import FieldWorkerPortal from './pages/FieldWorkerPortal.jsx'
import AttentionAreas from './pages/AttentionAreas.jsx'
import AuditLog from './pages/AuditLog.jsx'
import WardDashboard from './pages/WardDashboard.jsx'
import GovernancePage from './pages/GovernancePage.jsx'
import DistrictDirectoryPage from './pages/DistrictDirectoryPage.jsx'
import DistrictProfilePage from './pages/DistrictProfilePage.jsx'
import OfficerDirectoryPage from './pages/OfficerDirectoryPage.jsx'
import OfficeLocatorPage from './pages/OfficeLocatorPage.jsx'
import FindLocalOfficerPage from './pages/FindLocalOfficerPage.jsx'
import PublicServicesPage from './pages/PublicServicesPage.jsx'
import AppShell from './components/AppShell.jsx'
import { LiveProvider } from './hooks/useLive.jsx'
import { authMe, authLogout } from './api.js'
import './styles/theme.css'

function ProtectedRoute({ user, roles, children, authLoading }) {
  const location = useLocation()
  if (authLoading) return <div className="page loading-screen" style={{ padding: '3rem', textAlign: 'center' }}>Authenticating NagarSync Session…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(user.role)) {
    if (user.role === 'citizen') return <Navigate to="/public" replace />
    if (user.role === 'field_worker') return <Navigate to="/field" replace />
    return <Navigate to="/dashboard" replace />
  }
  return children
}

function PageFade({ children }) {
  const loc = useLocation()
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={loc.pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.2 }}
        style={{ width: '100%' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

function ContentRoutes({ user, authLoading, onLogin }) {
  const location = useLocation()
  const isPublicLanding = location.pathname === '/'
  const isLoginPage = location.pathname === '/login'

  if (isPublicLanding) {
    return <LandingPage user={user} />
  }

  if (isLoginPage) {
    return authLoading ? (
      <div className="page loading-screen" style={{ padding: '3rem', textAlign: 'center' }}>Verifying credentials…</div>
    ) : (
      <LoginPage onLogin={onLogin} />
    )
  }

  return (
    <PageFade>
      <Routes>
        <Route path="/admin" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><AdminConsole user={user} /></ProtectedRoute>} />
        <Route path="/admin/records" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><AdminCrudPage /></ProtectedRoute>} />
        <Route path="/admin/wards" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><WardDashboard /></ProtectedRoute>} />
        <Route path="/admin/audit" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><AuditLog /></ProtectedRoute>} />
        <Route path="/governance" element={<ProtectedRoute user={user} authLoading={authLoading}><GovernancePage user={user} /></ProtectedRoute>} />
        <Route path="/attention" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><AttentionAreas user={user} /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin', 'field_worker']}><Dashboard user={user} /></ProtectedRoute>} />
        <Route path="/map" element={<ProtectedRoute user={user} authLoading={authLoading}><CityMap /></ProtectedRoute>} />
        <Route path="/directory" element={<ProtectedRoute user={user} authLoading={authLoading}><DistrictDirectoryPage /></ProtectedRoute>} />
        <Route path="/directory/districts/:districtId" element={<ProtectedRoute user={user} authLoading={authLoading}><DistrictProfilePage /></ProtectedRoute>} />
        <Route path="/directory/officers" element={<ProtectedRoute user={user} authLoading={authLoading}><OfficerDirectoryPage /></ProtectedRoute>} />
        <Route path="/directory/offices" element={<ProtectedRoute user={user} authLoading={authLoading}><OfficeLocatorPage /></ProtectedRoute>} />
        <Route path="/directory/find-local-officer" element={<ProtectedRoute user={user} authLoading={authLoading}><FindLocalOfficerPage /></ProtectedRoute>} />
        <Route path="/directory/services" element={<ProtectedRoute user={user} authLoading={authLoading}><PublicServicesPage /></ProtectedRoute>} />
        <Route path="/planner" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><Planner /></ProtectedRoute>} />
        <Route path="/field" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['field_worker', 'admin']}><FieldWorkerPortal user={user} /></ProtectedRoute>} />
        <Route path="/agent" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><AgentPage /></ProtectedRoute>} />
        <Route path="/public" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['citizen', 'field_worker', 'admin']}><PublicPage user={user} /></ProtectedRoute>} />
        <Route path="/report" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['citizen', 'admin']}><CitizenReport /></ProtectedRoute>} />
        <Route path="/experiments" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin']}><Experiments /></ProtectedRoute>} />
        <Route path="/leaks" element={<ProtectedRoute user={user} authLoading={authLoading}><LeaksTraffic /></ProtectedRoute>} />
        <Route path="/inspector" element={<ProtectedRoute user={user} authLoading={authLoading} roles={['admin', 'field_worker']}><AssetInspector /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </PageFade>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('ns_token'))
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    localStorage.removeItem('digonce_user')
    if (!token) {
      setAuthLoading(false)
      return
    }
    authMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('ns_token')
        localStorage.removeItem('ns_user')
        setToken(null)
      })
      .finally(() => setAuthLoading(false))
  }, [token])

  const handleLogin = (session) => {
    localStorage.setItem('ns_token', session.token)
    localStorage.removeItem('ns_user')
    setToken(session.token)
    setUser(session.user)
  }

  const handleLogout = async () => {
    try { await authLogout() } catch { /* clear session even if standby */ }
    localStorage.removeItem('ns_token')
    localStorage.removeItem('ns_user')
    setToken(null)
    setUser(null)
  }

  return (
    <BrowserRouter>
      <LiveProvider token={token}>
        <AppLayout user={user} onLogout={handleLogout}>
          <ContentRoutes user={user} authLoading={authLoading} onLogin={handleLogin} />
        </AppLayout>
      </LiveProvider>
    </BrowserRouter>
  )
}

function AppLayout({ user, onLogout, children }) {
  const location = useLocation()
  const isPublicLanding = location.pathname === '/'
  const isLoginPage = location.pathname === '/login'

  // Landing page and Login page render in their dedicated unboxed full-width layouts
  if (isPublicLanding || isLoginPage) {
    return children
  }

  // All authenticated workspaces render inside the enterprise AppShell (Sidebar + TopBar)
  return (
    <AppShell user={user} onLogout={onLogout}>
      {children}
    </AppShell>
  )
}
