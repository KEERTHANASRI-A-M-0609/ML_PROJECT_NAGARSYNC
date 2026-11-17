import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, MapPin, Building2, ExternalLink, ChevronRight } from 'lucide-react'
import { getDistrictDirectory } from '../api.js'
import { Badge, Button, Card } from '../components/ui/Primitives.jsx'

export default function DistrictDirectoryPage() {
  const [data, setData] = useState({ items: [], source: {} })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    getDistrictDirectory()
      .then((res) => { if (active) { setData(res || { items: [], source: {} }); setError('') } })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Could not load district directory.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const items = data.items || []
    if (!q) return items
    return items.filter((d) => [d.name, d.headquarters, d.overview].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)))
  }, [data.items, query])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="page-title">Tamil Nadu District Directory</div>
          <div className="page-sub">Explore all 38 districts: administration, offices, officers, services, projects, and local intelligence.</div>
        </div>
        <Link to="/directory/find-local-officer" style={{ textDecoration: 'none' }}><Button variant="primary" icon={MapPin}>Find My Local Officer</Button></Link>
      </div>

      <Card>
        <div style={{ display: 'grid', gap: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, border: '1px solid #A2C2E2', borderRadius: 10, padding: '8px 12px', background: '#fff', maxWidth: 520 }}>
            <Search size={16} color="#006699" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search district or headquarters" style={{ border: 0, outline: 'none', width: '100%', color: '#003366' }} />
          </label>
          {data.source?.note && (
            <div style={{ fontSize: '0.82rem', color: '#006699', background: '#FFFFFF', border: '1px solid #A2C2E2', borderRadius: 10, padding: '10px 12px' }}>
              <strong>Data note:</strong> {data.source.note} {data.source.url && <a href={data.source.url} target="_blank" rel="noreferrer">Source reference</a>}
            </div>
          )}
          {error && <div role="alert" style={{ color: '#FF9933' }}>{error}</div>}
          {loading ? <div>Loading districts…</div> : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 12 }}>
              {filtered.map((d) => (
                <Link key={d.id || d.name} to={`/directory/districts/${encodeURIComponent(d.id || d.name)}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className="ns-card" style={{ padding: '1rem', height: '100%', border: '1px solid #A2C2E2' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'start' }}>
                      <div>
                        <div style={{ fontWeight: 800, color: '#003366', fontSize: '1.02rem' }}>{d.name}</div>
                        <div style={{ color: '#006699', fontSize: '0.82rem', marginTop: 2 }}><Building2 size={13} style={{ verticalAlign: 'middle' }} /> HQ: {d.headquarters || 'Not specified'}</div>
                      </div>
                      <Badge variant={d.data_status === 'partial' ? 'gold' : 'navy'}>{d.data_status === 'partial' ? 'Profile' : 'Ref'}</Badge>
                    </div>
                    <p style={{ color: '#003366', fontSize: '0.84rem', margin: '8px 0', lineHeight: 1.5 }}>{d.overview || 'District profile information available. Detailed administrative records are shown where verified.'}</p>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: '#006699' }}>
                      <span>{d.official_portal ? 'Official portal linked' : 'Official portal: verify'}</span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontWeight: 700 }}>Open <ChevronRight size={14} /></span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
          {!loading && !error && filtered.length === 0 && <div>No districts match your search.</div>}
        </div>
      </Card>
    </div>
  )
}
