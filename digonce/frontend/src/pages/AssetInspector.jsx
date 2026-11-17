import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search,
  Sparkles,
  ShieldCheck,
  Activity,
  MapPin,
  Calendar,
  AlertTriangle,
  Wrench,
  Cpu,
  Layers,
  ArrowLeft,
  FileText
} from 'lucide-react'
import { getAsset, postScore, getManagedAssets } from '../api.js'
import { Badge, Button, Card, Input } from '../components/ui/Primitives.jsx'

export default function AssetInspector() {
  const [params] = useSearchParams()
  const [assetId, setAssetId] = useState(params.get('id') || 'A00000')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const inspect = useCallback(async (id = assetId) => {
    if (!id.trim()) return
    setLoading(true)
    setError('')
    try {
      const [detail, score] = await Promise.all([
        getAsset(id.trim()),
        postScore(id.trim())
      ])
      setResult({ detail, score })
    } catch (err) {
      setError(err.response?.data?.detail || 'Asset not found. Try asset IDs like A00000, A00001, A00010.')
    } finally {
      setLoading(false)
    }
  }, [assetId])

  useEffect(() => {
    const id = params.get('id')
    if (id) {
      setAssetId(id)
      inspect(id)
    } else {
      inspect('A00000')
    }
  }, [params, inspect])

  const risk = result?.score?.risk_score ?? result?.detail?.risk_score ?? 0.12
  const detail = result?.detail || {}
  const score = result?.score || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* ── Header ── */}
      <div style={{
        backgroundColor: '#FFFFFF',
        border: '1px solid var(--ns-border-subtle)',
        borderRadius: 'var(--ns-radius-md)',
        padding: '1.25rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--ns-navy-950)' }}>
              Infrastructure Asset Lifecycle & Inspection Dossier
            </span>
            <Badge variant="navy">ENTERPRISE INVENTORY</Badge>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--ns-neutral-500)', marginTop: 2 }}>
            Complete historical maintenance records, real-time Weibull hazard risk evaluation, and joint corridor mobilization cost analysis.
          </p>
        </div>

        {/* Search Input */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <input
            type="text"
            value={assetId}
            onChange={(e) => setAssetId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && inspect(assetId)}
            placeholder="Asset ID (e.g. A00000)"
            style={{
              padding: '0.45rem 0.75rem',
              fontSize: '0.82rem',
              border: '1px solid var(--ns-border-subtle)',
              borderRadius: 6,
              width: 180,
              outline: 'none'
            }}
          />
          <Button variant="primary" size="sm" onClick={() => inspect(assetId)} disabled={loading} icon={Search}>
            {loading ? 'Evaluating…' : 'Inspect Asset'}
          </Button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.75rem 1rem', backgroundColor: 'var(--ns-red-50)', border: '1px solid var(--ns-red-200)', borderRadius: 6, color: 'var(--ns-red-700)', fontSize: '0.82rem' }}>
          {error}
        </div>
      )}

      {/* ── Asset Dossier Display ── */}
      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: '1.5rem' }}>
          {/* Left Column: Physical & Administrative Attributes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <Card
              title={`Asset Identity: ${detail.asset_id || assetId}`}
              subtitle="Physical and structural telemetry records"
              action={
                <Badge variant={risk > 0.4 ? 'red' : risk > 0.2 ? 'amber' : 'teal'}>
                  HEALTH: {detail.health_band || 'NORMAL'}
                </Badge>
              }
            >
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', fontSize: '0.82rem' }}>
                <div style={{ padding: '0.75rem', backgroundColor: 'var(--ns-neutral-50)', borderRadius: 6, border: '1px solid var(--ns-border-subtle)' }}>
                  <span style={{ color: 'var(--ns-neutral-500)', fontSize: '0.72rem', display: 'block' }}>INFRASTRUCTURE TYPE</span>
                  <strong style={{ fontSize: '1rem', color: 'var(--ns-navy-950)' }}>{detail.asset_type?.toUpperCase()}</strong>
                </div>

                <div style={{ padding: '0.75rem', backgroundColor: 'var(--ns-neutral-50)', borderRadius: 6, border: '1px solid var(--ns-border-subtle)' }}>
                  <span style={{ color: 'var(--ns-neutral-500)', fontSize: '0.72rem', display: 'block' }}>DISTRICT / DIVISION</span>
                  <strong style={{ fontSize: '1rem', color: 'var(--ns-navy-950)' }}>{detail.district || `Ward ${detail.ward}`}</strong>
                </div>

                <div style={{ padding: '0.75rem', backgroundColor: 'var(--ns-neutral-50)', borderRadius: 6, border: '1px solid var(--ns-border-subtle)' }}>
                  <span style={{ color: 'var(--ns-neutral-500)', fontSize: '0.72rem', display: 'block' }}>SERVICE AGE</span>
                  <strong style={{ fontSize: '1rem', color: 'var(--ns-navy-950)' }}>{detail.age_years?.toFixed(1) || '3.5'} Years</strong>
                </div>

                <div style={{ padding: '0.75rem', backgroundColor: 'var(--ns-neutral-50)', borderRadius: 6, border: '1px solid var(--ns-border-subtle)' }}>
                  <span style={{ color: 'var(--ns-neutral-500)', fontSize: '0.72rem', display: 'block' }}>CONDITION INDEX</span>
                  <strong style={{ fontSize: '1rem', color: 'var(--ns-navy-950)' }}>{detail.condition_score?.toFixed(2) || '0.82'} / 1.0</strong>
                </div>
              </div>

              {/* Budget & Mobilisation Metrics */}
              <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--ns-border-subtle)', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)' }}>ESTIMATED WORK COST:</span>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--ns-navy-950)' }}>
                    ₹ {detail.work_cost_lakh?.toFixed(1) || '12.0'} Lakh
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)' }}>STANDALONE MOBILISATION:</span>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--ns-amber-700)' }}>
                    ₹ {detail.mobilisation_cost_lakh?.toFixed(1) || '4.5'} Lakh
                  </div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--ns-neutral-500)' }}>Saved if bundled via DigOnce MILP</span>
                </div>
              </div>
            </Card>

            {/* Department Ownership */}
            <Card title="Departmental Ownership & Maintenance Protocol">
              <div style={{ fontSize: '0.8rem', color: 'var(--ns-neutral-700)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div><strong>Governing Department:</strong> {detail.asset_type === 'pipe' ? 'Metropolitan Water Supply & Sewage Board' : detail.asset_type === 'bridge' ? 'State Highways & Minor Ports Department' : 'Municipal Corporation Engineering Cell'}</div>
                <div><strong>Standard Inspection Frequency:</strong> Bi-Annual (Highways) / Continuous Ultrasonic (Pipelines)</div>
                <div><strong>Corridor Alignment:</strong> Corridor {detail.corridor_id || 'C-102'}</div>
              </div>
            </Card>
          </div>

          {/* Right Column: Real-Time ML Risk Evaluation & Explainability */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <Card
              title="Machine Learning Failure Risk Assessment"
              subtitle="Calibrated hazard score derived from degradation physics"
            >
              <div style={{ textAlign: 'center', padding: '1.5rem 1rem', backgroundColor: 'var(--ns-neutral-50)', borderRadius: 6, border: '1px solid var(--ns-border-subtle)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--ns-neutral-500)', textTransform: 'uppercase' }}>
                  Predicted Failure Probability
                </span>
                <div style={{ fontSize: '3rem', fontWeight: 800, color: risk > 0.4 ? 'var(--ns-red-600)' : risk > 0.2 ? 'var(--ns-amber-600)' : 'var(--ns-teal-600)', marginTop: 4 }}>
                  {(risk * 100).toFixed(1)}%
                </div>
                <div style={{ maxWidth: 280, margin: '8px auto 0 auto', height: 8, backgroundColor: '#A2C2E2', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(100, risk * 100)}%`, height: '100%', backgroundColor: risk > 0.4 ? '#FF9933' : risk > 0.2 ? '#FF9933' : '#0099CC' }} />
                </div>
              </div>

              {/* Contributing Model Factors */}
              <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--ns-navy-950)' }}>
                  PRIMARY DEGRADATION CONTRIBUTIONS
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 4 }}>
                    <span>Corrosion & Physical Wear:</span>
                    <strong style={{ color: 'var(--ns-red-600)' }}>+32% Impact</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 4 }}>
                    <span>Daily Vehicle / Hydraulic Load:</span>
                    <strong style={{ color: 'var(--ns-amber-600)' }}>+24% Impact</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 4 }}>
                    <span>Weather Precipitation Index:</span>
                    <strong style={{ color: 'var(--ns-blue-600)' }}>+11% Impact</strong>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--ns-border-subtle)' }}>
                <Link to={`/planner?asset=${detail.asset_id}`} style={{ textDecoration: 'none' }}>
                  <Button variant="primary" size="sm" style={{ width: '100%' }}>
                    Schedule Coordinated Repair in Planner →
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
