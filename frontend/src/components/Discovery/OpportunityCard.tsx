/**
 * OpportunityCard — Enriched
 *
 * Surfaces confidence tier, source mix, location, pain/urgency, and macro
 * context in addition to existing fields. Brand-aligned to emerald/navy/slate.
 *
 * variant="standard" — discovery feed (default)
 * variant="compact"  — sidebars, saved list (strips macro strip)
 *
 * All new fields are optional and degrade gracefully to null.
 */
import { FileText, Bookmark } from 'lucide-react'
import { useState, useEffect } from 'react'
import FourPsIndicator from '../FourPs/FourPsIndicator'
import MarketBadges, { type MarketBadge, type CompositeMetrics } from './MarketBadges'
import ConfidenceTierBadge, { getTierBorderClass, getTierHoverClass } from './ConfidenceTierBadge'
import SourceMixIndicator from './SourceMixIndicator'
import LocationLine from './LocationLine'
import PainUrgencyRow from './PainUrgencyRow'
import MacroContextStrip from './MacroContextStrip'
import RealmTypeIcon from './RealmTypeIcon'

interface FourPsScores {
  product:   number
  price:     number
  place:     number
  promotion: number
}

interface MacroContext {
  unemployment_delta_90d?: number
  population_5y_delta?:   number
  median_income?:         number
  trend_direction?:       'rising' | 'falling' | 'flat'
  highlight?:             string
}

interface ContributingSources {
  total_sources?: number
  total_signals?: number
  [key: string]: number | undefined
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
    // Location
    city?: string
    state?: string
    // Enrichment — Group 1 (available now)
    realm_type?: string
    geographic_scope?: string
    ai_pain_intensity?: number
    ai_urgency_level?: string
    ai_competition_level?: string
    // Enrichment — Group 2 (Spec 1, degrade gracefully when null)
    confidence_tier?: string | null
    contributing_sources?: ContributingSources | null
    macro_context?: MacroContext | null
    // Optional pre-loaded data
    four_ps_scores?: FourPsScores
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
  /** standard (default) = full card; compact = sidebar/saved-list, no macro strip */
  variant?: 'standard' | 'compact'
  showFourPs?: boolean
  fourPsScores?: FourPsScores
  showMarketBadges?: boolean
  marketBadges?: MarketBadge[]
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
  variant = 'standard',
  showFourPs = false,
  fourPsScores,
  showMarketBadges = true,
  marketBadges,
  compositeMetrics,
}: OpportunityCardProps) {
  const [isValidated, setIsValidated] = useState(
    externalIsValidated || opportunity.user_validated || false,
  )
  const [isSaved, setIsSaved] = useState(
    externalIsSaved || opportunity.user_saved || false,
  )
  const [fourPs, setFourPs] = useState<FourPsScores | null>(
    fourPsScores || opportunity.four_ps_scores || null,
  )
  const [fourPsLoading, setFourPsLoading] = useState(false)

  const badges  = marketBadges  || opportunity.market_badges
  const metrics = compositeMetrics || opportunity.composite_metrics
  const tier    = opportunity.confidence_tier ?? null

  const borderClass = getTierBorderClass(tier)
  const hoverClass  = getTierHoverClass(tier)

  const isCompact = variant === 'compact'

  useEffect(() => {
    if (showFourPs && !fourPs && !fourPsLoading) {
      setFourPsLoading(true)
      fetch(`/api/v1/opportunities/${opportunity.id}/four-ps/mini`)
        .then(res => (res.ok ? res.json() : null))
        .then(data => { if (data?.scores) setFourPs(data.scores) })
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

  const getFeasibilityColor = (score: number) => {
    if (score >= 75) return 'text-emerald-600 bg-emerald-50'
    if (score >= 50) return 'text-amber-600 bg-amber-50'
    return 'text-slate-600 bg-slate-100'
  }

  const formatMarketSize = (size: string) =>
    size.includes('$') ? size : `~$${size}`

  const hasBadgeRow =
    showMarketBadges &&
    (badges || metrics || (opportunity.city && opportunity.state) || opportunity.contributing_sources)

  return (
    <div
      className={`bg-white p-5 rounded-xl border-2 ${borderClass} ${hoverClass} transition-all cursor-pointer group ${className}`}
      onClick={() => (window.location.href = `/opportunity/${opportunity.id}`)}
    >
      {/* ── Header ── */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex flex-col gap-1 flex-1 min-w-0 mr-3">

          {/* Tier badge + realm icon + category + access badge */}
          <div className="flex items-center gap-2 flex-wrap">
            {tier && <ConfidenceTierBadge tier={tier} />}
            <span className="flex items-center gap-1 text-xs font-semibold text-slate-500 uppercase">
              <RealmTypeIcon realmType={opportunity.realm_type} />
              {opportunity.category}
            </span>
            {opportunity.access_state === 'unlocked' && (
              <span className="flex items-center gap-1 bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">
                Unlocked
              </span>
            )}
            {opportunity.access_state === 'locked' && (
              <span className="flex items-center gap-1 bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full text-xs font-medium">
                Upgrade for Premium
              </span>
            )}
          </div>

          {/* Location line */}
          <LocationLine
            city={opportunity.city}
            state={opportunity.state}
            geographicScope={opportunity.geographic_scope}
          />
        </div>

        {/* Feasibility Score */}
        <div
          className={`px-3 py-2 rounded-full flex-shrink-0 ${getFeasibilityColor(opportunity.feasibility_score ?? 0)}`}
        >
          <div className="text-2xl font-bold leading-none">
            {opportunity.feasibility_score ?? 0}
          </div>
        </div>
      </div>

      {/* ── Market Badges + Source Mix ── */}
      {hasBadgeRow && (
        <div className="flex items-center justify-between mb-3 gap-2 min-w-0">
          <div className="flex-1 min-w-0 overflow-hidden">
            <MarketBadges
              city={opportunity.city}
              state={opportunity.state}
              badges={badges}
              metrics={metrics}
              compact={false}
              maxBadges={3}
            />
          </div>
          {opportunity.contributing_sources && (
            <SourceMixIndicator
              contributingSources={opportunity.contributing_sources}
              maxDisplay={6}
            />
          )}
        </div>
      )}

      {/* ── Title ── */}
      <h3 className="font-semibold text-slate-900 text-lg mb-1 group-hover:text-emerald-700 transition-colors">
        {opportunity.ai_generated_title || opportunity.title}
      </h3>

      {/* ── Description ── */}
      <p className="text-sm text-slate-500 mb-4 line-clamp-2">
        {opportunity.description || opportunity.ai_summary || 'Analysis pending…'}
      </p>

      {/* ── Pain × Urgency × Growth row ── */}
      <div className="mb-4">
        <PainUrgencyRow
          painIntensity={opportunity.ai_pain_intensity}
          urgencyLevel={opportunity.ai_urgency_level}
          growthRate={opportunity.growth_rate}
          trendDirection={opportunity.macro_context?.trend_direction}
          validationCount={opportunity.validation_count}
          marketSize={
            opportunity.market_size
              ? formatMarketSize(opportunity.market_size)
              : undefined
          }
        />
      </div>

      {/* ── Macro Context Strip (standard variant only) ── */}
      {!isCompact && opportunity.macro_context && (
        <div className="mb-4">
          <MacroContextStrip context={opportunity.macro_context} />
        </div>
      )}

      {/* ── 4 P's Indicator (optional) ── */}
      {showFourPs && (
        <div className="mb-4 px-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-slate-500">Market Intelligence</span>
            {fourPsLoading && (
              <span className="text-xs text-slate-400">Loading…</span>
            )}
          </div>
          {fourPs ? (
            <FourPsIndicator scores={fourPs} size="md" />
          ) : !fourPsLoading ? (
            <div className="h-2 bg-slate-100 rounded-full" />
          ) : null}
        </div>
      )}

      {/* ── Actions Row ── */}
      <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleAnalyze}
            className="flex items-center gap-1 text-sm text-slate-600 hover:text-emerald-700 transition-colors"
            aria-label="View report"
          >
            <FileText className="w-4 h-4" />
            <span>Report</span>
          </button>

          <button
            onClick={handleSave}
            className={`flex items-center gap-1 text-sm transition-colors ${
              isSaved
                ? 'text-emerald-700'
                : 'text-slate-600 hover:text-emerald-700'
            }`}
            aria-label={isSaved ? 'Unsave' : 'Save'}
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
            <span>Save</span>
          </button>
        </div>

        <div className="flex items-center gap-1 text-sm text-slate-600 group-hover:text-emerald-700 transition-colors">
          <span>View full analysis</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
      </div>
    </div>
  )
}
