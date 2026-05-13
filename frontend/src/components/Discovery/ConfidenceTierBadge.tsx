import { Star, Check } from 'lucide-react'

type Tier = 'goldmine' | 'validated' | 'weak_signal'

interface Props {
  tier?: Tier | string | null
  size?: 'sm' | 'md'
  className?: string
}

const TIER_CONFIG: Record<Tier, {
  label: string
  bg: string
  text: string
  Icon: React.ComponentType<{ className?: string }>
}> = {
  goldmine: {
    label: 'Goldmine',
    bg: 'bg-emerald-600',
    text: 'text-white',
    Icon: Star,
  },
  validated: {
    label: 'Validated',
    bg: 'bg-emerald-100',
    text: 'text-emerald-800',
    Icon: Check,
  },
  weak_signal: {
    label: 'Early Signal',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    Icon: () => null,
  },
}

export default function ConfidenceTierBadge({ tier, size = 'sm', className = '' }: Props) {
  if (!tier || !(tier in TIER_CONFIG)) return null
  const c = TIER_CONFIG[tier as Tier]
  const pad      = size === 'md' ? 'px-2.5 py-1' : 'px-2 py-0.5'
  const iconSize = size === 'md' ? 'w-3.5 h-3.5' : 'w-3 h-3'

  return (
    <span
      className={`inline-flex items-center gap-1 ${pad} rounded-full text-xs font-semibold uppercase tracking-wide ${c.bg} ${c.text} ${className}`}
    >
      <c.Icon className={iconSize} />
      {c.label}
    </span>
  )
}

/** Single combined className for the card border + hover ring */
export function getTierBorderClass(tier?: string | null): string {
  if (tier === 'goldmine')  return 'border-emerald-500 hover:ring-4 hover:ring-emerald-100'
  if (tier === 'validated') return 'border-slate-300 hover:border-slate-400'
  return 'border-slate-200 hover:border-slate-300'
}
