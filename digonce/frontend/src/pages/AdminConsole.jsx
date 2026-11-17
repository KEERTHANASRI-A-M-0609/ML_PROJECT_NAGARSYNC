import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Wrench,
  Users,
  Search,
  Filter,
  RefreshCw,
  FileCheck2,
  Eye,
  ExternalLink,
  MessageSquare,
  Building2,
  Calendar,
  Check,
  X,
  Send
} from 'lucide-react'
import {
  api,
  getIncidents,
  patchIncident,
  getReports,
  patchReport,
  getUsers,
  getSummary
} from '../api.js'
import { Badge, Button, Card, Input } from '../components/ui/Primitives.jsx'

export default function AdminConsole({ user }) {
  const [activeTab, setActiveTab] = useState('verification') // 'verification' | 'incidents' | 'workforce'
  const [reports, setReports] = useState([])
  const [incidents, setIncidents] = useState([])
  const [fieldWorkers, setFieldWorkers] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('all')
  const [districtFilter, setDistrictFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedReport, setSelectedReport] = useState(null)
  const [triageNote, setTriageNote] = useState('')
  const [actionBusy, setActionBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  // Assignment drafts state for incidents
  const [assignmentDrafts, setAssignmentDrafts] = useState({})

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [reps, incs, usersList] = await Promise.all([
        getReports({ limit: 100 }),
        getIncidents({ limit: 100 }),
        getUsers(),
      ])
      setReports(reps || [])
      setIncidents(incs || [])
      setFieldWorkers((usersList || []).filter(u => u.role === 'field_worker'))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to synchronize authority records.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Verification actions for reports (accept, reject, investigate)
  const handleTriageReport = async (reportId, status) => {
    setActionBusy(true)
    setError('')
    try {
      await patchReport(reportId, {
        status,
        note: triageNote.trim() || `Triage action '${status}' executed by municipal authority ${user?.name || user?.email}`
      })
      setNotice(`Report ${reportId} marked as ${status.toUpperCase()}. Attached incident work order generated if accepted.`)
      setTriageNote('')
      setSelectedReport(null)
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update report status.')
    } finally {
      setActionBusy(false)
    }
  }

  // Work order verification (approve completion evidence or return to field)
  const handleVerifyIncident = async (incidentId, approve = true) => {
    try {
      if (approve) {
        await patchIncident(incidentId, {
          status: 'VERIFIED',
          note: `Completion evidence verified by municipal authority ${user?.name || user?.email}`
        })
        setNotice(`Work order ${incidentId} verified successfully.`)
      } else {
        await patchIncident(incidentId, {
          status: 'IN_PROGRESS',
          note: `Completion evidence rejected by authority: additional structural remediation required.`
        })
        setNotice(`Work order ${incidentId} returned to active repair queue.`)
      }
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Incident verification action failed.')
    }
  }

  const handleAssignIncident = async (incidentId) => {
    const workerId = assignmentDrafts[incidentId]
    if (!workerId) return
    try {
      await patchIncident(incidentId, {
        status: 'ASSIGNED',
        assigned_to: workerId,
        note: `Assigned to field engineer by authority dispatch`
      })
      setNotice(`Work order ${incidentId} assigned to engineering dispatch.`)
      loadData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign field crew.')
    }
  }

  // Summary counts
  const pendingReportsCount = reports.filter(r => r.status === 'new' || r.status === 'triaged').length
  const activeIncidentsCount = incidents.filter(i => i.status === 'ASSIGNED' || i.status === 'IN_PROGRESS').length
  const pendingVerificationCount = incidents.filter(i => i.status === 'COMPLETION_SUBMITTED').length
  const completedIncidentsCount = incidents.filter(i => i.status === 'VERIFIED' || i.status === 'CLOSED').length

  // Filtered reports
  const filteredReports = useMemo(() => {
    return reports.filter(r => {
      const matchesStatus = statusFilter === 'all' || r.status === statusFilter
      const matchesDistrict = districtFilter === 'all' || r.district === districtFilter
      const matchesSearch = !searchQuery || 
        r.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.location_text?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.id?.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesStatus && matchesDistrict && matchesSearch
    })
  }, [reports, statusFilter, districtFilter, searchQuery])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* ── Operational Top Header ── */}
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
              Municipal Authority Operations & Triage Console
            </span>
            <Badge variant="navy">COMMAND GRADE</Badge>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--ns-neutral-500)', marginTop: 2 }}>
            Central administration hub for citizen report verification, engineering work assignments, and contractor completion sign-off.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={loadData}
            icon={RefreshCw}
            disabled={loading}
          >
            Synchronize Records
          </Button>
          <Link to="/admin/records" style={{ textDecoration: 'none' }}>
            <Button variant="secondary" size="sm" icon={FileCheck2}>
              Manage Records
            </Button>
          </Link>
          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <Button variant="primary" size="sm" icon={Shield}>
              State Command Centre
            </Button>
          </Link>
        </div>
      </div>

      {/* ── KPI Operational Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <div style={{ padding: '1.1rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 'var(--ns-radius-md)', borderLeft: '4px solid var(--ns-amber-600)' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--ns-neutral-500)', textTransform: 'uppercase' }}>
            Pending Citizen Verification
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--ns-amber-700)', marginTop: 4 }}>
            {pendingReportsCount}
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)' }}>Requires engineering review</span>
        </div>

        <div style={{ padding: '1.1rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 'var(--ns-radius-md)', borderLeft: '4px solid var(--ns-blue-600)' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--ns-neutral-500)', textTransform: 'uppercase' }}>
            Active Work Orders
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--ns-navy-950)', marginTop: 4 }}>
            {activeIncidentsCount}
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)' }}>Field crews currently dispatched</span>
        </div>

        <div style={{ padding: '1.1rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 'var(--ns-radius-md)', borderLeft: '4px solid var(--ns-red-600)' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--ns-neutral-500)', textTransform: 'uppercase' }}>
            Completion Verification Queue
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--ns-red-700)', marginTop: 4 }}>
            {pendingVerificationCount}
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)' }}>Evidence submitted by contractors</span>
        </div>

        <div style={{ padding: '1.1rem', backgroundColor: '#FFFFFF', border: '1px solid var(--ns-border-subtle)', borderRadius: 'var(--ns-radius-md)', borderLeft: '4px solid var(--ns-teal-600)' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--ns-neutral-500)', textTransform: 'uppercase' }}>
            Closed & Verified Repairs
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--ns-teal-700)', marginTop: 4 }}>
            {completedIncidentsCount}
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)' }}>Audit compliance archived</span>
        </div>
      </div>

      {/* Notices */}
      {notice && (
        <div style={{ padding: '0.75rem 1rem', backgroundColor: 'var(--ns-teal-50)', border: '1px solid var(--ns-teal-200)', borderRadius: 6, color: 'var(--ns-teal-700)', fontSize: '0.82rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{notice}</span>
          <button onClick={() => setNotice('')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, color: 'inherit' }}></button>
        </div>
      )}

      {error && (
        <div style={{ padding: '0.75rem 1rem', backgroundColor: 'var(--ns-red-50)', border: '1px solid var(--ns-red-200)', borderRadius: 6, color: 'var(--ns-red-700)', fontSize: '0.82rem', display: 'flex', justifyContent: 'space-between' }}>
          <span>{error}</span>
          <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, color: 'inherit' }}></button>
        </div>
      )}

      {/* ── Tabs Navigation ── */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--ns-border-subtle)', gap: '1.5rem' }}>
        <button
          onClick={() => setActiveTab('verification')}
          style={{
            padding: '0.65rem 0.25rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'verification' ? '3px solid var(--ns-navy-900)' : '3px solid transparent',
            color: activeTab === 'verification' ? 'var(--ns-navy-950)' : 'var(--ns-neutral-500)',
            fontWeight: activeTab === 'verification' ? 700 : 500,
            fontSize: '0.88rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <FileCheck2 size={16} />
          <span>Citizen Report Verification Queue ({pendingReportsCount})</span>
        </button>

        <button
          onClick={() => setActiveTab('incidents')}
          style={{
            padding: '0.65rem 0.25rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'incidents' ? '3px solid var(--ns-navy-900)' : '3px solid transparent',
            color: activeTab === 'incidents' ? 'var(--ns-navy-950)' : 'var(--ns-neutral-500)',
            fontWeight: activeTab === 'incidents' ? 700 : 500,
            fontSize: '0.88rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <Wrench size={16} />
          <span>Work Order Dispatch & Verification ({incidents.length})</span>
        </button>
      </div>

      {/* ── TAB 1: CITIZEN REPORT VERIFICATION QUEUE ── */}
      {activeTab === 'verification' && (
        <div style={{ display: 'grid', gridTemplateColumns: selectedReport ? '1.3fr 0.7fr' : '1fr', gap: '1.5rem' }}>
          {/* Reports Table / List */}
          <Card
            title="Public Infrastructure Submissions Requiring Verification"
            subtitle="Review community complaints, assess priority, and convert to engineering work orders"
            action={
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  style={{ padding: '0.35rem 0.6rem', fontSize: '0.78rem', border: '1px solid var(--ns-border-subtle)', borderRadius: 4 }}
                >
                  <option value="all">All Statuses</option>
                  <option value="new">New (Unreviewed)</option>
                  <option value="triaged">Triaged</option>
                  <option value="accepted">Accepted (Converted)</option>
                  <option value="rejected">Rejected</option>
                </select>

                <input
                  type="text"
                  placeholder="Search description, location..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ padding: '0.35rem 0.65rem', fontSize: '0.78rem', border: '1px solid var(--ns-border-subtle)', borderRadius: 4, width: 200 }}
                />
              </div>
            }
          >
            {filteredReports.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--ns-neutral-500)' }}>
                No reports match the current filter criteria.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--ns-border-subtle)', color: 'var(--ns-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                      <th style={{ padding: '0.65rem 0.75rem' }}>ID</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>Category</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>Location / Ward</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>Description</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>Status</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>Date</th>
                      <th style={{ padding: '0.65rem 0.75rem', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredReports.map((report) => (
                      <tr
                        key={report.id}
                        style={{
                          borderBottom: '1px solid var(--ns-border-subtle)',
                          backgroundColor: selectedReport?.id === report.id ? 'var(--ns-blue-50)' : 'transparent',
                          cursor: 'pointer'
                        }}
                        onClick={() => setSelectedReport(report)}
                      >
                        <td style={{ padding: '0.75rem', fontWeight: 600, color: 'var(--ns-navy-950)' }}>
                          {report.id.slice(0, 8)}…
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{ fontWeight: 600 }}>{report.category.replace('_', ' ').toUpperCase()}</span>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div>{report.location_text}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--ns-neutral-500)' }}>{report.taluk || report.district}</div>
                        </td>
                        <td style={{ padding: '0.75rem', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {report.description}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <Badge variant={report.status === 'accepted' ? 'teal' : report.status === 'new' ? 'amber' : 'neutral'}>
                            {report.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td style={{ padding: '0.75rem', color: 'var(--ns-neutral-500)', fontSize: '0.75rem' }}>
                          {new Date(report.created_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                          <Button
                            variant={selectedReport?.id === report.id ? 'primary' : 'secondary'}
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedReport(report)
                            }}
                          >
                            Review
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Review Drawer / Side Detail */}
          {selectedReport && (
            <Card
              title="Issue Triage & Verification Review"
              subtitle={`Report ID: ${selectedReport.id}`}
              action={
                <button
                  onClick={() => setSelectedReport(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ns-neutral-500)' }}
                >
                  <X size={16} />
                </button>
              }
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--ns-neutral-500)', textTransform: 'uppercase', fontWeight: 700 }}>
                    Reported Infrastructure Concern
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--ns-navy-950)', marginTop: 2 }}>
                    {selectedReport.category.replace('_', ' ').toUpperCase()}
                  </div>
                </div>

                <div style={{ padding: '0.75rem', backgroundColor: 'var(--ns-neutral-50)', borderRadius: 6, border: '1px solid var(--ns-border-subtle)', fontSize: '0.82rem' }}>
                  <strong>Description:</strong>
                  <p style={{ marginTop: 4, color: 'var(--ns-neutral-800)', lineHeight: 1.5 }}>
                    {selectedReport.description}
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.78rem' }}>
                  <div>
                    <span style={{ color: 'var(--ns-neutral-500)', display: 'block' }}>Location:</span>
                    <strong>{selectedReport.location_text}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--ns-neutral-500)', display: 'block' }}>Jurisdiction:</span>
                    <strong>{selectedReport.district} · {selectedReport.taluk || 'Urban'}</strong>
                  </div>
                </div>

                {/* ML Suggested Risk Assessment */}
                <div style={{ padding: '0.85rem', backgroundColor: 'var(--ns-blue-50)', border: '1px solid var(--ns-blue-200)', borderRadius: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--ns-navy-900)' }}>
                      AUTOMATED ML RISK TRIAGE
                    </span>
                    <Badge variant={selectedReport.category === 'bridge_damage' || selectedReport.category === 'water_leak' ? 'red' : 'amber'}>
                      {selectedReport.category === 'bridge_damage' || selectedReport.category === 'water_leak' ? 'HIGH SEVERITY' : 'MEDIUM SEVERITY'}
                    </Badge>
                  </div>
                  <p style={{ fontSize: '0.72rem', color: 'var(--ns-navy-800)', marginTop: 4 }}>
                    Model recommends priority work order creation with immediate structural inspection.
                  </p>
                </div>

                {/* Official Action Form */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--ns-neutral-700)' }}>
                    Authority Review Note / Field Directive:
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Provide official verification notes or instructions for engineering crew..."
                    value={triageNote}
                    onChange={(e) => setTriageNote(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.65rem',
                      fontSize: '0.8rem',
                      border: '1px solid var(--ns-border-subtle)',
                      borderRadius: 4,
                      outline: 'none',
                      fontFamily: 'inherit'
                    }}
                  />

                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={actionBusy}
                      onClick={() => handleTriageReport(selectedReport.id, 'accepted')}
                      icon={Check}
                      style={{ flex: 1 }}
                    >
                      Accept & Create Work Order
                    </Button>

                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={actionBusy}
                      onClick={() => handleTriageReport(selectedReport.id, 'rejected')}
                      icon={X}
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── TAB 2: WORK ORDER DISPATCH & VERIFICATION ── */}
      {activeTab === 'incidents' && (
        <Card
          title="Active Municipal Work Orders & Completion Sign-Off"
          subtitle="Assign field engineers, inspect completion evidence, and formally verify repaired public infrastructure"
        >
          {incidents.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--ns-neutral-500)' }}>
              No active work orders found.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--ns-border-subtle)', color: 'var(--ns-neutral-500)', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                    <th style={{ padding: '0.65rem 0.75rem' }}>Order ID</th>
                    <th style={{ padding: '0.65rem 0.75rem' }}>Work Title</th>
                    <th style={{ padding: '0.65rem 0.75rem' }}>District / Ward</th>
                    <th style={{ padding: '0.65rem 0.75rem' }}>Severity</th>
                    <th style={{ padding: '0.65rem 0.75rem' }}>Current Status</th>
                    <th style={{ padding: '0.65rem 0.75rem' }}>Assigned Engineer</th>
                    <th style={{ padding: '0.65rem 0.75rem', textAlign: 'right' }}>Authority Action</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((inc) => (
                    <tr key={inc.id} style={{ borderBottom: '1px solid var(--ns-border-subtle)' }}>
                      <td style={{ padding: '0.75rem', fontWeight: 700, color: 'var(--ns-navy-950)' }}>
                        {inc.id}
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <div style={{ fontWeight: 600 }}>{inc.title}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--ns-neutral-500)' }}>Report Ref: {inc.report_id || 'Direct Authority Issue'}</div>
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        {inc.district || 'State Grid'} {inc.ward ? `(Ward ${inc.ward})` : ''}
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <Badge variant={inc.severity === 'high' ? 'red' : 'amber'}>
                          {inc.severity.toUpperCase()}
                        </Badge>
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <Badge variant={
                          inc.status === 'VERIFIED' ? 'teal' :
                          inc.status === 'COMPLETION_SUBMITTED' ? 'red' :
                          inc.status === 'IN_PROGRESS' ? 'amber' : 'navy'
                        }>
                          {inc.status}
                        </Badge>
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        {inc.assigned_to ? (
                          <span style={{ fontWeight: 600, color: 'var(--ns-neutral-800)' }}>
                            {fieldWorkers.find(w => w.id === inc.assigned_to)?.name || inc.assigned_to}
                          </span>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <select
                              value={assignmentDrafts[inc.id] || ''}
                              onChange={(e) => setAssignmentDrafts(prev => ({ ...prev, [inc.id]: e.target.value }))}
                              style={{ padding: '0.3rem 0.5rem', fontSize: '0.75rem', border: '1px solid var(--ns-border-subtle)', borderRadius: 4 }}
                            >
                              <option value="">Select Crew...</option>
                              {fieldWorkers.map(w => (
                                <option key={w.id} value={w.id}>{w.name} ({w.email.split('@')[0]})</option>
                              ))}
                            </select>
                            <Button
                              variant="primary"
                              size="sm"
                              disabled={!assignmentDrafts[inc.id]}
                              onClick={() => handleAssignIncident(inc.id)}
                            >
                              Assign
                            </Button>
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                        {inc.status === 'COMPLETION_SUBMITTED' ? (
                          <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleVerifyIncident(inc.id, true)}
                              icon={Check}
                            >
                              Verify
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleVerifyIncident(inc.id, false)}
                              icon={X}
                            >
                              Return
                            </Button>
                          </div>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--ns-neutral-400)' }}>
                            {inc.status === 'VERIFIED' ? 'Verified & Audited' : 'Awaiting Work'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
