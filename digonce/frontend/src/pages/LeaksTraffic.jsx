import { useApi, fmt } from '../utils.js'
import { getLeaks, getTraffic } from '../api.js'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { useState } from 'react'

export default function LeaksTraffic() {
  const { data: leaks, loading: ll } = useApi(getLeaks)
  const { data: traffic, loading: tl } = useApi(getTraffic)
  const [selDma, setSelDma] = useState(0)
  const [selJunc, setSelJunc] = useState(0)
  const [isWeekend, setIsWeekend] = useState(false)

  if (ll || tl) return <div className="page loading-screen"><div className="spinner" /><div>Loading sensors…</div></div>

  const dmaData = leaks?.find(d => d.dma === selDma)
  const mnfSeries = (dmaData?.mnf_series || []).map((v, i) => ({ day: i, mnf: v }))

  const juncProfile = traffic?.find(t => t.junction === selJunc && t.is_weekend === isWeekend)
  const hourlyData = (juncProfile?.hourly_profile || []).map((v, h) => ({ hour: h, count: v }))
  const minHour = hourlyData.length > 0 ? hourlyData.reduce((a, b) => a.count < b.count ? a : b).hour : null

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Sensors</div>
          <div className="page-sub">Leak detector DMA scores and traffic profiles that feed scheduling</div>
        </div>
      </div>
      <div className="grid-2" style={{ gap: '1.5rem' }}>

        {/* Leaks panel */}
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h2>DMA Leak Alerts</h2>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr><th>DMA</th><th>Leak Score</th><th>Recent Leak Days</th><th>Mean MNF (L/s)</th><th>Mean Pressure (bar)</th></tr>
                </thead>
                <tbody>
                  {(leaks || []).map(d => (
                    <tr key={d.dma} style={{ cursor: 'pointer', background: selDma === d.dma ? 'rgba(0, 102, 153, 0.08)' : '' }}
                      onClick={() => setSelDma(d.dma)}>
                      <td>DMA {d.dma}</td>
                      <td>
                        <span style={{
                          color: d.leak_score > 0.3 ? 'var(--danger)' : d.leak_score > 0.1 ? 'var(--warning)' : 'var(--success)',
                          fontWeight: 600
                        }}>{(d.leak_score * 100).toFixed(0)}%</span>
                      </td>
                      <td>{d.recent_leak_days}</td>
                      <td>{fmt(d.mean_mnf)}</td>
                      <td>{fmt(d.mean_pressure, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h2>MNF Sparkline — DMA {selDma} (last 30 days)</h2>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={mnfSeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" label={{ value: 'Day', position: 'insideBottom', offset: -5 }} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="mnf" stroke="#0099CC" dot={false} name="MNF (L/s)" />
              </LineChart>
            </ResponsiveContainer>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Simulated minimum night flow. Spikes indicate potential leak events.
            </p>
          </div>
        </div>

        {/* Traffic panel */}
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h2>Junction Hourly Profile</h2>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
              <select value={selJunc} onChange={e => setSelJunc(+e.target.value)}>
                {[...new Set((traffic || []).map(t => t.junction))].map(j => (
                  <option key={j} value={j}>Junction {j}</option>
                ))}
              </select>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem' }}>
                <input type="checkbox" checked={isWeekend} onChange={e => setIsWeekend(e.target.checked)} />
                Weekend
              </label>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" label={{ value: 'Hour', position: 'insideBottom', offset: -5 }} />
                <YAxis label={{ value: 'Vehicles', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                {minHour !== null && (
                  <ReferenceLine x={minHour} stroke="#0099CC" strokeWidth={2}
                    label={{ value: `Best: ${minHour}:00`, fill: '#0099CC', fontSize: 11 }} />
                )}
                <Bar dataKey="count" fill="#0099CC" name="Mean Vehicles" />
              </BarChart>
            </ResponsiveContainer>
            {minHour !== null && (
              <p style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: 4 }}>
                Lowest-disruption window starts at <strong>{minHour}:00</strong> (green line).
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
