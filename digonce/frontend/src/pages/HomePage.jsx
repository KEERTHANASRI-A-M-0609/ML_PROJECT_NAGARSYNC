import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  ClipboardList,
  Layers,
  MapPinned,
  ShieldCheck,
  Users,
} from 'lucide-react'

const services = [
  {
    icon: ClipboardList,
    title: 'Report an issue',
    description: 'Sign in to submit and follow a local infrastructure report.',
    to: '/login?mode=register',
    label: 'Get started',
  },
  {
    icon: MapPinned,
    title: 'Explore the infrastructure map',
    description: 'View the demonstration’s modeled assets and locations.',
    to: '/login',
    label: 'Sign in to explore',
  },
  {
    icon: BarChart3,
    title: 'Municipal operations',
    description: 'Authorized teams can review priorities and coordinate work.',
    to: '/login',
    label: 'Staff sign in',
  },
]

function getWorkspace(user) {
  if (user?.role === 'admin') return { to: '/dashboard', label: 'Open operations dashboard' }
  if (user?.role === 'field_worker') return { to: '/field', label: 'Open field work' }
  if (user?.role === 'citizen') return { to: '/public', label: 'Open my reports' }
  return null
}

export default function HomePage({ user }) {
  const workspace = getWorkspace(user)

  return (
    <main className="home-page">
      <div className="home-notice">
        <span><ShieldCheck size={15} aria-hidden="true" /> NagarSync civic infrastructure platform</span>
        <span>Independent demonstration · Not an official government service</span>
      </div>

      <header className="home-header">
        <Link to="/" className="home-brand" aria-label="NagarSync home">
          <span className="home-brand-mark"><Layers size={21} aria-hidden="true" /></span>
          <span>
            <strong>NagarSync</strong>
            <small>Tamil Nadu demonstration</small>
          </span>
        </Link>
        <nav className="home-nav" aria-label="Main navigation">
          <a href="#services">Services</a>
          <a href="#about">About the demo</a>
          {user ? (
            <Link className="home-nav-primary" to={workspace?.to || '/public'}>
              {workspace?.label || 'Open workspace'} <ArrowRight size={16} aria-hidden="true" />
            </Link>
          ) : (
            <>
              <Link className="home-nav-signin" to="/login">Sign in</Link>
              <Link className="home-nav-primary" to="/login?mode=register">
                Create account <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="home-eyebrow"><MapPinned size={15} aria-hidden="true" /> PUBLIC SERVICE EXPERIENCE · TAMIL NADU</span>
          <h1>Better coordinated infrastructure. Stronger communities.</h1>
          <p>
            NagarSync brings residents and municipal teams together to report infrastructure
            concerns, review modeled asset priorities, and coordinate maintenance planning.
          </p>
          <div className="home-actions">
            {workspace ? (
              <Link to={workspace.to} className="home-button home-button-primary">
                {workspace.label} <ArrowRight size={17} aria-hidden="true" />
              </Link>
            ) : (
              <>
                <Link to="/login?mode=register" className="home-button home-button-primary">
                  Create a resident account <ArrowRight size={17} aria-hidden="true" />
                </Link>
                <Link to="/login" className="home-button home-button-secondary">Sign in</Link>
              </>
            )}
          </div>
          <div className="home-trust-line">
            <Users size={16} aria-hidden="true" />
            <span>Designed for residents, field teams, and municipal administrators</span>
          </div>
        </div>
        <aside className="home-hero-card" aria-label="Demonstration overview">
          <div className="home-card-topline">
            <span className="home-card-icon"><Layers size={19} aria-hidden="true" /></span>
            <span className="home-demo-tag">DEMONSTRATION</span>
          </div>
          <h2>One place to coordinate civic work</h2>
          <p>Explore the sample workflows for reporting, asset review, and maintenance planning.</p>
          <div className="home-card-divider" />
          <div className="home-card-detail">
            <span>Sample coverage</span>
            <strong>37 Tamil Nadu districts</strong>
          </div>
          <div className="home-card-detail">
            <span>Data status</span>
              <strong><span className="home-status-dot" /> Simulated demonstration data</strong>
          </div>
        </aside>
      </section>

      <section id="services" className="home-services">
        <div className="home-section-heading">
          <span className="home-eyebrow">GET STARTED</span>
          <h2>What would you like to do?</h2>
          <p>Choose a service to continue. Some areas require an account and the appropriate role.</p>
        </div>
        <div className="home-service-grid">
          {services.map(({ icon: Icon, title, description, to, label }) => (
            <Link
              key={title}
              className="home-service-card"
              to={to}
              state={to === '/login' ? { from: title === 'Explore the infrastructure map' ? '/map' : '/dashboard' } : undefined}
            >
              <span className="home-service-icon"><Icon size={20} aria-hidden="true" /></span>
              <span className="home-service-title">{title}</span>
              <span className="home-service-description">{description}</span>
              <span className="home-service-link">{label} <ArrowRight size={15} aria-hidden="true" /></span>
            </Link>
          ))}
        </div>
      </section>

      <section id="about" className="home-about">
        <div>
          <span className="home-eyebrow">ABOUT THIS PLATFORM</span>
          <h2>A practical demonstration of connected civic services.</h2>
        </div>
        <p>
          The asset inventory, locations, and analytics shown here are illustrative sample data
          for 37 districts—not verified municipal records, real-time alerts, engineering assessments,
          or official government services. Recommendations are examples for decision support only.
        </p>
      </section>

      <footer className="home-footer">
        <Link to="/" className="home-footer-brand"><Layers size={17} aria-hidden="true" /> NagarSync</Link>
        <span>Academic demonstration · Tamil Nadu sample data</span>
        <Link to="/login">Account access</Link>
      </footer>
    </main>
  )
}
