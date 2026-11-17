import { useEffect, useMemo, useState } from 'react'
import {
  CircleMarker,
  LayerGroup,
  LayersControl,
  MapContainer,
  Popup,
  ScaleControl,
  TileLayer,
  Tooltip as MapTooltip,
  ZoomControl,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import { AnimatePresence, motion } from 'framer-motion'
import { Activity, AlertTriangle, BellRing, Compass, Layers, MapPin, Radio, Search, X } from 'lucide-react'
import { getAsset, getAssets, getCorridors, getIncidents, getWards, getProjects, getReports, reverseGeo, notifyMapLocation } from '../api.js'
import { useLive } from '../hooks/useLive.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'
import { Badge, Button } from '../components/ui/Primitives.jsx'
import 'leaflet/dist/leaflet.css'

const { BaseLayer, Overlay } = LayersControl

const TN_CENTER = [11.1271, 78.6569]
const TN_ZOOM = 7

const TN_DISTRICTS = [
  { name: 'Ariyalur', coords: [11.1401, 79.0786], zoom: 11 },
  { name: 'Chengalpattu', coords: [12.6841, 79.9836], zoom: 11 },
  { name: 'Chennai', coords: [13.0827, 80.2707], zoom: 12 },
  { name: 'Coimbatore', coords: [11.0168, 76.9558], zoom: 11 },
  { name: 'Cuddalore', coords: [11.748, 79.7714], zoom: 11 },
  { name: 'Dharmapuri', coords: [12.1211, 78.1582], zoom: 11 },
  { name: 'Dindigul', coords: [10.3624, 77.9695], zoom: 11 },
  { name: 'Erode', coords: [11.341, 77.7172], zoom: 11 },
  { name: 'Kallakurichi', coords: [11.7404, 78.959], zoom: 11 },
  { name: 'Kancheepuram', coords: [12.8342, 79.7036], zoom: 11 },
  { name: 'Kanyakumari', coords: [8.0883, 77.5385], zoom: 11 },
  { name: 'Karur', coords: [10.9601, 78.0766], zoom: 11 },
  { name: 'Krishnagiri', coords: [12.5266, 78.214], zoom: 11 },
  { name: 'Madurai', coords: [9.9252, 78.1198], zoom: 11 },
  { name: 'Mayiladuthurai', coords: [11.1035, 79.655], zoom: 11 },
  { name: 'Nagapattinam', coords: [10.7672, 79.8449], zoom: 11 },
  { name: 'Namakkal', coords: [11.2189, 78.1674], zoom: 11 },
  { name: 'Nilgiris', coords: [11.4102, 76.695], zoom: 11 },
  { name: 'Perambalur', coords: [11.232, 78.8806], zoom: 11 },
  { name: 'Pudukkottai', coords: [10.3833, 78.8001], zoom: 11 },
  { name: 'Ramanathapuram', coords: [9.3639, 78.8395], zoom: 11 },
  { name: 'Ranipet', coords: [12.9249, 79.3335], zoom: 11 },
  { name: 'Salem', coords: [11.6643, 78.146], zoom: 11 },
  { name: 'Sivaganga', coords: [9.8433, 78.4809], zoom: 11 },
  { name: 'Tenkasi', coords: [8.9564, 77.3152], zoom: 11 },
  { name: 'Thanjavur', coords: [10.787, 79.1378], zoom: 11 },
  { name: 'Theni', coords: [10.0104, 77.4768], zoom: 11 },
  { name: 'Thoothukudi', coords: [8.7642, 78.1348], zoom: 11 },
  { name: 'Tiruchirappalli', coords: [10.7905, 78.7047], zoom: 11 },
  { name: 'Tirunelveli', coords: [8.7139, 77.7567], zoom: 11 },
  { name: 'Tirupathur', coords: [12.496, 78.573], zoom: 11 },
  { name: 'Tiruppur', coords: [11.1085, 77.3411], zoom: 11 },
  { name: 'Tiruvallur', coords: [13.144, 79.9086], zoom: 11 },
  { name: 'Tiruvannamalai', coords: [12.2253, 79.0747], zoom: 11 },
  { name: 'Tiruvarur', coords: [10.7725, 79.6368], zoom: 11 },
  { name: 'Vellore', coords: [12.9165, 79.1325], zoom: 11 },
  { name: 'Viluppuram', coords: [11.9401, 79.4861], zoom: 11 },
  { name: 'Virudhunagar', coords: [9.568, 77.9624], zoom: 11 },
].sort((a, b) => a.name.localeCompare(b.name))

const ESRI_SATELLITE = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
const ESRI_LABELS = 'https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'
const OSM_STANDARD = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'

const ESRI_ATTRIBUTION = 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community'
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

const BAND_COLORS = {
  Healthy: '#0099CC',
  Moderate: '#FFCC00',
  Degrading: '#FF9933',
  Critical: '#FF9933',
}

function isValidCoord(lat, lon) {
  return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
}

function flyToIfValid(map, center, zoom) {
  if (!map || !Array.isArray(center) || center.length !== 2) return
  const [lat, lon] = center
  if (!isValidCoord(lat, lon)) return
  map.flyTo([lat, lon], zoom, { duration: 0.8, easeLinearity: 0.25 })
}

function MapViewController({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    flyToIfValid(map, center, zoom)
  }, [center, zoom, map])
  return null
}

function MapClickSelector({ onSelect }) {
  useMapEvents({
    click(e) {
      if (e?.latlng) onSelect(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

function riskColor(risk = 0, band) {
  if (band && BAND_COLORS[band]) return BAND_COLORS[band]
  if (risk >= 0.75) return '#FF9933'
  if (risk >= 0.5) return '#FF9933'
  if (risk >= 0.25) return '#FFCC00'
  return '#0099CC'
}

function riskRadius(risk = 0) {
  return Math.max(6, Math.min(18, 6 + risk * 18))
}

export default function CityMap() {
  const [corridors, setCorridors] = useState([])
  const [wards, setWards] = useState([])
  const [incidents, setIncidents] = useState([])
  const [projects, setProjects] = useState([])
  const [reports, setReports] = useState([])
  const [selectedCorridor, setSelectedCorridor] = useState(null)
  const [assetDetail, setAssetDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [districtFilter, setDistrictFilter] = useState('')
  const [navDistrict, setNavDistrict] = useState('')
  const [minRisk, setMinRisk] = useState(0)
  const [searchText, setSearchText] = useState('')
  const [mapCenter, setMapCenter] = useState(TN_CENTER)
  const [mapZoom, setMapZoom] = useState(TN_ZOOM)
  const [picked, setPicked] = useState(null)
  const [pickedLoading, setPickedLoading] = useState(false)
  const [notifyState, setNotifyState] = useState({ status: 'idle', message: '' })
  const { tick, connected } = useLive()
  const { t } = useLanguage()

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.allSettled([
      getCorridors(),
      getWards(),
      getIncidents({ limit: 120 }),
      getProjects({ limit: 120 }),
      getReports({ limit: 120 }),
    ])
      .then(([cRes, wRes, iRes, pRes, rRes]) => {
        if (!active) return
        if (cRes.status === 'fulfilled') setCorridors(Array.isArray(cRes.value) ? cRes.value : [])
        if (wRes.status === 'fulfilled') setWards(Array.isArray(wRes.value) ? wRes.value : [])
        if (iRes.status === 'fulfilled') setIncidents(Array.isArray(iRes.value) ? iRes.value : [])
        if (pRes.status === 'fulfilled') setProjects(Array.isArray(pRes.value) ? pRes.value : [])
        if (rRes.status === 'fulfilled') setReports(Array.isArray(rRes.value) ? rRes.value : [])
        if (cRes.status === 'rejected' && pRes.status === 'rejected') {
          setError('Some map layers could not be loaded. Available layers are shown from accessible records.')
        }
      })
      .catch((e) => {
        if (active) setError(e?.message || 'Failed to load GIS map data.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  const districtOptions = useMemo(() => {
    const fromWards = (wards || [])
      .map((w) => ({ ward: String(w.ward ?? ''), district: String(w.district || w.name || '').trim() }))
      .filter((w) => w.ward || w.district)
    const byKey = new Map()
    for (const w of fromWards) {
      const key = w.district || w.ward
      if (!byKey.has(key)) byKey.set(key, w)
    }
    return Array.from(byKey.values()).sort((a, b) => (a.district || a.ward).localeCompare(b.district || b.ward))
  }, [wards])

  const filteredCorridors = useMemo(() => {
    const q = searchText.trim().toLowerCase()
    return corridors.filter((c) => {
      const risk = Number(c.max_risk || c.risk || 0)
      if (risk < minRisk) return false
      if (districtFilter) {
        const wardMatch = String(c.ward ?? '') === districtFilter
        const districtMatch = String(c.district || '').toLowerCase() === districtFilter.toLowerCase()
        const selected = districtOptions.find((d) => d.ward === districtFilter || d.district === districtFilter)
        const byName = selected?.district && String(c.district || '').toLowerCase() === selected.district.toLowerCase()
        if (!wardMatch && !districtMatch && !byName) return false
      }
      if (q) {
        const hay = `${c.corridor_id || ''} ${c.asset_id || ''} ${c.district || ''} ${c.ward || ''} ${c.asset_type || ''} ${c.health_band || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return isValidCoord(Number(c.lat), Number(c.lon))
    })
  }, [corridors, districtFilter, districtOptions, minRisk, searchText])

  const visibleIncidents = useMemo(() => {
    return incidents.filter((i) => {
      if (!isValidCoord(Number(i.lat), Number(i.lon))) return false
      if (districtFilter) {
        const d = districtOptions.find((x) => x.ward === districtFilter || x.district === districtFilter)?.district
        if (d && String(i.district || '').toLowerCase() !== d.toLowerCase() && String(i.ward ?? '') !== districtFilter) return false
      }
      return true
    })
  }, [districtOptions, districtFilter, incidents])

  const visibleReports = useMemo(() => {
    return (reports || []).filter((r) => {
      if (!isValidCoord(Number(r.lat), Number(r.lon))) return false
      if (districtFilter) {
        const d = districtOptions.find((x) => x.ward === districtFilter || x.district === districtFilter)?.district
        if (d && String(r.district || '').toLowerCase() !== d.toLowerCase()) return false
      }
      const q = searchText.trim().toLowerCase()
      if (q) {
        const hay = `${r.id || ''} ${r.category || ''} ${r.district || ''} ${r.locality || ''} ${r.status || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [districtFilter, districtOptions, reports, searchText])

  const visibleProjects = useMemo(() => {
    return (projects || []).filter((p) => {
      if (!isValidCoord(Number(p.lat), Number(p.lon))) return false
      if (districtFilter) {
        const d = districtOptions.find((x) => x.ward === districtFilter || x.district === districtFilter)?.district
        if (d && String(p.district || '').toLowerCase() !== d.toLowerCase()) return false
      }
      const q = searchText.trim().toLowerCase()
      if (q) {
        const hay = `${p.id || ''} ${p.title || ''} ${p.category || ''} ${p.district || ''} ${p.status || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [districtFilter, districtOptions, projects, searchText])

  const handleCorridorClick = async (c) => {
    setSelectedCorridor(c)
    setAssetDetail(null)
    setDetailLoading(true)
    try {
      const list = await getAssets({ corridor_id: c.corridor_id, limit: 10 })
      const first = Array.isArray(list) && list.length ? list[0] : null
      if (first?.asset_id) {
        const full = await getAsset(first.asset_id)
        setAssetDetail(full)
      } else if (c.asset_id) {
        const full = await getAsset(c.asset_id)
        setAssetDetail(full)
      }
    } catch {
      setAssetDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const navigateToDistrict = (name) => {
    setNavDistrict(name)
    if (!name) {
      setMapCenter(TN_CENTER)
      setMapZoom(TN_ZOOM)
      return
    }
    const d = TN_DISTRICTS.find((x) => x.name === name)
    if (d) {
      setMapCenter(d.coords)
      setMapZoom(d.zoom)
      const match = districtOptions.find((opt) => (opt.district || '').toLowerCase() === name.toLowerCase())
      if (match) setDistrictFilter(match.ward || match.district)
    }
  }

  const resetView = () => {
    setDistrictFilter('')
    setNavDistrict('')
    setMinRisk(0)
    setSearchText('')
    setMapCenter(TN_CENTER)
    setMapZoom(TN_ZOOM)
  }

  const handleMapPick = async (lat, lon) => {
    if (!isValidCoord(lat, lon)) return
    setPicked({ lat, lon, loading: true })
    setNotifyState({ status: 'idle', message: '' })
    setPickedLoading(true)
    try {
      const h = await reverseGeo(lat, lon)
      setPicked({ lat, lon, ...h, loading: false })
    } catch {
      setPicked({ lat, lon, state: 'Tamil Nadu', loading: false })
    } finally {
      setPickedLoading(false)
    }
  }

  const sendNotification = async () => {
    if (!picked || !isValidCoord(picked.lat, picked.lon)) return
    setNotifyState({ status: 'sending', message: t.map?.notifying || 'Sending notification…' })
    try {
      const res = await notifyMapLocation({
        lat: picked.lat,
        lon: picked.lon,
        district: picked.district || '',
        taluk: picked.taluk || '',
        block: picked.block || '',
        local_body: picked.local_body || '',
        ward: picked.ward || picked.ward_or_village || '',
        village: picked.village || '',
        locality: picked.locality || '',
        display_name: picked.display_name || '',
      })
      const extra = res?.email_configured ? ` (${res.email_delivered || 0} email delivered)` : (res?.message || '')
      setNotifyState({ status: 'sent', message: `${t.map?.notified || 'Notification sent to administrators and field staff for this area.'} ${extra}`.trim() })
    } catch (e) {
      setNotifyState({ status: 'error', message: e?.response?.data?.detail || t.map?.notifyError || 'Could not send notification.' })
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'calc(100vh - 120px)', minHeight: 560 }}>
      <div className="ns-card" style={{ padding: '0.9rem 1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 36, height: 36, borderRadius: 10, background: '#003366', color: '#fff', display: 'grid', placeItems: 'center' }}><Compass size={18} /></span>
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: '#003366' }}>{t.map?.title || 'Tamil Nadu Infrastructure GIS Map'}</div>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#006699', letterSpacing: '0.04em' }}>
                {t.map?.subtitle || 'CLICK ANYWHERE IN TAMIL NADU · ESRI SATELLITE · STANDARD MAP · VERIFIED COORDINATES'}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <Badge variant={connected ? 'teal' : 'amber'}>{connected ? `Telemetry Sync · Cycle ${tick}` : 'Telemetry Standby'}</Badge>
            <Button variant="secondary" size="sm" onClick={resetView}>Reset View</Button>
          </div>
        </div>

        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10, alignItems: 'end' }}>
          <label style={{ display: 'grid', gap: 4, fontSize: '0.78rem', fontWeight: 700, color: '#006699' }}>
            District Navigation (Tamil Nadu)
            <select value={navDistrict} onChange={(e) => navigateToDistrict(e.target.value)} style={{ minHeight: 38, borderRadius: 8, border: '1px solid #A2C2E2', padding: '0 0.6rem', color: '#003366' }}>
              <option value="">Statewide view (all districts)</option>
              {TN_DISTRICTS.map((d) => <option key={d.name} value={d.name}>{d.name}</option>)}
            </select>
          </label>

          <label style={{ display: 'grid', gap: 4, fontSize: '0.78rem', fontWeight: 700, color: '#006699' }}>
            Filter by District / Ward Data
            <select value={districtFilter} onChange={(e) => setDistrictFilter(e.target.value)} style={{ minHeight: 38, borderRadius: 8, border: '1px solid #A2C2E2', padding: '0 0.6rem', color: '#003366' }}>
              <option value="">All mapped areas</option>
              {districtOptions.map((d) => <option key={`${d.ward}-${d.district}`} value={d.ward || d.district}>{d.district || `Ward ${d.ward}`}</option>)}
            </select>
          </label>

          <label style={{ display: 'grid', gap: 4, fontSize: '0.78rem', fontWeight: 700, color: '#006699' }}>
            Minimum Risk Level ({Math.round(minRisk * 100)}%)
            <input type="range" min="0" max="1" step="0.05" value={minRisk} onChange={(e) => setMinRisk(Number(e.target.value))} />
          </label>

          <label style={{ display: 'grid', gap: 4, fontSize: '0.78rem', fontWeight: 700, color: '#006699' }}>
            Search Asset / Corridor
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, border: '1px solid #A2C2E2', borderRadius: 8, padding: '0 0.55rem', minHeight: 38, background: '#fff' }}>
              <Search size={14} color="#006699" />
              <input value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="ID, district, type..." style={{ border: 0, outline: 'none', width: '100%', color: '#003366', background: 'transparent' }} />
            </div>
          </label>
        </div>

        <div style={{ marginTop: 10, display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: '0.76rem', color: '#006699', fontWeight: 700 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><Layers size={14} /> {filteredCorridors.length} infrastructure points</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><AlertTriangle size={14} /> Risk layer active</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><Activity size={14} /> {visibleIncidents.length} work orders</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><MapPin size={14} /> {visibleReports.length} citizen reports</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><Compass size={14} /> {visibleProjects.length} projects</span>
          {loading && <span>Loading map layers…</span>}
          {error && <span style={{ color: '#FF9933' }}>{error}</span>}
        </div>
        <div style={{ marginTop: 8, fontSize: '0.78rem', color: '#006699', fontWeight: 600 }}>
          {t.map?.clickHint || 'Click anywhere on the map to identify location and notify responsible administrators and field teams.'}
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative', borderRadius: 16, overflow: 'hidden', border: '1px solid #A2C2E2', boxShadow: '0 12px 30px rgba(0,51,102,0.12)', minHeight: 420 }}>
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          minZoom={6}
          maxZoom={19}
          zoomControl={false}
          scrollWheelZoom
          doubleClickZoom
          touchZoom
          inertia
          zoomAnimation
          fadeAnimation
          markerZoomAnimation
          style={{ width: '100%', height: '100%', background: '#A2C2E2', cursor: 'crosshair' }}
        >
          <MapViewController center={mapCenter} zoom={mapZoom} />
          <MapClickSelector onSelect={handleMapPick} />
          <ZoomControl position="bottomright" />
          <ScaleControl position="bottomleft" imperial={false} />

          <LayersControl position="topright">
            <BaseLayer checked name="Satellite (Esri World Imagery)">
              <TileLayer url={ESRI_SATELLITE} attribution={ESRI_ATTRIBUTION} maxZoom={19} />
            </BaseLayer>
            <BaseLayer name="Standard Map (OpenStreetMap)">
              <TileLayer url={OSM_STANDARD} attribution={OSM_ATTRIBUTION} maxZoom={19} />
            </BaseLayer>
            <Overlay checked name="Place Labels">
              <TileLayer url={ESRI_LABELS} attribution={ESRI_ATTRIBUTION} maxZoom={19} />
            </Overlay>

            <Overlay checked name="Infrastructure Assets">
              <LayerGroup>
                {filteredCorridors.map((c) => {
                  const lat = Number(c.lat)
                  const lon = Number(c.lon)
                  const risk = Number(c.max_risk || c.risk || 0)
                  const color = riskColor(risk, c.health_band)
                  const selected = selectedCorridor?.corridor_id === c.corridor_id
                  return (
                    <CircleMarker
                      key={`c-${c.corridor_id || c.asset_id || `${lat}-${lon}`}`}
                      center={[lat, lon]}
                      radius={riskRadius(risk) + (selected ? 2 : 0)}
                      pathOptions={{ color: '#FFFFFF', weight: selected ? 3 : 1.5, fillColor: color, fillOpacity: 0.85 }}
                      eventHandlers={{ click: () => handleCorridorClick(c) }}
                    >
                      <MapTooltip direction="top" offset={[0, -4]} opacity={1}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700 }}>
                          {c.district || `Ward ${c.ward || '—'}`} · {c.asset_type || 'Infrastructure Asset'}
                          <div style={{ fontSize: '0.7rem', color: '#006699', fontWeight: 600 }}>
                            Corridor {c.corridor_id || '—'} · Risk {(risk * 100).toFixed(0)}% · {c.health_band || 'Assessed'}
                          </div>
                        </div>
                      </MapTooltip>
                    </CircleMarker>
                  )
                })}
              </LayerGroup>
            </Overlay>

            <Overlay checked name="Risk Overlay">
              <LayerGroup>
                {filteredCorridors
                  .filter((c) => Number(c.max_risk || c.risk || 0) >= 0.35)
                  .map((c) => {
                    const lat = Number(c.lat)
                    const lon = Number(c.lon)
                    const risk = Number(c.max_risk || c.risk || 0)
                    return (
                      <CircleMarker
                        key={`r-${c.corridor_id || c.asset_id || `${lat}-${lon}`}`}
                        center={[lat, lon]}
                        radius={riskRadius(risk) + 8}
                        pathOptions={{ color: riskColor(risk, c.health_band), weight: 1, fillColor: riskColor(risk, c.health_band), fillOpacity: 0.12 }}
                        interactive={false}
                      />
                    )
                  })}
              </LayerGroup>
            </Overlay>

            <Overlay checked name="Work Orders / Incidents">
              <LayerGroup>
                {visibleIncidents.map((inc, idx) => {
                  const lat = Number(inc.lat)
                  const lon = Number(inc.lon)
                  return (
                    <CircleMarker
                      key={`i-${inc.id || idx}-${lat}-${lon}`}
                      center={[lat, lon]}
                      radius={7}
                      pathOptions={{ color: '#FFFFFF', weight: 2, fillColor: '#006699', fillOpacity: 0.95 }}
                    >
                      <Popup>
                        <div style={{ fontSize: '0.82rem', color: '#003366', minWidth: 200 }}>
                          <div style={{ fontWeight: 800, marginBottom: 4 }}>{inc.title || 'Work Order'}</div>
                          <div><strong>Status:</strong> {inc.status || 'Reported'}</div>
                          <div><strong>Severity:</strong> {inc.severity || 'Not specified'}</div>
                          {(inc.district || inc.ward || inc.locality) && <div><strong>Area:</strong> {[inc.locality, inc.ward, inc.local_body, inc.taluk, inc.district].filter(Boolean).join(', ')}</div>}
                          {inc.description && <div style={{ marginTop: 4, color: '#006699' }}>{String(inc.description).slice(0, 140)}</div>}
                        </div>
                      </Popup>
                      <MapTooltip direction="top" offset={[0, -4]} opacity={1}>Work order · {inc.status || 'Reported'}</MapTooltip>
                    </CircleMarker>
                  )
                })}
              </LayerGroup>
            </Overlay>

            <Overlay checked name="Citizen Reports">
              <LayerGroup>
                {visibleReports.map((r, idx) => {
                  const lat = Number(r.lat)
                  const lon = Number(r.lon)
                  return (
                    <CircleMarker
                      key={`rep-${r.id || idx}-${lat}-${lon}`}
                      center={[lat, lon]}
                      radius={6}
                      pathOptions={{ color: '#FFFFFF', weight: 2, fillColor: '#FF9933', fillOpacity: 0.9 }}
                    >
                      <Popup>
                        <div style={{ fontSize: '0.82rem', color: '#003366', minWidth: 210 }}>
                          <div style={{ fontWeight: 800, marginBottom: 4 }}>{String(r.category || 'Report').replace(/_/g, ' ')}</div>
                          <div><strong>Status:</strong> {r.status || 'Submitted'}</div>
                          {r.severity && <div><strong>Severity:</strong> {r.severity}</div>}
                          <div><strong>Area:</strong> {[r.locality, r.ward || r.ward_or_village, r.local_body, r.taluk, r.district].filter(Boolean).join(', ') || 'Tamil Nadu'}</div>
                          {r.description && <div style={{ marginTop: 4, color: '#006699' }}>{String(r.description).slice(0, 160)}</div>}
                          <div style={{ marginTop: 4, fontSize: '0.74rem', color: '#006699' }}>{Number.isFinite(lat) && Number.isFinite(lon) ? `${lat.toFixed(5)}, ${lon.toFixed(5)}` : ''}</div>
                        </div>
                      </Popup>
                      <MapTooltip direction="top" offset={[0, -4]} opacity={1}>Report · {String(r.category || '').replace(/_/g,' ')}</MapTooltip>
                    </CircleMarker>
                  )
                })}
              </LayerGroup>
            </Overlay>

            <Overlay checked name="Development Projects">
              <LayerGroup>
                {visibleProjects.map((p, idx) => {
                  const lat = Number(p.lat)
                  const lon = Number(p.lon)
                  return (
                    <CircleMarker
                      key={`prj-${p.id || idx}-${lat}-${lon}`}
                      center={[lat, lon]}
                      radius={7}
                      pathOptions={{ color: '#FFFFFF', weight: 2, fillColor: '#0099CC', fillOpacity: 0.9 }}
                    >
                      <Popup>
                        <div style={{ fontSize: '0.82rem', color: '#003366', minWidth: 210 }}>
                          <div style={{ fontWeight: 800, marginBottom: 4 }}>{p.title || p.name || 'Development Project'}</div>
                          <div><strong>Status:</strong> {p.status || 'Planned'}</div>
                          {p.progress != null && <div><strong>Progress:</strong> {p.progress}%</div>}
                          <div><strong>Area:</strong> {[p.locality, p.ward, p.local_body, p.taluk, p.district].filter(Boolean).join(', ') || 'Tamil Nadu'}</div>
                          {p.description && <div style={{ marginTop: 4, color: '#006699' }}>{String(p.description).slice(0, 150)}</div>}
                        </div>
                      </Popup>
                      <MapTooltip direction="top" offset={[0, -4]} opacity={1}>Project · {p.status || 'Planned'}</MapTooltip>
                    </CircleMarker>
                  )
                })}
              </LayerGroup>
            </Overlay>

            <Overlay checked name="Selected Location">
              <LayerGroup>
                {picked && isValidCoord(picked.lat, picked.lon) && (
                  <CircleMarker
                    center={[picked.lat, picked.lon]}
                    radius={10}
                    pathOptions={{ color: '#FFCC00', weight: 3, fillColor: '#FF9933', fillOpacity: 0.95 }}
                  >
                    <Popup>
                      <div style={{ fontSize: '0.82rem', color: '#003366', minWidth: 220 }}>
                        <div style={{ fontWeight: 800, marginBottom: 4 }}>{t.map?.selectedLocation || 'Selected Location'}</div>
                        <div>{[picked.locality, picked.ward || picked.ward_or_village || picked.village, picked.local_body, picked.taluk, picked.district, 'Tamil Nadu'].filter(Boolean).join(', ')}</div>
                        <div style={{ marginTop: 4, color: '#006699' }}>{Number(picked.lat).toFixed(6)}, {Number(picked.lon).toFixed(6)}</div>
                      </div>
                    </Popup>
                  </CircleMarker>
                )}
              </LayerGroup>
            </Overlay>
          </LayersControl>
        </MapContainer>

        <div style={{ position: 'absolute', left: 12, bottom: 12, zIndex: 500, background: 'rgba(255,255,255,0.94)', border: '1px solid #A2C2E2', borderRadius: 10, padding: '8px 10px', fontSize: '0.72rem', color: '#003366', boxShadow: '0 6px 16px rgba(0,51,102,0.12)' }}>
          <div style={{ fontWeight: 800, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}><MapPin size={13} /> Risk Legend</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {[['Healthy', '#0099CC'], ['Moderate', '#FFCC00'], ['High', '#FF9933']].map(([k, c]) => (
              <span key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: c, border: '1px solid #fff' }} /> {k}</span>
            ))}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: '#006699', border: '1px solid #fff' }} /> Work order</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: '#FF9933', border: '1px solid #fff' }} /> Citizen report</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: '#0099CC', border: '1px solid #fff' }} /> Project</span>
          </div>
        </div>

        <AnimatePresence>
          {picked && (
            <motion.div
              initial={{ y: 120, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 120, opacity: 0 }}
              style={{ position: 'absolute', left: 12, right: 12, bottom: 78, zIndex: 900, maxWidth: 520, background: '#FFFFFF', border: '1px solid #A2C2E2', borderRadius: 12, boxShadow: '0 14px 30px rgba(0,51,102,0.18)', overflow: 'hidden' }}
            >
              <div style={{ padding: '0.7rem 0.9rem', background: '#003366', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontWeight: 800, fontSize: '0.9rem' }}><MapPin size={14} style={{ verticalAlign: 'middle' }} /> {t.map?.selectedLocation || 'Selected Location'}</div>
                <button onClick={() => { setPicked(null); setNotifyState({ status: 'idle', message: '' }) }} style={{ background: 'transparent', border: 0, color: '#fff', cursor: 'pointer' }} aria-label="Close"><X size={16} /></button>
              </div>
              <div style={{ padding: '0.8rem 0.9rem', display: 'grid', gap: 6, fontSize: '0.84rem', color: '#003366' }}>
                {pickedLoading ? <div>{t.common?.loading || 'Loading…'}</div> : (
                  <>
                    <div><strong>{t.map?.district || 'District'}:</strong> {picked.district || '—'}</div>
                    <div><strong>{t.map?.taluk || 'Taluk'}:</strong> {picked.taluk || '—'}</div>
                    <div><strong>{t.map?.localBody || 'Local Body'}:</strong> {picked.local_body || '—'}</div>
                    <div><strong>{t.map?.ward || 'Ward/Village'}:</strong> {picked.ward || picked.ward_or_village || picked.village || '—'}</div>
                    <div><strong>{t.map?.locality || 'Locality'}:</strong> {picked.locality || '—'}</div>
                    <div><strong>{t.map?.coordinates || 'Coordinates'}:</strong> {Number(picked.lat).toFixed(6)}, {Number(picked.lon).toFixed(6)}</div>
                    {picked.display_name && <div style={{ color: '#006699', fontSize: '0.78rem' }}>{picked.display_name}</div>}
                  </>
                )}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                  <Button variant="primary" size="sm" icon={BellRing} onClick={sendNotification} disabled={pickedLoading || notifyState.status === 'sending'}>
                    {notifyState.status === 'sending' ? (t.map?.notifying || 'Sending notification…') : (t.map?.notify || 'Notify Admin & Field Team')}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => window.open(`https://www.google.com/maps?q=${picked.lat},${picked.lon}`, '_blank', 'noopener,noreferrer')}>Open in Maps</Button>
                </div>
                {notifyState.message && <div style={{ fontSize: '0.78rem', color: notifyState.status === 'error' ? '#FF9933' : '#006699', fontWeight: 600 }}>{notifyState.message}</div>}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {selectedCorridor && (
            <motion.div
              initial={{ x: 360, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 360, opacity: 0 }}
              transition={{ type: 'spring', damping: 26, stiffness: 240 }}
              style={{ position: 'absolute', top: 12, right: 12, bottom: 12, width: 'min(360px, calc(100% - 24px))', background: '#FFFFFF', border: '1px solid #A2C2E2', borderRadius: 14, boxShadow: '0 20px 40px rgba(0,51,102,0.2)', zIndex: 1000, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            >
              <div style={{ padding: '0.85rem 1rem', background: '#003366', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.68rem', color: '#A2C2E2', fontWeight: 700, letterSpacing: '0.06em' }}>ASSET DETAILS</div>
                  <div style={{ fontWeight: 800, fontSize: '0.98rem' }}>Corridor {selectedCorridor.corridor_id || '—'}</div>
                </div>
                <button onClick={() => setSelectedCorridor(null)} style={{ background: 'transparent', border: 0, color: '#fff', cursor: 'pointer' }} aria-label="Close details"><X size={18} /></button>
              </div>

              <div style={{ padding: '1rem', overflowY: 'auto', display: 'grid', gap: 12 }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Badge variant={Number(selectedCorridor.max_risk || 0) >= 0.6 ? 'red' : Number(selectedCorridor.max_risk || 0) >= 0.35 ? 'amber' : 'teal'}>
                    {selectedCorridor.health_band || 'Assessed'}
                  </Badge>
                  <Badge variant="navy">{(Number(selectedCorridor.max_risk || 0) * 100).toFixed(0)}% Risk</Badge>
                </div>

                <div style={{ display: 'grid', gap: 6, fontSize: '0.84rem', color: '#003366' }}>
                  <div><strong>District/Area:</strong> {selectedCorridor.district || `Ward ${selectedCorridor.ward || '—'}`}</div>
                  <div><strong>Coordinates:</strong> {Number(selectedCorridor.lat).toFixed(5)}, {Number(selectedCorridor.lon).toFixed(5)}</div>
                  <div><strong>Asset Type:</strong> {selectedCorridor.asset_type || 'Infrastructure'}</div>
                  {selectedCorridor.length_m && <div><strong>Length:</strong> {selectedCorridor.length_m} m</div>}
                </div>

                <div className="ns-card" style={{ padding: '0.8rem' }}>
                  <div style={{ fontWeight: 800, color: '#003366', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}><Radio size={14} /> Asset Inspection Data</div>
                  {detailLoading ? (
                    <div style={{ color: '#006699', fontSize: '0.84rem' }}>Loading asset details…</div>
                  ) : assetDetail ? (
                    <div style={{ display: 'grid', gap: 5, fontSize: '0.83rem', color: '#003366' }}>
                      <div><strong>Asset ID:</strong> {assetDetail.asset_id || '—'}</div>
                      <div><strong>Type:</strong> {assetDetail.asset_type || selectedCorridor.asset_type || '—'}</div>
                      <div><strong>Condition:</strong> {assetDetail.condition_score != null ? Number(assetDetail.condition_score).toFixed(2) : '—'}</div>
                      <div><strong>Age:</strong> {assetDetail.age_years != null ? `${Number(assetDetail.age_years).toFixed(1)} years` : '—'}</div>
                      <div><strong>Estimated Work Cost:</strong> {assetDetail.work_cost_lakh != null ? `₹ ${Number(assetDetail.work_cost_lakh).toFixed(1)} lakh` : '—'}</div>
                    </div>
                  ) : (
                    <div style={{ color: '#006699', fontSize: '0.84rem' }}>Detailed asset record is not available for this point. Map coordinates and risk overlay remain accurate from the selected infrastructure data.</div>
                  )}
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  style={{ width: '100%' }}
                  onClick={() => {
                    const id = assetDetail?.asset_id || selectedCorridor.asset_id
                    if (id) window.location.href = `/inspector?id=${encodeURIComponent(id)}`
                  }}
                  disabled={!assetDetail?.asset_id && !selectedCorridor.asset_id}
                >
                  Open Full Inspection Dossier
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}



