import { useAuthStore } from '@/stores/authStore'

export interface ApiResponse<T> {
  data: T | null
  error: string | null
  status: number
}

export function useConsultantApi() {
  const token = useAuthStore((state) => state.token)

  const authFetch = async <T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> => {
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
      }

      if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
      }

      const res = await fetch(endpoint, {
        ...options,
        headers,
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        return {
          data: null,
          error: errorData.detail || `Request failed with status ${res.status}`,
          status: res.status,
        }
      }

      const data = await res.json()
      return { data, error: null, status: res.status }
    } catch (err) {
      return {
        data: null,
        error: err instanceof Error ? err.message : 'Network error',
        status: 0,
      }
    }
  }

  const validateIdea = async (ideaDescription: string, businessContext?: Record<string, boolean>) => {
    return authFetch<ValidateIdeaResult>('/api/v1/consultant/validate-idea', {
      method: 'POST',
      body: JSON.stringify({ idea_description: ideaDescription, business_context: businessContext }),
    })
  }

  const searchIdeas = async (query?: string, category?: string) => {
    return authFetch<SearchIdeasResult>('/api/v1/consultant/search-ideas', {
      method: 'POST',
      body: JSON.stringify({ query, category }),
    })
  }

  const identifyLocation = async (city: string, businessDescription: string) => {
    return authFetch<LocationResult>('/api/v1/consultant/identify-location', {
      method: 'POST',
      body: JSON.stringify({ city, business_description: businessDescription }),
    })
  }

  const cloneSuccess = async (data: CloneSuccessInput) => {
    return authFetch<CloneSuccessResult>('/api/v1/consultant/clone-success', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  const getConsultantStats = async () => {
    return authFetch<ConsultantStats>('/api/v1/consultant/stats', {
      method: 'GET',
    })
  }

  return {
    authFetch,
    validateIdea,
    searchIdeas,
    identifyLocation,
    cloneSuccess,
    getConsultantStats,
  }
}

export interface ValidateIdeaResult {
  success: boolean
  analysis: {
    viability_score: number
    market_size: string
    competition_level: string
    key_risks: string[]
    opportunities: string[]
    recommended_next_steps: string[]
    summary: string
  }
  cached?: boolean
}

export interface SearchIdeasResult {
  opportunities: Array<{
    id: number
    title: string
    description: string
    category: string
    score: number
  }>
  total: number
}

export interface LocationResult {
  success: boolean
  city: string
  state: string
  coordinates: { lat: number; lng: number }
  demographics: Record<string, unknown>
  market_analysis: string
  recommendations: string[]
}

export interface CloneSuccessInput {
  business_name: string
  business_address: string
  target_city?: string
  target_state?: string
  radius_miles: number
}

export interface CloneSuccessResult {
  success: boolean
  original_business: {
    name: string
    address: string
    rating: number
    reviews_count: number
  }
  locations: Array<{
    city: string
    state: string
    score: number
    demographics: Record<string, unknown>
    competition: string
  }>
  analysis: string
}

export interface ConsultantStats {
  validations_count: number
  searches_count: number
  locations_count: number
  clones_count: number
  reports_generated: number
}
