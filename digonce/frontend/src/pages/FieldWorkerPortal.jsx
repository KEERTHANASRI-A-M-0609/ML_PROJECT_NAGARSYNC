import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Wrench, CheckCircle2, Clock, AlertTriangle, Camera, Upload, 
  MapPin, ShieldAlert, ArrowRight, X, Sparkles, RefreshCw, Eye
} from 'lucide-react'
import { getIncidents, patchIncident, addEvidence, api } from '../api.js'

function IncidentCitizenImage({ reportId }) {
  const [src, setSrc] = useState('')

  useEffect(() => {
    let objectUrl
    let cancelled = false
    if (!reportId) return
    api.get(`/reports/${reportId}/image`, { responseType: 'blob' })
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
  }, [reportId])

  if (!src) return null
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--muted)', marginBottom: 4 }}>
        Citizen Evidence Photo:
      </div>
      <img 
        src={src} 
        alt="Citizen incident report evidence" 
        style={{ width: '100%', maxHeight: 180, objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }} 
      />
    </div>
  )
}

export default function FieldWorkerPortal({ user }) {
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')
  const [activeModal, setActiveModal] = useState(null) // incident object for evidence submission
  const [evidenceNote, setEvidenceNote] = useState('')
  const [imageDataUrl, setImageDataUrl] = useState('')
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const loadJobs = async () => {
    setLoading(true)
    try {
      const data = await getIncidents({ limit: 100 })
      setIncidents(data)
    } catch {
      setStatusMsg('Could not load assigned jobs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [])

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setCameraActive(false)
  }

  const startCamera = async () => {
    setCameraError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      setCameraActive(true)
      setTimeout(() => {
        if (videoRef.current) videoRef.current.srcObject = stream
      }, 100)
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setCameraError('Camera permission denied. Please upload a photo from your gallery.')
      } else {
        setCameraError('Camera unavailable. Please upload a photo file.')
      }
    }
  }

  const capturePhoto = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    canvas.getContext('2d').drawImage(video, 0, 0)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
    setImageDataUrl(dataUrl)
    stopCamera()
  }

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCameraError('')
    if (file.size > 4 * 1024 * 1024) {
      setCameraError('Photo must be 4 MB or smaller.')
      return
    }
    const reader = new FileReader()
    reader.onload = () => setImageDataUrl(String(reader.result))
    reader.readAsDataURL(file)
  }

  const handleStartWork = async (incId) => {
    try {
      await patchIncident(incId, {
        status: 'IN_PROGRESS',
        note: `Work commenced on site by field engineer ${user?.name || user?.email}`,
      })
      setStatusMsg(`Job ${incId} marked IN_PROGRESS.`)
      await loadJobs()
    } catch (err) {
      setStatusMsg(err.response?.data?.detail || 'Failed to start work.')
    }
  }

  const handleEscalate = async (incId) => {
    const reason = window.prompt('Reason for escalation (e.g. specialized equipment needed, traffic congestion):')
    if (!reason) return
    try {
      await patchIncident(incId, {
        status: 'ESCALATED',
        note: `Escalated from field: ${reason}`,
      })
      setStatusMsg(`Job ${incId} escalated to municipal planner.`)
      await loadJobs()
    } catch (err) {
      setStatusMsg(err.response?.data?.detail || 'Failed to escalate.')
    }
  }

  const handleSubmitEvidence = async (e) => {
    e.preventDefault()
    if (!activeModal) return
    if (!imageDataUrl && !evidenceNote) {
      setCameraError('Please provide either completion photo evidence or detailed completion notes.')
      return
    }
    setSubmitting(true)
    setCameraError('')
    try {
      // 1. Upload evidence record with photo
      await addEvidence(activeModal.id, {
        evidence_url: imageDataUrl ? 'photo_attached' : 'inspection_notes',
        image_data_url: imageDataUrl || null,
        note: evidenceNote,
      })

      // 2. Transition status to COMPLETION_SUBMITTED
      await patchIncident(activeModal.id, {
        status: 'COMPLETION_SUBMITTED',
        note: `Field completion submitted: ${evidenceNote || 'Repairs completed and site cleared.'}`,
        evidence_url: 'evidence_attached',
      })

      setStatusMsg(`Completion submitted for ${activeModal.id}! Awaiting municipal verification.`)
      setActiveModal(null)
      setImageDataUrl('')
      setEvidenceNote('')
      stopCamera()
      await loadJobs()
    } catch (err) {
      setCameraError(err.response?.data?.detail || 'Failed to submit completion.')
    } finally {
      setSubmitting(false)
    }
  }

  const filteredIncidents = incidents.filter((i) => {
    if (filter === 'ALL') return true
    if (filter === 'ASSIGNED') return i.status === 'ASSIGNED'
    if (filter === 'IN_PROGRESS') return i.status === 'IN_PROGRESS'
    if (filter === 'SUBMITTED') return i.status === 'COMPLETION_SUBMITTED'
    if (filter === 'VERIFIED') return ['VERIFIED', 'CLOSED'].includes(i.status)
    return true
  })

  const assignedCount = incidents.filter((i) => i.status === 'ASSIGNED').length
  const inProgressCount = incidents.filter((i) => i.status === 'IN_PROGRESS').length
  const submittedCount = incidents.filter((i) => i.status === 'COMPLETION_SUBMITTED').length
  const closedCount = incidents.filter((i) => ['VERIFIED', 'CLOSED'].includes(i.status)).length

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Field Operations Portal</div>
          <div className="page-sub">
            Logged in as {user?.name || 'Field Engineer'} · Manage assigned work orders, upload completion evidence, and submit for verification
          </div>
        </div>
        <button className="btn btn-secondary" onClick={loadJobs} disabled={loading}>
          <RefreshCw size={14} /> Refresh Jobs
        </button>
      </div>

      {statusMsg && (
        <div className="panel" role="status" style={{ marginBottom: 16, background: '#FFFFFF', borderColor: '#A2C2E2', color: '#0099CC' }}>
          {statusMsg}
        </div>
      )}

      {/* KPI Cards */}
      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <div className="kpi" style={{ borderLeft: '4px solid #FF9933' }}>
          <div className="kpi-value">{assignedCount}</div>
          <div className="kpi-label">Ready to start (Assigned)</div>
        </div>
        <div className="kpi" style={{ borderLeft: '4px solid #0099CC' }}>
          <div className="kpi-value">{inProgressCount}</div>
          <div className="kpi-label">Work in progress</div>
        </div>
        <div className="kpi" style={{ borderLeft: '4px solid #006699' }}>
          <div className="kpi-value">{submittedCount}</div>
          <div className="kpi-label">Awaiting verification</div>
        </div>
        <div className="kpi" style={{ borderLeft: '4px solid #0099CC' }}>
          <div className="kpi-value">{closedCount}</div>
          <div className="kpi-label">Verified & closed</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="toggle-row" style={{ marginBottom: 16 }}>
        {['ALL', 'ASSIGNED', 'IN_PROGRESS', 'SUBMITTED', 'VERIFIED'].map((f) => (
          <button
            key={f}
            className={`chip ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Job Cards */}
      <div style={{ display: 'grid', gap: 14 }}>
        {loading && <div className="panel">Loading assigned jobs…</div>}
        {!loading && filteredIncidents.length === 0 && (
          <div className="panel" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--muted)' }}>
            No jobs found matching "{filter}". All assigned maintenance is currently up to date.
          </div>
        )}

        {filteredIncidents.map((inc) => (
          <article key={inc.id} className="panel" style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.1rem' }}>
                    {inc.id}
                  </span>
                  <span className={`badge ${
                    inc.status === 'IN_PROGRESS' ? 'badge-degrading' :
                    inc.status === 'ASSIGNED' ? 'badge-moderate' :
                    inc.status === 'COMPLETION_SUBMITTED' ? 'badge-healthy' : 'badge-healthy'
                  }`}>
                    {inc.status}
                  </span>
                  <span className="badge badge-moderate" style={{ textTransform: 'uppercase' }}>
                    {inc.severity}
                  </span>
                </div>
                <div style={{ fontWeight: 600, fontSize: '1rem', marginTop: 4, color: 'var(--navy)' }}>
                  {inc.title}
                </div>
              </div>

              <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                Created: {new Date(inc.created_at * 1000).toLocaleDateString()}
              </div>
            </div>

            <div style={{ fontSize: '0.9rem', color: 'var(--ink)' }}>
              {inc.description}
            </div>

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: '0.82rem', color: 'var(--muted)' }}>
              {inc.asset_id && <span>Asset: <strong>{inc.asset_id}</strong></span>}
              {inc.district && <span>District: <strong>{inc.district}</strong></span>}
              {inc.lat && inc.lon && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <MapPin size={13} /> {inc.lat.toFixed(4)}, {inc.lon.toFixed(4)}
                </span>
              )}
            </div>

            {/* If there's an original citizen report, show photo evidence */}
            {inc.report_id && <IncidentCitizenImage reportId={inc.report_id} />}

            {/* If work completion evidence already submitted, show thumbnail */}
            {inc.evidence && inc.evidence.length > 0 && (
              <div style={{ padding: 10, background: '#FFFFFF', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--navy)', marginBottom: 4 }}>
                  Submitted Completion Evidence:
                </div>
                {inc.evidence.map((ev, idx) => (
                  <div key={idx} style={{ fontSize: '0.82rem' }}>
                    • {ev.note || 'Work completed'} ({new Date(ev.ts * 1000).toLocaleString()})
                    {ev.url && ev.url.includes('/evidence-image/') && (
                      <div style={{ marginTop: 4 }}>
                        <img 
                          src={ev.url} 
                          alt="Work completion evidence" 
                          style={{ maxHeight: 160, borderRadius: 6, border: '1px solid var(--border)' }} 
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Actions for Field Crew */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', paddingTop: 8, borderTop: '1px solid var(--border)' }}>
              {inc.status === 'ASSIGNED' && (
                <button 
                  className="btn btn-primary btn-sm" 
                  onClick={() => handleStartWork(inc.id)}
                >
                  <Wrench size={14} /> Start Work (Set In-Progress)
                </button>
              )}

              {inc.status === 'IN_PROGRESS' && (
                <button 
                  className="btn btn-primary btn-sm" 
                  style={{ background: '#0099CC', borderColor: '#0099CC' }}
                  onClick={() => {
                    setActiveModal(inc)
                    setImageDataUrl('')
                    setEvidenceNote('')
                    setCameraError('')
                  }}
                >
                  <Camera size={14} /> Submit Completion Evidence
                </button>
              )}

              {['ASSIGNED', 'IN_PROGRESS'].includes(inc.status) && (
                <button 
                  className="btn btn-secondary btn-sm" 
                  style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
                  onClick={() => handleEscalate(inc.id)}
                >
                  <AlertTriangle size={14} /> Escalate Issue
                </button>
              )}

              {inc.status === 'COMPLETION_SUBMITTED' && (
                <span style={{ fontSize: '0.85rem', color: '#0099CC', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={16} /> Awaiting municipal admin inspection & verification
                </span>
              )}

              {['VERIFIED', 'CLOSED'].includes(inc.status) && (
                <span style={{ fontSize: '0.85rem', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={16} /> Verified by municipal inspector & closed
                </span>
              )}
            </div>
          </article>
        ))}
      </div>

      {/* Modal for Submitting Completion Evidence with Device Camera */}
      <AnimatePresence>
        {activeModal && (
          <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0, 51, 102, 0.6)', 
            display: 'grid', placeItems: 'center', zIndex: 1000, padding: 16,
          }}>
            <motion.div 
              className="panel" 
              style={{ width: 'min(500px, 100%)', maxHeight: '90vh', overflowY: 'auto' }}
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontFamily: 'var(--display)', fontWeight: 800, fontSize: '1.2rem' }}>
                  Submit Completion Evidence
                </div>
                <button className="btn btn-secondary btn-sm" onClick={() => { stopCamera(); setActiveModal(null) }}>
                  <X size={16} />
                </button>
              </div>

              <div style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: 12 }}>
                Submitting verified evidence for <strong>{activeModal.id}</strong> ({activeModal.title})
              </div>

              {cameraError && (
                <div style={{ color: 'var(--danger)', fontSize: '0.85rem', marginBottom: 12 }}>
                  {cameraError}
                </div>
              )}

              <form onSubmit={handleSubmitEvidence} style={{ display: 'grid', gap: 14 }}>
                {/* Camera / Photo Section */}
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Repair Photo Evidence (Required for municipal sign-off)
                  </label>

                  {!cameraActive && !imageDataUrl && (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={startCamera}>
                        <Camera size={14} /> Open Device Camera
                      </button>
                      <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                        <Upload size={14} /> Upload Image File
                        <input type="file" accept="image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
                      </label>
                    </div>
                  )}

                  {/* Active Camera Stream */}
                  {cameraActive && (
                    <div style={{ borderRadius: 10, overflow: 'hidden', background: '#003366', position: 'relative' }}>
                      <video ref={videoRef} autoPlay playsInline style={{ width: '100%', maxHeight: 240, display: 'block' }} />
                      <div style={{ padding: 8, background: 'rgba(0, 51, 102, 0.7)', display: 'flex', justifyContent: 'space-between' }}>
                        <button type="button" className="btn btn-primary btn-sm" onClick={capturePhoto}>
                          <Camera size={14} /> Capture Photo
                        </button>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={stopCamera}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Photo Preview */}
                  {imageDataUrl && (
                    <div style={{ marginTop: 8 }}>
                      <img src={imageDataUrl} alt="Captured evidence" style={{ width: '100%', maxHeight: 220, objectFit: 'cover', borderRadius: 8 }} />
                      <button 
                        type="button" 
                        className="btn btn-secondary btn-sm" 
                        style={{ marginTop: 6 }}
                        onClick={() => { setImageDataUrl(''); setCameraError('') }}
                      >
                        Retake / Change Photo
                      </button>
                    </div>
                  )}

                  <canvas ref={canvasRef} style={{ display: 'none' }} />
                </div>

                {/* Completion Notes */}
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Completion Details & Materials Used
                  </label>
                  <textarea 
                    className="input" 
                    rows={3} 
                    required 
                    value={evidenceNote} 
                    onChange={(e) => setEvidenceNote(e.target.value)}
                    placeholder="e.g. Cleared debris, laid 50mm bitumen binder, compacted joint, verified water pressure normal."
                  />
                </div>

                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 10 }}>
                  <button type="button" className="btn btn-secondary" onClick={() => { stopCamera(); setActiveModal(null) }}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? 'Submitting…' : 'Submit for Verification'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
