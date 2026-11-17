import { useState, useEffect, useCallback } from 'react'

export function useApi(fn) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    fn()
      .then((result) => {
        if (cancelled) return
        setData(result)
        setError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.response?.data?.detail || err.message || 'Request failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [fn, attempt])

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    setAttempt((current) => current + 1)
  }, [])

  return { data, loading, error, reload }
}

export function healthColor(band) {
  return { Healthy: '#0099CC', Moderate: '#FF9933', Degrading: '#FF9933', Critical: '#FF9933' }[band] || '#006699'
}

export function healthBadgeClass(band) {
  return { Healthy: 'badge-healthy', Moderate: 'badge-moderate', Degrading: 'badge-degrading', Critical: 'badge-critical' }[band] || ''
}

export function fmt(n, d = 1) {
  if (n == null || n === '') return '—'
  if (typeof n !== 'number' || Number.isNaN(n)) return n
  const abs = Math.abs(n)
  const sign = n < 0 ? '-' : ''
  // Indian-style: crore / lakh / thousand
  if (abs >= 1e7) return `${sign}${(abs / 1e7).toFixed(d)} Cr`
  if (abs >= 1e5) return `${sign}${(abs / 1e5).toFixed(d)} Lakh`
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(d)}K`
  return `${sign}${abs.toFixed(d)}`
}

/** Format lakh-INR values already stored in lakh units */
export function fmtLakh(n, d = 1) {
  if (n == null || Number.isNaN(n)) return '—'
  const abs = Math.abs(n)
  const sign = n < 0 ? '-' : ''
  if (abs >= 100) return `${sign}${(abs / 100).toFixed(d)} Cr`
  if (abs >= 1) return `${sign}${abs.toFixed(d)} Lakh`
  return `${sign}${(abs * 1000).toFixed(0)}K`
}
