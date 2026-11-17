import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Droplets, Landmark, Lightbulb, Route, Sparkles } from 'lucide-react'
import { healthBadgeClass, fmtLakh } from '../utils.js'

const ICONS = {
  pipe: Droplets,
  bridge: Landmark,
  streetlight: Lightbulb,
  road: Route,
}

export function RecCard({ item, index = 0 }) {
  const nav = useNavigate()
  const Icon = ICONS[item.asset_type] || Sparkles
  const band = item.health_band || 'Moderate'
  const reason = (item.reasons && item.reasons[0]) || item.action ||
    (item.score_mode === 'simulated_condition_priority' ? 'Demo condition-priority ranking' : 'ML ranked repair')
  const scoreLabel = item.score_mode === 'simulated_condition_priority' ? 'Priority' : 'Risk'

  return (
    <motion.div
      className="product-card"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      whileHover={{ y: -6 }}
      onClick={() => nav(`/inspector?id=${encodeURIComponent(item.asset_id)}`)}
    >
      <div className={`product-media ${item.asset_type || ''}`}>
        <div>
          <div style={{ fontSize: '0.72rem', opacity: 0.85 }}>#{item.rank || index + 1} · {item.district || `D${item.ward}`}</div>
          <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
            <Icon size={16} /> {item.asset_type}
          </div>
        </div>
        <span className={`badge ${healthBadgeClass(band)}`}>{band}</span>
      </div>
      <div className="product-body">
        <div className="product-title">{item.asset_id}</div>
        <div className="product-meta">
          Corridor {item.corridor_id} · {scoreLabel} {(item.risk_score * 100).toFixed(1)}%
        </div>
        <div className="product-reasons">{reason}</div>
        <div className="product-footer">
          <div className="price-tag">₹{fmtLakh(item.work_cost_lakh ?? 0)}</div>
          <button
            className="btn btn-primary btn-sm"
            onClick={(e) => {
              e.stopPropagation()
              nav('/planner')
            }}
          >
            Plan
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export function RecommendationRail({ title, items, subtitle }) {
  if (!items?.length) return null
  return (
    <section>
      <div className="rail-head">
        <div>
          <div className="rail-title">{title}</div>
          {subtitle && <div className="page-sub">{subtitle}</div>}
        </div>
      </div>
      <div className="rail-scroll">
        {items.map((item, i) => (
          <RecCard key={`${item.asset_id}-${item.rank || i}`} item={item} index={i} />
        ))}
      </div>
    </section>
  )
}
