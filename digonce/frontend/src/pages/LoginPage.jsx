import { useState } from 'react'
import { useLocation, useNavigate, Link, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Eye, EyeOff, ShieldCheck, Lock, CheckCircle2, Activity, LayoutDashboard, MapPin, Radio } from 'lucide-react'
import { authLogin, authRegister } from '../api.js'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const PASSWORD_RULE = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{16,}$/

function validateAuth({ email, password, isSignup, name }) {
  const e = (email || '').trim()
  if (!EMAIL_RE.test(e)) return 'Enter a valid email address.'
  if (isSignup) {
    if (!(name || '').trim()) return 'Full name is required.'
    if (!PASSWORD_RULE.test(password || '')) {
      return 'Password must be at least 16 characters and include uppercase, lowercase, number, and special character.'
    }
  } else if (!password) {
    return 'Password is required.'
  }
  return ''
}

function authErrorMessage(error, action) {
  const detail = error.response?.data?.detail
  if (error.code === 'ECONNABORTED') return 'Sign-in timed out. Check the service connection and try again.'
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ')
  if (typeof detail === 'string') {
    if (detail === 'Email already registered') return 'This email already has an account. Sign in instead.'
    return detail
  }
  if (!error.response) return 'Could not reach the API. Start the FastAPI backend on port 8000, then try again.'
  return `${action} failed (HTTP ${error.response.status}). Please try again.`
}

export default function LoginPage({ onLogin }) {
  const nav = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const isRegisterLink = searchParams.get('mode') === 'register'
  const [tab, setTab] = useState(isRegisterLink ? 'signup' : 'login')
  const [form, setForm] = useState({ email: '', password: '', name: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    const v = validateAuth({ email: form.email, password: form.password, isSignup: false })
    if (v) { setError(v); return }
    setLoading(true)
    try {
      const session = await authLogin({ email: form.email.trim(), password: form.password })
      onLogin(session)
      const defaultPath = session.user.role === 'admin'
        ? '/admin'
        : session.user.role === 'field_worker'
          ? '/field'
          : '/public'
      nav(location.state?.from || defaultPath, { replace: true })
    } catch (e) {
      setError(authErrorMessage(e, 'Sign in'))
    } finally {
      setLoading(false)
    }
  }

  const handleSignup = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    const v = validateAuth({ email: form.email, password: form.password, isSignup: true, name: form.name })
    if (v) { setError(v); return }
    setLoading(true)
    try {
      await authRegister({ email: form.email.trim(), password: form.password, name: form.name.trim() })
      setForm((c) => ({ ...c, password: '' }))
      setTab('login')
      setSuccess('Account created. Sign in to continue.')
    } catch (e) {
      setError(authErrorMessage(e, 'Account creation'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-shell">
      <motion.div
        className="login-layout"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
      >
        {/* Sign-in form */}
        <section className="login-card" aria-label="Access portal">
          <Link to="/" className="login-home-link">← NagarSync home</Link>
          <div className="login-brand login-form-brand">
            <span className="login-brand-mark"><ShieldCheck size={20} /></span>
            <span>NagarSync</span>
          </div>
            <div className="login-card-heading">
              <span className="login-card-kicker">SECURE CIVIC SERVICES PORTAL</span>
              <h2>{tab === 'login' ? 'Welcome back' : 'Create your account'}</h2>
              <p>{tab === 'login' ? 'Sign in to access your citizen, field, or admin workspace and participate in area governance.' : 'Create a citizen account to follow your area, join the community forum, and report local issues.'}</p>
            </div>

          <div className="login-tabs" role="tablist">
            <button type="button" role="tab" aria-selected={tab === 'login'} className={tab === 'login' ? 'is-active' : ''} onClick={() => { setTab('login'); setError(''); setSuccess('') }}>Sign in</button>
            <button type="button" role="tab" aria-selected={tab === 'signup'} className={tab === 'signup' ? 'is-active' : ''} onClick={() => { setTab('signup'); setError(''); setSuccess('') }}>Create account</button>
          </div>

          {tab === 'login' ? (
            <form className="login-form" onSubmit={handleLogin}>
              <div className="login-field">
                <label htmlFor="login-email">Email address</label>
                <input id="login-email" value={form.email} onChange={(e) => set('email', e.target.value)} type="email" autoComplete="email" placeholder="you@example.com" pattern="^[^\s@]+@[^\s@]+\.[^\s@]{2,}$" required />
              </div>
              <div className="login-field">
                <label htmlFor="login-password">Password</label>
                <div className="password-field">
                  <input id="login-password" value={form.password} onChange={(e) => set('password', e.target.value)} type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" required />
                  <button type="button" className="password-visibility" aria-label={showPassword ? 'Hide' : 'Show'} onClick={() => setShowPassword((v) => !v)}>
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </div>
              <p className="login-role-note"><Lock size={12} /> Your workspace is selected automatically from your account.</p>
              <button className="btn btn-primary login-submit" disabled={loading}>
                {loading ? 'Signing in…' : <>Sign in securely <ArrowRight size={17} /></>}
              </button>
            </form>
          ) : (
            <form className="login-form" onSubmit={handleSignup}>
              <div className="login-field">
                <label htmlFor="signup-name">Full name</label>
                <input id="signup-name" value={form.name} onChange={(e) => set('name', e.target.value)} autoComplete="name" placeholder="Your full name" required />
              </div>
              <div className="login-field">
                <label htmlFor="signup-email">Email address</label>
                <input id="signup-email" value={form.email} onChange={(e) => set('email', e.target.value)} type="email" autoComplete="email" placeholder="you@example.com" pattern="^[^\s@]+@[^\s@]+\.[^\s@]{2,}$" required />
              </div>
              <div className="login-field">
                <label htmlFor="signup-password">Create password</label>
                <input id="signup-password" value={form.password} onChange={(e) => set('password', e.target.value)} type="password" autoComplete="new-password" placeholder="Minimum 16 characters" minLength={16} maxLength={200} required />
                <small className="login-field-hint">Use at least 16 characters with uppercase, lowercase, number, and special character.</small>
              </div>
              <p className="login-role-note">Registering as a public citizen. Authority accounts are provisioned by administrators.</p>
              <button className="btn btn-primary login-submit" disabled={loading}>
                {loading ? 'Creating account…' : <>Create account <ArrowRight size={17} /></>}
              </button>
            </form>
          )}

          {success && <div className="login-feedback login-feedback-success" role="status">{success}</div>}
          {error && <div className="login-feedback login-feedback-error" role="alert">{error}</div>}
          <p className="login-card-foot"><ShieldCheck size={15} /> Demo service · Role checks are enforced by the server</p>
        </section>

        {/* Platform overview */}
        <section className="login-intro" aria-label="NagarSync platform overview">
          <div className="login-brand">
            <span className="login-brand-mark"><ShieldCheck size={20} /></span>
            <span>NagarSync <small>INFRASTRUCTURE OS</small></span>
          </div>
              <div className="login-intro-copy">
                <span className="login-eyebrow"><Lock size={13} /> CONNECTED CIVIC OPERATIONS</span>
                <h1>One clear view of your area.</h1>
                <p>Report issues, follow local progress, join the area forum, and coordinate governance actions from one secure workspace.</p>
            <div className="login-visual" aria-hidden="true">
              <div className="login-visual-orbit">
                <span className="login-visual-node node-map"><MapPin size={19} /></span>
                <span className="login-visual-node node-activity"><Activity size={19} /></span>
                <span className="login-visual-node node-radio"><Radio size={19} /></span>
                <span className="login-visual-line line-one" />
                <span className="login-visual-line line-two" />
                <div className="login-visual-card">
                  <div className="login-visual-card-head"><LayoutDashboard size={15} /><span>City overview</span><i /></div>
                  <div className="login-visual-stat"><span className="stat-dot" /><span><b>Infrastructure</b><small>Synchronized condition monitoring</small></span><CheckCircle2 size={15} /></div>
                  <div className="login-visual-stat"><span className="stat-dot stat-dot-orange" /><span><b>Field operations</b><small>Work orders coordinated</small></span><ArrowRight size={15} /></div>
                  <div className="login-visual-stat"><span className="stat-dot stat-dot-light" /><span><b>Community reports</b><small>Updates in one place</small></span><CheckCircle2 size={15} /></div>
                </div>
              </div>
            </div>
          </div>
          <p className="login-intro-foot"><ShieldCheck size={13} /> Secure access for citizens, authorities, and field teams</p>
        </section>
      </motion.div>
    </main>
  )
}
