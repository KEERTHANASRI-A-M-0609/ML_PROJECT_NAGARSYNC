import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { RefreshCw, SlidersHorizontal, Zap } from 'lucide-react'
import { postRecommend, getWards } from '../api.js'
import { fmt, fmtLakh, healthBadgeClass } from '../utils.js'
import { RecommendationRail } from '../components/RecCard.jsx'
import { useLive } from '../hooks/useLive.jsx'

const STRATEGIES = ['greedy_coordinated', 'digonce_ilp', 'ml_per_rupee', 'risk_first', 'oldest_first']
const URGENCIES = [
  { id: 'balanced', label: 'Balanced' },
  { id: 'critical_first', label: 'Critical first' },
  { id: 'leak_focus', label: 'Leak focus' },
  { id: 'equity', label: 'Ward equity' },
]
const TYPES = ['', 'pipe', 'road', 'bridge', 'streetlight']

export default function Planner() {
  const { tick, meta, recommendations: liveRecs } = useLive()
  const [budget, setBudget] = useState(5000)
  const [strategy, setStrategy] = useState('greedy_coordinated')
  const [mobScale, setMobScale] = useState(1.0)
  const [wardShare, setWardShare] = useState(0.0)
  const [ward, setWard] = useState('')
  const [districts, setDistricts] = useState([])
  const [assetType, setAssetType] = useState('')
  const [minRisk, setMinRisk] = useState(0)
  const [urgency, setUrgency] = useState('balanced')
  const [preferCoordination, setPreferCoordination] = useState(true)
  const [trafficAware, setTrafficAware] = useState(true)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [auto, setAuto] = useState(true)
  const demoMode = meta?.score_mode === 'simulated_condition_priority'

  const requestError = (error) => {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ')
    return error.message || 'The recommender request failed.'
  }

  useEffect(() => {
    getWards().then(setDistricts).catch((requestFailure) => setError(requestError(requestFailure)))
  }, [])

  const body = useMemo(() => ({
    budget_lakh: budget,
    strategy,
    mobilisation_scale: mobScale,
    min_ward_share: wardShare,
    ward: ward === '' ? null : Number(ward),
    asset_type: assetType || null,
    min_risk: minRisk,
    prefer_coordination: preferCoordination,
    traffic_aware: trafficAware,
    urgency,
    limit: 40,
  }), [budget, strategy, mobScale, wardShare, ward, assetType, minRisk, preferCoordination, trafficAware, urgency])

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await postRecommend(body)
      setResult(r)
    } catch (e) {
      setError(requestError(e))
    } finally {
      setLoading(false)
    }
  }

  // Re-run when filters change (debounced) and optionally on telemetry cycles
  useEffect(() => {
    const t = setTimeout(run, 450)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [body])

  // Automatic refresh on telemetry cycles for fast strategies (ILP remains manual)
  useEffect(() => {
    if (!auto) return
    if (strategy === 'digonce_ilp') return
    if (tick > 0 && tick % 4 === 0) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, auto, strategy])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Synchronized recommender</div>
          <div className="page-sub">
            {demoMode
              ? 'Explore simulated maintenance priorities and costs across the 37-district Tamil Nadu demo'
              : 'Tune budget, equity, urgency and filters — NagarSync optimization and traffic windows refresh as the city pulse moves'}
          </div>
        </div>
        <button className="btn btn-navy" onClick={run} disabled={loading}>
          {loading ? <RefreshCw size={16} className="spin" /> : <Zap size={16} />}
          {loading ? 'Scoring…' : 'Refresh now'}
        </button>
      </div>

      <RecommendationRail
        title="Streaming maintenance picks"
        subtitle={demoMode
          ? 'Illustrative district-wide rankings from simulated asset conditions'
          : 'Updates from the WebSocket risk loop'}
        items={liveRecs}
      />

      <div className="grid-2" style={{ marginTop: '1.2rem' }}>
        <motion.div className="panel" layout>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SlidersHorizontal size={18} /> Flexible controls
          </div>

          <div className="toggle-row">
            {URGENCIES.map((u) => (
              <button
                key={u.id}
                className={`chip ${urgency === u.id ? 'active' : ''}`}
                onClick={() => setUrgency(u.id)}
              >
                {u.label}
              </button>
            ))}
          </div>

          <div className="slider-group">
            <div className="slider-label">
              <span>Budget (lakh ₹)</span>
              <span className="slider-val">{budget}</span>
            </div>
            <input type="range" min={500} max={20000} step={100} value={budget} onChange={(e) => setBudget(+e.target.value)} />
          </div>

          <div className="slider-group">
            <div className="slider-label">
              <span>Mobilisation scale</span>
              <span className="slider-val">{mobScale.toFixed(1)}×</span>
            </div>
            <input type="range" min={0} max={3} step={0.1} value={mobScale} onChange={(e) => setMobScale(+e.target.value)} />
          </div>

          <div className="slider-group">
            <div className="slider-label">
              <span>Min ward share</span>
              <span className="slider-val">{(wardShare * 100).toFixed(0)}%</span>
            </div>
            <input type="range" min={0} max={1} step={0.05} value={wardShare} onChange={(e) => setWardShare(+e.target.value)} />
          </div>

          <div className="slider-group">
            <div className="slider-label">
              <span>{demoMode ? 'Minimum priority score' : 'Minimum risk filter'}</span>
              <span className="slider-val">{(minRisk * 100).toFixed(0)}%</span>
            </div>
            <input type="range" min={0} max={0.4} step={0.01} value={minRisk} onChange={(e) => setMinRisk(+e.target.value)} />
          </div>

          <div className="filter-bar" style={{ padding: 0, border: 'none', boxShadow: 'none' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Strategy</label>
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                {STRATEGIES.map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>District</label>
              <select value={ward} onChange={(e) => setWard(e.target.value)}>
                <option value="">All districts</option>
                {districts.map((d) => (
                  <option key={d.ward} value={d.ward}>{d.district || `District ${d.ward}`}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Asset type</label>
              <select value={assetType} onChange={(e) => setAssetType(e.target.value)}>
                {TYPES.map((t) => (
                  <option key={t || 'all'} value={t}>{t || 'All types'}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 8 }}>
            <label className="switch">
              <input type="checkbox" checked={preferCoordination} onChange={(e) => setPreferCoordination(e.target.checked)} />
              Prefer coordinated corridor repairs
            </label>
            <label className="switch">
              <input type="checkbox" checked={trafficAware} onChange={(e) => setTrafficAware(e.target.checked)} />
              Traffic-aware windows
            </label>
            <label className="switch">
              <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
              Auto-refresh on telemetry cycles
            </label>
          </div>
          {error && <div style={{ color: 'var(--danger)', marginTop: 10 }}>{error}</div>}
        </motion.div>

        <div className="panel">
          <div className="panel-title">Plan snapshot</div>
          {!result && <div style={{ color: 'var(--muted)' }}>Adjust filters to generate a plan…</div>}
          {result && (
            <>
              <div className="kpi-grid" style={{ marginBottom: '1rem' }}>
                <div className="kpi"><div className="kpi-value">{result.selected_count}</div><div className="kpi-label">Selected</div></div>
                <div className="kpi"><div className="kpi-value">{result.corridors_opened}</div><div className="kpi-label">Corridors</div></div>
                <div className="kpi"><div className="kpi-value">₹{fmtLakh(result.planned_spend, 0)}</div><div className="kpi-label">Spend</div></div>
                <div className="kpi"><div className="kpi-value">{fmt(result.risk_reduction, 2)}</div><div className="kpi-label">Risk cut</div></div>
                <div className="kpi"><div className="kpi-value">{fmt(result.saving_vs_uncoordinated, 2)}</div><div className="kpi-label">vs uncoord.</div></div>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
                Models: {result.model?.risk} · {result.model?.leak} · {result.model?.traffic} · cycle {result.tick}
              </div>
            </>
          )}
        </div>
      </div>

      {result?.assets?.length > 0 && (
        <>
          <RecommendationRail
            title="Your filtered cart"
            subtitle="Optimiser output for current knobs — click a card to inspect"
            items={result.assets.map((a, i) => ({ ...a, rank: i + 1 }))}
          />

          <div className="panel" style={{ marginTop: '1rem' }}>
            <div className="panel-title">Work windows</div>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Asset</th><th>Type</th><th>Ward</th><th>Risk</th>
                    <th>Cost</th><th>Start</th><th>VH save</th><th>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {result.assets.slice(0, 40).map((a) => (
                    <tr key={a.asset_id}>
                      <td>{a.asset_id}</td>
                      <td>{a.asset_type}</td>
                      <td>{a.ward}</td>
                      <td>
                        <span className={`badge ${healthBadgeClass(a.health_band)}`}>
                          {(a.risk_score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td>₹{fmtLakh(a.work_cost_lakh)}</td>
                      <td>{String(a.best_start_hour).padStart(2, '0')}:00</td>
                      <td>{fmt(a.saving_vh, 0)}</td>
                      <td style={{ maxWidth: 280, fontSize: '0.78rem' }}>{a.reasons?.[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
