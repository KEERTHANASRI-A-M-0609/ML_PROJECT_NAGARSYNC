import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import { Search, Phone, Globe, MapPin, Navigation } from 'lucide-react'
import { getOffices, getDistrictDirectory } from '../api.js'
import { Badge, Card } from '../components/ui/Primitives.jsx'
import 'leaflet/dist/leaflet.css'

export default function OfficeLocatorPage() {
  const [districts, setDistricts] = useState([])
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ q: '', district: '', taluk: '', department: '', office_type: '', locality: '' })

  useEffect(() => { getDistrictDirectory().then(r => setDistricts(r.items || [])).catch(() => {}) }, [])
  useEffect(() => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => String(v || '').trim()))
    setLoading(true)
    getOffices({ ...params, page: 1, page_size: 100 })
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setError('') })
      .catch((e) => setError(e.response?.data?.detail || 'Could not load offices.'))
      .finally(() => setLoading(false))
  }, [filters])

  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }))
  const withCoords = items.filter(o => Number.isFinite(Number(o.lat)) && Number.isFinite(Number(o.lon)))
  const center = withCoords.length ? [Number(withCoords[0].lat), Number(withCoords[0].lon)] : [11.1271, 78.6569]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Government Office Locator</div>
          <div className="page-sub">Search and map recorded government offices across Tamil Nadu. Coordinates, contacts, and details are shown only when available in verified/entered records.</div>
        </div>
      </div>

      <Card title="Search offices" subtitle={`${total} office record(s)`}>
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, border: '1px solid #A2C2E2', borderRadius: 10, padding: '8px 10px' }}><Search size={15} color="#006699" /><input value={filters.q} onChange={(e) => set('q', e.target.value)} placeholder="Office, type, department, address" style={{ border: 0, outline: 'none', width: '100%' }} /></label>
            <select value={filters.district} onChange={(e) => set('district', e.target.value)}><option value="">All districts</option>{districts.map(d => <option key={d.id} value={d.name}>{d.name}</option>)}</select>
            <input value={filters.taluk} onChange={(e) => set('taluk', e.target.value)} placeholder="Taluk" />
            <input value={filters.department} onChange={(e) => set('department', e.target.value)} placeholder="Department" />
            <input value={filters.office_type} onChange={(e) => set('office_type', e.target.value)} placeholder="Office type" />
            <input value={filters.locality} onChange={(e) => set('locality', e.target.value)} placeholder="Locality" />
          </div>
          {error && <div role="alert" style={{ color: '#FF9933' }}>{error}</div>}
          <div style={{ height: 360, borderRadius: 12, overflow: 'hidden', border: '1px solid #A2C2E2' }}>
            <MapContainer center={center} zoom={withCoords.length ? 10 : 7} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
              <TileLayer attribution='Tiles &copy; Esri' url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
              <TileLayer url="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}" />
              {withCoords.map((o) => (
                <CircleMarker key={o.id} center={[Number(o.lat), Number(o.lon)]} radius={7} pathOptions={{ color: '#fff', weight: 2, fillColor: '#006699', fillOpacity: 0.95 }}>
                  <Popup>
                    <div style={{ minWidth: 220 }}>
                      <div style={{ fontWeight: 800 }}>{o.name}</div>
                      <div>{o.office_type}{o.department ? ` · ${o.department}` : ''}</div>
                      {o.address && <div style={{ marginTop: 4 }}>{o.address}</div>}
                      {o.phone && <div><a href={`tel:${o.phone}`}>{o.phone}</a></div>}
                      {Number.isFinite(Number(o.lat)) && <div style={{ marginTop: 4 }}><a href={`https://www.google.com/maps/dir/?api=1&destination=${o.lat},${o.lon}`} target="_blank" rel="noreferrer">Directions</a></div>}
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
          <div style={{ fontSize: '0.82rem', color: '#006699' }}>{withCoords.length ? `${withCoords.length} office(s) mapped with verified/recorded coordinates.` : 'No mapped office coordinates available for current results. Offices without coordinates are listed below when records exist.'}</div>
          {loading ? <div>Loading offices…</div> : items.length ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 10 }}>
              {items.map((o) => (
                <div key={o.id} className="ns-card" style={{ padding: 12, border: '1px solid #A2C2E2' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><strong style={{ color: '#003366' }}>{o.name}</strong><Badge variant={o.verification_status === 'verified' ? 'ocean' : 'gold'}>{o.verification_status || 'unverified'}</Badge></div>
                  <div style={{ color: '#006699', fontSize: '0.84rem' }}>{o.office_type || 'Office'}{o.department ? ` · ${o.department}` : ''}</div>
                  <div style={{ fontSize: '0.84rem', marginTop: 4 }}>{[o.jurisdiction, o.locality, o.local_body, o.taluk, o.district].filter(Boolean).join(', ')}</div>
                  {o.address && <div style={{ fontSize: '0.83rem', marginTop: 4 }}><MapPin size={13} /> {o.address}</div>}
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 6, fontSize: '0.83rem' }}>
                    {o.phone && <a href={`tel:${o.phone}`}><Phone size={13} /> {o.phone}</a>}
                    {o.website && <a href={o.website} target="_blank" rel="noreferrer"><Globe size={13} /> Website</a>}
                    {Number.isFinite(Number(o.lat)) && <a href={`https://www.google.com/maps/dir/?api=1&destination=${o.lat},${o.lon}`} target="_blank" rel="noreferrer"><Navigation size={13} /> Directions</a>}
                  </div>
                  <div style={{ fontSize: '0.77rem', color: '#006699', marginTop: 6 }}>Hours: {o.working_hours || 'Not specified'} · Source: {o.source_name || 'Not specified'} · Last verified: {o.last_verified || '—'}</div>
                </div>
              ))}
            </div>
          ) : <div style={{ padding: '1rem', border: '1px dashed #A2C2E2', borderRadius: 10, color: '#006699' }}>No office records found. Administrators can add verified office records (collectorates, taluk offices, local bodies, PWD/highways/rural/water/sanitation and other departments) with source details.</div>}
        </div>
      </Card>
    </div>
  )
}
