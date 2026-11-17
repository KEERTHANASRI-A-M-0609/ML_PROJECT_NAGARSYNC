import { useApi } from '../utils.js'
import { getSummary, getExperiments } from '../api.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ErrorBar, ResponsiveContainer
} from 'recharts'
import ChartState from '../components/ChartState.jsx'

export default function Overview() {
  const { data: kpis, loading: kl, error: ke, reload: reloadKpis } = useApi(getSummary)
  const { data: exp, loading: el, error: ee, reload: reloadExperiments } = useApi(getExperiments)

  if (kl && el) return <div className="page loading-screen"><div className="spinner" /><div>Loading overview…</div></div>

  const summary = exp?.summary || {}
  const strategies = ['reactive_only','oldest_first','risk_first','ml_per_rupee','greedy_coordinated','digonce']
  const chartData = strategies.map(s => {
    const m = summary[s]
    if (!m) return null
    const mean = m.failures?.mean ?? 0
    const ci = m.failures?.ci95 ?? [mean, mean]
    return { name: s.replace(/_/g,' ').replace('digonce', 'NagarSync'), failures: mean, err: mean - ci[0] }
  }).filter(Boolean)

  const digonce = summary['digonce']
  const mlpr = summary['ml_per_rupee']
  const reactive = summary['reactive_only']
  const failSaving = mlpr && digonce ? (mlpr.failures.mean - digonce.failures.mean).toFixed(1) : '—'
  const spendSaving = mlpr && digonce ? (mlpr.total_spend?.mean - digonce.total_spend?.mean).toFixed(0) : '—'
  const breakeven = exp?.breakeven_mob_scale ?? '—'

  return (
    <div>
      <h2 style={{marginBottom:'1rem'}}>Overview — NagarSync: Intelligent Urban Infrastructure Management</h2>

      {kpis && (
        <div className="kpi-grid">
          <div className="kpi-card"><div className="value">{kpis.total_assets}</div><div className="label">Total Assets</div></div>
          <div className="kpi-card"><div className="value">{kpis.critical_assets}</div><div className="label">Critical Assets (&gt;15% risk)</div></div>
          <div className="kpi-card"><div className="value">{(kpis.mean_risk*100).toFixed(1)}%</div><div className="label">Mean Monthly Risk</div></div>
          <div className="kpi-card"><div className="value">{failSaving}</div><div className="label">Failure Reduction (NagarSync vs ML/₹)</div></div>
          <div className="kpi-card"><div className="value">{kpis.n_wards}</div><div className="label">Wards</div></div>
          <div className="kpi-card"><div className="value">{kpis.n_corridors}</div><div className="label">Corridors</div></div>
        </div>
      )}

      <div className="grid-2" style={{gap:'1.5rem'}}>
        <div className="card">
          <h2>Strategy Comparison — Failures (12 months, simulated)</h2>
          <ChartState data={exp ? chartData : null} loading={el} error={ee} onRetry={reloadExperiments} height={280} emptyMessage="No strategy results. Run the simulation pipeline to generate experiments.">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-25} textAnchor="end" interval={0} tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="failures" fill="#0099CC" name="Mean Failures" radius={[7, 7, 0, 0]} isAnimationActive>
                  <ErrorBar dataKey="err" width={4} strokeWidth={2} stroke="#006699" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartState>
          <p style={{fontSize:'0.75rem',color:'var(--text-muted)',marginTop:'0.5rem'}}>
            Error bars = 95% CI over {exp?.summary?.digonce?.failures?.ci95 ? 'multiple' : '?'} seeds. Simulated data only.
          </p>
        </div>

        <div className="card">
          <h2>Key Findings (from experiments.json)</h2>
          {ke && (
            <div className="chart-state chart-state-error" role="alert">
              <strong>Could not load summary KPIs</strong>
              <span>{ke}</span>
              <button className="btn btn-secondary btn-sm" onClick={reloadKpis}>Retry</button>
            </div>
          )}
          <table>
            <tbody>
              <tr><td>NagarSync vs ML/₹ failure reduction</td><td><strong>{failSaving}</strong></td></tr>
              <tr><td>Break-even mobilisation scale</td><td><strong>{breakeven}</strong></td></tr>
              <tr><td>Reactive-only failures (mean)</td><td><strong>{reactive?.failures?.mean?.toFixed(1) ?? '—'}</strong></td></tr>
              <tr><td>NagarSync failures (mean)</td><td><strong>{digonce?.failures?.mean?.toFixed(1) ?? '—'}</strong></td></tr>
              <tr><td>NagarSync re-dig events (mean)</td><td><strong>{digonce?.re_dig_events?.mean?.toFixed(1) ?? '—'}</strong></td></tr>
              <tr><td>NagarSync total spend (mean lakh)</td><td><strong>{digonce?.total_spend?.mean?.toFixed(0) ?? '—'}</strong></td></tr>
            </tbody>
          </table>
          <p style={{marginTop:'1rem',fontSize:'0.8rem',color:'var(--text-muted)'}}>
            <strong>When does coordination help?</strong> Coordination beats independent repair when
            mobilisation cost &gt; 0 and multiple assets share a corridor. At zero mobilisation cost
            (break-even scale = {breakeven}), coordination provides no extra saving.
          </p>
          <p style={{marginTop:'0.5rem',fontSize:'0.8rem',color:'var(--text-muted)'}}>
            <strong>When it does NOT help:</strong> Single-asset corridors, very low mobilisation cost,
            or when budget is so tight only the single highest-risk asset fits.
          </p>
        </div>
      </div>
    </div>
  )
}
