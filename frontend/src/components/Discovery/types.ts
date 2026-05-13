/**
 * Type definitions for Discovery Feed components
 */

export interface MacroContext {
  unemployment_delta_90d?: number
  population_5y_delta?:   number
  median_income?:         number
  trend_direction?:       'rising' | 'falling' | 'flat'
  highlight?:             string
}

export interface ContributingSources {
  total_sources?: number
  total_signals?: number
  [key: string]: number | undefined
}

export interface Opportunity {
  id: number
  title: string
  description?: string
  category?: string
  validation_count?: number
  growth_rate?: number
  severity?: number
  feasibility_score?: number
  market_size?: string
  geographic_scope?: string
  city?: string
  state?: string
  region?: string
  country?: string
  created_at: string
  ai_generated_title?: string
  ai_problem_statement?: string
  ai_summary?: string
  ai_opportunity_score?: number
  ai_competition_level?: 'low' | 'medium' | 'high'
  ai_market_size_estimate?: string
  ai_analyzed?: boolean
  status?: string
  moderation_status?: string
  user_validated?: boolean
  user_saved?: boolean
  match_score?: number

  // Enrichment — Group 1 (available immediately, no migration needed)
  realm_type?: string
  ai_pain_intensity?: number | null
  ai_urgency_level?: string | null
  access_state?: 'unlocked' | 'locked' | 'preview'

  // Enrichment — Group 2 (Spec 1 migration, degrade gracefully when null)
  confidence_tier?: string | null
  contributing_sources?: ContributingSources | null
  macro_context?: MacroContext | null

  // Optional pre-loaded auxiliary data
  four_ps_scores?: {
    product: number
    price: number
    place: number
    promotion: number
  }
  market_badges?: unknown[]
  composite_metrics?: unknown
}

export interface FilterState {
  search: string
  category: string | null
  feasibility: string | null
  location: string | null
  sortBy: 'recent' | 'trending' | 'validated' | 'market' | 'feasibility' | 'recommended'
  maxDaysOld: number | null
  myAccessOnly: boolean
}

export interface PaginationState {
  currentPage: number
  pageSize: number
  totalItems: number
  totalPages: number
}

export type ViewMode = 'grid' | 'list'

export type UserTier = 'free' | 'pro' | 'business' | 'enterprise'

export interface FreshnessBadge {
  icon: string
  label: string
  color: string
  tierRequired: UserTier
}
