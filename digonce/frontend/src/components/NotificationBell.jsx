import { useState, useEffect, useRef, useCallback } from 'react'
import { Bell, Check, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../api.js'

export default function NotificationBell({ user }) {
  const [notifications, setNotifications] = useState([])
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const menuRef = useRef(null)

  const fetchNotes = useCallback(async () => {
    if (!user) return
    try {
      const data = await getNotifications({ limit: 15 })
      setNotifications(data)
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not refresh notifications.')
    }
  }, [user])

  useEffect(() => {
    fetchNotes()
    const timer = setInterval(fetchNotes, 8000)
    return () => clearInterval(timer)
  }, [fetchNotes])

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length

  const handleRead = async (id) => {
    try {
      await markNotificationRead(id)
      setNotifications((items) => items.map((n) => n.id === id ? { ...n, read: true } : n))
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not mark notification as read.')
    }
  }

  const handleReadAll = async () => {
    try {
      await markAllNotificationsRead()
      setNotifications((items) => items.map((n) => ({ ...n, read: true })))
      setError('')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not mark notifications as read.')
    }
  }

  if (!user) return null

  return (
    <div style={{ position: 'relative' }} ref={menuRef}>
      <button 
        className="btn btn-secondary btn-sm"
        onClick={() => setOpen(!open)}
        style={{ position: 'relative', padding: '6px 9px', borderRadius: 8 }}
        aria-label="Notifications"
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: -4, right: -4,
            background: 'var(--danger)', color: '#FFFFFF',
            borderRadius: '50%', width: 17, height: 17,
            fontSize: '0.68rem', fontWeight: 800,
            display: 'grid', placeItems: 'center',
          }}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', right: 0, top: 'calc(100% + 8px)',
          width: 320, background: 'var(--card-bg, #FFFFFF)',
          border: '1px solid var(--border)', borderRadius: 12,
          boxShadow: '0 10px 25px rgba(0, 51, 102, 0.15)',
          zIndex: 1000, overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 14px', background: '#FFFFFF',
            borderBottom: '1px solid var(--border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--navy)' }}>
              Notifications ({unreadCount} new)
            </span>
            {unreadCount > 0 && (
              <button 
                onClick={handleReadAll} 
                style={{ background: 'none', border: 'none', color: 'var(--teal)', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}
              >
                Mark all read
              </button>
            )}
          </div>

          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {error && <div role="alert" style={{ padding: '8px 14px', color: 'var(--danger)', fontSize: '0.78rem' }}>{error}</div>}
            {notifications.length === 0 ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--muted)', fontSize: '0.85rem' }}>
                No notifications yet.
              </div>
            ) : (
              notifications.map((n) => (
                <div 
                  key={n.id}
                  style={{
                    padding: '10px 14px',
                    borderBottom: '1px solid var(--border)',
                    background: n.read ? 'transparent' : 'rgba(0, 102, 153, 0.04)',
                    display: 'grid', gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 6 }}>
                    <div style={{ fontWeight: n.read ? 500 : 700, fontSize: '0.85rem', color: 'var(--ink)' }}>
                      {n.title}
                    </div>
                    {!n.read && (
                      <button 
                        onClick={() => handleRead(n.id)}
                        title="Mark read"
                        style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', padding: 2 }}
                      >
                        <Check size={13} />
                      </button>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                    {n.message}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                      {new Date(n.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {n.link && (
                      <Link 
                        to={n.link} 
                        onClick={() => { handleRead(n.id); setOpen(false) }}
                        style={{ fontSize: '0.75rem', color: 'var(--teal)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 2 }}
                      >
                        View <ExternalLink size={11} />
                      </Link>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
