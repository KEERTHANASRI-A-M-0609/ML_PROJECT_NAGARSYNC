import { useCallback, useEffect, useState } from 'react'
import {
  Archive, CalendarDays, CheckCircle2, CircleDollarSign, ClipboardList,
  FolderKanban, MapPin, Plus, RefreshCw, ShieldCheck, X,
} from 'lucide-react'
import {
  addProjectExpenditure, addProjectMilestone, archiveProject, createProject,
  getProjects, updateProject, updateProjectMilestone,
} from '../api.js'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'

const STATUSES = [
  'PROPOSED', 'SUBMITTED_FOR_APPROVAL', 'APPROVED', 'PLANNED',
  'ONGOING', 'DELAYED', 'COMPLETED', 'VERIFIED', 'CANCELLED',
]
const STATUS_NEXT = {
  PROPOSED: ['SUBMITTED_FOR_APPROVAL', 'CANCELLED'],
  SUBMITTED_FOR_APPROVAL: ['APPROVED', 'PROPOSED', 'CANCELLED'],
  APPROVED: ['PLANNED', 'CANCELLED'],
  PLANNED: ['ONGOING', 'CANCELLED'],
  ONGOING: ['DELAYED', 'COMPLETED', 'CANCELLED'],
  DELAYED: ['ONGOING', 'COMPLETED', 'CANCELLED'],
  COMPLETED: ['VERIFIED', 'ONGOING'],
  VERIFIED: [],
  CANCELLED: [],
}
const COLORS = {
  navy: '#003366',
  blue: '#0099CC',
  teal: '#0099CC',
  amber: '#FFCC00',
  line: '#A2C2E2',
  muted: '#006699',
  red: '#FF9933',
}

const panel = {
  background: '#FFFFFF',
  border: `1px solid ${COLORS.line}`,
  borderRadius: 12,
  padding: 18,
  boxShadow: '0 2px 8px rgba(0,51,102,.05)',
}

const EMPTY_FORM = {
  title: '', description: '', category: '', district: '', taluk: '', local_body: '',
  ward: '', department: '', responsible_authority: '', estimated_cost_lakh: '',
  funding_source: '', start_date: '', expected_completion_date: '',
}

function statusLabel(status = '') {
  return status.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase())
}

function money(value) {
  if (value === null || value === undefined || value === '') return 'Not recorded'
  return `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })} lakh`
}

function sampleBadge(isSample) {
  return isSample ? <Badge variant="amber">ILLUSTRATIVE SAMPLE</Badge> : null
}

function ProjectForm({ onCancel, onCreated, setError }) {
  const [values, setValues] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const set = (key, value) => setValues(current => ({ ...current, [key]: value }))

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const body = { ...values }
      if (body.estimated_cost_lakh) body.estimated_cost_lakh = Number(body.estimated_cost_lakh)
      else delete body.estimated_cost_lakh
      Object.keys(body).forEach(key => {
        if (body[key] === '') delete body[key]
      })
      await createProject(body)
      await onCreated()
      setValues(EMPTY_FORM)
      onCancel()
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Could not create the project.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="Register a development project" subtitle="New projects begin as proposed. Administrative actions are recorded in the audit history." action={<Button variant="ghost" onClick={onCancel}><X size={15} /> Close</Button>}>
      <form onSubmit={submit} style={gridForm}>
        <Field label="Project title" required><input required maxLength={200} value={values.title} onChange={event => set('title', event.target.value)} /></Field>
        <Field label="Category" required><input required maxLength={80} placeholder="Roads, water, drainage…" value={values.category} onChange={event => set('category', event.target.value)} /></Field>
        <Field label="District" required><input required maxLength={100} value={values.district} onChange={event => set('district', event.target.value)} /></Field>
        <Field label="Taluk"><input maxLength={100} value={values.taluk} onChange={event => set('taluk', event.target.value)} /></Field>
        <Field label="Local body"><input maxLength={100} value={values.local_body} onChange={event => set('local_body', event.target.value)} /></Field>
        <Field label="Ward / village"><input maxLength={100} value={values.ward} onChange={event => set('ward', event.target.value)} /></Field>
        <Field label="Department"><input maxLength={150} value={values.department} onChange={event => set('department', event.target.value)} /></Field>
        <Field label="Responsible authority"><input maxLength={150} value={values.responsible_authority} onChange={event => set('responsible_authority', event.target.value)} /></Field>
        <Field label="Estimated cost (₹ lakh)"><input type="number" min="0.01" step="0.01" value={values.estimated_cost_lakh} onChange={event => set('estimated_cost_lakh', event.target.value)} /></Field>
        <Field label="Funding source"><input maxLength={150} value={values.funding_source} onChange={event => set('funding_source', event.target.value)} /></Field>
        <Field label="Start date"><input type="date" value={values.start_date} onChange={event => set('start_date', event.target.value)} /></Field>
        <Field label="Expected completion"><input type="date" value={values.expected_completion_date} onChange={event => set('expected_completion_date', event.target.value)} /></Field>
        <Field label="Description" wide><textarea rows={3} maxLength={3000} value={values.description} onChange={event => set('description', event.target.value)} /></Field>
        <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Create proposed project'}</Button>
        </div>
      </form>
    </Card>
  )
}

function Field({ label, required, wide, children }) {
  return (
    <label style={{ display: 'grid', gap: 5, gridColumn: wide ? '1 / -1' : undefined, color: COLORS.navy, fontSize: 12, fontWeight: 700 }}>
      {label}{required && <span aria-hidden="true"> *</span>}
      {children}
    </label>
  )
}

function ProjectCard({ project, isAdmin, onRefresh, setError }) {
  const [status, setStatus] = useState(project.status)
  const [progress, setProgress] = useState(String(project.progress ?? 0))
  const [statusNote, setStatusNote] = useState('')
  const [milestoneOpen, setMilestoneOpen] = useState(false)
  const [expenditureOpen, setExpenditureOpen] = useState(false)
  const [milestone, setMilestone] = useState({ title: '', description: '', due_date: '' })
  const [expenditure, setExpenditure] = useState({ amount_lakh: '', description: '', expenditure_date: '', funding_source: '', reference: '' })
  const [saving, setSaving] = useState(false)

  const run = async (action) => {
    setSaving(true)
    setError('')
    try {
      await action()
      await onRefresh()
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Could not update this project.')
    } finally {
      setSaving(false)
    }
  }

  const saveStatus = () => run(() => updateProject(project.id, {
    status,
    progress: Number(progress),
    status_note: statusNote || `Status updated to ${statusLabel(status)}`,
  }))

  const saveMilestone = (event) => {
    event.preventDefault()
    const body = { ...milestone }
    if (!body.due_date) delete body.due_date
    run(async () => {
      await addProjectMilestone(project.id, body)
      setMilestone({ title: '', description: '', due_date: '' })
      setMilestoneOpen(false)
    })
  }

  const saveExpenditure = (event) => {
    event.preventDefault()
    const body = { ...expenditure, amount_lakh: Number(expenditure.amount_lakh) }
    Object.keys(body).forEach(key => { if (body[key] === '') delete body[key] })
    run(async () => {
      await addProjectExpenditure(project.id, body)
      setExpenditure({ amount_lakh: '', description: '', expenditure_date: '', funding_source: '', reference: '' })
      setExpenditureOpen(false)
    })
  }

  const archive = () => {
    if (window.confirm(`Archive “${project.title}”? It will no longer appear in the public project list.`)) {
      run(() => archiveProject(project.id))
    }
  }

  return (
    <Card
      title={project.title}
      subtitle={`${project.id} · ${project.category} · ${[project.ward, project.local_body, project.taluk, project.district].filter(Boolean).join(' · ')}`}
      action={<div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>{sampleBadge(project.is_demo_sample)}<Badge variant={project.status === 'DELAYED' ? 'amber' : ['COMPLETED', 'VERIFIED'].includes(project.status) ? 'teal' : 'navy'}>{statusLabel(project.status)}</Badge></div>}
    >
      <div style={{ display: 'grid', gap: 14 }}>
        <p style={{ margin: 0, color: COLORS.muted, fontSize: 13, lineHeight: 1.55 }}>
          {project.description || 'No project description has been recorded.'}
        </p>
        <div style={metricGrid}>
          <ProjectMetric label="Estimated cost" value={money(project.estimated_cost_lakh)} icon={CircleDollarSign} />
          <ProjectMetric label="Recorded expenditure" value={money(project.actual_expenditure_lakh)} icon={CircleDollarSign} />
          <ProjectMetric label="Expected completion" value={project.expected_completion_date || 'Not recorded'} icon={CalendarDays} />
          <ProjectMetric label="Department" value={project.department || 'Not recorded'} icon={ShieldCheck} />
        </div>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: COLORS.muted, marginBottom: 5 }}>
            <span>Recorded progress</span><strong>{project.progress ?? 0}%</strong>
          </div>
          <progress value={project.progress ?? 0} max="100" style={{ width: '100%', height: 9, accentColor: COLORS.teal }} aria-label={`Project progress ${project.progress ?? 0}%`} />
        </div>

        {!!project.milestones?.length && (
          <section>
            <h3 style={subheading}><ClipboardList size={15} /> Milestones</h3>
            <ul style={listStyle}>
              {project.milestones.map(item => (
                <li key={item.id} style={listRow}>
                  <span>{item.title}{item.due_date && <small style={mutedBlock}> · due {item.due_date}</small>}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    {item.completed ? <Badge variant="teal">Complete</Badge> : <Badge variant="amber">Pending</Badge>}
                    {isAdmin && <Button variant="ghost" disabled={saving} onClick={() => run(() => updateProjectMilestone(project.id, item.id, !item.completed))}>
                      {item.completed ? 'Reopen' : 'Complete'}
                    </Button>}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {!!project.expenditures?.length && (
          <section>
            <h3 style={subheading}><CircleDollarSign size={15} /> Expenditure records</h3>
            <ul style={listStyle}>
              {project.expenditures.map(item => (
                <li key={item.id} style={listRow}>
                  <span>{item.description}<small style={mutedBlock}> · {item.expenditure_date || 'date not recorded'}</small></span>
                  <strong>{money(item.amount_lakh)}</strong>
                </li>
              ))}
            </ul>
          </section>
        )}

        {!!project.status_history?.length && (
          <details>
            <summary style={{ cursor: 'pointer', color: COLORS.blue, fontSize: 12, fontWeight: 700 }}>View project history ({project.status_history.length})</summary>
            <ul style={listStyle}>
              {project.status_history.map((item, index) => (
                <li key={`${item.status}-${item.ts}-${index}`} style={listRow}>
                  <span><strong>{statusLabel(item.status)}</strong>{item.note && <small style={mutedBlock}> · {item.note}</small>}</span>
                  <time style={{ color: COLORS.muted, fontSize: 11 }}>{item.ts ? new Date(item.ts * 1000).toLocaleString('en-IN') : ''}</time>
                </li>
              ))}
            </ul>
          </details>
        )}

        {isAdmin && (
          <div style={{ borderTop: `1px solid ${COLORS.line}`, paddingTop: 13, display: 'grid', gap: 10 }}>
            <strong style={{ color: COLORS.navy, fontSize: 13 }}>Authority actions</strong>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 8, alignItems: 'end' }}>
              <Field label="Update project status">
                <select value={status} onChange={event => setStatus(event.target.value)} style={inputStyle}>
                  {[project.status, ...(STATUS_NEXT[project.status] || [])].map(value => <option key={value} value={value}>{statusLabel(value)}</option>)}
                </select>
              </Field>
              <Field label="Progress (%)"><input type="number" min="0" max="100" value={progress} onChange={event => setProgress(event.target.value)} style={inputStyle} /></Field>
              <Field label="Action note"><input value={statusNote} onChange={event => setStatusNote(event.target.value)} maxLength={500} placeholder="Reason or update" style={inputStyle} /></Field>
              <Button disabled={saving} onClick={saveStatus}><CheckCircle2 size={14} /> Save status</Button>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button variant="secondary" onClick={() => setMilestoneOpen(value => !value)}><Plus size={14} /> Add milestone</Button>
              <Button variant="secondary" onClick={() => setExpenditureOpen(value => !value)}><Plus size={14} /> Record expenditure</Button>
              <Button variant="ghost" onClick={archive}><Archive size={14} /> Archive</Button>
            </div>
            {milestoneOpen && (
              <form onSubmit={saveMilestone} style={gridForm}>
                <Field label="Milestone title" required><input required maxLength={200} value={milestone.title} onChange={event => setMilestone({ ...milestone, title: event.target.value })} /></Field>
                <Field label="Due date"><input type="date" value={milestone.due_date} onChange={event => setMilestone({ ...milestone, due_date: event.target.value })} /></Field>
                <Field label="Description" wide><input maxLength={1000} value={milestone.description} onChange={event => setMilestone({ ...milestone, description: event.target.value })} /></Field>
                <Button type="submit" disabled={saving}>Save milestone</Button>
              </form>
            )}
            {expenditureOpen && (
              <form onSubmit={saveExpenditure} style={gridForm}>
                <Field label="Amount (₹ lakh)" required><input required type="number" min="0.01" step="0.01" value={expenditure.amount_lakh} onChange={event => setExpenditure({ ...expenditure, amount_lakh: event.target.value })} /></Field>
                <Field label="Expenditure date" required><input required type="date" value={expenditure.expenditure_date} onChange={event => setExpenditure({ ...expenditure, expenditure_date: event.target.value })} /></Field>
                <Field label="Description" required><input required maxLength={500} value={expenditure.description} onChange={event => setExpenditure({ ...expenditure, description: event.target.value })} /></Field>
                <Field label="Reference"><input maxLength={100} value={expenditure.reference} onChange={event => setExpenditure({ ...expenditure, reference: event.target.value })} /></Field>
                <Button type="submit" disabled={saving}>Record expenditure</Button>
              </form>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

function ProjectMetric({ label, value, icon: Icon }) {
  return (
    <div style={{ border: `1px solid ${COLORS.line}`, borderRadius: 8, padding: 10, minWidth: 0 }}>
      <div style={{ color: COLORS.muted, fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}>
        <Icon size={13} /> {label}
      </div>
      <div style={{ color: COLORS.navy, fontSize: 12, fontWeight: 700, marginTop: 5, overflowWrap: 'anywhere' }}>{value}</div>
    </div>
  )
}

export default function GovernancePage({ user }) {
  const [items, setItems] = useState([])
  const [district, setDistrict] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const isAdmin = user?.role === 'admin'

  const refresh = useCallback(() => {
    setLoading(true)
    setError('')
    const params = projectFilters(district, statusFilter)
    return getProjects(params)
      .then(result => setItems(result))
      .catch(requestError => setError(requestError?.response?.data?.detail || requestError?.message || 'Could not load projects.'))
      .finally(() => setLoading(false))
  }, [district, statusFilter])

  useEffect(() => {
    let active = true
    getProjects(projectFilters(district, statusFilter))
      .then(result => { if (active) setItems(result) })
      .catch(requestError => {
        if (active) setError(requestError?.response?.data?.detail || requestError?.message || 'Could not load projects.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [district, statusFilter])

  return (
    <div style={{ display: 'grid', gap: 16, maxWidth: 1280, margin: '0 auto' }}>
      <header style={{ ...panel, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 15, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <h1 style={{ color: COLORS.navy, fontSize: 'clamp(20px, 3vw, 28px)', margin: 0 }}>Development projects</h1>
            <Badge variant="navy">Application records</Badge>
          </div>
          <p style={{ color: COLORS.muted, fontSize: 13, margin: '6px 0 0' }}>
            Area-based project records, progress history, milestones, and recorded expenditure. This is not an official government feed.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button variant="secondary" onClick={refresh} disabled={loading}><RefreshCw size={14} /> Refresh</Button>
          {isAdmin && <Button onClick={() => setCreating(value => !value)}><Plus size={15} /> New project</Button>}
        </div>
      </header>

      <div role="note" style={{ ...panel, borderLeft: `4px solid ${COLORS.blue}`, color: COLORS.muted, fontSize: 12, lineHeight: 1.5 }}>
        Only recorded application data is shown. Public users see projects after they reach an approved/public lifecycle status; proposed projects are authority-only.
        No official connection, project register, or verified expenditure source is configured.
      </div>

      {error && <div role="alert" style={{ ...panel, color: COLORS.red, borderColor: '#FF9933' }}>{error}</div>}
      {creating && isAdmin && <ProjectForm onCancel={() => setCreating(false)} onCreated={refresh} setError={setError} />}

      <section style={{ ...panel, display: 'flex', gap: 10, alignItems: 'end', flexWrap: 'wrap' }}>
        <Field label="District filter"><input value={district} onChange={event => { setLoading(true); setDistrict(event.target.value) }} maxLength={100} placeholder="Any district" style={inputStyle} /></Field>
        {isAdmin && (
          <Field label="Status filter">
            <select value={statusFilter} onChange={event => { setLoading(true); setStatusFilter(event.target.value) }} style={inputStyle}>
              <option value="">All statuses</option>
              {STATUSES.map(value => <option key={value} value={value}>{statusLabel(value)}</option>)}
            </select>
          </Field>
        )}
        <div style={{ color: COLORS.muted, fontSize: 12, marginLeft: 'auto' }}>{items.length} project record{items.length === 1 ? '' : 's'}</div>
      </section>

      {loading ? (
        <div style={panel} role="status">Loading project records…</div>
      ) : items.length ? (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 480px), 1fr))', gap: 14 }}>
          {items.map(project => (
            <ProjectCard key={project.id} project={project} isAdmin={isAdmin} onRefresh={refresh} setError={setError} />
          ))}
        </section>
      ) : (
        <div style={{ ...panel, textAlign: 'center', padding: '30px 16px' }}>
          <FolderKanban size={28} color={COLORS.muted} />
          <h2 style={{ color: COLORS.navy, fontSize: 17, margin: '10px 0 5px' }}>No project records found</h2>
          <p style={{ color: COLORS.muted, fontSize: 13, margin: 0 }}>
            {district ? 'Try another district filter.' : 'Projects will appear here after an authorized administrator records them.'}
          </p>
        </div>
      )}
      <footer style={{ color: COLORS.muted, fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
        <MapPin size={13} /> Locality names, budgets, and progress are records entered into this installation and are not independently verified.
      </footer>
    </div>
  )
}

const gridForm = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 210px), 1fr))',
  gap: 10,
  alignItems: 'end',
}
function projectFilters(district, statusFilter) {
  const params = {}
  if (district.trim()) params.district = district.trim()
  if (statusFilter) params.status = statusFilter
  return params
}
const metricGrid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
  gap: 8,
}
const inputStyle = {
  width: '100%',
  minHeight: 36,
  boxSizing: 'border-box',
  padding: '7px 9px',
  border: `1px solid ${COLORS.line}`,
  borderRadius: 7,
  color: COLORS.navy,
  background: '#FFFFFF',
}
const subheading = {
  color: COLORS.navy,
  fontSize: 12,
  margin: '0 0 7px',
  display: 'flex',
  alignItems: 'center',
  gap: 6,
}
const listStyle = { listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 5 }
const listRow = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: 10,
  borderBottom: `1px solid ${COLORS.line}`,
  padding: '7px 0',
  color: COLORS.navy,
  fontSize: 12,
}
const mutedBlock = { display: 'inline', color: COLORS.muted, fontSize: 11 }
