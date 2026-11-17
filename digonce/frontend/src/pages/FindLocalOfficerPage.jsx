import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet'
import { Search, MapPin, LocateFixed, Phone, Mail, Globe, Navigation, Building2 } from 'lucide-react'
import { findLocalOfficer, searchGeo, reverseGeo, getDistrictDirectory, getPublicServices } from '../api.js'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'
import 'leaflet/dist/leaflet.css'

function ClickPick({ onPick }) { useMapEvents({ click(e){ onPick(e.latlng.lat, e.latlng.lng) } }); return null }
function Fly({ center }) { const map = useMap(); useEffect(()=>{ if(center) map.flyTo(center, 14, {duration:0.6}) },[center,map]); return null }

export default function FindLocalOfficerPage() {
  const [districts, setDistricts] = useState([])
  const [services, setServices] = useState([])
  const [query, setQuery] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [form, setForm] = useState({ district:'', taluk:'', block:'', local_body:'', ward:'', village:'', locality:'' })
  const [pin, setPin] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchResults, setSearchResults] = useState([])

  useEffect(() => { getDistrictDirectory().then(r=>setDistricts(r.items||[])).catch(()=>{}); getPublicServices().then(r=>setServices(r.items||[])).catch(()=>{}) }, [])
  useEffect(() => {
    const p = new URLSearchParams(window.location.search)
    const d = p.get('district'); if (d) setForm(f=>({...f,district:d}))
  }, [])

  const run = async (params) => {
    setLoading(true); setError('')
    try { const res = await findLocalOfficer(params); setResults(res) }
    catch (e) { setError(e.response?.data?.detail || 'Could not resolve local contacts.') }
    finally { setLoading(false) }
  }

  const search = async () => {
    if (query.trim().length < 2) return
    try { const r = await searchGeo(query, 6); setSearchResults(r.results || []) } catch { setSearchResults([]) }
  }
  const pickResult = async (r) => {
    setSearchResults([]); setQuery(r.display_name || ''); if (r.lat && r.lon) setPin([r.lat,r.lon])
    setForm(f=>({ ...f, district:r.district||f.district, taluk:r.taluk||f.taluk, block:r.block||f.block, local_body:r.local_body||f.local_body, ward:r.ward||r.ward_or_village||f.ward, village:r.village||f.village, locality:r.locality||f.locality }))
    await run({ lat:r.lat, lon:r.lon, service_id: serviceId || undefined })
  }
  const useGps = () => {
    if (!navigator.geolocation) { setError('GPS not supported. Drop a pin or search a location.'); return }
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const lat = pos.coords.latitude, lon = pos.coords.longitude
      setPin([lat,lon])
      try { const h = await reverseGeo(lat,lon); setForm(f=>({ ...f, district:h.district||f.district, taluk:h.taluk||f.taluk, block:h.block||f.block, local_body:h.local_body||f.local_body, ward:h.ward||h.ward_or_village||f.ward, village:h.village||f.village, locality:h.locality||f.locality })) } catch {}
      await run({ lat, lon, service_id: serviceId || undefined })
    }, () => setError('Could not get GPS location. Drop a pin on the map or search manually.'), { enableHighAccuracy: true, timeout: 10000 })
  }
  const pickPin = async (lat, lon) => {
    setPin([lat,lon])
    try { const h = await reverseGeo(lat,lon); setForm(f=>({ ...f, district:h.district||f.district, taluk:h.taluk||f.taluk, block:h.block||f.block, local_body:h.local_body||f.local_body, ward:h.ward||h.ward_or_village||f.ward, village:h.village||f.village, locality:h.locality||f.locality })) } catch {}
    await run({ lat, lon, service_id: serviceId || undefined })
  }

  const manualFind = async () => {
    await run({ ...Object.fromEntries(Object.entries(form).filter(([,v])=>String(v||'').trim())), service_id: serviceId || undefined })
  }

  const officers = results?.officers || []
  const offices = results?.offices || []

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Find My Local Officer</div>
          <div className="page-sub">Identify responsible administration for any location in Tamil Nadu using GPS, map pin, place search, or manual area selection. Results show recorded/verified contacts only.</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.1fr) minmax(320px,0.9fr)', gap: 14 }}>
        <Card title="Locate your area" subtitle="Use GPS, search, or drop a pin anywhere in Tamil Nadu">
          <div style={{ display: 'grid', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button variant="secondary" icon={LocateFixed} onClick={useGps}>Use GPS</Button>
              <select value={serviceId} onChange={(e)=>setServiceId(e.target.value)}><option value="">All services / general administration</option>{services.map(s=> <option key={s.id} value={s.id}>{s.label}</option>)}</select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input value={query} onChange={(e)=>setQuery(e.target.value)} onKeyDown={(e)=>e.key==='Enter' && (e.preventDefault(),search())} placeholder="Search village, town, landmark, district…" style={{ flex: 1 }} />
              <Button variant="secondary" icon={Search} onClick={search}>Search</Button>
            </div>
            {searchResults.length > 0 && <div style={{ border: '1px solid #A2C2E2', borderRadius: 10, maxHeight: 180, overflow: 'auto' }}>{searchResults.map((r,i)=>(<button key={i} onClick={()=>pickResult(r)} style={{ display:'block', width:'100%', textAlign:'left', padding:'8px 10px', border:0, borderBottom:'1px solid #eef4fb', background:'#fff', cursor:'pointer' }}><div style={{ fontWeight:700, color:'#003366' }}>{[r.locality,r.ward_or_village,r.local_body,r.taluk,r.district].filter(Boolean).join(', ') || 'Location'}</div><div style={{ fontSize:'0.78rem', color:'#006699' }}>{r.display_name}</div></button>))}</div>}
            <div style={{ height: 320, borderRadius: 12, overflow: 'hidden', border: '1px solid #A2C2E2' }}>
              <MapContainer center={pin || [11.1271,78.6569]} zoom={pin ? 14 : 7} style={{ height: '100%', width: '100%' }}>
                <TileLayer attribution='Tiles &copy; Esri' url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
                <TileLayer url="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}" />
                {pin && <Fly center={pin} />}
                <ClickPick onPick={pickPin} />
                {pin && <Marker position={pin} />}
              </MapContainer>
            </div>
            <div style={{ fontSize:'0.82rem', color:'#006699' }}>{pin ? `Selected: ${pin[0].toFixed(5)}, ${pin[1].toFixed(5)}` : 'Click anywhere on the map to identify the area.'}</div>
          </div>
        </Card>

        <Card title="Manual area selection" subtitle="Select known administrative details">
          <div style={{ display: 'grid', gap: 8 }}>
            <select value={form.district} onChange={(e)=>setForm(f=>({...f,district:e.target.value}))}><option value="">Select district</option>{districts.map(d=><option key={d.id} value={d.name}>{d.name}</option>)}</select>
            <input placeholder="Taluk" value={form.taluk} onChange={(e)=>setForm(f=>({...f,taluk:e.target.value}))} />
            <input placeholder="Block" value={form.block} onChange={(e)=>setForm(f=>({...f,block:e.target.value}))} />
            <input placeholder="Municipality / Corporation / Panchayat" value={form.local_body} onChange={(e)=>setForm(f=>({...f,local_body:e.target.value}))} />
            <input placeholder="Ward / Village" value={form.ward} onChange={(e)=>setForm(f=>({...f,ward:e.target.value}))} />
            <input placeholder="Locality / street / hamlet" value={form.locality} onChange={(e)=>setForm(f=>({...f,locality:e.target.value}))} />
            <Button variant="primary" icon={Search} onClick={manualFind} disabled={loading}>{loading ? 'Finding…' : 'Find responsible contacts'}</Button>
            {error && <div role="alert" style={{ color:'#FF9933' }}>{error}</div>}
          </div>
        </Card>
      </div>

      <Card title="Responsible officers and offices" subtitle={results ? `Best available recorded contacts for the selected jurisdiction` : 'Select a location to view results'}>
        {results ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ padding: 10, border: '1px solid #A2C2E2', borderRadius: 10, background: '#fff' }}>
              <div style={{ fontWeight: 800, color: '#003366' }}>Identified area</div>
              <div style={{ color:'#006699', fontSize:'0.9rem' }}>{[results.area?.locality, results.area?.ward || results.area?.village, results.area?.local_body, results.area?.taluk, results.area?.district, 'Tamil Nadu'].filter(Boolean).join(', ')}</div>
              <div style={{ marginTop: 6 }}><Badge variant={results.exact_jurisdiction_match ? 'ocean' : 'gold'}>{results.exact_jurisdiction_match ? 'Jurisdiction match found in records' : 'Best available contacts'}</Badge></div>
              {results.limitation && <div style={{ marginTop: 8, color:'#006699', fontSize:'0.88rem' }}><strong>Note:</strong> {results.limitation}</div>}
            </div>

            <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))', gap: 12 }}>
              <div>
                <div style={{ fontWeight: 800, color:'#003366', marginBottom: 8 }}>Officers ({officers.length})</div>
                {officers.length ? officers.map(o => (
                  <div key={o.id} style={{ border:'1px solid #A2C2E2', borderRadius:10, padding:10, marginBottom:8 }}>
                    <div style={{ fontWeight:800, color:'#003366' }}>{o.name || 'Name not recorded'}</div>
                    <div style={{ color:'#006699' }}>{o.designation}{o.department ? ` · ${o.department}` : ''}</div>
                    <div style={{ fontSize:'0.84rem', marginTop:4 }}>{[o.jurisdiction, o.local_body, o.taluk, o.district].filter(Boolean).join(', ')}</div>
                    <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginTop:6, fontSize:'0.84rem' }}>
                      {o.phone ? <a href={`tel:${o.phone}`}><Phone size={13}/> {o.phone}</a> : <span>Phone not available</span>}
                      {o.email ? <a href={`mailto:${o.email}`}><Mail size={13}/> {o.email}</a> : null}
                    </div>
                    <div style={{ marginTop:6, fontSize:'0.78rem', color:'#006699' }}>Verification: {o.verification_status || 'unverified'} · Source: {o.source_name || 'Not specified'}</div>
                  </div>
                )) : <div style={{ color:'#006699', border:'1px dashed #A2C2E2', borderRadius:10, padding:10 }}>No officer records available for this area. Contact details are shown only from entered/verified records.</div>}
              </div>
              <div>
                <div style={{ fontWeight: 800, color:'#003366', marginBottom: 8 }}>Offices ({offices.length})</div>
                {offices.length ? offices.map(o => (
                  <div key={o.id} style={{ border:'1px solid #A2C2E2', borderRadius:10, padding:10, marginBottom:8 }}>
                    <div style={{ fontWeight:800, color:'#003366' }}>{o.name}</div>
                    <div style={{ color:'#006699' }}>{o.office_type}{o.department ? ` · ${o.department}` : ''}</div>
                    {o.address && <div style={{ fontSize:'0.84rem', marginTop:4 }}><MapPin size={13}/> {o.address}</div>}
                    <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginTop:6, fontSize:'0.84rem' }}>
                      {o.phone ? <a href={`tel:${o.phone}`}><Phone size={13}/> {o.phone}</a> : <span>Phone not available</span>}
                      {o.website ? <a href={o.website} target="_blank" rel="noreferrer"><Globe size={13}/> Website</a> : null}
                      {Number.isFinite(Number(o.lat)) && <a href={`https://www.google.com/maps/dir/?api=1&destination=${o.lat},${o.lon}`} target="_blank" rel="noreferrer"><Navigation size={13}/> Directions</a>}
                    </div>
                    <div style={{ marginTop:6, fontSize:'0.78rem', color:'#006699' }}>Verification: {o.verification_status || 'unverified'} · Source: {o.source_name || 'Not specified'}</div>
                  </div>
                )) : <div style={{ color:'#006699', border:'1px dashed #A2C2E2', borderRadius:10, padding:10 }}>No office records available for this area. Use the official district portal or state grievance channels when local records are unavailable.</div>}
              </div>
            </div>
          </div>
        ) : <div style={{ color:'#006699' }}>Choose a location using GPS, map pin, search, or manual selection to see relevant officers and offices.</div>}
      </Card>
    </div>
  )
}
