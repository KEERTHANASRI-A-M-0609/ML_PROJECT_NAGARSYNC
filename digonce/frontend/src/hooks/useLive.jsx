import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { getLive, liveWsUrl } from '../api.js'

const LiveContext = createContext(null)

export function LiveProvider({ children, token }) {
  const [connected, setConnected] = useState(false)
  const [connectionIssue, setConnectionIssue] = useState(false)
  const [tick, setTick] = useState(0)
  const [kpis, setKpis] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [alerts, setAlerts] = useState([])
  const [topWards, setTopWards] = useState([])
  const [meta, setMeta] = useState({})
  const [riskHistory, setRiskHistory] = useState([])
  const wsRef = useRef(null)
  const retryRef = useRef(0)

  useEffect(() => {
    if (!token) {
      setConnected(false)
      setConnectionIssue(false)
      return undefined
    }

    let cancelled = false
    let timer

    const recordSnapshot = (snapshot) => {
      if (!snapshot.kpis) return
      setRiskHistory((prev) => {
        const next = [
          ...prev.filter((point) => point.tick !== snapshot.tick),
          {
            tick: snapshot.tick,
            time: new Date((snapshot.ts || Date.now() / 1000) * 1000).toLocaleTimeString(),
            meanRisk: snapshot.kpis.mean_risk,
            maxRisk: snapshot.kpis.max_risk ?? snapshot.kpis.mean_risk,
          },
        ]
        return next.slice(-30)
      })
    }

    getLive()
      .then((s) => {
        if (cancelled) return
        setConnectionIssue(false)
        setTick(s.tick || 0)
        setKpis(s.kpis)
        setRecommendations(s.recommendations || [])
        setAlerts(s.recent_alerts || [])
        setMeta(s.meta || {})
        recordSnapshot({ ...s, ts: Date.now() / 1000 })
      })
      .catch(() => {
        if (!cancelled) setConnectionIssue(true)
      })

    const connect = () => {
      if (cancelled) return
      const ws = new WebSocket(liveWsUrl(), ['nagar-sync', `bearer.${token}`])
      wsRef.current = ws
      ws.onopen = () => {
        setConnected(true)
        setConnectionIssue(false)
        retryRef.current = 0
      }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'hello') {
            setTick(msg.tick || 0)
            setKpis(msg.kpis)
            setRecommendations(msg.recommendations || [])
            setAlerts(msg.recent_alerts || [])
            setMeta(msg.meta || {})
            recordSnapshot(msg)
            return
          }
          if (msg.type === 'tick') {
            setTick(msg.tick)
            setKpis(msg.kpis)
            setMeta(msg.meta || {})
            recordSnapshot(msg)
            if (msg.recommendations?.length) setRecommendations(msg.recommendations)
            if (msg.top_wards?.length) setTopWards(msg.top_wards)
            if (msg.alerts?.length) {
              setAlerts((prev) => [...msg.alerts, ...prev].slice(0, 25))
            }
          }
        } catch { /* ignore */ }
      }
      ws.onclose = () => {
        setConnected(false)
        const delay = Math.min(8000, 800 * 2 ** retryRef.current)
        retryRef.current += 1
        timer = setTimeout(connect, delay)
      }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      cancelled = true
      clearTimeout(timer)
      wsRef.current?.close()
    }
  }, [token])

  return (
    <LiveContext.Provider value={{ connected, connectionIssue, tick, kpis, recommendations, alerts, topWards, meta, riskHistory }}>
      {children}
    </LiveContext.Provider>
  )
}

export function useLive() {
  const ctx = useContext(LiveContext)
  if (!ctx) {
    return {
      connected: false, connectionIssue: false, tick: 0, kpis: null,
      recommendations: [], alerts: [], topWards: [], meta: {}, riskHistory: [],
    }
  }
  return ctx
}
