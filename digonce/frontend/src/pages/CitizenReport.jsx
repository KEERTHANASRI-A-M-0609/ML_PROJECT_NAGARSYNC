import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Camera, Upload, MapPin, Send, CheckCircle2, AlertCircle, X, RefreshCw } from 'lucide-react'
import { createReport } from '../api.js'

const CATEGORIES = [
  { id: 'pothole',       label: 'Pothole',        color: '#FF9933' },
  { id: 'water_leak',    label: 'Water Leak',     color: '#0099CC' },
  { id: 'streetlight',   label: 'Streetlight',    color: '#FF9933' },
  { id: 'bridge_damage', label: 'Bridge Damage',  color: '#FF9933' },
  { id: 'other',         label: 'Other Issue',    color: '#006699' },
]

const MAX_IMAGE_BYTES = 2 * 1024 * 1024 // 2 MB

export default function CitizenReport() {
  const [step, setStep] = useState(1) // 1=category 2=photo 3=location 4=describe 5=done
  const [category, setCategory] = useState('')
  const [imageDataUrl, setImageDataUrl] = useState(null)
  const [imageFilename, setImageFilename] = useState(null)
  const [imageError, setImageError] = useState('')
  const [cameraActive, setCameraActive] = useState(false)
  const [lat, setLat] = useState(null)
  const [lon, setLon] = useState(null)
  const [locationText, setLocationText] = useState('')
  const [geoLoading, setGeoLoading] = useState(false)
  const [geoError, setGeoError] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const fileRef = useRef(null)
  const streamRef = useRef(null)

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    setCameraActive(false)
  }

  const startCamera = async () => {
    setImageError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      setCameraActive(true)
      setTimeout(() => {
        if (videoRef.current) videoRef.current.srcObject = stream
      }, 100)
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setImageError('Camera permission denied. Please upload a photo instead.')
      } else if (err.name === 'NotFoundError') {
        setImageError('No camera found on this device. Please upload a photo.')
      } else {
        setImageError('Camera unavailable. Please upload a photo.')
      }
    }
  }

  const capturePhoto = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.7)
    setImageDataUrl(dataUrl)
    setImageFilename('camera_capture.jpg')
    stopCamera()
  }

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImageError('')
    if (!file.type.startsWith('image/')) {
      setImageError('Please select an image file.')
      return
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setImageError(`Image too large (max 2 MB). Your file: ${(file.size / 1024 / 1024).toFixed(1)} MB.`)
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => {
      setImageDataUrl(ev.target.result)
      setImageFilename(file.name)
    }
    reader.readAsDataURL(file)
  }

  const getLocation = () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation not supported by your browser.')
      return
    }
    setGeoLoading(true)
    setGeoError('')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude)
        setLon(pos.coords.longitude)
        setLocationText(`${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`)
        setGeoLoading(false)
      },
      (err) => {
        setGeoError(err.code === 1 ? 'Location permission denied. Enter location manually.' : 'Could not get location.')
        setGeoLoading(false)
      },
      { timeout: 10000 }
    )
  }

  const submit = async () => {
    if (!description.trim()) { setError('Please describe the issue.'); return }
    setSubmitting(true)
    setError('')
    try {
      const res = await createReport({
        category,
        description,
        lat,
        lon,
        location_text: locationText,
        image_filename: imageFilename,
        image_data_url: imageDataUrl,
      })
      setResult(res)
      setStep(5)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Submission failed')
    }
    setSubmitting(false)
  }

  if (step === 5 && result) {
    return (
      <div className="page">
        <motion.div className="panel" style={{ maxWidth: 520, margin: '3rem auto', textAlign: 'center', padding: '2.5rem' }}
          initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
          <CheckCircle2 size={52} color="var(--ok)" style={{ marginBottom: 16 }} />
          <div className="page-title" style={{ marginBottom: 8 }}>Report Submitted</div>
          <div style={{ fontFamily: 'var(--display)', fontSize: '1.5rem', fontWeight: 800, color: 'var(--navy)', marginBottom: 8 }}>
            {result.report?.id}
          </div>
          <p style={{ color: 'var(--muted)', marginBottom: 16 }}>
            Save this ID to track your report. Our team will review it shortly.
          </p>
          {result.possible_duplicates > 0 && (
            <div style={{ background: '#FFCC00', border: '1px solid #FF9933', borderRadius: 10, padding: '10px 14px', marginBottom: 16, fontSize: '0.85rem' }}>
              <strong>Note:</strong> {result.possible_duplicates} similar report(s) already exist nearby. Your report has been recorded and will be reviewed for merging.
            </div>
          )}
          <button className="btn btn-primary" onClick={() => { setStep(1); setCategory(''); setImageDataUrl(null); setDescription(''); setResult(null); setLat(null); setLon(null); setLocationText('') }}>
            Submit another report
          </button>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Report an Issue</div>
          <div className="page-sub">Help us fix infrastructure problems in your area</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[1,2,3,4].map(s => (
            <div key={s} style={{
              width: 32, height: 32, borderRadius: '50%', display: 'grid', placeItems: 'center',
              background: step >= s ? 'var(--navy)' : 'var(--bg-soft)',
              color: step >= s ? '#FFFFFF' : 'var(--muted)',
              fontSize: '0.8rem', fontWeight: 700,
            }}>{s}</div>
          ))}
        </div>
      </div>

      {/* Step 1: Category */}
      {step === 1 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="panel">
            <div className="panel-title">What type of issue?</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
              {CATEGORIES.map(c => (
                <button key={c.id} onClick={() => { setCategory(c.id); setStep(2) }}
                  style={{
                    padding: '1.2rem', borderRadius: 12, border: `2px solid ${category === c.id ? c.color : 'var(--line)'}`,
                    background: category === c.id ? c.color + '18' : '#FFFFFF',
                    cursor: 'pointer', fontWeight: 700, color: c.color, fontSize: '0.9rem',
                    transition: '0.2s',
                  }}>
                  {c.label}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Step 2: Photo */}
      {step === 2 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="panel">
            <div className="panel-title">Add a photo (optional but helpful)</div>
            {imageError && (
              <div style={{ background: '#FF9933', border: '1px solid #FF9933', borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: '0.85rem', color: 'var(--danger)' }}>
                <AlertCircle size={14} style={{ marginRight: 6 }} />{imageError}
              </div>
            )}
            {!imageDataUrl && !cameraActive && (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <button className="btn btn-secondary" onClick={startCamera}>
                  <Camera size={16} /> Use Camera
                </button>
                <button className="btn btn-secondary" onClick={() => fileRef.current?.click()}>
                  <Upload size={16} /> Upload Photo
                </button>
                <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFileUpload} />
              </div>
            )}
            {cameraActive && (
              <div>
                <video ref={videoRef} autoPlay playsInline style={{ width: '100%', maxWidth: 480, borderRadius: 10, marginBottom: 10 }} />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
                <div style={{ display: 'flex', gap: 10 }}>
                  <button className="btn btn-primary" onClick={capturePhoto}><Camera size={16} /> Capture</button>
                  <button className="btn btn-secondary" onClick={stopCamera}><X size={16} /> Cancel</button>
                </div>
              </div>
            )}
            {imageDataUrl && (
              <div>
                <img src={imageDataUrl} alt="Preview" style={{ width: '100%', maxWidth: 360, borderRadius: 10, marginBottom: 10 }} />
                <div style={{ display: 'flex', gap: 10 }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => { setImageDataUrl(null); setImageFilename(null) }}>
                    <RefreshCw size={14} /> Retake
                  </button>
                </div>
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>Back</button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>
                {imageDataUrl ? 'Continue with photo' : 'Skip photo'}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Step 3: Location */}
      {step === 3 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="panel">
            <div className="panel-title">Where is the issue?</div>
            {geoError && (
              <div style={{ background: '#FF9933', border: '1px solid #FF9933', borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: '0.85rem', color: 'var(--danger)' }}>
                {geoError}
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" onClick={getLocation} disabled={geoLoading}>
                <MapPin size={16} /> {geoLoading ? 'Getting location…' : 'Use my location'}
              </button>
            </div>
            {lat && lon && (
              <div style={{ background: '#FFFFFF', border: '1px solid #A2C2E2', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: '0.85rem', color: 'var(--ok)' }}>
                 Location captured: {lat.toFixed(5)}, {lon.toFixed(5)}
              </div>
            )}
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'block', marginBottom: 6 }}>
                Or describe the location (street name, landmark, area)
              </label>
              <input
                placeholder="e.g. Near Anna Nagar water tank, Chennai"
                value={locationText}
                onChange={e => setLocationText(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-secondary" onClick={() => setStep(2)}>Back</button>
              <button className="btn btn-primary" onClick={() => setStep(4)} disabled={!lat && !locationText.trim()}>
                Continue
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Step 4: Description + Submit */}
      {step === 4 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="panel">
            <div className="panel-title">Describe the issue</div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                <span className="badge badge-moderate">{category.replace('_', ' ')}</span>
                {imageDataUrl && <span className="badge badge-healthy">Photo attached</span>}
                {(lat || locationText) && <span className="badge badge-healthy">Location set</span>}
              </div>
              <textarea
                className="input"
                rows={5}
                placeholder="Describe the problem in detail — how severe, how long it's been there, any safety concerns…"
                value={description}
                onChange={e => setDescription(e.target.value)}
                style={{ resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>
            {error && <div style={{ color: 'var(--danger)', marginBottom: 10, fontSize: '0.85rem' }}>{error}</div>}
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-secondary" onClick={() => setStep(3)}>Back</button>
              <button className="btn btn-primary" onClick={submit} disabled={submitting || !description.trim()}>
                <Send size={16} /> {submitting ? 'Submitting…' : 'Submit Report'}
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
