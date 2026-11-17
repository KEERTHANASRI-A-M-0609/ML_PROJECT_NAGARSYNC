import { AlertCircle, BarChart3, RefreshCw } from 'lucide-react'

export default function ChartState({ data, loading, error, onRetry, children, height = 260, emptyMessage = 'No chart data is available yet.' }) {
  if (loading && !data) {
    return (
      <div className="chart-state chart-state-loading" style={{ minHeight: height }} role="status">
        <span className="chart-state-pulse"><BarChart3 size={22} /></span>
        <span>Loading analytics data…</span>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="chart-state chart-state-error" style={{ minHeight: height }} role="alert">
        <AlertCircle size={22} />
        <strong>Could not load chart data</strong>
        <span>{error}</span>
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry}>
            <RefreshCw size={14} /> Retry
          </button>
        )}
      </div>
    )
  }

  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="chart-state" style={{ minHeight: height }}>
        <BarChart3 size={22} />
        <span>{emptyMessage}</span>
      </div>
    )
  }

  return children
}
