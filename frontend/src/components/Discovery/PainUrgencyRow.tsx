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
  critical: { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Critical' },
  high:     { bg: 'bg-orange-100', text: 'text-orange-700', label: 'High' },
  medium:   { bg: 'bg-amber-100',  text: 'text-amber-700',  label: 'Medium' },
  low:      { bg: 'bg-slate-100',  text: 'text-slate-600',  label: 'Low' },
}

/** Returns both text color AND background color for the pain cell */
function painCellClass(pain: number): string {
  if (pain >= 7) return 'text-red-600 bg-red-50'
  if (pain >= 4) return 'text-amber-600 bg-amber-50'
  return 'text-slate-700 bg-slate-50'
}

export default function PainUrgencyRow({
  painIntensity,
  urgencyLevel,
  growthRate,
  trendDirection,
  validationCount,
  marketSize,
}: Props) {
  const TrendIcon =
    (trendDirection === 'rising'  || (growthRate ?? 0) > 0) ? TrendingUp  :
    (trendDirection === 'falling' || (growthRate ?? 0) < 0) ? TrendingDown :
    Minus

  return (
    <div className="grid grid-cols-3 gap-3 mb-4">
      {/* Cell 1: Pain (or Signals fallback) */}
      <div className={`rounded-lg p-3 ${painIntensity ? painCellClass(painIntensity) : 'bg-slate-50'}`}>
        <div className="text-xs text-slate-500 mb-1">
          {painIntensity ? 'Pain' : 'Signals'}
        </div>
        <div className="text-lg font-bold">
          {painIntensity ? `${painIntensity}/10` : (validationCount ?? 0)}
        </div>
      </div>

      {/* Cell 2: Urgency (or Market fallback) */}
      <div className="bg-slate-50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">
          {urgencyLevel ? 'Urgency' : 'Market'}
        </div>
        {urgencyLevel && URGENCY_STYLES[urgencyLevel] ? (
          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold
            ${URGENCY_STYLES[urgencyLevel].bg} ${URGENCY_STYLES[urgencyLevel].text}`}>
            {URGENCY_STYLES[urgencyLevel].label}
          </span>
        ) : (
          <div className="text-lg font-bold text-slate-900">
            {marketSize ?? 'N/A'}
          </div>
        )}
      </div>

      {/* Cell 3: Growth (always shown) */}
      <div className="bg-slate-50 rounded-lg p-3">
        <div className="text-xs text-slate-500 mb-1">Growth</div>
        <div className="flex items-center gap-1 text-lg font-bold text-emerald-600">
          {growthRate !== null && growthRate !== undefined ? (
            <>
              <TrendIcon className="w-4 h-4" />
              {growthRate > 0 ? '+' : ''}{growthRate}%
            </>
          ) : <span className="text-slate-400">—</span>}
        </div>
      </div>
    </div>
  )
}
