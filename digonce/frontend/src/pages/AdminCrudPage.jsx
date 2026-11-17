import { useCallback, useEffect, useState } from 'react'
import { Archive, ClipboardList, MapPinned, RotateCcw, Save, Shield, Wrench } from 'lucide-react'
import {
  archiveIncident, archiveManagedAsset, archiveManagedUser, archiveReport,
  createIncident, createManagedAsset, createManagedUser, createReport,
  getIncidents, getManagedAssets, getReports, getUsers, restoreIncident,
  restoreManagedAsset, restoreManagedUser, restoreReport, updateIncident, getWards,
  updateManagedAsset, updateManagedUser, updateReport,
} from '../api.js'

const TABS = [
  ['reports', 'Reports', ClipboardList],
  ['incidents', 'Incidents', Wrench],
  ['users', 'User accounts', Shield],
  ['assets', 'Managed assets', MapPinned],
]

const EMPTY_REPORT = { category: 'pothole', severity: 'medium', description: '', location_text: '', district: '', taluk: '', block: '', local_body: '', ward: '', locality: '', lat: '', lon: '' }
const EMPTY_INCIDENT = { title: '', description: '', severity: 'medium', district: '', taluk: '', block: '', local_body: '', ward: '', locality: '', asset_type: '' }
const EMPTY_USER = { name: '', email: '', password: '', role: 'field_worker' }
const EMPTY_ASSET = {
  name: '', asset_type: 'road', district: '', ward: '', lat: '', lon: '',
  age_years: '', condition_score: '', criticality: 1, work_cost_lakh: '',
}
const REPORT_CATEGORIES = [
  ['pothole', 'Pothole / road damage'],
  ['water_leak', 'Water leak'],
  ['streetlight', 'Streetlight issue'],
  ['drainage', 'Drainage problem'],
  ['waste', 'Waste / sanitation'],
  ['bridge_damage', 'Bridge / structure damage'],
  ['other', 'Other infrastructure issue'],
]

function errorText(error) {
  return error.response?.data?.detail || error.message || 'The operation failed.'
}

function numberOrNull(value) {
  return value === '' || value == null ? null : Number(value)
}

function fetchRecords(tab, includeArchived) {
  const params = { include_archived: includeArchived }
  if (tab === 'reports') return getReports({ ...params, limit: 200 })
  if (tab === 'incidents') return getIncidents({ ...params, limit: 200 })
  if (tab === 'users') return getUsers(params)
  return getManagedAssets(params)
}

function Field({ label, value, onChange, type = 'text', options = null, required = false, ...props }) {
  return (
    <label style={{ display: 'grid', gap: 4, fontSize: '0.82rem', color: 'var(--muted)' }}>
      {label}
      {options ? (
        <select value={value ?? ''} required={required} onChange={(event) => onChange(event.target.value)}>
          {options.map(([key, text]) => <option key={key} value={key}>{text}</option>)}
        </select>
      ) : type === 'textarea' ? (
        <textarea className="input" rows={3} maxLength={props.maxLength || 2000} value={value ?? ''} required={required} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input type={type} value={value ?? ''} required={required} onChange={(event) => onChange(event.target.value)} {...props} />
      )}
    </label>
  )
}

export default function AdminCrudPage() {
  const [tab, setTab] = useState('reports')
  const [includeArchived, setIncludeArchived] = useState(false)
  const [rows, setRows] = useState([])
  const [districts, setDistricts] = useState([])
  const [editing, setEditing] = useState(null)
  const [reportDraft, setReportDraft] = useState(EMPTY_REPORT)
  const [incidentDraft, setIncidentDraft] = useState(EMPTY_INCIDENT)
  const [userDraft, setUserDraft] = useState(EMPTY_USER)
  const [assetDraft, setAssetDraft] = useState(EMPTY_ASSET)
  const [busy, setBusy] = useState(false)
  const [loadedKey, setLoadedKey] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    const data = await fetchRecords(tab, includeArchived)
    setRows(data)
  }, [includeArchived, tab])

  const currentKey = `${tab}:${includeArchived}`
  const districtOptions = (currentDistrict) => {
    const options = districts.map((item) => [item.district, item.district])
    if (currentDistrict && !options.some(([value]) => value === currentDistrict)) {
      options.unshift([currentDistrict, currentDistrict])
    }
    return [['', 'Select a district'], ...options]
  }

  useEffect(() => {
    getWards()
      .then(setDistricts)
      .catch((requestError) => setError(errorText(requestError)))
  }, [])

  useEffect(() => {
    let active = true
    fetchRecords(tab, includeArchived)
      .then((data) => {
        if (!active) return
        setRows(data)
        setLoadedKey(currentKey)
      })
      .catch((requestError) => {
        if (active) {
          setRows([])
          setLoadedKey(currentKey)
          setError(errorText(requestError))
        }
      })
    return () => { active = false }
  }, [currentKey, includeArchived, tab])

  const perform = async (label, action) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      setNotice(label)
      setEditing(null)
      await load()
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(false)
    }
  }

  const setDraft = (setter, key, value) => setter((current) => ({ ...current, [key]: value }))
  const create = (event, kind) => {
    event.preventDefault()
    if (kind === 'reports') {
      const body = {
        ...reportDraft,
        lat: numberOrNull(reportDraft.lat),
        lon: numberOrNull(reportDraft.lon),
        location_text: reportDraft.location_text || null,
        state: 'Tamil Nadu',
        district: reportDraft.district || null,
        taluk: reportDraft.taluk || null,
        block: reportDraft.block || null,
        local_body: reportDraft.local_body || null,
        ward: reportDraft.ward || null,
        locality: reportDraft.locality || null,
        severity: reportDraft.severity || 'medium',
      }
      return perform('Report created.', async () => { await createReport(body); setReportDraft(EMPTY_REPORT) })
    }
    if (kind === 'incidents') {
      const body = {
        ...incidentDraft,
        district: incidentDraft.district || null,
        taluk: incidentDraft.taluk || null,
        block: incidentDraft.block || null,
        local_body: incidentDraft.local_body || null,
        ward: incidentDraft.ward || null,
        locality: incidentDraft.locality || null,
        asset_type: incidentDraft.asset_type || null,
        lat: numberOrNull(incidentDraft.lat),
        lon: numberOrNull(incidentDraft.lon),
      }
      return perform('Incident created.', async () => { await createIncident(body); setIncidentDraft(EMPTY_INCIDENT) })
    }
    if (kind === 'users') {
      return perform('User account created.', async () => { await createManagedUser(userDraft); setUserDraft(EMPTY_USER) })
    }
    const body = {
      ...assetDraft,
      ward: numberOrNull(assetDraft.ward),
      lat: numberOrNull(assetDraft.lat),
      lon: numberOrNull(assetDraft.lon),
      age_years: numberOrNull(assetDraft.age_years),
      condition_score: numberOrNull(assetDraft.condition_score),
      criticality: Number(assetDraft.criticality),
      work_cost_lakh: numberOrNull(assetDraft.work_cost_lakh),
    }
    return perform('Managed asset created.', async () => { await createManagedAsset(body); setAssetDraft(EMPTY_ASSET) })
  }

  const save = (event) => {
    event.preventDefault()
    let action
    if (tab === 'reports') {
      action = () => updateReport(editing.id, {
        category: editing.category,
        description: editing.description,
        location_text: editing.location_text || null,
        state: editing.state || 'Tamil Nadu',
        district: editing.district || null,
        taluk: editing.taluk || null,
        block: editing.block || null,
        local_body: editing.local_body || null,
        ward: editing.ward || null,
        locality: editing.locality || null,
        severity: editing.severity || 'medium',
        lat: numberOrNull(editing.lat),
        lon: numberOrNull(editing.lon),
      })
    } else if (tab === 'incidents') {
      action = () => updateIncident(editing.id, {
        title: editing.title,
        description: editing.description,
        severity: editing.severity,
        district: editing.district || null,
        taluk: editing.taluk || null,
        block: editing.block || null,
        local_body: editing.local_body || null,
        ward: editing.ward || null,
        locality: editing.locality || null,
        asset_type: editing.asset_type || null,
        lat: numberOrNull(editing.lat),
        lon: numberOrNull(editing.lon),
      })
    } else if (tab === 'users') {
      const body = { name: editing.name, role: editing.role }
      if (editing.password) body.password = editing.password
      action = () => updateManagedUser(editing.id, body)
    } else {
      action = () => updateManagedAsset(editing.id, {
        name: editing.name,
        asset_type: editing.asset_type,
        district: editing.district,
        ward: numberOrNull(editing.ward),
        lat: numberOrNull(editing.lat),
        lon: numberOrNull(editing.lon),
        age_years: numberOrNull(editing.age_years),
        condition_score: numberOrNull(editing.condition_score),
        criticality: Number(editing.criticality),
        work_cost_lakh: numberOrNull(editing.work_cost_lakh),
      })
    }
    return perform('Record updated.', action)
  }

  const setArchived = (row) => {
    const restore = row.archived_at != null
    const action = tab === 'reports'
      ? restore ? restoreReport : archiveReport
      : tab === 'incidents'
        ? restore ? restoreIncident : archiveIncident
        : tab === 'users'
          ? restore ? restoreManagedUser : archiveManagedUser
          : restore ? restoreManagedAsset : archiveManagedAsset
    return perform(restore ? 'Record restored.' : 'Record archived.', () => action(row.id))
  }

  const startEditing = (row) => setEditing({
    ...row,
    lat: row.lat ?? '',
    lon: row.lon ?? '',
    password: '',
  })

  const reportFields = (draft, setter) => (
    <>
      <Field label="Category" value={draft.category} onChange={(value) => setDraft(setter, 'category', value)} options={REPORT_CATEGORIES} />
      <Field label="Severity" value={draft.severity || 'medium'} onChange={(value) => setDraft(setter, 'severity', value)} options={[['low','Low'],['medium','Medium'],['high','High'],['critical','Critical']]} />
      <Field label="Description" value={draft.description} onChange={(value) => setDraft(setter, 'description', value)} type="textarea" required />
      <Field label="Location description" value={draft.location_text} onChange={(value) => setDraft(setter, 'location_text', value)} maxLength={300} />
      <Field label="District" value={draft.district} onChange={(value) => setDraft(setter, 'district', value)} options={districtOptions(draft.district)} />
      <Field label="Taluk" value={draft.taluk} onChange={(value) => setDraft(setter, 'taluk', value)} maxLength={100} />
      <Field label="Block" value={draft.block} onChange={(value) => setDraft(setter, 'block', value)} maxLength={100} />
      <Field label="Local body" value={draft.local_body} onChange={(value) => setDraft(setter, 'local_body', value)} maxLength={120} />
      <Field label="Ward / Village" value={draft.ward} onChange={(value) => setDraft(setter, 'ward', value)} maxLength={120} />
      <Field label="Locality" value={draft.locality} onChange={(value) => setDraft(setter, 'locality', value)} maxLength={200} />
      <Field label="Latitude" value={draft.lat} onChange={(value) => setDraft(setter, 'lat', value)} type="number" min="-90" max="90" step="any" />
      <Field label="Longitude" value={draft.lon} onChange={(value) => setDraft(setter, 'lon', value)} type="number" min="-180" max="180" step="any" />
    </>
  )

  const incidentFields = (draft, setter) => (
    <>
      <Field label="Title" value={draft.title} onChange={(value) => setDraft(setter, 'title', value)} required maxLength={300} />
      <Field label="Severity" value={draft.severity} onChange={(value) => setDraft(setter, 'severity', value)} options={[['low','Low'],['medium','Medium'],['high','High'],['critical','Critical']]} />
      <Field label="Description" value={draft.description} onChange={(value) => setDraft(setter, 'description', value)} type="textarea" />
      <Field label="District" value={draft.district} onChange={(value) => setDraft(setter, 'district', value)} options={districtOptions(draft.district)} />
      <Field label="Taluk" value={draft.taluk} onChange={(value) => setDraft(setter, 'taluk', value)} maxLength={100} />
      <Field label="Block" value={draft.block} onChange={(value) => setDraft(setter, 'block', value)} maxLength={100} />
      <Field label="Local body" value={draft.local_body} onChange={(value) => setDraft(setter, 'local_body', value)} maxLength={120} />
      <Field label="Ward / Village" value={draft.ward} onChange={(value) => setDraft(setter, 'ward', value)} maxLength={120} />
      <Field label="Locality" value={draft.locality} onChange={(value) => setDraft(setter, 'locality', value)} maxLength={200} />
      <Field label="Asset type" value={draft.asset_type} onChange={(value) => setDraft(setter, 'asset_type', value)} maxLength={50} />
      <Field label="Latitude" value={draft.lat} onChange={(value) => setDraft(setter, 'lat', value)} type="number" min="-90" max="90" step="any" />
      <Field label="Longitude" value={draft.lon} onChange={(value) => setDraft(setter, 'lon', value)} type="number" min="-180" max="180" step="any" />
    </>
  )

  const userFields = (draft, setter, editingMode = false) => (
    <>
      <Field label="Name" value={draft.name} onChange={(value) => setDraft(setter, 'name', value)} required maxLength={100} />
      {!editingMode && <Field label="Email" value={draft.email} onChange={(value) => setDraft(setter, 'email', value)} type="email" required maxLength={200} />}
      <Field label="Role" value={draft.role} onChange={(value) => setDraft(setter, 'role', value)} options={ [['citizen', 'Citizen'], ['field_worker', 'Field worker'], ['admin', 'Administrator']] } />
      <Field label={editingMode ? 'New password (optional)' : 'Password (10+ characters)'} value={draft.password} onChange={(value) => setDraft(setter, 'password', value)} type="password" required={!editingMode} minLength={10} maxLength={200} />
    </>
  )

  const assetFields = (draft, setter) => (
    <>
      <Field label="Asset name" value={draft.name} onChange={(value) => setDraft(setter, 'name', value)} required maxLength={150} />
      <Field label="Asset type" value={draft.asset_type} onChange={(value) => setDraft(setter, 'asset_type', value)} required maxLength={50} />
      <Field label="District" value={draft.district} onChange={(value) => setDraft(setter, 'district', value)} options={districtOptions(draft.district)} required />
      <Field label="Ward" value={draft.ward} onChange={(value) => setDraft(setter, 'ward', value)} type="number" min="1" />
      <Field label="Latitude" value={draft.lat} onChange={(value) => setDraft(setter, 'lat', value)} type="number" min="-90" max="90" step="any" />
      <Field label="Longitude" value={draft.lon} onChange={(value) => setDraft(setter, 'lon', value)} type="number" min="-180" max="180" step="any" />
      <Field label="Age in years" value={draft.age_years} onChange={(value) => setDraft(setter, 'age_years', value)} type="number" min="0" max="500" step="any" />
      <Field label="Condition score (0â€“1)" value={draft.condition_score} onChange={(value) => setDraft(setter, 'condition_score', value)} type="number" min="0" max="1" step="any" />
      <Field label="Criticality (1â€“5)" value={draft.criticality} onChange={(value) => setDraft(setter, 'criticality', value)} type="number" min="1" max="5" required />
      <Field label="Estimated work cost (lakh)" value={draft.work_cost_lakh} onChange={(value) => setDraft(setter, 'work_cost_lakh', value)} type="number" min="0" step="any" />
    </>
  )

  const currentFields = () => tab === 'reports'
    ? reportFields(editing, setEditing)
    : tab === 'incidents'
      ? incidentFields(editing, setEditing)
      : tab === 'users'
        ? userFields(editing, setEditing, true)
        : assetFields(editing, setEditing)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Admin record management</h1>
          <p className="page-sub">Create, view, edit, and archive reports, incidents, accounts, and manually managed assets.</p>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--muted)' }}>
          <input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} />
          Include archived
        </label>
      </div>

      <div className="toggle-row" style={{ marginBottom: 16, flexWrap: 'wrap' }}>
        {TABS.map(([id, title, Icon]) => <button key={id} className={`chip ${tab === id ? 'active' : ''}`} onClick={() => { setTab(id); setEditing(null) }}><Icon size={15} style={{ verticalAlign: 'text-bottom', marginRight: 5 }} />{title}</button>)}
      </div>
      {notice && <div className="panel" role="status" style={{ marginBottom: 12, color: 'var(--ok)' }}>{notice}</div>}
      {error && <div className="panel" role="alert" style={{ marginBottom: 12, color: 'var(--danger)' }}>{error}</div>}

      {tab === 'assets' && (
        <div className="panel" style={{ marginBottom: 12, background: 'var(--bg-soft)' }}>
          These manually managed asset records are stored separately from the simulated model dataset. They are marked <strong>Unscored</strong> and are not included in ML recommendations.
        </div>
      )}

      <form className="panel" onSubmit={(event) => create(event, tab)} style={{ marginBottom: 16 }}>
        <h2 className="panel-title">Create {tab === 'users' ? 'user account' : tab === 'assets' ? 'managed asset' : tab.slice(0, -1)}</h2>
        <div className="grid-2">
          {tab === 'reports' && reportFields(reportDraft, setReportDraft)}
          {tab === 'incidents' && incidentFields(incidentDraft, setIncidentDraft)}
          {tab === 'users' && userFields(userDraft, setUserDraft)}
          {tab === 'assets' && assetFields(assetDraft, setAssetDraft)}
        </div>
        <button className="btn btn-primary" disabled={busy} style={{ marginTop: 12 }}>Create record</button>
      </form>

      {loadedKey !== currentKey ? <div className="panel">Loading recordsâ€¦</div> : rows.length === 0 ? <div className="panel">No records found.</div> : rows.map((row) => (
        <article className="panel" key={row.id} style={{ marginBottom: 10, opacity: row.archived_at ? 0.7 : 1 }}>
          <div className="panel-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span>{row.id} Â· {tab === 'users' ? `${row.name} Â· ${row.role}` : tab === 'assets' ? `${row.name} Â· ${row.asset_type} Â· Unscored` : tab === 'reports' ? `${row.category} Â· ${row.status}` : `${row.status} Â· ${row.severity}`}</span>
            <span style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => startEditing(row)}><Save size={14} /> Edit</button>
              <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => setArchived(row)}>
                {row.archived_at ? <RotateCcw size={14} /> : <Archive size={14} />}{row.archived_at ? 'Restore' : 'Archive'}
              </button>
            </span>
          </div>
          {tab === 'users' ? <p>{row.email}</p> : tab === 'reports' ? <p>{row.description}</p> : tab === 'incidents' ? <p>{row.title} â€” {row.description}</p> : <p>{row.district}{row.ward ? ` Â· Ward ${row.ward}` : ''}{row.age_years != null ? ` Â· Age ${row.age_years} years` : ''}</p>}
          {editing?.id === row.id && (
            <form onSubmit={save} style={{ marginTop: 12 }}>
              <div className="grid-2">{currentFields()}</div>
              <button className="btn btn-primary btn-sm" disabled={busy} style={{ marginTop: 10 }}><Save size={14} /> Save changes</button>
            </form>
          )}
        </article>
      ))}
    </div>
  )
}









