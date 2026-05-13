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

function formatPct(n: number): string {
  return `${n > 0 ? '+' : ''}${(n * 100).toFixed(0)}%`
}

function formatIncome(n: number): string {
  return `$${Math.round(n / 1000)}k`
}

interface Fact {
  key:      string
  icon:     React.ReactNode
  text:     string
  positive: boolean
}

export default function MacroContextStrip({ context }: Props) {
  if (!context) return null

  const facts: Fact[] = []

  if (context.population_5y_delta != null) {
    const v = context.population_5y_delta
    facts.push({
      key:      'population_5y_delta',
      icon:     <Users className="w-3 h-3" />,
      text:     `Pop ${formatPct(v)} 5Y`,
      positive: v > 0,
    })
  }

  if (context.unemployment_delta_90d != null) {
    const v = context.unemployment_delta_90d
    facts.push({
      key:      'unemployment_delta_90d',
      icon:     v < 0 ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />,
      text:     `Unemp ${formatPct(v)} 90D`,
      positive: v < 0,
    })
  }

  if (context.median_income != null) {
    facts.push({
      key:      'median_income',
      icon:     <DollarSign className="w-3 h-3" />,
      text:     `Income ${formatIncome(context.median_income)}/yr`,
      positive: true,
    })
  }

  if (!facts.length) return null

  const highlight = context.highlight
  const sorted = highlight
    ? [...facts.filter(f => f.key === highlight), ...facts.filter(f => f.key !== highlight)]
    : facts

  return (
    <div className="flex items-center gap-0 py-1.5 px-2.5 bg-slate-50 rounded-lg text-xs text-slate-600 flex-wrap">
      {sorted.map((fact, idx) => (
        <span key={fact.key} className="flex items-center gap-1">
          {idx > 0 && <span className="text-slate-300 mx-1.5">·</span>}
          <span className={`flex items-center gap-0.5 ${fact.positive ? 'text-emerald-600' : 'text-red-500'}`}>
            {fact.icon}
          </span>
          <span>{fact.text}</span>
        </span>
      ))}
    </div>
  )
}
