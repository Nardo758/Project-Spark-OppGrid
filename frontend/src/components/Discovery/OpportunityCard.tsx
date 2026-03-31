/**
 * OpportunityCard Component - Matches existing OppGrid card design
 * 
 * Now with optional 4 P's indicator for market intelligence preview
 * and JediRe market badges (Hot Market, Buy Window, etc.)
 */

import { FileText, Bookmark } from 'lucide-react'
import { useState, useEffect } from 'react'
import FourPsIndicator from '../FourPs/FourPsIndicator'
import MarketBadges, { type MarketBadge, type CompositeMetrics } from './MarketBadges'

interface FourPsScores {
  product: number
  price: number
  place: number
  promotion: number
}

interface OpportunityCardProps {
  opportunity: {
    id: number
    title: string
    description?: string
    category?: string
    feasibility_score?: number
    validation_count?: number
    market_size?: string
    growth_rate?: number
    access_state?: 'unlocked' | 'locked' | 'preview'
    user_validated?: boolean
    user_saved?: boolean
    ai_generated_title?: string
    ai_summary?: string
    // Location for badge fetching
    city?: string
    state?: string
    // Optional pre-loaded 4P's data
    four_ps_scores?: FourPsScores
    // Optional pre-loaded market badges
    market_badges?: MarketBadge[]
    composite_metrics?: CompositeMetrics
  }
  userTier?: string
  onValidate?: (id: number) => void
  onSave?: (id: number) => void
  onAnalyze?: (id: number) => void
  onShare?: (id: number) => void
  isValidated?: boolean
  isSaved?: boolean
  className?: string
  /** Show 4 P's indicator bar */
  showFourPs?: boolean
  /** Pre-loaded 4P's scores (for batch loading) */
  fourPsScores?: FourPsScores
  /** Show JediRe market badges */
  showMarketBadges?: boolean
  /** Pre-loaded market badges */
  marketBadges?: MarketBadge[]
  /** Pre-loaded composite metrics (badges computed locally) */
  compositeMetrics?: CompositeMetrics
}

export default function OpportunityCard({
  opportunity,
  userTier,
  onValidate,
  onSave,
  onAnalyze,
  onShare,
  isValidated: externalIsValidated,
  isSaved: externalIsSaved,
  className = '',
  showFourPs = false,
  fourPsScores,
  showMarketBadges = true,
  marketBadges,
  compositeMetrics
}: OpportunityCardProps) {
  const [isValidated, setIsValidated] = useState(externalIsValidated || opportunity.user_validated || false)
  const [isSaved, setIsSaved] = useState(externalIsSaved || opportunity.user_saved || false)
  const [fourPs, setFourPs] = useState<FourPsScores | null>(fourPsScores || opportunity.four_ps_scores || null)
  const [fourPsLoading, setFourPsLoading] = useState(false)
  
  // Market badges from props or opportunity
  const badges = marketBadges || opportunity.market_badges
  const metrics = compositeMetrics || opportunity.composite_metrics

  // Fetch 4P's data if showFourPs is true and we don't have it
  useEffect(() => {
    if (showFourPs && !fourPs && !fourPsLoading) {
      setFourPsLoading(true)
      fetch(`/api/v1/opportunities/${opportunity.id}/four-ps/mini`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.scores) {
            setFourPs(data.scores)
          }
        })
        .catch(() => {})
        .finally(() => setFourPsLoading(false))
    }
  }, [showFourPs, fourPs, fourPsLoading, opportunity.id])

  const handleValidate = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsValidated(!isValidated)
    onValidate?.(opportunity.id)
  }

  const handleSave = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsSaved(!isSaved)
    onSave?.(opportunity.id)
  }

  const handleAnalyze = (e: React.MouseEvent) => {
    e.stopPropagation()
    onAnalyze?.(opportunity.id)
  }

  // Get feasibility color
  const getFeasibilityColor = (score: number) => {
    if (score >= 75) return 'text-emerald-600 bg-emerald-50'
    if (score >= 50) return 'text-amber-600 bg-amber-50'
    return 'text-gray-600 bg-gray-50'
  }

  // Format market size
  const formatMarketSize = (size: string) => {
    if (size.includes('$')) return size
    return `~$${size}`
  }

  // Format growth rate
  const formatGrowth = (rate: number) => {
    return rate > 0 ? `+${rate}%` : `${rate}%`
  }

  return (
    <div
      className={`bg-white p-5 rounded-xl border-2 border-stone-200 hover:border-stone-900 transition-all cursor-pointer group ${className}`}
      onClick={() => window.location.href = `/opportunity/${opportunity.id}`}
    >
      {/* Header - Category + Score */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-stone-500 uppercase">
            {opportunity.category}
          </span>
          {opportunity.access_state === 'unlocked' && (
            <span className="flex items-center gap-1 bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">
              Unlocked
            </span>
          )}
          {opportunity.access_state === 'locked' && (
            <span className="flex items-center gap-1 bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-xs font-medium">
              Upgrade for Premium
            </span>
          )}
        </div>

        {/* Feasibility Score */}
        <div className="bg-emerald-100 text-emerald-700 px-3 py-2 rounded-full flex-shrink-0">
          <div className="text-2xl font-bold leading-none">{opportunity.feasibility_score || 0}</div>
        </div>
      </div>

      {/* JediRe Market Intelligence Badges */}
      {showMarketBadges && (badges || metrics || (opportunity.city && opportunity.state)) && (
        <div className="mb-3">
          <MarketBadges
            city={opportunity.city}
            state={opportunity.state}
            badges={badges}
            metrics={metrics}
            compact={false}
            maxBadges={3}
          />
        </div>
      )}

      {/* Title */}
      <h3 className="font-semibold text-stone-900 text-lg mb-1 group-hover:text-violet-600 transition-colors">
        {opportunity.title}
      </h3>

      {/* Description */}
      <p className="text-sm text-stone-500 mb-4 line-clamp-2">
        {opportunity.description || opportunity.ai_summary || 'Analysis pending...'}
      </p>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-stone-50 rounded-lg p-3">
          <div className="text-xs text-stone-500 mb-1">Signals</div>
          <div className="text-lg font-bold text-stone-900">
            {opportunity.validation_count || 0}
          </div>
        </div>
        <div className="bg-stone-50 rounded-lg p-3">
          <div className="text-xs text-stone-500 mb-1">Market</div>
          <div className="text-lg font-bold text-stone-900">
            {formatMarketSize(opportunity.market_size || 'N/A')}
          </div>
        </div>
        <div className="bg-stone-50 rounded-lg p-3">
          <div className="text-xs text-stone-500 mb-1">Growth</div>
          <div className="text-lg font-bold text-emerald-600">
            {formatGrowth(opportunity.growth_rate || 0)}
          </div>
        </div>
      </div>

      {/* 4 P's Indicator (optional) */}
      {showFourPs && (
        <div className="mb-4 px-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-stone-500">Market Intelligence</span>
            {fourPsLoading && (
              <span className="text-xs text-stone-400">Loading...</span>
            )}
          </div>
          {fourPs ? (
            <FourPsIndicator scores={fourPs} size="md" />
          ) : !fourPsLoading ? (
            <div className="h-2 bg-stone-100 rounded-full" />
          ) : null}
        </div>
      )}

      {/* Actions Row */}
      <div className="pt-4 border-t border-stone-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Report Button */}
          <button
            onClick={handleAnalyze}
            className="flex items-center gap-1 text-sm text-stone-600 hover:text-violet-600"
            aria-label="View report"
          >
            <FileText className="w-4 h-4" />
            <span>Report</span>
          </button>

          {/* Save Button */}
          <button
            onClick={handleSave}
            className={`flex items-center gap-1 text-sm ${
              isSaved
                ? 'text-violet-600'
                : 'text-stone-600 hover:text-violet-600'
            }`}
            aria-label={isSaved ? 'Unsave' : 'Save'}
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
            <span>Save</span>
          </button>
        </div>

        {/* View Full Analysis Link */}
        <div className="flex items-center gap-1 text-sm text-stone-600 group-hover:text-violet-600 transition-colors">
          <span>View full analysis</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  )
}
