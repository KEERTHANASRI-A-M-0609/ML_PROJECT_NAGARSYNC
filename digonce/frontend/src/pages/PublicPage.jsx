import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  BellRing,
  Building2,
  Camera,
  CheckCircle2,
  ClipboardList,
  FileText,
  Landmark,
  MapPin,
  MessageCircle,
  PlusCircle,
  RefreshCw,
  Send,
  ThumbsUp,
  Users,
  Wrench,
} from 'lucide-react'
import {
  api,
  acknowledgeCommunityReport,
  commentOnCommunityReport,
  createReport,
  getCommunityReports,
  getCommunitySubscription,
  getCommunityWork,
  getProjects,
  getReports,
  setCommunitySubscription,
} from '../api.js'
import { Badge, Button, Card, Input } from '../components/ui/Primitives.jsx'

const CATEGORIES = [
  ['pothole', 'Road / Pothole Issue', 'Damaged road surface, pothole, or unsafe walking/driving condition'],
  ['water_leak', 'Water or Pipeline Leak', 'Leak, overflow, low pressure, or drainage issue'],
  ['streetlight', 'Streetlight / Electrical', 'Non-working light, exposed wiring concern, or dark public area'],
  ['drainage', 'Drainage Problem', 'Blocked drain, flooding, or sewage overflow concern'],
  ['waste', 'Waste / Sanitation', 'Garbage accumulation or sanitation issue'],
  ['bridge_damage', 'Bridge / Public Structure', 'Damage to bridge, culvert, footpath, or public structure'],
  ['other', 'Other Civic Issue', 'Other infrastructure concern affecting the community'],
]

const STATUS_LABELS = {
  new: 'Submitted',
  triaged: 'Under Review',
  accepted: 'Accepted',
  in_progress: 'Work In Progress',
  resolved: 'Resolved',
  rejected: 'Not Accepted',
  closed: 'Closed',
}

function statusVariant(status = '') {
  if (['accepted', 'resolved', 'closed', 'VERIFIED', 'COMPLETED'].includes(status)) return 'teal'
  if (['rejected', 'CANCELLED'].includes(status)) return 'red'
  if (['triaged', 'IN_PROGRESS', 'ASSIGNED', 'COMPLETION_SUBMITTED', 'PLANNED', 'ONGOING', 'DELAYED'].includes(status)) return 'amber'
  return 'navy'
}

function fmtDate(value) {
  if (!value) return '—'
  const d = typeof value === 'number' ? new Date(value * 1000) : new Date(value)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString()
}

function areaLabel(area) {
  if (!area) return 'Select your area'
  return [area.locality, area.ward || area.ward_or_village, area.local_body, area.block, area.taluk, area.district].filter(Boolean).join(', ') || 'Select your area'
}

function ReportImage({ report }) {
  const [src, setSrc] = useState('')
  useEffect(() => {
    let objectUrl
    let cancelled = false
    if (!report.has_image && !report.id) return undefined
    api.get(`/reports/${report.id}/image`, { responseType: 'blob' })
      .then(({ data }) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(data)
        setSrc(objectUrl)
      })
      .catch(() => setSrc(''))
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [report.id, report.has_image])
  if (!src) return null
  return <img src={src} alt="Report evidence" style={{ width: '100%', maxHeight: 220, objectFit: 'cover', borderRadius: 12, border: '1px solid #A2C2E2' }} />
}

export default function PublicPage({ user }) {
  const role = user?.role || 'citizen'
  const isAdmin = role === 'admin'
  const isField = role === 'field_worker'
  const isCitizen = role === 'citizen'

  const [tab, setTab] = useState(isCitizen ? 'forum' : 'forum')
  const [district, setDistrict] = useState('')
  const [taluk, setTaluk] = useState('')
  const [localBody, setLocalBody] = useState('')
  const [block, setBlock] = useState('')
  const [locality, setLocality] = useState('')
  const [ward, setWard] = useState('')
  const [followedArea, setFollowedArea] = useState(null)
  const [forumReports, setForumReports] = useState([])
  const [communityWork, setCommunityWork] = useState([])
  const [projects, setProjects] = useState([])
  const [myReports, setMyReports] = useState([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [commentDrafts, setCommentDrafts] = useState({})

  const [category, setCategory] = useState('pothole')
  const [description, setDescription] = useState('')
  const [locationText, setLocationText] = useState('')

  const area = useMemo(() => ({
    district: district.trim(),
    taluk: taluk.trim(),
    block: block.trim(),
    local_body: localBody.trim(),
    ward: ward.trim(),
    locality: locality.trim(),
  }), [district, taluk, localBody, ward])

  const hasAreaSelection = !!(area.district && (area.taluk || area.block || area.local_body || area.ward || area.locality))
  const isFollowingCurrent = !!(followedArea && hasAreaSelection
    && (followedArea.district || '').toLowerCase() === area.district.toLowerCase()
    && (followedArea.taluk || '').toLowerCase() === (area.taluk || '').toLowerCase()
    && (followedArea.block || '').toLowerCase() === (area.block || '').toLowerCase()
    && (followedArea.local_body || '').toLowerCase() === (area.local_body || '').toLowerCase()
    && (followedArea.ward || followedArea.ward_or_village || '').toLowerCase() === (area.ward || '').toLowerCase()
    && (followedArea.locality || '').toLowerCase() === (area.locality || '').toLowerCase())

  const loadAreaData = useCallback(async (targetArea, opts = {}) => {
    const a = targetArea || area
    const canLoad = isAdmin ? !!a.district : !!(a.district && (a.taluk || a.local_body || a.ward) && opts.followed)
    if (!canLoad) {
      setForumReports([])
      setCommunityWork([])
      setProjects([])
      return
    }
    setLoading(true)
    try {
      const params = Object.fromEntries(Object.entries(a).filter(([, v]) => v))
      const [reports, work] = await Promise.all([
        getCommunityReports(params),
        getCommunityWork(params).catch(() => []),
      ])
      setForumReports(Array.isArray(reports) ? reports : [])
      setCommunityWork(Array.isArray(work) ? work : [])
      try {
        const proj = await getProjects({ district: a.district })
        setProjects(Array.isArray(proj) ? proj.filter((p) => {
          if (!a.taluk && !a.local_body && !a.ward) return true
          const pArea = [p.ward, p.local_body, p.taluk].filter(Boolean).map((x) => String(x).toLowerCase())
          return [a.ward, a.local_body, a.taluk].filter(Boolean).some((x) => pArea.includes(String(x).toLowerCase()))
        }) : [])
      } catch {
        setProjects([])
      }
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not load area forum data. Follow the selected area to view community updates.')
      setForumReports([])
      setCommunityWork([])
    } finally {
      setLoading(false)
    }
  }, [area, isAdmin])

  const loadMyReports = useCallback(async () => {
    if (!isCitizen) return
    try {
      const list = await getReports({ limit: 50 })
      setMyReports(Array.isArray(list) ? list : [])
    } catch {
      setMyReports([])
    }
  }, [isCitizen])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const sub = await getCommunitySubscription().catch(() => ({ area: null }))
        const a = sub?.area
        if (!mounted) return
        if (a) {
          setFollowedArea(a)
          setDistrict(a.district || '')
          setTaluk(a.taluk || '')
          setBlock(a.block || '')
          setLocalBody(a.local_body || '')
          setWard(a.ward || a.ward_or_village || '')
          setLocality(a.locality || '')
          await loadAreaData(a, { followed: true })
        }
      } catch { /* ignore */ }
      await loadMyReports()
    })()
    return () => { mounted = false }
  }, [loadAreaData, loadMyReports])

  const handleFollow = async () => {
    setError('')
    setNotice('')
    if (!hasAreaSelection) {
      setError('Enter district and at least one subdivision (taluk, block, local body, ward/village, or locality) to follow your area.')
      return
    }
    try {
      const res = await setCommunitySubscription(area)
      const saved = res?.area || area
      setFollowedArea(saved)
      setNotice(`You are now following ${areaLabel(saved)}. Community reports, updates, and area work will appear here.`)
      await loadAreaData(saved, { followed: true })
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not follow this area.')
    }
  }

  const handleRefresh = async () => {
    setError('')
    if (isAdmin) await loadAreaData(area, { followed: true })
    else if (followedArea) await loadAreaData(followedArea, { followed: true })
    await loadMyReports()
  }

  const handleAcknowledge = async (id) => {
    try {
      await acknowledgeCommunityReport(id)
      const target = isAdmin ? area : followedArea
      if (target) await loadAreaData(target, { followed: isAdmin || !!followedArea })
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not acknowledge this report.')
    }
  }

  const handleComment = async (id) => {
    const msg = (commentDrafts[id] || '').trim()
    if (!msg) return
    try {
      await commentOnCommunityReport(id, msg)
      setCommentDrafts((p) => ({ ...p, [id]: '' }))
      const target = isAdmin ? area : followedArea
      if (target) await loadAreaData(target, { followed: isAdmin || !!followedArea })
      setNotice('Your update was posted to the area forum.')
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not post comment.')
    }
  }

  const handleSubmitReport = async (e) => {
    e.preventDefault()
    setError('')
    setNotice('')
    if (!description.trim()) { setError('Please describe the issue clearly.'); return }
    setNotice('Use the full map-based Report Issue page to select an exact location anywhere in Tamil Nadu and attach evidence. This ensures accurate routing to the responsible authority.');
  }

  const tabs = [
    { id: 'forum', label: 'Area Forum', icon: Users },
    ...(isCitizen ? [{ id: 'my_reports', label: 'My Reports', icon: FileText }] : []),
    ...(isCitizen ? [{ id: 'report', label: 'Report Issue', icon: PlusCircle }] : []),
    { id: 'governance', label: 'Area Progress', icon: Landmark },
  ]

  const intro = isCitizen
    ? { title: 'Citizen Community & Area Forum', sub: 'Follow your locality, report issues, discuss with your community, and track municipal progress in one place.' }
    : isField
      ? { title: 'Field Team Area Forum', sub: 'Follow assigned localities, view citizen concerns, share field updates, and coordinate visible progress for the area.' }
      : { title: 'Governance & Community Forum', sub: 'Monitor area-level concerns, community discussion, work progress, and development records to strengthen local governance.' }

  return (
    <div className="page" style={{ display: 'grid', gap: 16 }}>
      <div className="ns-card" style={{ padding: '1.2rem 1.3rem', background: 'linear-gradient(135deg, #FFFFFF 0%, #FFFFFF 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Users size={22} color="#006699" />
              <h1 style={{ margin: 0, fontSize: '1.45rem', color: '#003366' }}>{intro.title}</h1>
              <Badge variant="navy">{isCitizen ? 'CITIZEN' : isField ? 'FIELD WORKER' : 'ADMIN'}</Badge>
            </div>
            <p style={{ margin: 0, color: '#006699', maxWidth: 760, lineHeight: 1.6 }}>{intro.sub}</p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Button variant="secondary" size="sm" onClick={handleRefresh} icon={RefreshCw} disabled={loading}>Refresh</Button>
            {isCitizen && <Link to="/report" style={{ textDecoration: 'none' }}><Button variant="primary" size="sm" icon={Camera}>Quick Report</Button></Link>}
            {(isAdmin || isField) && <Link to="/field" style={{ textDecoration: 'none' }}><Button variant="primary" size="sm" icon={Wrench}>Field Work</Button></Link>}
            {isAdmin && <Link to="/governance" style={{ textDecoration: 'none' }}><Button variant="secondary" size="sm" icon={Landmark}>Governance</Button></Link>}
          </div>
        </div>
      </div>

      {notice && <div style={{ padding: '0.85rem 1rem', borderRadius: 12, border: '1px solid #A2C2E2', background: '#FFFFFF', color: '#003366', fontWeight: 600 }}>{notice}</div>}
      {error && <div role="alert" style={{ padding: '0.85rem 1rem', borderRadius: 12, border: '1px solid #FF9933', background: '#FFFFFF', color: '#003366', fontWeight: 600 }}>{error}</div>}

      <div className="ns-card" style={{ padding: '1rem 1.1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <div style={{ fontWeight: 800, color: '#003366', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8 }}><MapPin size={17} color="#006699" /> Select and follow your area</div>
            <div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 2 }}>Choose district and locality to view the community forum, active work, and governance updates for that area.</div>
          </div>
          {followedArea && <Badge variant="teal">Following: {areaLabel(followedArea)}</Badge>}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 10 }}>
          <Input label="District *" value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="Any district in Tamil Nadu" />
          <Input label="Taluk" value={taluk} onChange={(e) => setTaluk(e.target.value)} placeholder="Taluk" />
          <Input label="Block" value={block} onChange={(e) => setBlock(e.target.value)} placeholder="Block" />
          <Input label="Local Body" value={localBody} onChange={(e) => setLocalBody(e.target.value)} placeholder="Corporation / Municipality / Panchayat" />
          <Input label="Ward / Village" value={ward} onChange={(e) => setWard(e.target.value)} placeholder="Ward or village" />
          <Input label="Locality" value={locality} onChange={(e) => setLocality(e.target.value)} placeholder="Street, hamlet, locality" />
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 12 }}>
          <Button variant="primary" onClick={handleFollow} icon={BellRing}>{followedArea ? 'Update Followed Area' : 'Follow This Area'}</Button>
          <Button variant="secondary" onClick={() => loadAreaData(isAdmin ? area : followedArea || area, { followed: isAdmin || !!followedArea })} icon={RefreshCw} disabled={loading || (!isAdmin && !followedArea)}>Load Area Forum</Button>
          {!isAdmin && !followedArea && <span style={{ color: '#006699', fontSize: '0.84rem', alignSelf: 'center' }}>Follow an area to participate in the community forum and receive relevant updates.</span>}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {tabs.map((t) => {
          const Icon = t.icon
          const active = tab === t.id
          return (
            <button key={t.id} type="button" onClick={() => setTab(t.id)} className={`ns-btn ${active ? 'ns-btn-primary' : 'ns-btn-secondary'} ns-btn-sm`} style={{ borderRadius: 999 }}>
              <Icon size={15} /> {t.label}
            </button>
          )
        })}
      </div>

      {tab === 'forum' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.45fr) minmax(280px,0.75fr)', gap: 16, alignItems: 'start' }}>
          <div style={{ display: 'grid', gap: 14 }}>
            <Card title={`Area Forum Discussions${followedArea || isAdmin ? `  ·  ${areaLabel(isAdmin ? area : followedArea)}` : ''}`} subtitle="Public issue reports, acknowledgements, and community updates for the selected area.">
              {!followedArea && !isAdmin ? (
                <div style={{ padding: '1rem', border: '1px dashed #A2C2E2', borderRadius: 12, color: '#006699' }}>
                  Follow your area above to open the local forum. You will be able to view reported issues, support concerns, and post helpful updates for your locality.
                </div>
              ) : loading ? (
                <div style={{ color: '#006699' }}>Loading area forum…</div>
              ) : forumReports.length === 0 ? (
                <div style={{ padding: '1rem', border: '1px dashed #A2C2E2', borderRadius: 12, color: '#006699' }}>
                  No community reports found for this area yet. {isCitizen ? 'Be the first to report an issue so authorities and neighbors can respond.' : 'Encourage residents to report issues and track progress transparently.'}
                </div>
              ) : (
                <div style={{ display: 'grid', gap: 12 }}>
                  {forumReports.map((report) => (
                    <motion.article key={report.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="ns-card" style={{ padding: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                        <div>
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                            <strong style={{ color: '#003366', fontSize: '1rem' }}>{String(report.category || 'Issue').replace(/_/g, ' ')}</strong>
                            <Badge variant={statusVariant(report.status)}>{STATUS_LABELS[report.status] || String(report.status || 'submitted').toUpperCase()}</Badge>
                            {report.work_status && <Badge variant={statusVariant(report.work_status)}>Work: {String(report.work_status).replace(/_/g, ' ')}</Badge>}
                          </div>
                          <div style={{ color: '#006699', fontSize: '0.82rem', marginTop: 4 }}>{report.location_text || 'Location provided'} · {[report.locality, report.ward, report.local_body, report.block, report.taluk, report.district].filter(Boolean).join(', ')}</div>
                        </div>
                        <div style={{ color: '#006699', fontSize: '0.78rem' }}>{fmtDate(report.created_at)}</div>
                      </div>
                      <p style={{ margin: '0.7rem 0', color: '#003366', lineHeight: 1.6 }}>{report.description}</p>
                      <ReportImage report={report} />
                      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginTop: 10 }}>
                        <Button variant={report.acknowledged ? 'secondary' : 'primary'} size="sm" onClick={() => handleAcknowledge(report.id)} icon={ThumbsUp}>
                          {report.acknowledged ? 'Acknowledged' : 'Support'} ({report.acknowledgement_count || 0})
                        </Button>
                        <span style={{ color: '#006699', fontSize: '0.84rem', display: 'inline-flex', alignItems: 'center', gap: 6 }}><MessageCircle size={15} /> {(report.comments || []).length} updates</span>
                        {report.incident_id && <span style={{ color: '#006699', fontSize: '0.8rem' }}>Work order: {report.incident_id}</span>}
                      </div>
                      {(report.comments || []).length > 0 && (
                        <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                          {(report.comments || []).slice(-4).map((c, i) => (
                            <div key={`${report.id}-c-${i}`} style={{ padding: '0.6rem 0.75rem', background: '#FFFFFF', border: '1px solid #A2C2E2', borderRadius: 10 }}>
                              <div style={{ fontSize: '0.75rem', color: '#006699', fontWeight: 700, marginBottom: 2 }}>{c.author || 'Community member'}  ·  {fmtDate(c.created_at)}</div>
                              <div style={{ color: '#003366', fontSize: '0.88rem', lineHeight: 1.5 }}>{c.message}</div>
                            </div>
                          ))}
                        </div>
                      )}
                      <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <input
                          type="text"
                          value={commentDrafts[report.id] || ''}
                          onChange={(e) => setCommentDrafts((p) => ({ ...p, [report.id]: e.target.value }))}
                          placeholder={isCitizen ? 'Add helpful information or support for this issue…' : 'Share an official update, observation, or action takenâ€¦'}
                          style={{ flex: '1 1 260px', minHeight: 40, padding: '0.55rem 0.75rem', borderRadius: 10, border: '1px solid #A2C2E2', font: 'inherit', color: '#003366' }}
                        />
                        <Button variant="secondary" size="sm" onClick={() => handleComment(report.id)} icon={Send}>Post</Button>
                      </div>
                    </motion.article>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div style={{ display: 'grid', gap: 14 }}>
            <Card title="Area At A Glance" subtitle="Key signals for the selected locality">
              <div style={{ display: 'grid', gap: 10 }}>
                <div style={{ padding: '0.8rem', border: '1px solid #A2C2E2', borderRadius: 12, background: '#FFFFFF' }}>
                  <div style={{ color: '#006699', fontSize: '0.78rem', fontWeight: 700 }}>Forum reports</div>
                  <div style={{ color: '#003366', fontSize: '1.5rem', fontWeight: 900 }}>{forumReports.length}</div>
                </div>
                <div style={{ padding: '0.8rem', border: '1px solid #A2C2E2', borderRadius: 12, background: '#FFFFFF' }}>
                  <div style={{ color: '#006699', fontSize: '0.78rem', fontWeight: 700 }}>Active municipal work items</div>
                  <div style={{ color: '#003366', fontSize: '1.5rem', fontWeight: 900 }}>{communityWork.length}</div>
                </div>
                <div style={{ padding: '0.8rem', border: '1px solid #A2C2E2', borderRadius: 12, background: '#FFFFFF' }}>
                  <div style={{ color: '#006699', fontSize: '0.78rem', fontWeight: 700 }}>Development projects in view</div>
                  <div style={{ color: '#003366', fontSize: '1.5rem', fontWeight: 900 }}>{projects.length}</div>
                </div>
              </div>
            </Card>

            <Card title="Active Municipal Work" subtitle="Visible work and progress for this area">
              {communityWork.length === 0 ? (
                <p style={{ margin: 0, color: '#006699', fontSize: '0.88rem' }}>No active public work records visible for this area yet.</p>
              ) : (
                <div style={{ display: 'grid', gap: 10 }}>
                  {communityWork.slice(0, 6).map((w) => (
                    <div key={w.id} style={{ padding: '0.75rem', border: '1px solid #A2C2E2', borderRadius: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                        <strong style={{ color: '#003366', fontSize: '0.9rem' }}>{w.title || w.id}</strong>
                        <Badge variant={statusVariant(w.status)}>{String(w.status || '').replace(/_/g, ' ') || 'Open'}</Badge>
                      </div>
                      <div style={{ color: '#006699', fontSize: '0.8rem', marginTop: 4 }}>{w.description || [w.ward, w.taluk, w.district].filter(Boolean).join(', ')}</div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card title="How this forum improves governance" subtitle="Clear, area-focused collaboration">
              <ul style={{ margin: 0, paddingLeft: 18, color: '#006699', lineHeight: 1.7, fontSize: '0.88rem' }}>
                <li>Citizens report and support local issues with location context.</li>
                <li>Field teams share operational updates and visible progress.</li>
                <li>Administrators track concerns, work, and projects by area.</li>
                <li>Shared visibility helps prioritize action and accountability.</li>
              </ul>
            </Card>
          </div>
        </div>
      )}

      {tab === 'my_reports' && isCitizen && (
        <Card title="My Submitted Reports" subtitle="Track status and municipal response for issues you reported">
          {myReports.length === 0 ? (
            <div style={{ padding: '1rem', color: '#006699' }}>You have not submitted any reports yet. Use <strong>Report Issue</strong> to raise a concern in your area.</div>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {myReports.map((r) => (
                <div key={r.id} style={{ padding: '0.9rem 1rem', border: '1px solid #A2C2E2', borderRadius: 12, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ minWidth: 220 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <strong style={{ color: '#003366' }}>{String(r.category || '').replace(/_/g, ' ')}</strong>
                      <Badge variant={statusVariant(r.status)}>{STATUS_LABELS[r.status] || String(r.status || '').toUpperCase()}</Badge>
                    </div>
                    <div style={{ color: '#003366', marginTop: 4 }}>{r.description}</div>
                    <div style={{ color: '#006699', fontSize: '0.8rem', marginTop: 4 }}>{r.location_text || '—'}  ·  {fmtDate(r.created_at)}</div>
                  </div>
                  {r.incident_id && <Badge variant="navy">Work order: {r.incident_id}</Badge>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === 'report' && isCitizen && (
        <Card title="Report an Infrastructure Issue" subtitle="Use the map-based reporting flow to select any location in Tamil Nadu, capture coordinates, identify jurisdiction, and attach evidence.">
          <div style={{ display: 'grid', gap: 14, maxWidth: 760 }}>
            <div style={{ padding: '1rem', border: '1px solid #A2C2E2', borderRadius: 12, color: '#003366', lineHeight: 1.7, background: '#FFFFFF' }}>
              Accurate location and jurisdiction details are required for statewide routing. The full report form supports satellite map pin-drop, GPS, place search, photo/video evidence, severity, and automatic area identification.
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Link to="/report" style={{ textDecoration: 'none' }}><Button type="button" variant="primary" icon={Camera}>Open Map-Based Report</Button></Link>
              <Button type="button" variant="secondary" onClick={() => setTab('forum')}>Back to Forum</Button>
            </div>
            <div style={{ color: '#006699', fontSize: '0.86rem' }}>
              After submitting, track status in <strong>My Reports</strong> and follow your area in the forum for community updates and municipal progress.
            </div>
          </div>
        </Card>
      )}
      {tab === 'governance' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 16 }}>
          <Card title="Area Development & Governance Progress" subtitle="Publicly visible project records and progress for the selected area">
            {projects.length === 0 ? (
              <div style={{ color: '#006699' }}>No development project records found for the selected area yet. Follow/select an area and refresh, or view the full governance workspace.</div>
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                {projects.slice(0, 8).map((p) => (
                  <div key={p.id} style={{ padding: '0.9rem', border: '1px solid #A2C2E2', borderRadius: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                      <strong style={{ color: '#003366' }}>{p.title || p.id}</strong>
                      <Badge variant={statusVariant(p.status)}>{String(p.status || 'PROPOSED').replace(/_/g, ' ')}</Badge>
                    </div>
                    <div style={{ color: '#006699', fontSize: '0.84rem', marginTop: 4 }}>{p.category || 'Development project'}  ·  {[p.ward, p.taluk, p.district].filter(Boolean).join(', ')}</div>
                    <div style={{ marginTop: 8, height: 8, background: '#A2C2E2', borderRadius: 999, overflow: 'hidden' }}>
                      <div style={{ width: `${Math.max(0, Math.min(100, Number(p.progress || 0)))}%`, height: '100%', background: '#0099CC' }} />
                    </div>
                    <div style={{ marginTop: 4, color: '#006699', fontSize: '0.8rem' }}>Progress: {Number(p.progress || 0)}% {p.expected_completion_date ? ` ·  Target: ${p.expected_completion_date}` : ''}</div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 12 }}>
              <Link to="/governance" style={{ textDecoration: 'none' }}><Button variant="secondary" icon={Landmark}>Open Governance Workspace</Button></Link>
            </div>
          </Card>

          <Card title="Role-based actions for this area" subtitle="Designed to make local governance more transparent and responsive">
            <div style={{ display: 'grid', gap: 10 }}>
              {isCitizen && (
                <>
                  <div className="ns-card" style={{ padding: '0.85rem' }}><strong style={{ color: '#003366' }}><ClipboardList size={15} /> Report & track</strong><div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 4 }}>Submit issues, follow your area, and monitor status updates from authorities and field teams.</div></div>
                  <div className="ns-card" style={{ padding: '0.85rem' }}><strong style={{ color: '#003366' }}><MessageCircle size={15} /> Participate in forum</strong><div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 4 }}>Support reports, add helpful details, and stay informed about work in your locality.</div></div>
                </>
              )}
              {isField && (
                <>
                  <div className="ns-card" style={{ padding: '0.85rem' }}><strong style={{ color: '#003366' }}><Wrench size={15} /> Operational updates</strong><div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 4 }}>Review area concerns, coordinate with assigned work, and post progress updates for transparency.</div></div>
                  <div className="ns-card" style={{ padding: '0.85rem' }}><strong style={{ color: '#003366' }}><Building2 size={15} /> Field visibility</strong><div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 4 }}>Use area context to prioritize site work and communicate clearly with the community.</div></div>
                </>
              )}
              {isAdmin && (
                <>
                  <div className="ns-card" style={{ padding: '0.85rem' }}><strong style={{ color: '#003366' }}><Landmark size={15} /> Governance oversight</strong><div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 4 }}>Monitor reports, work progress, and development projects by area to improve planning and accountability.</div></div>
                  <div className="ns-card" style={{ padding: '0.85rem' }}><strong style={{ color: '#003366' }}><AlertTriangle size={15} /> Prioritize action</strong><div style={{ color: '#006699', fontSize: '0.86rem', marginTop: 4 }}>Identify recurring issues, coordinate departments, and keep residents informed through the forum.</div></div>
                </>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}













