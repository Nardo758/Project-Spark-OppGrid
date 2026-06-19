export type ConsultantPath = 'validate' | 'search' | 'location' | 'clone'
export type ReportType = 'feasibility' | 'market-analysis' | 'strategic-assessment' | 'pestle' | 'business-plan' | 'financials' | 'pitch-deck'
export type BusinessType = 'specific_business' | 'retail' | 'multifamily' | 'hospitality'
export type StudioMode = 'consultant' | 'business-plan' | 'financials' | 'pitch-deck' | 'feasibility' | 'market-analysis' | 'strategic-assessment' | 'pestle'

export type MatchingLocation = {
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

export type Competitor = {
  name: string
  lat?: number
  lng?: number
  rating?: number
  reviews?: number
  address?: string
}

export type MapData = {
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
    pins: { data: any[]; count: number }
    heatmap: { data: any[]; count: number }
    polygons: { data: any[]; count: number }
  }
  totalFeatures: number
  city?: string
}

export type ValidateIdeaResult = {
  success: boolean
  recommendation?: string
  online_score?: number
  physical_score?: number
  viability_report?: {
    executive_summary?: string
    strengths?: string[]
    weaknesses?: string[]
    opportunities?: string[]
    threats?: string[]
    confidence_score?: number
  }
  similar_opportunities?: Array<{ id: number; title: string; score: number }>
  processing_time_ms?: number
}

export type SearchIdeasResult = {
  success: boolean
  opportunities?: Array<{
    id: number
    title: string
    description?: string
    category?: string
    score?: number
    created_at?: string
  }>
  trends?: Array<{
    id: number
    name: string
    strength: number
    description?: string
    growth_rate?: number
    opportunities_count: number
  }>
  synthesis?: {
    summary?: string
    top_insight?: string
    recommendations?: string[]
  }
  total_count?: number
  processing_time_ms?: number
}

export type LocationResult = {
  success: boolean
  city?: string
  business_description?: string
  inferred_category?: string
  geo_analysis?: {
    market_density?: string
    competition_level?: string
    competitor_count?: number
    white_space_score?: number
    trade_area_radius_miles?: number
    competitors?: Competitor[]
    demographics?: {
      population?: number | string
      median_income?: number | string
      median_age?: number | string
      unemployment_rate?: string
      median_home_value?: string
    }
  }
  market_report?: {
    executive_summary?: string
    market_conditions?: string
    key_factors?: string[]
  }
  site_recommendations?: Array<{
    type: string
    priority: string
    reason: string
  }>
  map_data?: {
    city?: string
    center?: { lat: number; lng: number }
    layers?: {
      pins?: { type?: string; data?: any[]; count?: number }
      heatmap?: { type?: string; data?: any[]; count?: number }
      polygons?: { type?: string; data?: any[]; count?: number }
    }
    totalFeatures?: number
  }
  from_cache?: boolean
  processing_time_ms?: number
}

export type CloneSuccessResult = {
  success: boolean
  source_business?: {
    name: string
    address: string
    category: string
    success_factors: string[]
    demographics: Record<string, any>
  }
  matching_locations?: MatchingLocation[]
  analysis_radius_miles: number
  processing_time_ms?: number
  error?: string
}

export type AnalysisContext = {
  type: 'validate' | 'search' | 'location' | 'clone'
  title: string
  summary: string
  data: Record<string, any>
}

export const consultantPaths = [
  { 
    id: 'validate' as ConsultantPath, 
    name: 'Validate Idea', 
    description: 'Online vs Physical decision engine',
  },
  { 
    id: 'search' as ConsultantPath, 
    name: 'Search Ideas', 
    description: 'Database exploration with trend detection',
  },
  { 
    id: 'location' as ConsultantPath, 
    name: 'Identify Location', 
    description: 'Geographic intelligence for site selection',
  },
  { 
    id: 'clone' as ConsultantPath, 
    name: 'Clone Success', 
    description: 'Replicate a successful business model',
  },
]

export const businessTypes = [
  { id: 'specific_business' as BusinessType, name: 'Specific Business', description: 'Targeted business analysis' },
  { id: 'retail' as BusinessType, name: 'Retail', description: 'Retail location analysis' },
  { id: 'multifamily' as BusinessType, name: 'Multifamily', description: 'Multifamily housing' },
  { id: 'hospitality' as BusinessType, name: 'Hospitality', description: 'Hotels & restaurants' },
]

export function formatReportType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return `${Math.floor(diffDays / 30)} months ago`
}
