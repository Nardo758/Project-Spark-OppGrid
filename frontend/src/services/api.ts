/**
 * API Client for OppGrid Discovery Feed
 * Handles all opportunity-related API calls
 */

import {
  OpportunityFilters,
  OpportunitiesResponse,
  Opportunity,
  SavedSearch,
  SavedSearchCreate,
  QuickValidationResponse,
} from '../types/opportunity'

const API_BASE = '/api/v1'

/**
 * Get auth token from localStorage
 */
function getAuthToken(): string | null {
  try {
    return localStorage.getItem('token') || localStorage.getItem('access_token')
  } catch {
    return null
  }
}

/**
 * Build fetch headers with auth
 */
function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }

  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return headers
}

/**
 * Handle API response errors
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text().catch(() => 'Unknown error')
    throw new Error(`API Error (${response.status}): ${error}`)
  }

  try {
    return await response.json()
  } catch {
    throw new Error('Invalid JSON response')
  }
}

/**
 * Build query string from filters and pagination
 */
function buildQueryString(
  filters: OpportunityFilters,
  page: number,
  pageSize: number
): string {
  const params = new URLSearchParams()

  // Pagination
  params.set('skip', ((page - 1) * pageSize).toString())
  params.set('limit', pageSize.toString())

  // Filters
  if (filters.search) params.set('search', filters.search)
  if (filters.category) params.set('category', filters.category)
  if (filters.geographic_scope) params.set('geographic_scope', filters.geographic_scope)
  if (filters.country) params.set('country', filters.country)
  if (filters.completion_status) params.set('completion_status', filters.completion_status)
  if (filters.realm_type) params.set('realm_type', filters.realm_type)
  if (filters.min_feasibility !== null && filters.min_feasibility !== undefined) {
    params.set('min_feasibility', filters.min_feasibility.toString())
  }
  if (filters.max_feasibility !== null && filters.max_feasibility !== undefined) {
    params.set('max_feasibility', filters.max_feasibility.toString())
  }
  if (filters.min_validations !== null && filters.min_validations !== undefined) {
    params.set('min_validations', filters.min_validations.toString())
  }
  if (filters.max_age_days !== null && filters.max_age_days !== undefined) {
    params.set('max_age_days', filters.max_age_days.toString())
  }
  if (filters.sort_by) params.set('sort_by', filters.sort_by)
  if (filters.my_access_only) {
    params.set('my_access_only', 'true')
  }

  return params.toString()
}

/**
 * Fetch opportunities with filters and pagination
 */
export async function fetchOpportunities(
  filters: OpportunityFilters,
  page: number = 1,
  pageSize: number = 20
): Promise<OpportunitiesResponse> {
  const queryString = buildQueryString(filters, page, pageSize)
  const url = `${API_BASE}/opportunities/?${queryString}`

  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })

  return handleResponse<OpportunitiesResponse>(response)
}

/**
 * Fetch personalized recommended opportunities
 */
export async function fetchRecommendedOpportunities(
  limit: number = 10
): Promise<Opportunity[]> {
  const url = `${API_BASE}/opportunities/recommended?limit=${limit}`

  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })

  const data = await handleResponse<{ opportunities: Opportunity[]; total: number; user_interests: string[] }>(response)
  return Array.isArray(data) ? data : (data?.opportunities ?? [])
}

/**
 * Quick validate an opportunity (optimistic update support)
 */
export async function quickValidateOpportunity(
  opportunityId: number
): Promise<QuickValidationResponse> {
  const url = `${API_BASE}/validations`

  const response = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ opportunity_id: opportunityId }),
  })

  return handleResponse<QuickValidationResponse>(response)
}

/**
 * Remove validation from an opportunity
 */
export async function unvalidateOpportunity(
  opportunityId: number
): Promise<void> {
  const url = `${API_BASE}/validations/${opportunityId}`

  const response = await fetch(url, {
    method: 'DELETE',
    headers: getHeaders(),
  })

  if (!response.ok) {
    throw new Error(`Failed to remove validation: ${response.statusText}`)
  }
}

/**
 * Save a search with notification preferences
 */
export async function saveSearch(
  searchData: SavedSearchCreate
): Promise<SavedSearch> {
  const url = `${API_BASE}/saved-searches/`

  const response = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(searchData),
  })

  return handleResponse<SavedSearch>(response)
}

/**
 * Get user's saved searches
 */
export async function fetchSavedSearches(): Promise<SavedSearch[]> {
  const url = `${API_BASE}/saved-searches/`

  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })

  return handleResponse<SavedSearch[]>(response)
}

/**
 * Delete a saved search
 */
export async function deleteSavedSearch(searchId: number): Promise<void> {
  const url = `${API_BASE}/saved-searches/${searchId}`

  const response = await fetch(url, {
    method: 'DELETE',
    headers: getHeaders(),
  })

  if (!response.ok) {
    throw new Error(`Failed to delete saved search: ${response.statusText}`)
  }
}

/**
 * Load opportunities from a saved search
 */
export async function loadSavedSearch(
  searchId: number,
  page: number = 1,
  pageSize: number = 20
): Promise<OpportunitiesResponse> {
  // First, get the saved search to retrieve filters
  const savedSearches = await fetchSavedSearches()
  const savedSearch = savedSearches.find(s => s.id === searchId)

  if (!savedSearch) {
    throw new Error('Saved search not found')
  }

  // Then fetch opportunities with those filters
  return fetchOpportunities(savedSearch.filters, page, pageSize)
}

/**
 * Fetch a single opportunity by ID
 */
export async function fetchOpportunityById(id: number): Promise<Opportunity> {
  const url = `${API_BASE}/opportunities/${id}`

  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })

  return handleResponse<Opportunity>(response)
}

/**
 * Save/bookmark an opportunity
 */
export async function saveOpportunity(opportunityId: number): Promise<void> {
  const url = `${API_BASE}/saved-opportunities`

  const response = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ opportunity_id: opportunityId }),
  })

  if (!response.ok) {
    throw new Error(`Failed to save opportunity: ${response.statusText}`)
  }
}

/**
 * Unsave/unbookmark an opportunity
 */
export async function unsaveOpportunity(opportunityId: number): Promise<void> {
  const url = `${API_BASE}/saved-opportunities/${opportunityId}`

  const response = await fetch(url, {
    method: 'DELETE',
    headers: getHeaders(),
  })

  if (!response.ok) {
    throw new Error(`Failed to unsave opportunity: ${response.statusText}`)
  }
}
