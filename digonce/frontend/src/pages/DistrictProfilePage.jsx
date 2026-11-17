import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import { Building2, MapPin, Phone, Mail, Globe, ExternalLink, AlertTriangle, Info, Users, FolderGit2, Megaphone, Landmark } from 'lucide-react'
import { getDistrictProfile } from '../api.js'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'
import 'leaflet/dist/leaflet.css'

function Section({ title, icon: Icon, children, subtitle }) {
  return (
    <Card title={title} subtitle={subtitle} action={Icon ? <Icon size={18} color="#006699" /> : null}>
      {children}
    </Card>
  )
}

function Empty({ text }) {
  return <div style={{ padding: '0.9rem', border: '1px dashed #A2C2E2', borderRadius: 10, color: '#006699', background: '#fff' }}><Info size={14} style={{ verticalAlign: 'middle' }} /> {text}</div>
}

export default function DistrictProfilePage() {
  const { districtId } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    getDistrictProfile(districtId)
      .then((res) => { if (active) { setData(res); setError('') } })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Could not load district profile.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [districtId])

  const profile = data?.profile || {}
  const officers = data?.officers || []
  const offices = data?.offices || []
  const announcements = data?.announcements || []
  const projects = data?.projects || []
  const intel = data?.intelligence || {}
  const center = useMemo(() => {
    const lat = Number(profile.lat), lon = Number(profile.lon)
    return Number.isFinite(lat) && Number.isFinite(lon) ? [lat, lon] : [11.1271, 78.6569]
  }, [profile.lat, profile.lon])

  if (loading) return <div className="page"><div className="panel">Loading district profile…</div></div>
  if (error || !data) return <div className="page"><div className="panel" role="alert" style={{ color: '#FF9933' }}>{error || 'District not found.'}</div></div>

  const openReports = (intel.open_reports || 0)
  const activeWork = (intel.active || 0)
  const resolvedWork = (intel.resolved || 0)

  return (
    <div className="page" style={{ display: 'grid', gap: 14 }}>
      <div className="page-head">
        <div>
          <div className="page-title">{profile.name} District</div>
          <div className="page-sub">Headquarters: <strong>{profile.headquarters || 'Not specified'}</strong> · Statewide district intelligence, administration, and citizen services.</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Link to="/directory" style={{ textDecoration: 'none' }}><Button variant="secondary">All Districts</Button></Link>
          <Link to={`/directory/find-local-officer?district=${encodeURIComponent(profile.name || '')}`} style={{ textDecoration: 'none' }}><Button variant="primary" icon={Users}>Find Local Officer</Button></Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12 }}>
        <Card><div style={{ fontSize: '0.75rem', color: '#006699', fontWeight: 700 }}>OFFICES (RECORDED)</div><div style={{ fontSize: '1.8rem', fontWeight: 900, color: '#003366' }}>{data.counts?.offices ?? offices.length}</div><div style={{ color: '#006699', fontSize: '0.82rem' }}>Verified/unverified directory records</div></Card>
        <Card><div style={{ fontSize: '0.75rem', color: '#006699', fontWeight: 700 }}>OFFICERS (RECORDED)</div><div style={{ fontSize: '1.8rem', fontWeight: 900, color: '#003366' }}>{data.counts?.officers ?? officers.length}</div><div style={{ color: '#006699', fontSize: '0.82rem' }}>Public office contacts entered</div></Card>
        <Card><div style={{ fontSize: '0.75rem', color: '#006699', fontWeight: 700 }}>OPEN REPORTS (RECORDED)</div><div style={{ fontSize: '1.8rem', fontWeight: 900, color: '#003366' }}>{openReports}</div><div style={{ color: '#006699', fontSize: '0.82rem' }}>Citizen/in-system reports</div></Card>
        <Card><div style={{ fontSize: '0.75rem', color: '#006699', fontWeight: 700 }}>WORK ORDERS</div><div style={{ fontSize: '1.8rem', fontWeight: 900, color: '#003366' }}>{activeWork} active / {resolvedWork} resolved</div><div style={{ color: '#006699', fontSize: '0.82rem' }}>From recorded operations</div></Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.1fr) minmax(320px,0.9fr)', gap: 14 }}>
        <Section title="District overview" icon={Landmark} subtitle="Reference profile and available administrative information">
          <div style={{ display: 'grid', gap: 10, color: '#003366' }}>
            <p style={{ margin: 0, lineHeight: 1.7 }}>{profile.overview || 'District overview information will appear here as verified records are added.'}</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 8, fontSize: '0.88rem' }}>
              <div><strong>Headquarters:</strong> {profile.headquarters || 'Not specified'}</div>
              <div><strong>State:</strong> Tamil Nadu</div>
              <div><strong>Coordinates (ref):</strong> {Number.isFinite(Number(profile.lat)) ? `${Number(profile.lat).toFixed(4)}, ${Number(profile.lon).toFixed(4)}` : 'Not available'}</div>
              <div><strong>Profile status:</strong> {profile.data_status || 'reference'}</div>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              {profile.official_portal ? <a href={profile.official_portal} target="_blank" rel="noreferrer"><Button variant="secondary" icon={Globe}>Official District Portal</Button></a> : <Badge variant="gold">Official portal link not verified</Badge>}
              <Badge variant="navy">Data source: {data.profile?.official_portal ? 'NIC district portal (reference link)' : 'reference/compiled'}</Badge>
            </div>
            <div style={{ fontSize: '0.82rem', color: '#006699', borderTop: '1px solid #A2C2E2', paddingTop: 8 }}>
              <strong>Administrative units (taluks, revenue divisions, blocks, local bodies, municipalities/corporations, town/village panchayats):</strong> detailed inventories are shown when verified records are available in the directory. Use district/office searches and map-based discovery for current recorded information.
            </div>
          </div>
        </Section>

        <Section title="District map" icon={MapPin} subtitle="Interactive reference location and recorded markers">
          <div style={{ height: 320, borderRadius: 12, overflow: 'hidden', border: '1px solid #A2C2E2' }}>
            <MapContainer center={center} zoom={10} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
              <TileLayer attribution='Tiles &copy; Esri' url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
              <TileLayer url="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}" />
              <Marker position={center}><Popup><strong>{profile.name}</strong><br/>District headquarters/reference point: {profile.headquarters || profile.name}</Popup></Marker>
              {offices.filter(o => Number.isFinite(Number(o.lat)) && Number.isFinite(Number(o.lon))).slice(0,30).map((o) => (
                <CircleMarker key={o.id} center={[Number(o.lat), Number(o.lon)]} radius={6} pathOptions={{ color: '#fff', weight: 2, fillColor: '#0099CC', fillOpacity: 0.95 }}>
                  <Popup><strong>{o.name}</strong><br/>{o.office_type || 'Office'}<br/>{o.address || ''}</Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
          <div style={{ fontSize: '0.8rem', color: '#006699', marginTop: 8 }}>Map shows district reference point and recorded office coordinates (when available). Verified administrative boundary overlays are not bundled; unavailable boundaries are not invented.</div>
        </Section>
      </div>

      <Section title="Government offices & contacts" icon={Building2} subtitle="Recorded collectorate and departmental offices for this district">
        {offices.length ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 10 }}>
            {offices.slice(0, 12).map((o) => (
              <div key={o.id} style={{ border: '1px solid #A2C2E2', borderRadius: 10, padding: 10 }}>
                <div style={{ fontWeight: 800, color: '#003366' }}>{o.name}</div>
                <div style={{ color: '#006699', fontSize: '0.84rem' }}>{o.office_type || 'Government office'}{o.department ? ` · ${o.department}` : ''}</div>
                {o.address && <div style={{ fontSize: '0.82rem', marginTop: 4 }}>{o.address}</div>}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6, fontSize: '0.82rem' }}>
                  {o.phone && <a href={`tel:${o.phone}`}><Phone size={13} /> {o.phone}</a>}
                  {o.website && <a href={o.website} target="_blank" rel="noreferrer"><Globe size={13} /> Website</a>}
                </div>
                <div style={{ marginTop: 6 }}><Badge variant={o.verification_status === 'verified' ? 'ocean' : 'gold'}>{o.verification_status || 'unverified'}</Badge></div>
              </div>
            ))}
          </div>
        ) : <Empty text="No government office records have been added for this district yet. Administrators can add verified office records with source and contact details." />}
        <div style={{ marginTop: 10 }}><Link to={`/directory/offices?district=${encodeURIComponent(profile.name || '')}`} style={{ textDecoration: 'none' }}><Button variant="secondary">Browse Office Locator</Button></Link></div>
      </Section>

      <Section title="Officer directory" icon={Users} subtitle="Recorded public officers and department contacts">
        {officers.length ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {officers.slice(0, 12).map((o) => (
              <div key={o.id} style={{ border: '1px solid #A2C2E2', borderRadius: 10, padding: 10, display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                <div>
                  <div style={{ fontWeight: 800, color: '#003366' }}>{o.name || 'Name not recorded'} <span style={{ fontWeight: 600, color: '#006699' }}>· {o.designation}</span></div>
                  <div style={{ fontSize: '0.84rem', color: '#006699' }}>{[o.department, o.jurisdiction || [o.local_body, o.taluk, o.district].filter(Boolean).join(', ')].filter(Boolean).join(' · ')}</div>
                  <div style={{ fontSize: '0.82rem', marginTop: 4, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    {o.phone ? <a href={`tel:${o.phone}`}><Phone size={13} /> {o.phone}</a> : <span>Phone: not available</span>}
                    {o.email ? <a href={`mailto:${o.email}`}><Mail size={13} /> {o.email}</a> : <span>Email: not available</span>}
                    {o.office_address && <span><MapPin size={13} /> {o.office_address}</span>}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Badge variant={o.verification_status === 'verified' ? 'ocean' : 'gold'}>{o.verification_status || 'unverified'}</Badge>
                  <div style={{ fontSize: '0.75rem', color: '#006699', marginTop: 4 }}>Last verified: {o.last_verified || '—'}</div>
                </div>
              </div>
            ))}
          </div>
        ) : <Empty text="No officer records have been added for this district yet. Officer profiles are shown only from entered/verified records (names and contact details are never invented)." />}
        <div style={{ marginTop: 10 }}><Link to={`/directory/officers?district=${encodeURIComponent(profile.name || '')}`} style={{ textDecoration: 'none' }}><Button variant="secondary">Open Officer Directory</Button></Link></div>
      </Section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 14 }}>
        <Section title="Infrastructure & citizen issues" icon={AlertTriangle} subtitle="Recorded reports, work orders, and available intelligence">
          <div style={{ display: 'grid', gap: 8, fontSize: '0.9rem' }}>
            <div><strong>Total reports:</strong> {intel.total_reports ?? 0} · <strong>Open:</strong> {intel.open_reports ?? 0} · <strong>Resolved reports:</strong> {intel.resolved_reports ?? 0}</div>
            <div><strong>Work orders:</strong> {intel.total_work_orders ?? 0} · <strong>Active:</strong> {intel.active ?? 0} · <strong>Resolved:</strong> {intel.resolved ?? 0}</div>
            {intel.by_category && Object.keys(intel.by_category).length > 0 && (
              <div><strong>By category:</strong> {Object.entries(intel.by_category).map(([k,v]) => `${String(k).replace(/_/g,' ')} (${v})`).join(', ')}</div>
            )}
            <div style={{ color: '#006699', fontSize: '0.82rem' }}>{intel.scope_note || 'Counts reflect records in this NagarSync instance (including labeled sample scenarios where present), not an official government feed. ML/risk signals, where shown elsewhere, are decision-support estimates and must be distinguished from verified field records.'}</div>
          </div>
        </Section>

        <Section title="Development projects" icon={FolderGit2} subtitle="Recorded district projects and status">
          {projects.length ? (
            <div style={{ display: 'grid', gap: 8 }}>
              {projects.slice(0, 8).map((p) => (
                <div key={p.id} style={{ border: '1px solid #A2C2E2', borderRadius: 10, padding: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><strong style={{ color: '#003366' }}>{p.title}</strong><Badge variant="navy">{String(p.status || '').replace(/_/g,' ')}</Badge></div>
                  <div style={{ fontSize: '0.82rem', color: '#006699' }}>{[p.category, p.department, p.local_body || p.ward || p.taluk].filter(Boolean).join(' · ')}</div>
                  <div style={{ fontSize: '0.82rem', marginTop: 4 }}>Progress: {p.progress ?? 0}% {p.estimated_cost_lakh ? `· Budget: ₹${Number(p.estimated_cost_lakh).toLocaleString('en-IN')} lakh` : ''}</div>
                </div>
              ))}
            </div>
          ) : <Empty text="No development project records are available for this district yet. Public/verified project records will appear here when added." />}
          <div style={{ marginTop: 10 }}><Link to={`/projects?district=${encodeURIComponent(profile.name || '')}`} style={{ textDecoration: 'none' }}><Button variant="secondary">Explore District Projects</Button></Link></div>
        </Section>
      </div>

      <Section title="Public services & grievance channels" icon={Globe} subtitle="Guidance to responsible departments and reporting options">
        <div style={{ display: 'grid', gap: 8, color: '#003366', fontSize: '0.9rem' }}>
          <div>Use the <Link to={`/directory/services?district=${encodeURIComponent(profile.name || '')}`}>“Who Should I Contact?”</Link> service directory to find the responsible department, local office (when recorded), grievance portals, and NagarSync reporting for roads, water, streetlights, drainage, sanitation, bridges, and other civic issues.</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
            <Link to="/directory/services" style={{ textDecoration: 'none' }}><Button variant="primary">Public Services</Button></Link>
            <Link to="/report" style={{ textDecoration: 'none' }}><Button variant="secondary">Report an Issue</Button></Link>
          </div>
        </div>
      </Section>

      <Section title="Announcements & verified updates" icon={Megaphone} subtitle="District notices from recorded/verified sources">
        {announcements.length ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {announcements.map((a) => (
              <div key={a.id} style={{ border: '1px solid #A2C2E2', borderRadius: 10, padding: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><strong style={{ color: '#003366' }}>{a.title}</strong><Badge variant={a.verification_status === 'verified' ? 'ocean' : 'gold'}>{a.verification_status || 'unverified'}</Badge></div>
                <div style={{ fontSize: '0.84rem', color: '#003366', marginTop: 4, lineHeight: 1.6 }}>{a.body || ''}</div>
                <div style={{ fontSize: '0.78rem', color: '#006699', marginTop: 6 }}>{a.source_name ? `Source: ${a.source_name}` : 'Source not specified'} {a.source_url ? <a href={a.source_url} target="_blank" rel="noreferrer"> <ExternalLink size={12} /></a> : ''}</div>
              </div>
            ))}
          </div>
        ) : <Empty text="No district announcements have been published in NagarSync yet. Verified updates will appear here when added by authorized administrators." />}
      </Section>
    </div>
  )
}
