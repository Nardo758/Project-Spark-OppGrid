/**
 * MarketBadges Component
 * 
 * Displays JediRe market intelligence badges:
 * - 🔥 Hot Market (surge_index > 20%)
 * - 📈 Buy Window (digital > physical demand)
 * - 🏆 Premium Location (TPI >= 70)
 * - ⚡ Accelerating (TVS > 60)
 * - 🐢 Slowing (TVS < 40)
 */

import { useState, useEffect } from 'react'
import { Flame, TrendingUp, Trophy, Zap, Turtle } from 'lucide-react'

interface MarketBadge {
  id: string
  emoji: string
  label: string
  description: string
  color: string
}

interface CompositeMetrics {
  surge_index: number
  digital_physical_gap: number
  tpi: number
  tvs: number
  computed_locally?: boolean
}

interface MarketBadgesProps {
  /** City name */
  city?: string
  /** State code */
  state?: string
  /** Pre-loaded badges (skip fetch) */
  badges?: MarketBadge[]
  /** Pre-loaded metrics (compute badges locally) */
  metrics?: CompositeMetrics
  /** Show compact version (icons only) */
  compact?: boolean
  /** Max badges to show */
  maxBadges?: number
  /** Additional class names */
  className?: string
}

// Badge computation from metrics
function computeBadges(metrics: CompositeMetrics): MarketBadge[] {
  const badges: MarketBadge[] = []
  
  const { surge_index, digital_physical_gap, tpi, tvs } = metrics
  
  // 🔥 Hot Market
  if (surge_index > 20) {
    badges.push({
      id: 'hot_market',
      emoji: '🔥',
      label: 'Hot Market',
      description: `Traffic surge ${surge_index.toFixed(0)}% above baseline`,
      color: 'bg-orange-100 text-orange-700 border-orange-200'
    })
  }
  
  // 📈 Buy Window
  if (digital_physical_gap > 5) {
    badges.push({
      id: 'buy_window',
      emoji: '📈',
      label: 'Buy Window',
      description: `Digital demand +${digital_physical_gap.toFixed(0)}% ahead of physical`,
      color: 'bg-emerald-100 text-emerald-700 border-emerald-200'
    })
  }
  
  // 🏆 Premium Location
  if (tpi >= 70) {
    badges.push({
      id: 'premium_location',
      emoji: '🏆',
      label: `Top ${100 - tpi}%`,
      description: `Traffic Position Index ${tpi}/100`,
      color: 'bg-amber-100 text-amber-700 border-amber-200'
    })
  }
  
  // ⚡ Accelerating
  if (tvs > 60) {
    badges.push({
      id: 'accelerating',
      emoji: '⚡',
      label: 'Accelerating',
      description: `Traffic velocity score ${tvs}/100`,
      color: 'bg-violet-100 text-violet-700 border-violet-200'
    })
  }
  
  // 🐢 Slowing
  if (tvs < 40) {
    badges.push({
      id: 'decelerating',
      emoji: '🐢',
      label: 'Slowing',
      description: `Traffic velocity score ${tvs}/100`,
      color: 'bg-stone-100 text-stone-600 border-stone-200'
    })
  }
  
  return badges
}

// Icon component for badge
function BadgeIcon({ id, className }: { id: string; className?: string }) {
  const iconProps = { className: className || 'w-3.5 h-3.5' }
  
  switch (id) {
    case 'hot_market':
      return <Flame {...iconProps} />
    case 'buy_window':
      return <TrendingUp {...iconProps} />
    case 'premium_location':
      return <Trophy {...iconProps} />
    case 'accelerating':
      return <Zap {...iconProps} />
    case 'decelerating':
      return <Turtle {...iconProps} />
    default:
      return null
  }
}

export default function MarketBadges({
  city,
  state,
  badges: preloadedBadges,
  metrics: preloadedMetrics,
  compact = false,
  maxBadges = 4,
  className = ''
}: MarketBadgesProps) {
  const [badges, setBadges] = useState<MarketBadge[]>(preloadedBadges || [])
  const [loading, setLoading] = useState(false)
  const [hoveredBadge, setHoveredBadge] = useState<string | null>(null)

  useEffect(() => {
    // If we have preloaded metrics, compute badges
    if (preloadedMetrics && !preloadedBadges) {
      setBadges(computeBadges(preloadedMetrics))
      return
    }
    
    // If we have preloaded badges, use them
    if (preloadedBadges) {
      setBadges(preloadedBadges)
      return
    }
    
    // Fetch from API if we have city/state
    if (city && state && !preloadedBadges && !preloadedMetrics) {
      setLoading(true)
      fetch(`/api/v1/market/badges?city=${encodeURIComponent(city)}&state=${encodeURIComponent(state)}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.badges) {
            setBadges(data.badges)
          } else if (data?.metrics) {
            setBadges(computeBadges(data.metrics))
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    }
  }, [city, state, preloadedBadges, preloadedMetrics])

  if (loading) {
    return (
      <div className={`flex gap-1 ${className}`}>
        <div className="h-5 w-16 bg-stone-100 rounded-full animate-pulse" />
        <div className="h-5 w-20 bg-stone-100 rounded-full animate-pulse" />
      </div>
    )
  }

  if (badges.length === 0) {
    return null
  }

  const displayBadges = badges.slice(0, maxBadges)
  const remainingCount = badges.length - maxBadges

  if (compact) {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {displayBadges.map(badge => (
          <div
            key={badge.id}
            className="relative group"
            onMouseEnter={() => setHoveredBadge(badge.id)}
            onMouseLeave={() => setHoveredBadge(null)}
          >
            <span 
              className={`inline-flex items-center justify-center w-6 h-6 rounded-full border ${badge.color} cursor-help transition-transform hover:scale-110`}
              title={badge.description}
            >
              <span className="text-xs">{badge.emoji}</span>
            </span>
            
            {/* Tooltip */}
            {hoveredBadge === badge.id && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-stone-900 text-white text-xs rounded whitespace-nowrap z-50">
                {badge.label}: {badge.description}
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-900" />
              </div>
            )}
          </div>
        ))}
        {remainingCount > 0 && (
          <span className="text-xs text-stone-400">+{remainingCount}</span>
        )}
      </div>
    )
  }

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {displayBadges.map(badge => (
        <div
          key={badge.id}
          className="relative group"
          onMouseEnter={() => setHoveredBadge(badge.id)}
          onMouseLeave={() => setHoveredBadge(null)}
        >
          <span 
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${badge.color} cursor-help transition-all hover:shadow-sm`}
          >
            <span>{badge.emoji}</span>
            <span>{badge.label}</span>
          </span>
          
          {/* Tooltip */}
          {hoveredBadge === badge.id && (
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-stone-900 text-white text-xs rounded-lg shadow-lg whitespace-nowrap z-50 max-w-xs">
              <div className="font-medium mb-0.5">{badge.label}</div>
              <div className="text-stone-300">{badge.description}</div>
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-900" />
            </div>
          )}
        </div>
      ))}
      {remainingCount > 0 && (
        <span className="inline-flex items-center px-2 py-0.5 text-xs text-stone-400">
          +{remainingCount} more
        </span>
      )}
    </div>
  )
}

// Export badge computation for use elsewhere
export { computeBadges, type MarketBadge, type CompositeMetrics }
