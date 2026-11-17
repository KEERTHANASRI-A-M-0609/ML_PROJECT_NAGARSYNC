import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, ShieldCheck } from 'lucide-react'
import { getAuditEvents } from '../api.js'

const ENTITY_TYPES = [
  ['all', 'All activity'],
  ['user', 'Accounts'],
  ['report', 'Citizen reports'],
  ['incident', 'Work orders'],
  ['asset', 'Managed assets'],
]

export default function AuditLog() {
  const [entityType, setEntityType] = useState('all')
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadEvents = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getAuditEvents({
        limit: 250,
        ...(entityType === 'all' ? {} : { entity_type: entityType }),
      })
      setEvents(data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load the audit log.')
    } finally {
      setLoading(false)
    }
  }, [entityType])

  useEffect(() => {
    loadEvents()
  }, [loadEvents])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Municipal service audit</h1>
          <p className="page-sub">Review account, report, work-order, and managed-asset changes recorded by NagarSync.</p>
        </div>
        <button className="btn btn-secondary" type="button" onClick={loadEvents} disabled={loading}>
          <RefreshCw size={14} aria-hidden="true" /> Refresh log
        </button>
      </div>

      <div className="panel" style={{ marginBottom: 14 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, maxWidth: 360 }}>
          Filter activity
          <select value={entityType} onChange={(event) => setEntityType(event.target.value)}>
            {ENTITY_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>

      {error && <div className="panel" role="alert" style={{ color: 'var(--danger)', marginBottom: 12 }}>{error}</div>}
      {loading ? (
        <div className="panel" role="status">Loading audit events…</div>
      ) : events.length === 0 ? (
        <div className="panel" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldCheck size={18} aria-hidden="true" /> No activity has been recorded for this filter yet.
        </div>
      ) : (
        <div className="panel audit-table-wrap">
          <table className="audit-table">
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Staff member</th>
                <th scope="col">Action</th>
                <th scope="col">Record</th>
                <th scope="col">Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.created_at * 1000).toLocaleString()}</td>
                  <td>{event.actor_name || event.actor_email}<small>{event.actor_role}</small></td>
                  <td><span className="badge badge-moderate">{event.action.replaceAll('_', ' ')}</span></td>
                  <td>{event.entity_type} · {event.entity_id}</td>
                  <td>{event.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
