import { TrendingUp, TrendingDown, DollarSign, Users } from 'lucide-react'

interface MacroContext {
  unemployment_delta_90d?: number
  population_5y_delta?:   number
  median_income?:         number
  trend_direction?:       'rising' | 'falling' | 'flat'
  highlight?:             string
}

interface Props {
  context?: MacroContext | null
}

function formatPct(n?: number): string {
  if (n === undefined || n === null) return ''
  return `${n > 0 ? '+' : ''}${(n * 100).toFixed(0)}%`
}

function formatIncome(n?: number): string {
  if (!n) return ''
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`
  return `$${n}`
}

export default function MacroContextStrip({ context }: Props) {
  if (!context) return null

  const items: { icon: React.ReactNode; label: string; value: string; positive?: boolean }[] = []

  if (context.population_5y_delta !== undefined) {
    items.push({
      icon:     <Users className="w-3.5 h-3.5" />,
      label:    'Population 5Y',
      value:    formatPct(context.population_5y_delta),
      positive: context.population_5y_delta > 0,
    })
  }
  if (context.median_income !== undefined) {
    items.push({
      icon:  <DollarSign className="w-3.5 h-3.5" />,
      label: 'Median income',
      value: formatIncome(context.median_income),
    })
  }
  if (context.unemployment_delta_90d !== undefined) {
    items.push({
      icon:     context.unemployment_delta_90d > 0
        ? <TrendingUp className="w-3.5 h-3.5" />
        : <TrendingDown className="w-3.5 h-3.5" />,
      label:    'Unemployment 90D',
      value:    formatPct(context.unemployment_delta_90d),
      positive: context.unemployment_delta_90d < 0,
    })
  }

  if (items.length === 0) return null

  return (
    <div className="flex items-center gap-3 text-xs text-slate-600 px-1 py-2 border-t border-slate-100">
      {items.slice(0, 3).map((item, i) => (
        <span key={i} className="inline-flex items-center gap-1">
          <span className={item.positive ? 'text-emerald-600' : 'text-slate-500'}>
            {item.icon}
          </span>
          <span className="text-slate-500">{item.label}</span>
          <span className={`font-semibold ${item.positive ? 'text-emerald-700' : 'text-slate-700'}`}>
            {item.value}
          </span>
        </span>
      ))}
    </div>
  )
}
