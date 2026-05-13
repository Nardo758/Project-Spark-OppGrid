/**
 * OpportunityCard — Enriched
 *
 * Surfaces confidence tier, source mix, location, pain/urgency, and macro
 * context in addition to existing fields. Brand-aligned to emerald/navy/slate.
 *
 * variant="standard" — discovery feed (default)
 * variant="compact"  — sidebars, saved list (strips macro strip and pain/urgency)
 *
 * All new fields are optional and degrade gracefully when null.
 */
import { FileText, Bookmark } from 'lucide-react'
import { useState, useEffect } from 'react'
import FourPsIndicator from '../FourPs/FourPsIndicator'
import MarketBadges, { type MarketBadge, type CompositeMetrics } from './MarketBadges'
import ConfidenceTierBadge, { getTierBorderClass } from './ConfidenceTierBadge'
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

interface ContributingSources {
  [source: string]: number
  total_sources?: number
  total_signals?: number
}

interface MacroContext {
  unemployment_delta_90d?: number
  population_5y_delta?:   number
  median_income?:         number
  trend_direction?:       'rising' | 'falling' | 'flat'
  highlight?:             string
}

export interface OpportunityCardData {
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
  // Enrichment fields
  confidence_tier?: 'goldmine' | 'validated' | 'weak_signal' | null
  contributing_sources?: ContributingSources | null
  macro_context?: MacroContext | null
  realm_type?: 'physical' | 'digital' | 'both' | null
  geographic_scope?: string | null
  city?: string | null
  state?: string | null
  ai_pain_intensity?: number | null
  ai_urgency_level?: string | null
  ai_competition_level?: string | null
  // Optional pre-loaded composite data
  four_ps_scores?: FourPsScores
  market_badges?: MarketBadge[]
  composite_metrics?: CompositeMetrics
}

interface OpportunityCardProps {
  opportunity: OpportunityCardData
  variant?: 'standard' | 'compact'
  userTier?: string
  onValidate?: (id: number) => void
  onSave?: (id: number) => void
  onAnalyze?: (id: number) => void
  onShare?: (id: number) => void
  isValidated?: boolean
  isSaved?: boolean
  className?: string
  showFourPs?: boolean
  showMarketBadges?: boolean
  fourPsScores?: FourPsScores
  marketBadges?: MarketBadge[]
  compositeMetrics?: CompositeMetrics
}

export default function OpportunityCard({
  opportunity,
  variant = 'standard',
  onSave,
  onAnalyze,
  isSaved: externalIsSaved,
  className = '',
  showFourPs = false,
  fourPsScores,
  showMarketBadges = true,
  marketBadges,
  compositeMetrics,
}: OpportunityCardProps) {
  const [isSaved, setIsSaved] = useState(externalIsSaved || opportunity.user_saved || false)
  const [fourPs, setFourPs] = useState<FourPsScores | null>(
    fourPsScores || opportunity.four_ps_scores || null,
  )
  const [fourPsLoading, setFourPsLoading] = useState(false)

  const badges  = marketBadges  || opportunity.market_badges
  const metrics = compositeMetrics || opportunity.composite_metrics

  const tier        = opportunity.confidence_tier
  const borderClass = getTierBorderClass(tier)
  const isCompact   = variant === 'compact'

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

  const handleSave = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsSaved(!isSaved)
    onSave?.(opportunity.id)
  }

  const handleAnalyze = (e: React.MouseEvent) => {
    e.stopPropagation()
    onAnalyze?.(opportunity.id)
  }

  return (
    <div
      className={`bg-white p-5 rounded-xl border-2 transition-all cursor-pointer group ${borderClass} ${className}`}
      onClick={() => (window.location.href = `/opportunity/${opportunity.id}`)}
    >
      {/* ── HEADER ROW: Tier · Category · Realm · Location · Score ── */}
      <div className="flex items-start justify-between mb-3 gap-2">
        <div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
          <ConfidenceTierBadge tier={tier ?? undefined} />
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            {opportunity.category}
          </span>
          <RealmTypeIcon realmType={opportunity.realm_type ?? undefined} />
          <LocationLine
            city={opportunity.city ?? undefined}
            state={opportunity.state ?? undefined}
            geographicScope={opportunity.geographic_scope ?? undefined}
          />
          {opportunity.access_state === 'unlocked' && (
            <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">
              Unlocked
            </span>
          )}
          {opportunity.access_state === 'locked' && (
            <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded-full text-xs font-medium">
              Upgrade for Premium
            </span>
          )}
        </div>

        {/* Feasibility Score */}
        <div className="bg-emerald-100 text-emerald-700 px-3 py-2 rounded-full flex-shrink-0">
          <div className="text-2xl font-bold leading-none">
            {opportunity.feasibility_score ?? 0}
          </div>
        </div>
      </div>

      {/* ── BADGES + SOURCE MIX ROW ── */}
      {(showMarketBadges || opportunity.contributing_sources) && (
        <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
          {showMarketBadges && (badges || metrics || (opportunity.city && opportunity.state)) ? (
            <MarketBadges
              city={opportunity.city ?? undefined}
              state={opportunity.state ?? undefined}
              badges={badges}
              metrics={metrics}
              compact={false}
              maxBadges={3}
            />
          ) : <span />}

          <SourceMixIndicator
            contributingSources={opportunity.contributing_sources}
            maxDisplay={5}
          />
        </div>
      )}

      {/* ── TITLE ── */}
      <h3 className="font-semibold text-slate-900 text-lg mb-1 group-hover:text-emerald-700 transition-colors">
        {opportunity.title}
      </h3>

      {/* ── DESCRIPTION ── */}
      <p className="text-sm text-slate-500 mb-4 line-clamp-2">
        {opportunity.description || opportunity.ai_summary || 'Analysis pending...'}
      </p>

      {/* ── METRICS ROW (Pain × Urgency × Growth) ── */}
      <PainUrgencyRow
        painIntensity={opportunity.ai_pain_intensity ?? null}
        urgencyLevel={opportunity.ai_urgency_level ?? null}
        growthRate={opportunity.growth_rate ?? null}
        trendDirection={opportunity.macro_context?.trend_direction ?? null}
        validationCount={opportunity.validation_count ?? null}
        marketSize={opportunity.market_size ?? null}
      />

      {/* ── 4 P's Indicator (optional, unchanged) ── */}
      {showFourPs && (
        <div className="mb-4 px-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-slate-500">Market Intelligence</span>
            {fourPsLoading && <span className="text-xs text-slate-400">Loading...</span>}
          </div>
          {fourPs ? (
            <FourPsIndicator scores={fourPs} size="md" />
          ) : !fourPsLoading ? (
            <div className="h-2 bg-slate-100 rounded-full" />
          ) : null}
        </div>
      )}

      {/* ── MACRO CONTEXT STRIP (skip in compact) ── */}
      {!isCompact && (
        <MacroContextStrip context={opportunity.macro_context} />
      )}

      {/* ── ACTIONS ROW ── */}
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
              isSaved ? 'text-emerald-700' : 'text-slate-600 hover:text-emerald-700'
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  )
}
