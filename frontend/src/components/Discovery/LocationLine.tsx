import { MapPin, Globe } from 'lucide-react'

interface Props {
  city?: string | null
  state?: string | null
  geographicScope?: string | null
  className?: string
}

const SCOPE_LABEL: Record<string, string> = {
  local:         'Local',
  regional:      'Regional',
  national:      'National',
  international: 'Global',
  online:        'Online',
}

export default function LocationLine({ city, state, geographicScope, className = '' }: Props) {
  if (geographicScope === 'online') {
    return (
      <span className={`flex items-center gap-1 text-xs text-slate-500 ${className}`}>
        <Globe className="w-3 h-3 flex-shrink-0" />
        Online · No geography
      </span>
    )
  }

  if (!city && !state) return null

  const location   = [city, state].filter(Boolean).join(', ')
  const scopeLabel = geographicScope ? SCOPE_LABEL[geographicScope] : null

  return (
    <span className={`flex items-center gap-1 text-xs text-slate-500 ${className}`}>
      <MapPin className="w-3 h-3 flex-shrink-0" />
      <span>{location}</span>
      {scopeLabel && <span className="text-slate-400">· {scopeLabel}</span>}
    </span>
  )
}
