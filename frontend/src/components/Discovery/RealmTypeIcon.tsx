import { Store, Monitor, Layers } from 'lucide-react'

interface Props {
  realmType?: string | null
  className?: string
}

export default function RealmTypeIcon({ realmType, className = '' }: Props) {
  const base = `w-3 h-3 text-slate-400 ${className}`

  if (realmType === 'physical') {
    return <Store   className={base} aria-label="Physical business" />
  }
  if (realmType === 'digital') {
    return <Monitor className={base} aria-label="Digital business" />
  }
  return <Layers className={base} aria-label="Physical and digital" />
}
