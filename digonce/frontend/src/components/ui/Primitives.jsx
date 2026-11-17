import React from 'react'

export function Badge({ children, variant = 'navy', className = '', style = {} }) {
  const mappedVariant =
    variant === 'teal' ? 'ocean' :
    variant === 'amber' ? 'gold' :
    variant === 'red' ? 'tangerine' :
    variant === 'neutral' ? 'silver' : variant
  return <span className={`ns-badge ns-badge-${mappedVariant} ${className}`} style={style}>{children}</span>
}

export function Button({ children, variant = 'primary', size = 'md', onClick, type = 'button', disabled = false, className = '', icon: Icon, style = {} }) {
  return (
    <button type={type} disabled={disabled} onClick={onClick} style={style} className={`ns-btn ns-btn-${variant} ${size === 'sm' ? 'ns-btn-sm' : ''} ${className}`}>
      {Icon && <Icon size={size === 'sm' ? 14 : 16} />}
      {children}
    </button>
  )
}

export function Card({ title, subtitle, action, children, className = '', headerClassName = '', bodyClassName = '', style = {} }) {
  return (
    <div className={`ns-card ${className}`} style={style}>
      {(title || action) && (
        <div className={`ns-card-header ${headerClassName}`}>
          <div>
            {title && <h3 className="ns-card-title">{title}</h3>}
            {subtitle && <p className="ns-card-subtitle">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={`ns-card-body ${bodyClassName}`}>{children}</div>
    </div>
  )
}

export function Input({ label, error, helperText, className = '', style = {}, ...props }) {
  return (
    <div className={`ns-field ${className}`} style={style}>
      {label && <label className="ns-label">{label}</label>}
      <input className="ns-input" style={error ? { borderColor: 'var(--ns-danger)' } : undefined} {...props} />
      {error && <span style={{ fontSize: '0.72rem', color: 'var(--ns-danger)', fontWeight: 600 }}>{error}</span>}
      {helperText && !error && <span style={{ fontSize: '0.72rem', color: 'var(--ns-muted)' }}>{helperText}</span>}
    </div>
  )
}
