import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Building2, MapPin, Radio, AlertTriangle, Cpu, Wrench, Activity, ShieldCheck,
  Gauge, ArrowRight, Sparkles, Droplets, Route
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
  AreaChart, Area
} from 'recharts'
import { getWards, getLeaks, getIncidents, getReports } from '../api.js'
import { useLive } from '../hooks/useLive.jsx'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'

function clamp(n, min, max) { return Math.max(min, Math.min(max, n)) }

export default function Dashboard({ user }) {
  const { connected, tick, recommendations, meta, riskHistory } = useLive()
  const [wards, setWards] = useState([])
  const [leaks, setLeaks] = useState([])
  const [incidents, setIncidents] = useState([])
  const [reports, setReports] = useState([])
  const [selectedDistrict, setSelectedDistrict] = useState('All Districts')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.allSettled([
      getWards(), getLeaks(), getIncidents({ limit: 120 }), getReports({ limit: 120 }),
    ]).then(([wRes, lRes, iRes, rRes]) => {
      if (!active) return
      if (wRes.status === 'fulfilled') setWards(wRes.value || [])
      if (lRes.status === 'fulfilled') setLeaks(lRes.value || [])
      if (iRes.status === 'fulfilled') setIncidents(iRes.value || [])
      if (rRes.status === 'fulfilled') setReports(rRes.value || [])
      setLoading(false)
    })
    return () => { active = false }
  }, [])

  const districtList = useMemo(() => ['All Districts', ...Array.from(new Set(wards.map(w => w.district).filter(Boolean))).sort()], [wards])
  const filteredWards = useMemo(() => selectedDistrict === 'All Districts' ? wards : wards.filter(w => w.district === selectedDistrict), [wards, selectedDistrict])

  const totalAssets = filteredWards.reduce((s, w) => s + (w.n_assets || 0), 0)
  const criticalAssets = filteredWards.reduce((s, w) => s + (w.critical_count || 0), 0)
  const meanRiskPct = filteredWards.length ? (filteredWards.reduce((s, w) => s + (w.mean_risk || 0), 0) / filteredWards.length) * 100 : 0
  const activeWorkOrders = incidents.filter(i => selectedDistrict === 'All Districts' || i.district === selectedDistrict).filter(i => !['CLOSED', 'CANCELLED', 'REJECTED'].includes(i.status)).length
  const pendingReports = reports.filter(r => (selectedDistrict === 'All Districts' || r.district === selectedDistrict) && ['new', 'triaged', 'open'].includes((r.status || '').toLowerCase())).length

  const healthScore = Math.round(clamp(100 - meanRiskPct * 1.35 - (criticalAssets / Math.max(totalAssets, 1)) * 120 - Math.min(pendingReports, 40) * 0.4, 18, 99))
  const scoreTone = healthScore >= 75 ? '#0099CC' : healthScore >= 55 ? '#FF9933' : '#FF9933'

  const wardRiskChartData = useMemo(() => filteredWards
    .slice()
    .sort((a, b) => (b.mean_risk || 0) - (a.mean_risk || 0))
    .slice(0, 10)
    .map(w => ({ name: (w.district || `Ward ${w.ward}`).slice(0, 12), meanRisk: +((w.mean_risk || 0) * 100).toFixed(1), critical: w.critical_count || 0 })), [filteredWards])

  const pulseData = useMemo(() => (riskHistory || []).slice(-12).map((p, i) => ({
    label: p.tick ? `T${p.tick}` : `#${i + 1}`,
    meanRisk: +((p.meanRisk || 0) * 100).toFixed(2),
    maxRisk: +((p.maxRisk || p.meanRisk || 0) * 100).toFixed(2),
  })), [riskHistory])

  const criticalLeaks = useMemo(() => leaks.filter(l => (l.leak_score || 0) > 0.08).sort((a,b) => (b.leak_score||0)-(a.leak_score||0)).slice(0, 5), [leaks])
  const priorityFeed = useMemo(() => {
    const recs = (recommendations || []).slice(0, 3).map((r, i) => ({
      id: r.asset_id || `rec-${i}`,
      title: `${r.asset_id || 'Asset'} · ${(r.asset_type || 'repair').replace('_', ' ')}`,
      subtitle: r.district || r.corridor_id || 'Priority maintenance',
      value: `${((r.risk_score || 0) * 100).toFixed(0)}% risk`,
      tone: (r.risk_score || 0) > 0.8 ? 'tangerine' : 'amber',
      to: '/planner',
    }))
    const leakItems = criticalLeaks.slice(0, 2).map((l, i) => ({ id: l.asset_id || `leak-${i}`, title: `Leak signal · ${l.asset_id}`, subtitle: l.location || 'Hydraulic anomaly detected', value: `${((l.leak_score || 0) * 100).toFixed(0)}% anomaly`, tone: 'red', to: '/leaks' }))
    return [...recs, ...leakItems].slice(0, 5)
  }, [recommendations, criticalLeaks])

  const quickActions = [
    { label: 'Run DigOnce Planner', to: '/planner', icon: Cpu, variant: 'primary' },
    { label: 'Open GIS Map', to: '/map', icon: MapPin, variant: 'secondary' },
    { label: 'Dispatch Field Work', to: '/field', icon: Wrench, variant: 'secondary' },
    { label: 'Review Hotspots', to: '/attention', icon: AlertTriangle, variant: 'secondary' },
  ]

  return (
    <div style={{ display: 'grid', gap: '1.25rem' }}>
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="ns-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '1.3rem 1.4rem', background: 'linear-gradient(135deg,#003366 0%,#006699 55%,#0099CC 100%)', color: '#fff', display: 'grid', gridTemplateColumns: '1.4fr 0.8fr', gap: '1rem', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Badge variant="navy" style={{ background: 'rgba(255,255,255,0.16)', color: '#fff', borderColor: 'rgba(255,255,255,0.2)' }}>STATE COMMAND CENTER</Badge>
              <span style={{ fontSize: '0.75rem', opacity: 0.9 }}>Tamil Nadu Infrastructure Intelligence</span>
            </div>
            <h1 style={{ margin: 0, fontSize: '1.55rem', lineHeight: 1.15, letterSpacing: '-0.02em' }}>NagarSync Aurora Operations Dashboard</h1>
            <p style={{ margin: '0.5rem 0 0', color: 'rgba(255,255,255,0.86)', maxWidth: 760, fontSize: '0.9rem' }}>
              Unified situational awareness for predictive maintenance, leak signals, citizen reports, and DigOnce joint mobilisation.
            </p>
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginTop: '1rem' }}>
              {quickActions.map(({ label, to, icon: Icon, variant }) => (
                <Link key={label} to={to} style={{ textDecoration: 'none' }}>
                  <Button variant={variant === 'primary' ? 'primary' : 'secondary'} size="sm" icon={Icon} style={variant !== 'primary' ? { background: 'rgba(255,255,255,0.12)', color: '#fff', borderColor: 'rgba(255,255,255,0.22)' } : {}}>
                    {label}
                  </Button>
                </Link>
              ))}
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: 18, padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.05em' }}>CITY RESILIENCE INDEX</span>
              <Gauge size={16} />
            </div>
            <div style={{ display: 'flex', alignItems: 'end', gap: 8 }}>
              <div style={{ fontSize: '2.4rem', fontWeight: 900, lineHeight: 1, color: '#fff' }}>{healthScore}</div>
              <div style={{ fontSize: '0.8rem', opacity: 0.9, paddingBottom: 4 }}>/ 100</div>
            </div>
            <div style={{ height: 8, background: 'rgba(255,255,255,0.18)', borderRadius: 999, marginTop: 10, overflow: 'hidden' }}>
              <div style={{ width: `${healthScore}%`, height: '100%', background: 'linear-gradient(90deg,#0099CC,#0099CC,#fbbf24)' }} />
            </div>
            <div style={{ marginTop: 10, display: 'grid', gap: 4, fontSize: '0.75rem', color: 'rgba(255,255,255,0.9)' }}>
              <span>• Mean risk: {meanRiskPct.toFixed(1)}%</span>
              <span>• Critical assets: {criticalAssets.toLocaleString('en-IN')}</span>
              <span>• Pending citizen reports: {pendingReports}</span>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="ns-card" style={{ padding: '0.85rem 1rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '0.4rem 0.7rem', border: '1px solid var(--ns-border)', borderRadius: 999, background: '#fff' }}>
              <Building2 size={14} />
              <strong style={{ fontSize: '0.78rem' }}>Jurisdiction</strong>
              <select value={selectedDistrict} onChange={(e) => setSelectedDistrict(e.target.value)} style={{ border: 0, background: 'transparent', fontWeight: 700, color: 'var(--ns-ink)', outline: 'none' }}>
                {districtList.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <Badge variant={connected ? 'ocean' : 'gold'}>{connected ? `TELEMETRY SYNCHRONIZED · CYCLE ${tick}` : 'TELEMETRY STANDBY'}</Badge>
            <Badge variant="navy">{meta?.score_mode === 'simulated_condition_priority' ? 'CONDITION PRIORITY' : 'PREDICTIVE RISK MODEL'}</Badge>
          </div>
          <Link to="/planner" style={{ textDecoration: 'none' }}><Button variant="accent" size="sm" icon={Sparkles}>Open AI Recommender</Button></Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0,1fr))', gap: '0.9rem' }}>
        {[
          { label: 'Monitored Assets', value: totalAssets.toLocaleString('en-IN'), hint: `In ${selectedDistrict}`, tone: 'navy', icon: ShieldCheck },
          { label: 'Critical Risk Assets', value: criticalAssets.toLocaleString('en-IN'), hint: 'Need urgent triage', tone: 'tangerine', icon: AlertTriangle },
          { label: 'Mean Risk Index', value: `${meanRiskPct.toFixed(1)}%`, hint: 'District average', tone: 'amber', icon: Activity },
          { label: 'Active Work Orders', value: activeWorkOrders, hint: 'Field operations', tone: 'teal', icon: Wrench },
          { label: 'Reports in Queue', value: pendingReports, hint: 'Citizen submissions', tone: 'ocean', icon: Radio },
        ].map(({ label, value, hint, tone, icon: Icon }) => (
          <Card key={label} className="" bodyClassName="" style={{ borderColor: '#A2C2E2' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div>
                <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--ns-muted)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontSize: '1.7rem', fontWeight: 900, color: 'var(--ns-ink)', marginTop: 4, lineHeight: 1 }}>{loading ? '—' : value}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ns-muted)', marginTop: 6 }}>{hint}</div>
              </div>
              <div style={{ width: 34, height: 34, borderRadius: 10, display: 'grid', placeItems: 'center', background: 'var(--ns-bg-soft)', color: 'var(--ns-primary)' }}>
                <Icon size={16} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        <Card title={`Risk & Critical Distribution · ${selectedDistrict}`} subtitle="Top jurisdictions by mean degradation risk and flagged critical assets">
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wardRiskChartData} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#A2C2E2" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#006699' }} interval={0} angle={-18} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11, fill: '#006699' }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #A2C2E2', boxShadow: '0 10px 24px rgba(0, 51, 102, 0.12)' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="meanRisk" name="Mean Risk %" fill="#0099CC" radius={[8,8,0,0]} />
                <Bar dataKey="critical" name="Critical Assets" fill="#FF9933" radius={[8,8,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Risk Trend Monitor" subtitle="Recent telemetry cycles from the analytics engine" action={<Link to="/leaks" style={{ textDecoration: 'none' }}><Button variant="secondary" size="sm">Telemetry</Button></Link>}>
          <div style={{ height: 300 }}>
            {pulseData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pulseData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="riskA" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0099CC" stopOpacity={0.35}/><stop offset="95%" stopColor="#0099CC" stopOpacity={0}/></linearGradient>
                    <linearGradient id="riskB" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#FF9933" stopOpacity={0.25}/><stop offset="95%" stopColor="#FF9933" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#A2C2E2" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#006699' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#006699' }} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #A2C2E2' }} />
                  <Area type="monotone" dataKey="meanRisk" name="Mean Risk %" stroke="#0099CC" fill="url(#riskA)" strokeWidth={2} />
                  <Area type="monotone" dataKey="maxRisk" name="Max Risk %" stroke="#FF9933" fill="url(#riskB)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: 'var(--ns-muted)', textAlign: 'center', border: '1px dashed var(--ns-border)', borderRadius: 12 }}>
                <div><Activity size={22} style={{ marginBottom: 8 }} /><div>Risk trend data will appear after telemetry cycles are received.</div></div>
              </div>
            )}
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        <Card title="Priority Action Feed" subtitle="AI-ranked repairs and urgent infrastructure signals" action={<Link to="/attention" style={{ textDecoration: 'none' }}><Button variant="secondary" size="sm">View All</Button></Link>}>
          <div style={{ display: 'grid', gap: '0.7rem' }}>
            {priorityFeed.length ? priorityFeed.map(item => (
              <Link key={item.id} to={item.to} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div style={{ padding: '0.75rem 0.85rem', border: '1px solid var(--ns-border)', borderRadius: 12, display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', background: '#fff' }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--ns-ink)' }}>{item.title}</div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--ns-muted)', marginTop: 2 }}>{item.subtitle}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Badge variant={item.tone}>{item.value}</Badge>
                    <ArrowRight size={15} color="var(--ns-muted)" />
                  </div>
                </div>
              </Link>
            )) : <div style={{ color: 'var(--ns-muted)', fontSize: '0.85rem' }}>No priority items available yet.</div>}
          </div>
        </Card>

        <Card title="Hydraulic Leak Signals" subtitle="Top acoustic/pressure anomalies from pipeline telemetry" action={<Link to="/leaks" style={{ textDecoration: 'none' }}><Button variant="secondary" size="sm" icon={Droplets}>Leak Console</Button></Link>}>
          <div style={{ display: 'grid', gap: '0.7rem' }}>
            {criticalLeaks.length ? criticalLeaks.map((l, idx) => (
              <div key={l.asset_id || idx} style={{ padding: '0.75rem 0.85rem', border: '1px solid #ffe4d6', background: '#FFFFFF', borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 800, color: 'var(--ns-ink)', fontSize: '0.86rem' }}><Radio size={14} color="#FF9933" /> Asset {l.asset_id}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--ns-muted)', marginTop: 2 }}>{l.location || 'Municipal water grid segment'}</div>
                </div>
                <Badge variant="red">{((l.leak_score || 0) * 100).toFixed(0)}% ANOMALY</Badge>
              </div>
            )) : <div style={{ color: 'var(--ns-muted)', fontSize: '0.85rem' }}>No active hydraulic anomalies above threshold.</div>}
          </div>
        </Card>
      </div>

      <Card title="ML Capabilities in Use" subtitle="Trained models and optimization drive prioritization and planning">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.8rem' }}>
          {[
            { icon: Cpu, title: 'Risk Prediction', text: 'Supervised risk model (trained/calibrated; metrics available) ranks assets by failure likelihood.' },
            { icon: Radio, title: 'Leak/Anomaly Detection', text: 'Telemetry-based leak/anomaly scoring highlights hydraulic issues for action.' },
            { icon: Route, title: 'DigOnce Optimization', text: 'Corridor-aware planning groups multi-utility work to reduce repeated excavation and cost.' },
            { icon: Activity, title: 'Explainability & Trends', text: 'Feature importance, trend monitoring, and traffic-aware scheduling support decisions.' },
          ].map(({ icon: Icon, title, text }) => (
            <div key={title} style={{ border: '1px solid var(--ns-border)', borderRadius: 14, padding: '0.9rem', background: '#fff' }}>
              <div style={{ width: 34, height: 34, borderRadius: 10, background: '#FFFFFF', color: '#006699', display: 'grid', placeItems: 'center', marginBottom: 8, border: '1px solid #A2C2E2' }}><Icon size={16} /></div>
              <div style={{ fontWeight: 800, fontSize: '0.88rem', marginBottom: 4, color: '#003366' }}>{title}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--ns-muted)', lineHeight: 1.45 }}>{text}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
