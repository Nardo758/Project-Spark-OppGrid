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
    label: 'Weak Signal',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    Icon: ({ className }) => <span className={className}>·</span>,
  },
}

export default function ConfidenceTierBadge({ tier, size = 'sm', className = '' }: Props) {
  if (!tier || !(tier in TIER_CONFIG)) return null
  const config = TIER_CONFIG[tier as Tier]
  const { Icon } = config
  const iconSize  = size === 'md' ? 'w-3.5 h-3.5' : 'w-3 h-3'
  const padding   = size === 'md' ? 'px-2.5 py-1' : 'px-2 py-0.5'

  return (
    <span
      className={`inline-flex items-center gap-1 ${padding} rounded-full font-semibold text-xs ${config.bg} ${config.text} ${className}`}
    >
      <Icon className={iconSize} />
      {config.label}
    </span>
  )
}

export function getTierBorderClass(tier?: string | null): string {
  if (tier === 'goldmine')   return 'border-emerald-500'
  if (tier === 'validated')  return 'border-slate-300'
  return 'border-slate-200'
}

export function getTierHoverClass(tier?: string | null): string {
  if (tier === 'goldmine') return 'hover:border-emerald-400 hover:ring-2 hover:ring-emerald-100'
  return 'hover:border-slate-400'
}
