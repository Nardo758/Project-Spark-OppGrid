export interface ValidateIdeaResult {
  success: boolean
  idea_description?: string
  recommendation?: string
  online_score?: number
  physical_score?: number
  pattern_analysis?: {
    market_size?: string
    competition_level?: string
    growth_trajectory?: string
    risk_factors?: string[]
  }
  viability_report?: {
    summary?: string
    strengths?: string[]
    weaknesses?: string[]
    opportunities?: string[]
    threats?: string[]
    confidence_score?: number
  }
  similar_opportunities?: Array<{
    id: number
    title: string
    category?: string
    score: number
  }>
  processing_time_ms?: number
  from_cache?: boolean
  error?: string
}

export interface SearchIdeasResult {
  success: boolean
  opportunities?: Array<{
    id: number
    title: string
    description?: string
    category: string
    score?: number
    source?: string
    created_at?: string
  }>
  trends?: Array<{
    id?: number
    name: string
    momentum?: string
    relevance?: number
    related_count?: number
  }>
  synthesis?: {
    summary?: string
    key_themes?: string[]
    market_signals?: string[]
  }
  total_count?: number
  processing_time_ms?: number
  error?: string
}

export interface Pin {
  id: number
  lat: number
  lng: number
  name: string
  rating?: number
  reviews?: number
  source: string
  popup?: string
}

export interface HeatmapPoint {
  lat: number
  lng: number
  intensity: number
  title?: string
  source: string
}

export interface MapData {
  city?: string
  bounds?: {
    north: number
    south: number
    east: number
    west: number
  }
  center?: {
    lat: number
    lng: number
  }
  layers: {
    pins: { type?: string; data: Pin[]; count: number }
    heatmap: { type?: string; data: HeatmapPoint[]; count: number }
    polygons: { type?: string; data: unknown[]; count: number }
  }
  totalFeatures: number
}

export interface GeoAnalysis {
  demographics?: {
    population?: number
    median_income?: number
    median_age?: number
    households?: number
    income_brackets?: Record<string, number>
  }
  competitors?: Array<{
    name: string
    address?: string
    lat: number
    lng: number
    rating?: number
    reviews?: number
  }>
  market_indicators?: {
    growth_rate?: number
    business_density?: number
    consumer_spending?: number
  }
  trade_area?: {
    center?: { lat: number; lng: number }
    radius_miles?: number
  }
}

export interface MarketReport {
  market_score?: number
  competition_level?: string
  competitor_count?: number
  demographics_summary?: {
    median_income?: number
    population?: number
    median_age?: number
  }
  key_insights?: string[]
  recommendation?: string
  executive_summary?: string
}

export interface SiteRecommendation {
  type: string
  priority: string
  reason: string
}

export interface IdentifyLocationResult {
  success: boolean
  city?: string
  state?: string
  business_description?: string
  inferred_category?: string
  geo_analysis?: GeoAnalysis
  market_report?: MarketReport
  site_recommendations?: SiteRecommendation[]
  map_data?: MapData
  from_cache?: boolean
  cache_hit_count?: number
  processing_time_ms?: number
  error?: string
}

export interface MatchingLocation {
  name: string
  city: string
  state: string
  lat: number
  lng: number
  address?: string
  similarity_score: number
  demographics_match: number
  competition_match: number
  population?: number
  median_income?: number
  competition_count?: number
  key_factors: string[]
}

export interface CloneSuccessResult {
  success: boolean
  source_business?: {
    name: string
    address: string
    lat?: number
    lng?: number
    category?: string
    rating?: number
    reviews_count?: number
  }
  matching_locations?: MatchingLocation[]
  analysis_radius_miles: number
  trade_area_data?: GeoAnalysis
  processing_time_ms?: number
  error?: string
}

export interface DeepCloneResult {
  success: boolean
  source_business?: {
    name: string
    address: string
    lat?: number
    lng?: number
  }
  target_city?: string
  three_mile_analysis?: {
    population: number
    median_income: number
    competition_count: number
  }
  five_mile_analysis?: {
    population: number
    median_income: number
    competition_count: number
  }
  match_score?: number
  key_factors?: string[]
  processing_time_ms?: number
  requires_payment?: boolean
  error?: string
}

export interface ConsultantStats {
  validate_count: number
  search_count: number
  location_count: number
  clone_count: number
  total_reports: number
  reports_this_month: number
}
