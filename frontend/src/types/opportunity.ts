// Opportunity types for the Discovery Feed

export interface Opportunity {
  id: number
  title: string
  description: string
  category?: string
  geographic_scope?: string
  country?: string
  feasibility_score: number
  validation_count: number
  growth_rate?: number
  market_size?: string
  status: string
  created_at: string
  updated_at: string
  
  // Personalization fields
  match_score?: number
  user_validated?: boolean
  match_reasons?: MatchReason[]
  social_proof?: SocialProof
}

export interface MatchReason {
  type: 'skills' | 'category' | 'location' | 'feasibility' | 'validation'
  label: string
  score: number
  description: string
}

export interface SocialProof {
  similar_users_validated: number
  similar_users_text?: string
  expert_validation_count?: number
  trending_indicator?: boolean
}

export interface RecommendedOpportunitiesResponse {
  opportunities: Opportunity[]
  total: number
  personalization_metadata?: {
    user_interests: string[]
    recommendation_strategy: string
  }
}

export interface OpportunitiesResponse {
  opportunities: Opportunity[]
  total: number
  page: number
  page_size: number
  has_more?: boolean
  is_gated: boolean
  gated_message: string | null
  full_total: number
}

export interface OpportunityFilters {
  search?: string
  category?: string
  geographic_scope?: string
  country?: string
  completion_status?: string
  realm_type?: string
  min_feasibility?: number | null
  max_feasibility?: number | null
  min_validations?: number | null
  max_age_days?: number | null
  sort_by?: 'recent' | 'trending' | 'validated' | 'market' | 'feasibility' | 'recommended'
  my_access_only?: boolean
}

export interface SavedSearch {
  id: number
  name: string
  filters: OpportunityFilters
  notification_prefs: {
    email: boolean
    push: boolean
    frequency: 'instant' | 'daily' | 'weekly'
  }
  created_at: string
  updated_at: string
}

export interface SavedSearchCreate {
  name: string
  filters: OpportunityFilters
  notification_prefs: {
    email: boolean
    push: boolean
    frequency: 'instant' | 'daily' | 'weekly'
  }
}

export interface QuickValidationResponse {
  success: boolean
  validation_count: number
  user_validated: boolean
}
