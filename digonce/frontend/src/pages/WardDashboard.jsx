import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, RefreshCw } from 'lucide-react'
import { getWards } from '../api.js'

export default function WardDashboard() {
  const [wards, setWards] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadWards = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setWards(await getWards())
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load ward metrics.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadWards()
  }, [loadWards])

  const totals = useMemo(() => wards.reduce((summary, ward) => ({
    assets: summary.assets + ward.n_assets,
    critical: summary.critical + ward.critical_count,
  }), { assets: 0, critical: 0 }), [wards])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Ward service dashboard</h1>
          <p className="page-sub">API-backed infrastructure risk and asset coverage by ward. Risk indicators are simulated decision-support data.</p>
        </div>
        <button className="btn btn-secondary" type="button" onClick={loadWards} disabled={loading}>
          <RefreshCw size={14} aria-hidden="true" /> Refresh wards
        </button>
      </div>

      {error && <div className="panel" role="alert" style={{ color: 'var(--danger)', marginBottom: 14 }}>{error}</div>}
      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        <div className="kpi"><div className="kpi-value">{loading ? '—' : wards.length}</div><div className="kpi-label">Wards reporting</div></div>
        <div className="kpi"><div className="kpi-value">{loading ? '—' : totals.assets.toLocaleString('en-IN')}</div><div className="kpi-label">Modeled assets</div></div>
        <div className="kpi"><div className="kpi-value">{loading ? '—' : totals.critical.toLocaleString('en-IN')}</div><div className="kpi-label">Assets above risk threshold</div></div>
      </div>

      {loading ? <div className="panel" role="status">Loading ward service metrics…</div> : wards.length === 0 ? (
        <div className="panel">No ward metrics are available.</div>
      ) : (
        <div className="ward-metric-grid">
          {[...wards].sort((a, b) => b.mean_risk - a.mean_risk).map((ward) => (
            <article key={ward.ward} className="panel ward-metric-card">
              <div className="ward-metric-head">
                <div>
                  <strong>{ward.district}</strong>
                  <span>Ward {ward.ward}</span>
                </div>
                {ward.critical_count > 0 && <span className="badge badge-degrading"><AlertTriangle size={12} aria-hidden="true" /> {ward.critical_count} flagged</span>}
              </div>
              <div className="ward-risk-value"><Activity size={16} aria-hidden="true" /> {(ward.mean_risk * 100).toFixed(1)}% <span>mean modeled risk</span></div>
              <div className="ward-risk-track" role="img" aria-label={`${ward.district}, ward ${ward.ward}: mean risk ${(ward.mean_risk * 100).toFixed(1)} percent`}>
                <span style={{ width: `${Math.min(100, ward.mean_risk * 100)}%` }} />
              </div>
              <div className="ward-metric-foot">
                <span>{ward.n_assets.toLocaleString('en-IN')} assets</span>
                <span>Peak {(ward.max_risk * 100).toFixed(1)}%</span>
                <span>Leak signal {(ward.leak_score * 100).toFixed(1)}%</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
