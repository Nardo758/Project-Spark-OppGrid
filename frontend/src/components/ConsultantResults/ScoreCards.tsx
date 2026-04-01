import { Globe, Store, TrendingUp, BarChart3 } from 'lucide-react'

interface ScoreCardsProps {
  onlineScore?: number
  physicalScore?: number
  confidenceScore?: number
  fourPsScores?: {
    product?: number
    price?: number
    place?: number
    promotion?: number
  }
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
      <div
        className={`h-2 rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
  )
}

export default function ScoreCards({ onlineScore, physicalScore, confidenceScore, fourPsScores }: ScoreCardsProps) {
  return (
    <div className="space-y-4">
      {/* Main scores */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <Globe className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">Online</span>
          </div>
          <div className="text-3xl font-bold text-blue-700">{onlineScore ?? '—'}%</div>
          <ScoreBar value={onlineScore ?? 0} color="bg-blue-500" />
        </div>
        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <Store className="w-4 h-4 text-green-600" />
            <span className="text-sm font-medium text-green-900">Physical</span>
          </div>
          <div className="text-3xl font-bold text-green-700">{physicalScore ?? '—'}%</div>
          <ScoreBar value={physicalScore ?? 0} color="bg-green-500" />
        </div>
        <div className="bg-amber-50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-900">Confidence</span>
          </div>
          <div className="text-3xl font-bold text-amber-700">{confidenceScore ?? '—'}%</div>
          <ScoreBar value={confidenceScore ?? 0} color="bg-amber-500" />
        </div>
      </div>

      {/* 4P's scores */}
      {fourPsScores && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-purple-600" />
            <span className="text-sm font-semibold text-gray-900">4P's Market Intelligence</span>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {(['product', 'price', 'place', 'promotion'] as const).map((pillar) => {
              const score = fourPsScores[pillar] ?? 0
              const colors: Record<string, string> = {
                product: 'text-blue-600',
                price: 'text-green-600',
                place: 'text-purple-600',
                promotion: 'text-amber-600',
              }
              const barColors: Record<string, string> = {
                product: 'bg-blue-500',
                price: 'bg-green-500',
                place: 'bg-purple-500',
                promotion: 'bg-amber-500',
              }
              return (
                <div key={pillar}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500 capitalize">{pillar}</span>
                    <span className={`text-sm font-bold ${colors[pillar]}`}>{score}</span>
                  </div>
                  <ScoreBar value={score} color={barColors[pillar]} />
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
