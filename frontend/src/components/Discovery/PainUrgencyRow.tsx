import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Props {
  painIntensity?:   number | null
  urgencyLevel?:    string | null
  growthRate?:      number | null
  trendDirection?:  'rising' | 'falling' | 'flat' | null
  validationCount?: number | null
  marketSize?:      string | null
}

const URGENCY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  low:      { bg: 'bg-slate-100',  text: 'text-slate-600',  label: 'Low' },
  medium:   { bg: 'bg-amber-100',  text: 'text-amber-700',  label: 'Medium' },
  high:     { bg: 'bg-orange-100', text: 'text-orange-700', label: 'High' },
  critical: { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Critical' },
}

function painColor(n: number): string {
  if (n >= 7) return 'text-red-600'
  if (n >= 4) return 'text-amber-600'
  return 'text-slate-700'
}

function TrendIcon({ direction }: { direction?: string | null }) {
  if (direction === 'rising')  return <TrendingUp  className="w-3.5 h-3.5 inline" />
  if (direction === 'falling') return <TrendingDown className="w-3.5 h-3.5 inline" />
  return <Minus className="w-3.5 h-3.5 inline" />
}

export default function PainUrgencyRow({
  painIntensity,
  urgencyLevel,
  growthRate,
  trendDirection,
  validationCount,
  marketSize,
}: Props) {
  if (
    painIntensity == null &&
    urgencyLevel  == null &&
    growthRate    == null &&
    validationCount == null
  ) return null

  const showPain    = painIntensity != null
  const showUrgency = urgencyLevel  != null
  const showGrowth  = growthRate    != null

  const formatGrowth = (r: number) => `${r > 0 ? '+' : ''}${r}%`
  const growthColor  = (r: number) => r >= 0 ? 'text-emerald-600' : 'text-red-500'

  return (
    <div className="grid grid-cols-3 gap-3">
      {/* Pain / fallback: Signals */}
      <div className="bg-slate-50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">{showPain ? 'Pain' : 'Signals'}</div>
        {showPain ? (
          <div className={`text-lg font-bold ${painColor(painIntensity!)}`}>
            {painIntensity}/10
          </div>
        ) : (
          <div className="text-lg font-bold text-slate-900">{validationCount ?? 0}</div>
        )}
      </div>

      {/* Urgency / fallback: Market */}
      <div className="bg-slate-50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">{showUrgency ? 'Urgency' : 'Market'}</div>
        {showUrgency ? (
          (() => {
            const s = URGENCY_STYLES[urgencyLevel!] ?? URGENCY_STYLES.low
            return (
              <span
                className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full leading-tight ${s.bg} ${s.text}`}
              >
                {s.label.toUpperCase()}
              </span>
            )
          })()
        ) : (
          <div className="text-lg font-bold text-slate-900 truncate text-sm leading-tight pt-0.5">
            {marketSize || 'N/A'}
          </div>
        )}
      </div>

      {/* Growth */}
      <div className="bg-slate-50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">Growth</div>
        {showGrowth ? (
          <div className={`text-lg font-bold flex items-center gap-0.5 ${growthColor(growthRate!)}`}>
            <TrendIcon direction={trendDirection} />
            {formatGrowth(growthRate!)}
          </div>
        ) : (
          <div className="text-lg font-bold text-slate-400">—</div>
        )}
      </div>
    </div>
  )
}
