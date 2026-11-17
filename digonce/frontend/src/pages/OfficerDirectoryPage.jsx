import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Phone, Mail, MapPin, Building2 } from 'lucide-react'
import { getOfficers, getDistrictDirectory } from '../api.js'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'

export default function OfficerDirectoryPage() {
  const [districts, setDistricts] = useState([])
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ q: '', district: '', taluk: '', department: '', designation: '', locality: '' })

  useEffect(() => { getDistrictDirectory().then(r => setDistricts(r.items || [])).catch(() => {}) }, [])
  useEffect(() => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => String(v || '').trim()))
    setLoading(true)
    getOfficers({ ...params, page: 1, page_size: 50 })
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setError('') })
      .catch((e) => setError(e.response?.data?.detail || 'Could not load officers.'))
      .finally(() => setLoading(false))
  }, [filters])

  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }))

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Officer Directory</div>
          <div className="page-sub">Search recorded public officers and department contacts across Tamil Nadu. Only entered/verified records are shown; names and contact details are never invented.</div>
        </div>
        <Link to="/directory/find-local-officer" style={{ textDecoration: 'none' }}><Button variant="primary" icon={MapPin}>Find My Local Officer</Button></Link>
      </div>

      <Card title="Search and filters" subtitle={`${total} record(s) found`}>
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, border: '1px solid #A2C2E2', borderRadius: 10, padding: '8px 10px' }}><Search size={15} color="#006699" /><input value={filters.q} onChange={(e) => set('q', e.target.value)} placeholder="Name, designation, department, office" style={{ border: 0, outline: 'none', width: '100%' }} /></label>
            <select value={filters.district} onChange={(e) => set('district', e.target.value)}><option value="">All districts</option>{districts.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}</select>
            <input value={filters.taluk} onChange={(e) => set('taluk', e.target.value)} placeholder="Taluk" />
            <input value={filters.department} onChange={(e) => set('department', e.target.value)} placeholder="Department" />
            <input value={filters.designation} onChange={(e) => set('designation', e.target.value)} placeholder="Designation" />
            <input value={filters.locality} onChange={(e) => set('locality', e.target.value)} placeholder="Locality / area" />
          </div>
          {error && <div role="alert" style={{ color: '#FF9933' }}>{error}</div>}
          {loading ? <div>Loading officer records…</div> : items.length ? (
            <div style={{ display: 'grid', gap: 10 }}>
              {items.map((o) => (
                <div key={o.id} className="ns-card" style={{ padding: 12, border: '1px solid #A2C2E2' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontWeight: 800, color: '#003366', fontSize: '1rem' }}>{o.name || 'Name not recorded'}</div>
                      <div style={{ color: '#006699', fontWeight: 700 }}>{o.designation || 'Designation not recorded'}{o.department ? ` · ${o.department}` : ''}</div>
                      <div style={{ fontSize: '0.84rem', color: '#003366', marginTop: 4 }}>{[o.jurisdiction, o.local_body, o.taluk, o.district].filter(Boolean).join(' · ') || 'Jurisdiction not specified'}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <Badge variant={o.verification_status === 'verified' ? 'ocean' : 'gold'}>{o.verification_status || 'unverified'}</Badge>
                      <div style={{ fontSize: '0.75rem', color: '#006699', marginTop: 4 }}>Last verified: {o.last_verified || '—'}</div>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 6, marginTop: 8, fontSize: '0.84rem' }}>
                    <div><Phone size={13} /> {o.phone ? <a href={`tel:${o.phone}`}>{o.phone}</a> : 'Phone not available'}</div>
                    <div><Mail size={13} /> {o.email ? <a href={`mailto:${o.email}`}>{o.email}</a> : 'Email not available'}</div>
                    <div><Building2 size={13} /> {o.office_name || o.office_address || 'Office details not available'}</div>
                    <div><MapPin size={13} /> {o.office_address || 'Address not available'}</div>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#006699', marginTop: 6 }}>Working hours: {o.working_hours || 'Not specified'} · Source: {o.source_name || 'Not specified'} {o.source_url ? <a href={o.source_url} target="_blank" rel="noreferrer">(source)</a> : ''} · Retrieved: {o.retrieved_at || '—'}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: '1rem', border: '1px dashed #A2C2E2', borderRadius: 10, color: '#006699' }}>
              No officer records match the current filters. This directory only displays records that have been entered and maintained by administrators with source/verification details. Try a broader search or select a district.
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
