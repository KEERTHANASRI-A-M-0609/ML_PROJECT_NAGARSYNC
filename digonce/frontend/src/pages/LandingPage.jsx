import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  ArrowRight,
  BarChart3,
  Building2,
  Camera,
  CheckCircle2,
  Cpu,
  Layers,
  MapPin,
  Radar,
  ShieldCheck,
  Sparkles,
  Wrench,
} from 'lucide-react'
import { useLive } from '../hooks/useLive.jsx'
import { getSummary } from '../api.js'
import { useApi } from '../utils.js'
import heroImage from '../assets/hero.png'
import '../styles/animations.css'

const SLIDES = [
  {
    src: heroImage,
    alt: 'Coordinated urban infrastructure corridor',
    title: 'Unified Infrastructure Operations',
    text: 'Monitor roads, pipelines, lighting, and civic assets through one enterprise command platform.',
  },
  {
    src: 'https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=1600&q=80',
    alt: 'Geospatial infrastructure planning view',
    title: 'Geospatial Intelligence at Scale',
    text: 'Visualize asset condition, risk concentration, and maintenance priorities across districts.',
  },
  {
    src: 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1600&q=80',
    alt: 'Infrastructure operations control environment',
    title: 'Predictive Maintenance Command',
    text: 'Coordinate field teams, analytics, and service workflows with calibrated decision support.',
  },
  {
    src: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80',
    alt: 'Modern metropolitan infrastructure skyline',
    title: 'Resilient Civic Service Delivery',
    text: 'Strengthen transparency, response coordination, and long-term infrastructure planning.',
  },
]

const CAPABILITIES = [
  {
    icon: Cpu,
    title: 'Predictive Risk Intelligence',
    text: 'Calibrated models prioritize assets by condition, consequence, and maintenance urgency.',
    image: 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=900&q=80',
  },
  {
    icon: Wrench,
    title: 'DigOnce Coordination',
    text: 'Synchronize multi-utility interventions to reduce repeated excavation and service disruption.',
    image: 'https://images.unsplash.com/photo-1578965879900-b610c1f6d3f2?auto=format&fit=crop&w=900&q=80',
  },
  {
    icon: Activity,
    title: 'Telemetry-Driven Monitoring',
    text: 'Track operational signals, incident patterns, and maintenance outcomes in one workspace.',
    image: 'https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=900&q=80',
  },
]

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

export default function LandingPage({ user }) {
  const { connected, tick } = useLive()
  const { data: summary } = useApi(getSummary)
  const [slide, setSlide] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setSlide((s) => (s + 1) % SLIDES.length), 5200)
    return () => clearInterval(id)
  }, [])

  const citizenLink = user ? '/public' : '/login'
  const authorityLink = user?.role === 'admin' ? '/dashboard' : '/login'
  const mapLink = user ? '/map' : '/login'

  const stats = [
    { label: 'Monitored Assets', value: summary?.kpis?.total_assets ?? '1,420+' },
    { label: 'High-Priority Risks', value: summary?.kpis?.critical_or_high_risk ?? '184' },
    { label: 'Resolved Service Reports', value: summary?.kpis?.resolved_reports ?? '892' },
    { label: 'Active Programs', value: summary?.kpis?.active_projects ?? '38' },
  ]

  return (
    <div style={{ minHeight: '100vh', background: '#FFFFFF', color: '#003366' }}>
      <div style={{ background: '#003366', color: '#FFFFFF', borderBottom: '1px solid #006699' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0.55rem 1.25rem', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', fontSize: '0.78rem', fontWeight: 700 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={14} color="#FFCC00" /> NagarSync Enterprise Infrastructure Intelligence Platform
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: connected ? '#0099CC' : '#FF9933', boxShadow: connected ? '0 0 0 4px rgba(0,153,204,0.18)' : 'none' }} />
            {connected ? `TELEMETRY SYNC · CYCLE ${tick}` : 'TELEMETRY STANDBY'}
          </span>
        </div>
      </div>

      <header style={{ position: 'sticky', top: 0, zIndex: 50, background: 'rgba(255,255,255,0.94)', backdropFilter: 'blur(14px)', borderBottom: '1px solid #A2C2E2' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0.85rem 1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: '#003366' }}>
            <span style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg,#003366,#006699)', color: '#FFFFFF', display: 'grid', placeItems: 'center' }}><Layers size={20} /></span>
            <span>
              <div style={{ fontWeight: 900, fontSize: '1.2rem', lineHeight: 1.1 }}>NagarSync</div>
              <div style={{ fontSize: '0.66rem', fontWeight: 700, color: '#006699', letterSpacing: '0.06em' }}>CIVIC INFRASTRUCTURE PLATFORM</div>
            </span>
          </Link>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap', fontSize: '0.88rem', fontWeight: 700, color: '#006699' }}>
            <a href="#capabilities" style={{ color: 'inherit', textDecoration: 'none' }}>Capabilities</a>
            <a href="#operations" style={{ color: 'inherit', textDecoration: 'none' }}>Operations</a>
            <a href="#community" style={{ color: 'inherit', textDecoration: 'none' }}>Community</a>
          </nav>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Link to={citizenLink} className="btn-cinema-secondary" style={{ textDecoration: 'none' }}>Citizen Portal</Link>
            <Link to={authorityLink} className="btn-cinema-primary" style={{ textDecoration: 'none' }}>Authority Access <ArrowRight size={15} /></Link>
          </div>
        </div>
      </header>

      <main>
        <section style={{ maxWidth: 1400, margin: '0 auto', padding: '2rem 1.25rem 1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 24, alignItems: 'center' }}>
          <motion.div variants={fadeUp} initial="hidden" animate="show">
            <div className="glow-pill" style={{ marginBottom: 16 }}><Radar size={14} color="#006699" /> ENTERPRISE INFRASTRUCTURE COMMAND</div>
            <h1 style={{ fontSize: 'clamp(2.1rem,4.4vw,3.8rem)', lineHeight: 1.08, letterSpacing: '-0.03em', margin: '0 0 1rem', color: '#003366' }}>
              Professional, predictive, and coordinated urban infrastructure management.
            </h1>
            <p style={{ fontSize: '1.05rem', lineHeight: 1.7, color: '#006699', maxWidth: 640, margin: '0 0 1.5rem' }}>
              NagarSync integrates geospatial visibility, predictive analytics, citizen reporting, and field coordination to support reliable, data-driven infrastructure operations.
            </p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: '1.5rem' }}>
              <Link to={mapLink} className="btn-cinema-primary" style={{ textDecoration: 'none' }}><MapPin size={16} /> Explore Spatial Map</Link>
              <Link to={citizenLink} className="btn-cinema-secondary" style={{ textDecoration: 'none' }}><Camera size={16} /> Submit Service Report</Link>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 12 }}>
              {stats.map((s, i) => (
                <motion.div key={s.label} className="glass-panel" variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} transition={{ delay: i * 0.05 }} style={{ padding: '1rem' }}>
                  <div style={{ fontSize: '1.7rem', fontWeight: 900, color: i === 1 ? '#FF9933' : '#003366' }}>{s.value}</div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#006699' }}>{s.label}</div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }} className="hero-slideshow" aria-label="Infrastructure slideshow">
            <AnimatePresence mode="wait">
              <motion.div
                key={slide}
                className="hero-slide active"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.8 }}
              >
                <img src={SLIDES[slide].src} alt={SLIDES[slide].alt} />
                <div className="hero-slide-overlay" />
                <div className="hero-slide-caption">
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: '0.72rem', fontWeight: 800, letterSpacing: '0.08em', color: '#A2C2E2' }}>
                    <ShieldCheck size={14} color="#FFCC00" /> NAGARSYNC OPERATIONS VIEW
                  </div>
                  <h2 style={{ margin: '0.35rem 0 0.2rem', fontSize: '1.6rem', lineHeight: 1.2 }}>{SLIDES[slide].title}</h2>
                  <p style={{ margin: 0, maxWidth: 520, color: '#FFFFFF', fontSize: '0.95rem', lineHeight: 1.5 }}>{SLIDES[slide].text}</p>
                  <div className="slide-dots" aria-label="Slideshow controls">
                    {SLIDES.map((_, i) => (
                      <button key={i} className={`slide-dot ${i === slide ? 'active' : ''}`} onClick={() => setSlide(i)} aria-label={`Show slide ${i + 1}`} />
                    ))}
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          </motion.div>
        </section>

        <section id="capabilities" style={{ maxWidth: 1400, margin: '0 auto', padding: '3.5rem 1.25rem 1rem' }}>
          <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 800, letterSpacing: '0.1em', color: '#006699' }}>ENTERPRISE CAPABILITIES</div>
            <h2 style={{ fontSize: '2.2rem', margin: '0.35rem 0 0.5rem', color: '#003366' }}>Integrated intelligence for civic infrastructure</h2>
            <p style={{ margin: 0, maxWidth: 760, color: '#006699', lineHeight: 1.7 }}>
              A unified workspace for planning, monitoring, response, and transparent service coordination across urban infrastructure domains.
            </p>
          </motion.div>
          <div style={{ marginTop: 20, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 18 }}>
            {CAPABILITIES.map((c, i) => {
              const Icon = c.icon
              return (
                <motion.article key={c.title} className="glass-panel glass-panel-hover" variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} transition={{ delay: i * 0.06 }} style={{ overflow: 'hidden' }}>
                  <div className="image-card" style={{ height: 180, border: 0, borderRadius: 0, borderBottom: '1px solid #A2C2E2' }}>
                    <img src={c.image} alt={c.title} loading="lazy" />
                  </div>
                  <div style={{ padding: '1.15rem' }}>
                    <div style={{ width: 40, height: 40, borderRadius: 10, background: '#A2C2E2', color: '#003366', display: 'grid', placeItems: 'center', marginBottom: 10 }}><Icon size={20} /></div>
                    <h3 style={{ margin: '0 0 0.35rem', fontSize: '1.05rem', color: '#003366' }}>{c.title}</h3>
                    <p style={{ margin: 0, color: '#006699', fontSize: '0.9rem', lineHeight: 1.6 }}>{c.text}</p>
                  </div>
                </motion.article>
              )
            })}
          </div>
        </section>

        <section id="operations" style={{ marginTop: 28, padding: '3.5rem 1.25rem', background: 'linear-gradient(180deg,#FFFFFF 0%, #FFFFFF 100%)', borderTop: '1px solid #A2C2E2', borderBottom: '1px solid #A2C2E2' }}>
          <div style={{ maxWidth: 1400, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 22, alignItems: 'center' }}>
            <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 800, letterSpacing: '0.1em', color: '#006699' }}>OPERATIONS WORKFLOW</div>
              <h2 style={{ fontSize: '2rem', margin: '0.35rem 0 0.6rem', color: '#003366' }}>From signal to coordinated action</h2>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 12 }}>
                {[
                  ['Monitor infrastructure condition', 'Aggregate telemetry, inspections, and service reports into a unified operational picture.'],
                  ['Prioritize with analytics', 'Rank risks and interventions using calibrated planning and impact-aware scoring.'],
                  ['Coordinate field execution', 'Dispatch crews, track work orders, and document verified completion evidence.'],
                ].map(([title, text]) => (
                  <li key={title} className="glass-panel" style={{ padding: '0.9rem 1rem', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <CheckCircle2 size={18} color="#0099CC" style={{ marginTop: 2, flex: '0 0 auto' }} />
                    <div>
                      <div style={{ fontWeight: 800, color: '#003366', marginBottom: 2 }}>{title}</div>
                      <div style={{ color: '#006699', fontSize: '0.88rem', lineHeight: 1.55 }}>{text}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </motion.div>
            <motion.div className="glass-panel" variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} style={{ overflow: 'hidden' }}>
              <div className="image-card" style={{ height: 320, border: 0, borderRadius: 0 }}>
                <img src="https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&q=80" alt="Operations coordination center" loading="lazy" />
              </div>
              <div style={{ padding: '1rem 1.1rem', display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, borderTop: '1px solid #A2C2E2' }}>
                <div><div style={{ fontSize: '0.72rem', color: '#006699', fontWeight: 700 }}>ANALYTICS</div><div style={{ fontWeight: 800, color: '#003366' }}><BarChart3 size={16} style={{ verticalAlign: '-2px' }} /> Calibrated</div></div>
                <div><div style={{ fontSize: '0.72rem', color: '#006699', fontWeight: 700 }}>MOBILIZATION</div><div style={{ fontWeight: 800, color: '#003366' }}><Building2 size={16} style={{ verticalAlign: '-2px' }} /> Coordinated</div></div>
                <div><div style={{ fontSize: '0.72rem', color: '#006699', fontWeight: 700 }}>STATUS</div><div style={{ fontWeight: 800, color: connected ? '#0099CC' : '#FF9933' }}>{connected ? 'Synchronized' : 'Standby'}</div></div>
              </div>
            </motion.div>
          </div>
        </section>

        <section id="community" style={{ maxWidth: 1400, margin: '0 auto', padding: '3.5rem 1.25rem 4rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 22 }}>
          <motion.div className="ns-card" variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
            <div className="image-card" style={{ height: 220, border: 0, borderRadius: 0 }}>
              <img src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80" alt="Urban community and infrastructure" loading="lazy" />
            </div>
            <div className="ns-card-body">
              <div style={{ fontSize: '0.75rem', fontWeight: 800, letterSpacing: '0.1em', color: '#006699' }}>COMMUNITY ENGAGEMENT</div>
              <h2 style={{ margin: '0.35rem 0 0.5rem', fontSize: '1.6rem', color: '#003366' }}>Transparent reporting and verified resolution</h2>
              <p style={{ margin: 0, color: '#006699', lineHeight: 1.7 }}>Enable residents to submit geo-tagged concerns, follow local updates, and track service progress through a structured civic workflow.</p>
              <div style={{ marginTop: 14 }}><Link to={citizenLink} className="ns-btn ns-btn-primary" style={{ textDecoration: 'none' }}>Open Citizen Portal <ArrowRight size={15} /></Link></div>
            </div>
          </motion.div>
          <motion.div className="ns-card" variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
            <div className="ns-card-body" style={{ display: 'grid', gap: 12 }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 800, letterSpacing: '0.1em', color: '#006699' }}>PLATFORM ASSURANCE</div>
              {[
                'Role-based access for citizens, field teams, and administrators',
                'Professional telemetry and status indicators for operational awareness',
                'Unified design system for consistent, enterprise-grade user experience',
                'Demonstration analytics and sample data for planning workflows',
              ].map((item) => (
                <div key={item} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '0.75rem 0.85rem', border: '1px solid #A2C2E2', borderRadius: 12, background: '#FFFFFF' }}>
                  <ShieldCheck size={18} color="#0099CC" style={{ marginTop: 1, flex: '0 0 auto' }} />
                  <span style={{ color: '#003366', fontSize: '0.92rem', lineHeight: 1.55 }}>{item}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </section>
      </main>

      <footer style={{ background: '#003366', color: '#FFFFFF', borderTop: '4px solid #FF9933' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '2rem 1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 20 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ width: 34, height: 34, borderRadius: 8, background: '#006699', display: 'grid', placeItems: 'center' }}><Layers size={18} /></span>
              <strong style={{ fontSize: '1.2rem' }}>NagarSync</strong>
            </div>
            <p style={{ margin: 0, color: '#A2C2E2', fontSize: '0.86rem', lineHeight: 1.65 }}>Enterprise civic infrastructure intelligence platform for predictive maintenance, coordinated operations, and transparent public service delivery.</p>
          </div>
          <div>
            <div style={{ fontWeight: 800, marginBottom: 8, fontSize: '0.85rem' }}>WORKSPACES</div>
            <div style={{ display: 'grid', gap: 6, color: '#A2C2E2', fontSize: '0.86rem' }}>
              <Link to="/map" style={{ color: 'inherit', textDecoration: 'none' }}>Spatial GIS Map</Link>
              <Link to="/planner" style={{ color: 'inherit', textDecoration: 'none' }}>Predictive Planning</Link>
              <Link to="/attention" style={{ color: 'inherit', textDecoration: 'none' }}>Risk Priorities</Link>
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 800, marginBottom: 8, fontSize: '0.85rem' }}>OPERATIONS</div>
            <div style={{ display: 'grid', gap: 6, color: '#A2C2E2', fontSize: '0.86rem' }}>
              <Link to="/public" style={{ color: 'inherit', textDecoration: 'none' }}>Citizen Portal</Link>
              <Link to="/field" style={{ color: 'inherit', textDecoration: 'none' }}>Field Operations</Link>
              <Link to="/governance" style={{ color: 'inherit', textDecoration: 'none' }}>Development Programs</Link>
            </div>
          </div>
        </div>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0.9rem 1.25rem 1.4rem', borderTop: '1px solid rgba(162,194,226,0.25)', color: '#A2C2E2', fontSize: '0.78rem', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <span>© 2026 NagarSync Enterprise. Demonstration platform for infrastructure coordination.</span>
          <span>Telemetry and analytics shown for planning support.</span>
        </div>
      </footer>
    </div>
  )
}
