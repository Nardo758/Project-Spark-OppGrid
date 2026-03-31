/**
 * FourPsIndicator - Mini 4-bar indicator for opportunity cards
 * 
 * Shows PRODUCT, PRICE, PLACE, PROMOTION scores as colored bars
 * with hover tooltips for details.
 */

import { useState } from 'react'
import { Package, DollarSign, MapPin, Megaphone } from 'lucide-react'

interface FourPsScores {
  product: number
  price: number
  place: number
  promotion: number
}

interface FourPsIndicatorProps {
  scores: FourPsScores
  size?: 'sm' | 'md' | 'lg'
  showLabels?: boolean
  className?: string
}

const PILLAR_CONFIG = {
  product: {
    label: 'Product',
    description: 'Demand Validation',
    icon: Package,
    color: 'bg-blue-500',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
  },
  price: {
    label: 'Price',
    description: 'Market Economics',
    icon: DollarSign,
    color: 'bg-emerald-500',
    bgColor: 'bg-emerald-100',
    textColor: 'text-emerald-700',
  },
  place: {
    label: 'Place',
    description: 'Location Intelligence',
    icon: MapPin,
    color: 'bg-amber-500',
    bgColor: 'bg-amber-100',
    textColor: 'text-amber-700',
  },
  promotion: {
    label: 'Promotion',
    description: 'Competition & Reach',
    icon: Megaphone,
    color: 'bg-purple-500',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
  },
}

function getScoreColor(score: number): string {
  if (score >= 75) return 'bg-emerald-500'
  if (score >= 50) return 'bg-amber-500'
  if (score >= 25) return 'bg-orange-500'
  return 'bg-red-500'
}

function getScoreLabel(score: number): string {
  if (score >= 75) return 'Excellent'
  if (score >= 50) return 'Good'
  if (score >= 25) return 'Fair'
  return 'Needs Data'
}

export default function FourPsIndicator({
  scores,
  size = 'sm',
  showLabels = false,
  className = ''
}: FourPsIndicatorProps) {
  const [hoveredPillar, setHoveredPillar] = useState<string | null>(null)

  const sizeConfig = {
    sm: { barHeight: 'h-1.5', barWidth: 'w-6', gap: 'gap-1', iconSize: 12 },
    md: { barHeight: 'h-2', barWidth: 'w-8', gap: 'gap-1.5', iconSize: 14 },
    lg: { barHeight: 'h-3', barWidth: 'w-12', gap: 'gap-2', iconSize: 16 },
  }

  const { barHeight, barWidth, gap, iconSize } = sizeConfig[size]

  const pillars = ['product', 'price', 'place', 'promotion'] as const

  return (
    <div className={`relative ${className}`}>
      <div className={`flex items-center ${gap}`}>
        {pillars.map((pillar) => {
          const config = PILLAR_CONFIG[pillar]
          const score = scores[pillar]
          const Icon = config.icon
          const fillWidth = `${Math.min(100, Math.max(0, score))}%`

          return (
            <div
              key={pillar}
              className="relative flex items-center gap-1"
              onMouseEnter={() => setHoveredPillar(pillar)}
              onMouseLeave={() => setHoveredPillar(null)}
            >
              {showLabels && (
                <Icon className={`${config.textColor}`} size={iconSize} />
              )}
              
              {/* Bar background */}
              <div className={`${barWidth} ${barHeight} bg-stone-200 rounded-full overflow-hidden`}>
                {/* Filled portion */}
                <div
                  className={`h-full ${getScoreColor(score)} rounded-full transition-all duration-300`}
                  style={{ width: fillWidth }}
                />
              </div>

              {/* Tooltip */}
              {hoveredPillar === pillar && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 pointer-events-none">
                  <div className="bg-stone-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon size={12} />
                      <span className="font-semibold">{config.label}</span>
                    </div>
                    <div className="text-stone-300 text-[10px] mb-1">{config.description}</div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-lg">{score}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        score >= 75 ? 'bg-emerald-600' :
                        score >= 50 ? 'bg-amber-600' :
                        score >= 25 ? 'bg-orange-600' : 'bg-red-600'
                      }`}>
                        {getScoreLabel(score)}
                      </span>
                    </div>
                  </div>
                  {/* Arrow */}
                  <div className="absolute left-1/2 -translate-x-1/2 top-full">
                    <div className="border-4 border-transparent border-t-stone-900" />
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Overall score badge (optional) */}
      {showLabels && (
        <div className="ml-2 text-xs font-semibold text-stone-600">
          {Math.round((scores.product + scores.price + scores.place + scores.promotion) / 4)}
        </div>
      )}
    </div>
  )
}

// Hook for fetching 4P's mini data
export function useFourPsMini(opportunityId: number | null) {
  const [data, setData] = useState<{
    scores: FourPsScores
    overall: number
    quality: number
    top_insight: string
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    if (!opportunityId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/four-ps/mini`)
      if (!res.ok) throw new Error('Failed to fetch 4Ps data')
      const json = await res.json()
      setData(json)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return { data, loading, error, fetchData }
}
