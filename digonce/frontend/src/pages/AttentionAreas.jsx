import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  AlertTriangle, ShieldAlert, Sparkles, MapPin, 
  Layers, ArrowRight, CheckCircle2, Filter, Info, Wrench
} from 'lucide-react'
import { getAttentionAreas, createIncident, getUsers, patchIncident } from '../api.js'
import { healthBadgeClass, fmt } from '../utils.js'

function requestError(error) {
  return error.response?.data?.detail || error.message || 'The attention dashboard could not be loaded.'
}

export default function AttentionAreas({ user }) {
  const nav = useNavigate()
  const [data, setData] = useState({ items: [], corridor_clusters: [], total_flagged: 0 })
  const [loading, setLoading] = useState(true)
  const [assetType, setAssetType] = useState('')
  const [minPriority, setMinPriority] = useState(30)
  const [activeTab, setActiveTab] = useState('assets') // 'assets' | 'zones'
  const [fieldWorkers, setFieldWorkers] = useState([])
  const [assignModal, setAssignModal] = useState(null)
  const [selectedWorker, setSelectedWorker] = useState('')
  const [actionNotice, setActionNotice] = useState('')
  const [error, setError] = useState('')
  const demoMode = data.score_mode === 'simulated_condition_priority'

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await getAttentionAreas({
        asset_type: assetType || undefined,
        min_priority: minPriority,
        limit: 60,
      })
      setData(res)
    } catch (requestFailure) {
      setError(requestError(requestFailure))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [assetType, minPriority])

  useEffect(() => {
    if (user?.role === 'admin') {
      getUsers().then((users) => {
        setFieldWorkers(users.filter((u) => u.role === 'field_worker'))
      }).catch((requestFailure) => setError(requestError(requestFailure)))
    }
  }, [user])

  const handleCreateAndAssign = async (item) => {
    if (!selectedWorker) {
      alert('Please select a registered field worker.')
      return
    }
    try {
      // 1. Create incident if not exists
      let incId = item.incident?.incident_id
      if (!incId) {
        const inc = await createIncident({
          asset_id: item.asset_id,
          title: `Priority Maintenance: ${item.asset_type.toUpperCase()} on Corridor ${item.corridor_id}`,
          description: `Identified by Priority Engine (Score ${item.priority_score}/100). Reasons: ${item.reasons.join(', ')}`,
          severity: item.priority_score >= 65 ? 'high' : 'medium',
          district: item.district,
          asset_type: item.asset_type,
          lat: item.lat,
          lon: item.lon,
        })
        incId = inc.id
      }

      // 2. Transition to ASSIGNED
      await patchIncident(incId, {
        status: 'ASSIGNED',
        assigned_to: selectedWorker,
        note: `Assigned by planner ${user?.name} to field engineer.`,
      })

      setActionNotice(`Assigned ${incId} (${item.asset_id}) to field crew!`)
      setAssignModal(null)
      setSelectedWorker('')
      await loadData()
    } catch (err) {
      alert(err.response?.data?.detail || 'Assignment failed.')
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Areas & Assets Needing Attention</div>
          <div className="page-sub">
            {demoMode
              ? 'Illustrative multi-factor ranking using simulated condition-priority signals across the district demo'
              : 'Ranked multi-factor priority index (Risk 35%, Criticality 25%, Traffic Disruption 15%, Maintenance Urgency 15%, Evidence 10%)'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={() => nav('/planner')}>
            <Sparkles size={14} /> Open Budget Recommender
          </button>
        </div>
      </div>

      {actionNotice && (
        <div className="panel" role="status" style={{ marginBottom: 14, background: '#FFFFFF', borderColor: '#A2C2E2', color: '#0099CC' }}>
          {actionNotice}
        </div>
      )}
      {error && <div className="dashboard-data-error" role="alert">{error}</div>}

      {/* Overview callout banner */}
      <div className="panel" style={{ 
        background: 'linear-gradient(135deg, #0099CC 0%, #0099CC 100%)', 
        color: '#FFFFFF', 
        marginBottom: 16,
        padding: '1.25rem 1.5rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#0099CC', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              Decision Support vs. Final Repair Selection
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: 4, color: '#FFFFFF' }}>
              Priority ranking identifies urgency; budget-constrained ILP bundles joint corridor mobilisations.
            </div>
            <div style={{ fontSize: '0.85rem', color: '#A2C2E2', marginTop: 4 }}>
              Total flagged components: <strong>{data.total_flagged}</strong> · High-synergy work zones: <strong>{data.corridor_clusters.length}</strong>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ textAlign: 'center', padding: '6px 14px', background: 'rgba(255,255,255,0.08)', borderRadius: 8 }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: '1.4rem', fontWeight: 800, color: '#FF9933' }}>
                {data.corridor_clusters.length}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#0099CC' }}>Work Zones</div>
            </div>
            <div style={{ textAlign: 'center', padding: '6px 14px', background: 'rgba(255,255,255,0.08)', borderRadius: 8 }}>
              <div style={{ fontFamily: 'var(--display)', fontSize: '1.4rem', fontWeight: 800, color: '#0099CC' }}>
                {data.items.length}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#0099CC' }}>Top Assets</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="panel" style={{ marginBottom: 16, padding: '1rem' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Filter size={15} color="var(--muted)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Filters:</span>
          </div>
          <select 
            value={assetType} 
            onChange={(e) => setAssetType(e.target.value)}
            style={{ padding: '6px 10px', borderRadius: 8, fontSize: '0.85rem' }}
          >
            <option value="">All Asset Types</option>
            <option value="road">Roads</option>
            <option value="pipe">Water Pipes</option>
            <option value="streetlight">Streetlights</option>
            <option value="bridge">Bridges</option>
          </select>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>Min Priority:</span>
            <input 
              type="range" 
              min="20" 
              max="80" 
              value={minPriority} 
              onChange={(e) => setMinPriority(Number(e.target.value))} 
              style={{ width: 100 }}
            />
            <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{minPriority}</span>
          </div>

          <div className="toggle-row" style={{ marginLeft: 'auto' }}>
            <button 
              className={`chip ${activeTab === 'assets' ? 'active' : ''}`}
              onClick={() => setActiveTab('assets')}
            >
              Ranked Assets ({data.items.length})
            </button>
            <button 
              className={`chip ${activeTab === 'zones' ? 'active' : ''}`}
              onClick={() => setActiveTab('zones')}
            >
              Coordinated Zones ({data.corridor_clusters.length})
            </button>
          </div>
        </div>
      </div>

      {/* Main Tab Content */}
      {loading ? (
        <div className="panel" style={{ textAlign: 'center', padding: '3rem' }}>
          <div className="spinner" style={{ margin: '0 auto 12px' }} />
          <div>{demoMode ? 'Ranking simulated condition, disruption, and maintenance indicators…' : 'Evaluating infrastructure risk, disruption, and maintenance signals…'}</div>
        </div>
      ) : activeTab === 'zones' ? (
        /* Work Zones / Corridors */
        <div style={{ display: 'grid', gap: 14 }}>
          {data.corridor_clusters.map((zone) => (
            <div key={zone.corridor_id} className="panel" style={{ display: 'grid', gap: 10, borderLeft: '4px solid #FF9933' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.15rem' }}>
                      Corridor {zone.corridor_id}
                    </span>
                    <span className="badge badge-degrading">
                      Mean Priority {zone.mean_priority}
                    </span>
                    <span className="nav-chip">{zone.district}</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginTop: 4 }}>
                    {zone.n_vulnerable_assets} co-located vulnerable components · Asset types: {zone.asset_types.join(', ')}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Estimated DigOnce Saving:</div>
                  <div style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.1rem', color: 'var(--success)' }}>
                    ₹{zone.estimated_coordination_saving_lakh} Lakh
                  </div>
                </div>
              </div>

              {/* Sub-assets */}
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                {zone.assets.map((a) => (
                  <span 
                    key={a.asset_id} 
                    className="badge badge-moderate" 
                    style={{ background: '#FFFFFF', border: '1px solid var(--border)', padding: '4px 8px' }}
                  >
                    {a.asset_id} ({a.asset_type}) · {demoMode ? 'Condition priority' : 'Risk'} {(a.risk_score * 100).toFixed(1)}% · Pri {a.priority_score}
                  </span>
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
                <button 
                  className="btn btn-secondary btn-sm"
                  onClick={() => nav(`/inspector?id=${zone.assets[0]?.asset_id}`)}
                >
                  Inspect Asset
                </button>
                <button 
                  className="btn btn-primary btn-sm"
                  onClick={() => nav('/planner')}
                >
                  <Sparkles size={14} /> Plan Joint Mobilisation
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Ranked Assets List */
        <div style={{ display: 'grid', gap: 14 }}>
          {data.items.map((item) => (
            <article key={item.asset_id} className="panel" style={{ display: 'grid', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ 
                      display: 'inline-grid', placeItems: 'center', width: 26, height: 26, 
                      borderRadius: '50%', background: 'var(--navy)', color: '#FFFFFF', fontSize: '0.78rem', fontWeight: 800 
                    }}>
                      #{item.rank}
                    </span>
                    <span style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.15rem' }}>
                      {item.asset_id}
                    </span>
                    <span className="badge badge-moderate" style={{ textTransform: 'capitalize' }}>
                      {item.asset_type}
                    </span>
                    <span className={`badge ${healthBadgeClass(item.health_band)}`}>
                      {item.health_band} ({item.health_score})
                    </span>
                    {item.incident?.status && item.incident.status !== 'NO_INCIDENT' && (
                      <span className="badge badge-degrading">
                        Incident: {item.incident.status}
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '0.82rem', color: 'var(--muted)', marginTop: 4 }}>
                    Corridor {item.corridor_id} · {item.district} (Ward {item.ward}) · {item.road_class} road · {item.daily_traffic.toLocaleString()} PCU/day
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ 
                    fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.4rem', 
                    color: item.priority_score >= 65 ? 'var(--danger)' : item.priority_score >= 45 ? '#FF9933' : 'var(--navy)'
                  }}>
                    {item.priority_score}<span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>/100</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Priority Index</div>
                </div>
              </div>

              {/* Multi-factor Score Breakdown Bar */}
              <div style={{ 
                background: '#FFFFFF', padding: '10px 14px', borderRadius: 8, 
                border: '1px solid var(--border)', display: 'grid', gap: 6 
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 600 }}>
                  <span>{demoMode ? 'Condition signal' : 'Risk'}: {item.components.risk}%</span>
                  <span>Criticality: {item.components.criticality}%</span>
                  <span>Disruption: {item.components.disruption}%</span>
                  <span>Maintenance: {item.components.maintenance}%</span>
                  <span>Evidence: {item.components.evidence}%</span>
                </div>
                <div style={{ height: 6, borderRadius: 3, background: '#A2C2E2', display: 'flex', overflow: 'hidden' }}>
                  <div style={{ width: `${item.components.risk * 0.35}%`, background: '#FF9933' }} title="Risk (35%)" />
                  <div style={{ width: `${item.components.criticality * 0.25}%`, background: '#FF9933' }} title="Criticality (25%)" />
                  <div style={{ width: `${item.components.disruption * 0.15}%`, background: '#0099CC' }} title="Disruption (15%)" />
                  <div style={{ width: `${item.components.maintenance * 0.15}%`, background: '#006699' }} title="Maintenance (15%)" />
                  <div style={{ width: `${item.components.evidence * 0.10}%`, background: '#0099CC' }} title="Evidence (10%)" />
                </div>
              </div>

              {/* Explanatory Reasons */}
              <div style={{ fontSize: '0.85rem' }}>
                <strong style={{ color: 'var(--navy)' }}>Key signals: </strong>
                {item.reasons.map((r, i) => (
                  <span key={i} style={{ color: 'var(--ink)' }}>
                    {i > 0 && ' · '} {r}
                  </span>
                ))}
              </div>

              {/* Recommended Action & Workflow Transition */}
              <div style={{ 
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
                flexWrap: 'wrap', gap: 10, paddingTop: 8, borderTop: '1px solid var(--border)' 
              }}>
                <div style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
                  Work cost: <strong>₹{item.work_cost_lakh}L</strong> · Mobilisation: <strong>₹{item.mobilisation_cost_lakh}L</strong> · Recommendation: <strong style={{ color: 'var(--navy)' }}>{item.recommendation}</strong>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button 
                    className="btn btn-secondary btn-sm"
                    onClick={() => nav(`/inspector?id=${item.asset_id}`)}
                  >
                    Inspect
                  </button>
                  {user?.role === 'admin' && (
                    <button 
                      className="btn btn-primary btn-sm"
                      onClick={() => setAssignModal(item)}
                    >
                      <Wrench size={14} /> Assign to Field Crew
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Admin Assignment Modal */}
      {assignModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0, 51, 102, 0.6)', 
          display: 'grid', placeItems: 'center', zIndex: 1000, padding: 16,
        }}>
          <div className="panel" style={{ width: 'min(440px, 100%)' }}>
            <div style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.2rem', marginBottom: 8 }}>
              Dispatch Field Engineer
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: 14 }}>
              Assigning {assignModal.asset_id} ({assignModal.asset_type}) on Corridor {assignModal.corridor_id}
            </div>

            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: 6 }}>
              Select Registered Field Worker
            </label>
            <select 
              value={selectedWorker} 
              onChange={(e) => setSelectedWorker(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, marginBottom: 16 }}
            >
              <option value="">-- Choose Field Engineer --</option>
              {fieldWorkers.map((fw) => (
                <option key={fw.id} value={fw.id}>
                  {fw.name} ({fw.email})
                </option>
              ))}
            </select>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setAssignModal(null)}>
                Cancel
              </button>
              <button 
                className="btn btn-primary" 
                onClick={() => handleCreateAndAssign(assignModal)}
                disabled={!selectedWorker}
              >
                Confirm Assignment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
