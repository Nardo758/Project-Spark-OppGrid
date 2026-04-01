import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'

export interface SavedOpportunity {
  id: number
  opportunity_id: number
  priority: number // 1-5 stars
  saved_at: string
}

export interface OpportunityCollection {
  id: number
  name: string
  description?: string
  color: string
  opportunity_count: number
  created_at: string
}

export interface OpportunityTag {
  id: number
  name: string
  color: string
}

export interface OpportunityNote {
  id: number
  content: string
  created_at: string
  updated_at: string
}

export function useSavedOpportunities(sortBy: 'priority' | 'date' | 'alpha' = 'priority') {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading, error } = useQuery<SavedOpportunity[]>({
    queryKey: ['saved-opportunities', sortBy],
    queryFn: async () => {
      const res = await fetch(`/api/v1/opportunities/saved?sort_by=${sortBy}`, {
        headers: headers(),
      })
      if (!res.ok) throw new Error('Failed to fetch saved opportunities')
      return res.json()
    },
    enabled: !!token,
  })

  return {
    saved: data || [],
    isLoading,
    error: error as Error | null,
  }
}

export function useSaveOpportunity() {
  const { token } = useAuthStore()
  const queryClient = useQueryClient()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const mutation = useMutation({
    mutationFn: async ({ opportunityId, priority }: { opportunityId: number; priority: number }) => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/save`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ priority }),
      })
      if (!res.ok) throw new Error('Failed to save opportunity')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-opportunities'] })
    },
  })

  return mutation
}

export function useCollections() {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading } = useQuery<OpportunityCollection[]>({
    queryKey: ['collections'],
    queryFn: async () => {
      const res = await fetch('/api/v1/opportunities/collections', {
        headers: headers(),
      })
      if (!res.ok) throw new Error('Failed to fetch collections')
      return res.json()
    },
    enabled: !!token,
  })

  return {
    collections: data || [],
    isLoading,
  }
}

export function useOpportunityTags() {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading } = useQuery<OpportunityTag[]>({
    queryKey: ['tags'],
    queryFn: async () => {
      const res = await fetch('/api/v1/opportunities/tags', {
        headers: headers(),
      })
      if (!res.ok) throw new Error('Failed to fetch tags')
      return res.json()
    },
    enabled: !!token,
  })

  return {
    tags: data || [],
    isLoading,
  }
}

export function useTagSuggestions() {
  const { data } = useQuery<OpportunityTag[]>({
    queryKey: ['tag-suggestions'],
    queryFn: async () => {
      const res = await fetch('/api/v1/opportunities/tags/suggestions')
      if (!res.ok) throw new Error('Failed to fetch suggestions')
      return res.json()
    },
  })

  return data || []
}

export function useOpportunityNotes(opportunityId: number) {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading } = useQuery<OpportunityNote[]>({
    queryKey: ['notes', opportunityId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/notes`, {
        headers: headers(),
      })
      if (!res.ok) throw new Error('Failed to fetch notes')
      return res.json()
    },
    enabled: !!token && !!opportunityId,
  })

  return {
    notes: data || [],
    isLoading,
  }
}

export function useSavedStatus(opportunityId: number) {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data } = useQuery({
    queryKey: ['saved-status', opportunityId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/saved-status`, {
        headers: headers(),
      })
      if (!res.ok) return { is_saved: false, priority: null }
      return res.json()
    },
    enabled: !!token && !!opportunityId,
  })

  return {
    isSaved: data?.is_saved || false,
    priority: data?.priority || 0,
  }
}
