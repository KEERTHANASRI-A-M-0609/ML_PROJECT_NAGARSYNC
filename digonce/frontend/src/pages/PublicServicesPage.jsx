import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Droplets, Lightbulb, Construction, Trash2, Waves, Bridge, Wrench, HelpCircle, ExternalLink, Search } from 'lucide-react'
import { getPublicServices, findLocalOfficer, getDistrictDirectory } from '../api.js'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'

const ICONS = { roads: Construction, water: Droplets, streetlight: Lightbulb, drainage: Waves, waste: Trash2, bridge: Bridge, maintenance: Wrench, other: HelpCircle }

export default function PublicServicesPage() {
  const [services, setServices] = useState([])
  const [districts, setDistricts] = useState([])
  const [selected, setSelected] = useState(null)
  const [district, setDistrict] = useState('')
  const [locality, setLocality] = useState('')
  const [contacts, setContacts] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getPublicServices().then(r => { const items = r.items || []; setServices(items); if (items[0]) setSelected(items[0]) }).catch(()=>{})
    getDistrictDirectory().then(r=>setDistricts(r.items||[])).catch(()=>{})
  }, [])

  useEffect(() => {
    const p = new URLSearchParams(window.location.search); const d = p.get('district'); if (d) setDistrict(d)
  }, [])

  const current = selected || services[0]
  const Icon = ICONS[current?.id] || HelpCircle

  const resolve = async () => {
    if (!current) return
    setLoading(true)
    try {
      const res = await findLocalOfficer({ district: district || undefined, locality: locality || undefined, service_id: current.id })
      setContacts(res)
    } catch { setContacts(null) }
    finally { setLoading(false) }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Who Should I Contact?</div>
          <div className="page-sub">Select a civic issue to find the responsible department, local contacts (when recorded), grievance options, and NagarSync reporting.</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px,0.9fr) minmax(0,1.3fr)', gap: 14 }}>
        <Card title="Select an issue" subtitle="Common infrastructure and civic services">
          <div style={{ display: 'grid', gap: 8 }}>
            {services.map((s) => {
              const I = ICONS[s.id] || HelpCircle
              const active = current?.id === s.id
              return (
                <button key={s.id} onClick={() => { setSelected(s); setContacts(null) }} style={{ textAlign: 'left', padding: 10, borderRadius: 10, border: `2px solid ${active ? '#006699' : '#A2C2E2'}`, background: '#fff', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: '#003366', fontWeight: 800 }}><I size={16} color="#006699" /> {s.label}</div>
                </button>
              )
            })}
          </div>
        </Card>

        <div style={{ display: 'grid', gap: 14 }}>
          {current && (
            <Card title={current.label} subtitle="Responsible service guidance">
              <div style={{ display: 'grid', gap: 10, color: '#003366' }}>
                <div><strong>Responsible department:</strong> {current.department || 'Depends on local jurisdiction'}</div>
                <div><strong>Typical offices:</strong> {(current.office_types || []).join(', ') || 'Local body / relevant department office'}</div>
                {current.note && <div style={{ color: '#006699' }}>{current.note}</div>}
                {current.grievance_portal && <div><strong>Official grievance portal:</strong> <a href={current.grievance_portal} target="_blank" rel="noreferrer">{current.grievance_portal} <ExternalLink size={13} /></a></div>}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Link to="/report" style={{ textDecoration: 'none' }}><Button variant="primary">Report in NagarSync</Button></Link>
                  <Link to="/directory/find-local-officer" style={{ textDecoration: 'none' }}><Button variant="secondary">Find Local Officer</Button></Link>
                </div>
                <div style={{ borderTop: '1px solid #A2C2E2', paddingTop: 10 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Find relevant local contacts for this issue</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <select value={district} onChange={(e)=>setDistrict(e.target.value)}><option value="">Select district (optional)</option>{districts.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}</select>
                    <input value={locality} onChange={(e)=>setLocality(e.target.value)} placeholder="Locality / ward / village (optional)" />
                    <Button variant="secondary" icon={Search} onClick={resolve} disabled={loading}>{loading ? 'Searching…' : 'Find contacts'}</Button>
                  </div>
                </div>
              </div>
            </Card>
          )}

          <Card title="Relevant local contacts" subtitle={contacts ? `${contacts.record_count?.officers || 0} officer(s), ${contacts.record_count?.offices || 0} office(s)` : 'Search by district/locality to see recorded contacts'}>
            {contacts ? (
              <div style={{ display: 'grid', gap: 8 }}>
                {contacts.limitation && <div style={{ color: '#006699', fontSize: '0.88rem', border: '1px solid #A2C2E2', borderRadius: 10, padding: 10 }}><strong>Note:</strong> {contacts.limitation}</div>}
                {[...(contacts.offices || []).slice(0,5), ...(contacts.officers || []).slice(0,5)].length ? (
                  [...(contacts.offices || []).slice(0,5).map(o => ({...o,_k:'o'})), ...(contacts.officers || []).slice(0,5).map(o => ({...o,_k:'p'}))].map((o) => (
                    <div key={`${o._k}-${o.id}`} style={{ border: '1px solid #A2C2E2', borderRadius: 10, padding: 10 }}>
                      <div style={{ fontWeight: 800, color: '#003366' }}>{o.name}</div>
                      <div style={{ color: '#006699', fontSize: '0.84rem' }}>{o.office_type || o.designation}{o.department ? ` · ${o.department}` : ''}</div>
                      <div style={{ fontSize: '0.82rem', marginTop: 4 }}>{[o.address || o.office_address, o.phone].filter(Boolean).join(' · ') || 'Contact details not available'}</div>
                      <Badge variant={o.verification_status === 'verified' ? 'ocean' : 'gold'}>{o.verification_status || 'unverified'}</Badge>
                    </div>
                  ))
                ) : <div style={{ color: '#006699' }}>No recorded contacts found for this selection. Use the Find My Local Officer tool or official district/grievance portals.</div>}
              </div>
            ) : <div style={{ color: '#006699' }}>Select district/locality and click “Find contacts” to view the best available recorded offices and officers for this issue.</div>}
          </Card>
        </div>
      </div>
    </div>
  )
}
