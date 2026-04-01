import { TrendingUp, Users, DollarSign, Building2, Shield, AlertTriangle } from 'lucide-react'

interface MarketIntelligenceProps {
  marketIntelligence?: {
    demand_level?: string
    competition_level?: string
    growth_trend?: string
    population?: number
    median_income?: number
    competitor_count?: number
    google_trends_interest?: number
    job_market_growth?: string
  }
  advantages?: string[]
  risks?: string[]
}

function Badge({ label, variant }: { label: string; variant: 'green' | 'amber' | 'red' | 'blue' | 'gray' }) {
  const styles = {
    green: 'bg-green-100 text-green-700',
    amber: 'bg-amber-100 text-amber-700',
    red: 'bg-red-100 text-red-700',
    blue: 'bg-blue-100 text-blue-700',
    gray: 'bg-gray-100 text-gray-700',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${styles[variant]}`}>
      {label}
    </span>
  )
}

function levelVariant(level?: string): 'green' | 'amber' | 'red' | 'gray' {
  if (!level) return 'gray'
  const l = level.toLowerCase()
  if (l === 'high' || l === 'growing') return 'green'
  if (l === 'medium' || l === 'stable') return 'amber'
  return 'red'
}

export default function MarketIntelligence({ marketIntelligence, advantages, risks }: MarketIntelligenceProps) {
  const mi = marketIntelligence
  if (!mi && !advantages?.length && !risks?.length) return null

  return (
    <div className="space-y-4">
      {mi && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-purple-600" />
            Market Intelligence
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <span className="text-xs text-gray-500 block mb-1">Demand</span>
              <Badge label={mi.demand_level || 'Unknown'} variant={levelVariant(mi.demand_level)} />
            </div>
            <div>
              <span className="text-xs text-gray-500 block mb-1">Competition</span>
              <Badge
                label={mi.competition_level || 'Unknown'}
                variant={mi.competition_level === 'low' ? 'green' : mi.competition_level === 'medium' ? 'amber' : 'red'}
              />
            </div>
            <div>
              <span className="text-xs text-gray-500 block mb-1">Growth Trend</span>
              <Badge label={mi.growth_trend || 'Unknown'} variant={levelVariant(mi.growth_trend)} />
            </div>
            <div>
              <span className="text-xs text-gray-500 block mb-1">Google Trends</span>
              <span className="text-lg font-bold text-gray-900">
                {mi.google_trends_interest ?? '—'}
                <span className="text-xs text-gray-500 font-normal">/100</span>
              </span>
            </div>
          </div>

          {(mi.population || mi.median_income || mi.competitor_count) && (
            <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-100">
              {mi.population && (
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-gray-400" />
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{mi.population.toLocaleString()}</div>
                    <div className="text-xs text-gray-500">Population</div>
                  </div>
                </div>
              )}
              {mi.median_income && (
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-gray-400" />
                  <div>
                    <div className="text-sm font-semibold text-gray-900">${mi.median_income.toLocaleString()}</div>
                    <div className="text-xs text-gray-500">Median Income</div>
                  </div>
                </div>
              )}
              {mi.competitor_count != null && (
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-gray-400" />
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{mi.competitor_count}</div>
                    <div className="text-xs text-gray-500">Competitors</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Advantages & Risks */}
      {(advantages?.length || risks?.length) ? (
        <div className="grid md:grid-cols-2 gap-4">
          {advantages && advantages.length > 0 && (
            <div className="bg-green-50 border border-green-100 rounded-xl p-4">
              <h5 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Advantages
              </h5>
              <ul className="space-y-2">
                {advantages.map((a, i) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">+</span>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {risks && risks.length > 0 && (
            <div className="bg-red-50 border border-red-100 rounded-xl p-4">
              <h5 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Risks
              </h5>
              <ul className="space-y-2">
                {risks.map((r, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <span className="text-red-500 mt-0.5">!</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
