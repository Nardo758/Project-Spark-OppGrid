import { useEffect, useState } from 'react'
import { TrendingUp, Activity, Wifi } from 'lucide-react'

type Indicator = {
  value: number
  date: string
  units: string
  name: string
}

type EconomicPreview = {
  available: boolean
  retrieved_at?: string
  report_types: string[]
  indicators: {
    fed_funds_rate?: Indicator | null
    inflation_rate?: Indicator | null
    unemployment?: Indicator | null
    gdp_growth?: Indicator | null
    consumer_sentiment?: Indicator | null
    mortgage_rate?: Indicator | null
  } | null
}

type Props = {
  reportType: string
}

const DISPLAY_METRICS: { key: keyof NonNullable<EconomicPreview['indicators']>; label: string; suffix?: string }[] = [
  { key: 'fed_funds_rate', label: 'Fed Funds', suffix: '%' },
  { key: 'inflation_rate', label: 'CPI Index', suffix: '' },
  { key: 'unemployment', label: 'Unemployment', suffix: '%' },
]

function fmt(value: number, suffix: string): string {
  if (suffix === '%') return `${value.toFixed(2)}%`
  return value.toFixed(1)
}

function shortDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

let _cache: EconomicPreview | null = null

export default function EconomicPreviewCard({ reportType }: Props) {
  const [data, setData] = useState<EconomicPreview | null>(_cache)
  const [loading, setLoading] = useState(!_cache)

  useEffect(() => {
    if (_cache) return
    let cancelled = false
    setLoading(true)
    fetch('/api/v1/reports/economic-preview')
      .then((r) => r.json())
      .then((d: EconomicPreview) => {
        if (!cancelled) {
          _cache = d
          setData(d)
        }
      })
      .catch(() => {
        if (!cancelled) setData(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 py-2 px-2.5 rounded-lg bg-gray-50 border border-gray-100">
        <Activity className="w-3 h-3 text-gray-300 animate-pulse" />
        <span className="text-[10px] text-gray-400">Loading live market data…</span>
      </div>
    )
  }

  if (!data?.available || !data.indicators || !data.report_types.includes(reportType)) {
    return null
  }

  const available = DISPLAY_METRICS.filter((m) => data.indicators![m.key] != null)
  if (available.length === 0) return null

  return (
    <div className="rounded-lg border border-[#0F6E56]/20 bg-[#0F6E56]/5 p-2.5">
      <div className="flex items-center gap-1.5 mb-2">
        <Wifi className="w-3 h-3 text-[#0F6E56]" />
        <span className="text-[10px] font-semibold text-[#0F6E56] uppercase tracking-wide">
          Live data sources
        </span>
        <span className="ml-auto text-[9px] text-gray-400">FRED / St. Louis Fed</span>
      </div>

      <div className="grid grid-cols-3 gap-1.5 mb-2">
        {available.map(({ key, label, suffix }) => {
          const ind = data.indicators![key]!
          return (
            <div key={key} className="text-center bg-white/70 rounded-md py-1.5 px-1">
              <div className="text-[13px] font-bold text-gray-900 leading-tight">
                {fmt(ind.value, suffix ?? '')}
              </div>
              <div className="text-[9px] text-gray-500 leading-tight">{label}</div>
              <div className="text-[8px] text-gray-400 leading-tight">{shortDate(ind.date)}</div>
            </div>
          )
        })}
      </div>

      <div className="flex items-center gap-1">
        <TrendingUp className="w-2.5 h-2.5 text-[#0F6E56] shrink-0" />
        <p className="text-[9px] text-[#0F6E56]/80 leading-tight">
          These indicators will be injected into your report's analysis
        </p>
      </div>
    </div>
  )
}
