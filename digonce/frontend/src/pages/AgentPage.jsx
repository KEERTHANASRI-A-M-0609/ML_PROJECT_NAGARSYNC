import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, Send, Sparkles, Zap } from 'lucide-react'
import { postAgent } from '../api.js'
import { RecommendationRail } from '../components/RecCard.jsx'
import { useLive } from '../hooks/useLive.jsx'
import { fmtLakh } from '../utils.js'

const CHIPS = [
  'system status',
  'plan Madurai with 2000 lakh',
  'top risks in Coimbatore',
  'leak hotspots',
  'plan Tamil Nadu critical first',
]

export default function AgentPage() {
  const { tick, connected } = useLive()
  const [input, setInput] = useState('')
  const [msgs, setMsgs] = useState([
    { role: 'agent', reply: 'NagarSync Operations Agent is ready. Request maintenance plans, district risk summaries, leak hotspots, or asset scoring.', cards: [] },
  ])
  const [busy, setBusy] = useState(false)
  const [cards, setCards] = useState([])
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, busy])

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || busy) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', reply: message }])
    setBusy(true)
    try {
      const hist = msgs.slice(-6).map((m) => ({ role: m.role, content: m.reply }))
      const res = await postAgent(message, hist)
      setMsgs((m) => [...m, { role: 'agent', ...res }])
      if (res.cards?.length) setCards(res.cards)
    } catch (e) {
      setMsgs((m) => [...m, { role: 'agent', reply: e.message || 'The request could not be completed. Please verify that the API service is available.', cards: [] }])
    }
    setBusy(false)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Operations Agent</div>
          <div className="page-sub">
            Interact with NagarSync analytics for calibrated risk scoring, coordinated repair planning, leak detection, and traffic-aware scheduling.
          </div>
        </div>
        <span className="ns-status-pill active">
          <span className="ns-status-dot" />
          {connected ? `TELEMETRY SYNC · CYCLE ${tick}` : 'TELEMETRY STANDBY'}
        </span>
      </div>

      <div className="grid-2" style={{ alignItems: 'stretch' }}>
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', minHeight: 480 }}>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Bot size={18} /> Conversation
          </div>
          <div style={{ flex: 1, overflowY: 'auto', maxHeight: 420, paddingRight: 4 }}>
            <AnimatePresence initial={false}>
              {msgs.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{ marginBottom: 10, display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}
                >
                  <div style={{
                    maxWidth: '88%', padding: '10px 14px', borderRadius: 14,
                    background: m.role === 'user' ? 'var(--navy)' : '#FFFFFF',
                    color: m.role === 'user' ? '#FFFFFF' : 'var(--ink)',
                    border: m.role === 'user' ? 'none' : '1px solid var(--line)',
                    whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: 1.45,
                  }}>
                    {m.reply}
                    {m.plan && (
                      <div style={{ marginTop: 8, fontSize: '0.78rem', opacity: 0.85 }}>
                        {m.plan.selected_count} assets · ₹{fmtLakh(m.plan.planned_spend)} · risk reduction {m.plan.risk_reduction}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            {busy && <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Processing analytics request…</div>}
            <div ref={endRef} />
          </div>

          <div className="toggle-row" style={{ marginTop: 10 }}>
            {CHIPS.map((c) => (
              <button key={c} className="chip" onClick={() => send(c)} disabled={busy}>{c}</button>
            ))}
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send() }} style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Example: plan Salem with 1500 lakh, critical first" disabled={busy} />
            <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()}>
              <Send size={16} />
            </button>
          </form>
        </div>

        <div className="panel">
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} /> Agent Recommendations
          </div>
          {!cards.length && (
            <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
              Request a plan or district risk summary to display recommended assets.
            </div>
          )}
          {!!cards.length && (
            <div style={{ display: 'grid', gap: 10 }}>
              {cards.slice(0, 6).map((c, i) => (
                <div key={`${c.asset_id}-${i}`} className="alert-row" style={{ alignItems: 'center' }}>
                  <Zap size={16} color="#FF9933" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700 }}>{c.asset_id} · {c.district || `District ${c.ward}`}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
                      {(c.risk_score * 100).toFixed(1)}% · {c.asset_type} · ₹{fmtLakh(c.work_cost_lakh ?? 0)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {!!cards.length && (
        <RecommendationRail title="Agent Recommendations" subtitle="Select a card to inspect asset details" items={cards} />
      )}
    </div>
  )
}
