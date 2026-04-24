import { useState } from 'react'
import { ChevronDown, ChevronUp, TrendingUp, Briefcase, BarChart3, ExternalLink } from 'lucide-react'

interface EconomicIndicator {
  value: number
  date: string
  units: string
  name: string
}

interface MacroData {
  fed_funds_rate?: EconomicIndicator
  inflation_rate?: EconomicIndicator
  unemployment?: EconomicIndicator
  consumer_sentiment?: EconomicIndicator
  mortgage_rate?: EconomicIndicator
  gdp_growth?: EconomicIndicator
}

interface LaborData {
  naics_code: string
  industry_name: string
  total_employment: number
  employment_change_yoy: number
  avg_weekly_wage: number
  establishment_count: number
  data_period: string
  source: string
}

interface PublicComp {
  ticker: string
  company_name: string
  fiscal_year: number
  revenue: number
  operating_income: number
  operating_margin: number | null
  net_income: number | null
}

interface BenchmarksData {
  avg_operating_margin: number
  avg_revenue_growth_3yr: number | null
  public_comps: PublicComp[]
  source: string
}

export interface EconomicSnapshot {
  macro?: MacroData
  macro_retrieved_at?: string
  labor?: LaborData
  benchmarks?: BenchmarksData
}

interface EconomicIntelPanelProps {
  snapshot: EconomicSnapshot
}

function fmt(value: number, units: string): string {
  if (units.includes('%') || units.toLowerCase().includes('percent')) {
    return `${value.toFixed(2)}%`
  }
  if (units.toLowerCase().includes('index') || units.toLowerCase().includes('ratio')) {
    return value.toFixed(1)
  }
  return value.toFixed(2)
}

function fmtRevenue(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`
  return `$${value.toFixed(0)}`
}

function fmtEmployment(value: number): string {
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toLocaleString()
}

const MACRO_LABELS: Record<string, { label: string; description: string }> = {
  fed_funds_rate: { label: 'Fed Funds Rate', description: 'Federal Reserve benchmark rate' },
  inflation_rate: { label: 'CPI Index (1982-84=100)', description: 'Consumer Price Index level — raw series CPIAUCSL as injected into report' },
  unemployment: { label: 'Unemployment Rate', description: 'U.S. national unemployment' },
  consumer_sentiment: { label: 'Consumer Sentiment', description: 'University of Michigan Index' },
  mortgage_rate: { label: '30-Yr Mortgage Rate', description: 'Average fixed mortgage rate' },
  gdp_growth: { label: 'GDP Growth', description: 'Real GDP annualised growth rate' },
}

export default function EconomicIntelPanel({ snapshot }: EconomicIntelPanelProps) {
  const [expanded, setExpanded] = useState(true)

  const hasMacro = snapshot.macro && Object.keys(snapshot.macro).length > 0
  const hasLabor = !!snapshot.labor
  const hasBenchmarks = snapshot.benchmarks && snapshot.benchmarks.public_comps.length > 0

  if (!hasMacro && !hasLabor && !hasBenchmarks) return null

  return (
    <div className="mt-6 border border-emerald-200 rounded-xl overflow-hidden bg-gradient-to-br from-emerald-50/60 to-slate-50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-4 bg-emerald-900/5 hover:bg-emerald-900/10 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-white" />
          </div>
          <div className="text-left">
            <div className="text-sm font-semibold text-gray-900">Economic Intelligence</div>
            <div className="text-xs text-gray-500">Live macro indicators, labor data &amp; public-comp benchmarks that grounded this report</div>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="p-5 space-y-5">
          {hasMacro && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-emerald-700" />
                <h4 className="text-xs font-bold text-emerald-800 uppercase tracking-wider">
                  Macroeconomic Environment
                </h4>
                <span className="ml-auto text-[10px] text-gray-400 font-mono">Source: FRED / Federal Reserve</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(snapshot.macro!).map(([key, indicator]) => {
                  const meta = MACRO_LABELS[key]
                  if (!meta || !indicator) return null
                  return (
                    <div key={key} className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                      <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">{meta.label}</div>
                      <div className="text-lg font-bold text-gray-900 leading-tight">
                        {fmt(indicator.value, indicator.units)}
                      </div>
                      <div className="text-[9px] text-gray-400 mt-0.5">
                        {indicator.date ? new Date(indicator.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : ''}
                      </div>
                    </div>
                  )
                })}
              </div>
              {snapshot.macro_retrieved_at && (
                <div className="text-[10px] text-gray-400 mt-1.5 text-right">
                  Retrieved {snapshot.macro_retrieved_at}
                </div>
              )}
            </section>
          )}

          {hasLabor && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Briefcase className="w-4 h-4 text-blue-700" />
                <h4 className="text-xs font-bold text-blue-800 uppercase tracking-wider">
                  Labor Market — {snapshot.labor!.industry_name}
                </h4>
                <span className="ml-auto text-[10px] text-gray-400 font-mono">{snapshot.labor!.source}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                  <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">Employment</div>
                  <div className="text-lg font-bold text-gray-900">{fmtEmployment(snapshot.labor!.total_employment)}</div>
                  <div className="text-[9px] text-gray-400">workers nationally</div>
                </div>
                <div className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                  <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">YoY Change</div>
                  <div className={`text-lg font-bold ${snapshot.labor!.employment_change_yoy >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                    {snapshot.labor!.employment_change_yoy >= 0 ? '+' : ''}{snapshot.labor!.employment_change_yoy.toFixed(1)}%
                  </div>
                  <div className="text-[9px] text-gray-400">employment growth</div>
                </div>
                <div className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                  <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">Avg Weekly Wage</div>
                  <div className="text-lg font-bold text-gray-900">${snapshot.labor!.avg_weekly_wage.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                  <div className="text-[9px] text-gray-400">per week</div>
                </div>
                {snapshot.labor!.establishment_count > 0 && (
                  <div className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                    <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">Establishments</div>
                    <div className="text-lg font-bold text-gray-900">{fmtEmployment(snapshot.labor!.establishment_count)}</div>
                    <div className="text-[9px] text-gray-400">businesses</div>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] text-gray-400">
                  NAICS {snapshot.labor!.naics_code} · {snapshot.labor!.data_period}
                </span>
              </div>
            </section>
          )}

          {hasBenchmarks && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-4 h-4 text-violet-700" />
                <h4 className="text-xs font-bold text-violet-800 uppercase tracking-wider">
                  Public-Comp Benchmarks
                </h4>
                <span className="ml-auto text-[10px] text-gray-400 font-mono">{snapshot.benchmarks!.source}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                  <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">Avg Operating Margin</div>
                  <div className="text-lg font-bold text-violet-700">
                    {(snapshot.benchmarks!.avg_operating_margin * 100).toFixed(1)}%
                  </div>
                  <div className="text-[9px] text-gray-400">industry median (public comps)</div>
                </div>
                {snapshot.benchmarks!.avg_revenue_growth_3yr != null && (
                  <div className="bg-white rounded-lg border border-gray-100 px-3 py-2.5 shadow-sm">
                    <div className="text-[10px] font-medium text-gray-500 mb-0.5 uppercase tracking-wide">3-Yr Revenue Growth</div>
                    <div className={`text-lg font-bold ${snapshot.benchmarks!.avg_revenue_growth_3yr >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                      {snapshot.benchmarks!.avg_revenue_growth_3yr >= 0 ? '+' : ''}{(snapshot.benchmarks!.avg_revenue_growth_3yr * 100).toFixed(1)}%
                    </div>
                    <div className="text-[9px] text-gray-400">CAGR (public comps)</div>
                  </div>
                )}
              </div>
              <div className="overflow-x-auto rounded-lg border border-gray-100">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      <th className="text-left py-2 px-3 font-semibold text-gray-700">Ticker</th>
                      <th className="text-left py-2 px-3 font-semibold text-gray-700">Company</th>
                      <th className="text-right py-2 px-3 font-semibold text-gray-700">FY</th>
                      <th className="text-right py-2 px-3 font-semibold text-gray-700">Revenue</th>
                      <th className="text-right py-2 px-3 font-semibold text-gray-700">Op. Income</th>
                      <th className="text-right py-2 px-3 font-semibold text-gray-700">Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.benchmarks!.public_comps.map((comp, i) => (
                      <tr key={i} className={`border-b border-gray-50 ${i % 2 === 1 ? 'bg-gray-50/50' : 'bg-white'}`}>
                        <td className="py-2 px-3 font-mono font-bold text-violet-700">{comp.ticker}</td>
                        <td className="py-2 px-3 text-gray-700">{comp.company_name}</td>
                        <td className="py-2 px-3 text-right text-gray-500">{comp.fiscal_year}</td>
                        <td className="py-2 px-3 text-right text-gray-900 font-medium">{fmtRevenue(comp.revenue)}</td>
                        <td className="py-2 px-3 text-right text-gray-900">{fmtRevenue(comp.operating_income)}</td>
                        <td className="py-2 px-3 text-right">
                          {comp.operating_margin != null ? (
                            <span className={`font-semibold ${comp.operating_margin >= 0.2 ? 'text-emerald-700' : comp.operating_margin >= 0 ? 'text-gray-700' : 'text-red-600'}`}>
                              {(comp.operating_margin * 100).toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center gap-1.5 mt-2 text-[10px] text-gray-400">
                <ExternalLink className="w-3 h-3" />
                <span>Data from SEC 10-K filings via sec-api.io</span>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
