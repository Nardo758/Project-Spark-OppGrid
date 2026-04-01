import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'

export interface OpportunityLifecycle {
  id: number
  user_id: number
  opportunity_id: number
  current_state: string
  progress_percent: number
  discovered_at: string
  saved_at?: string
  analyzing_at?: string
  planning_at?: string
  executing_at?: string
  launched_at?: string
  paused_at?: string
  archived_at?: string
  notes?: string
  updated_at: string
}

export interface StateTransition {
  id: number
  lifecycle_id: number
  from_state: string
  to_state: string
  reason?: string
  transitioned_at: string
}

export interface Milestone {
  id: number
  lifecycle_id: number
  state: string
  title: string
  description?: string
  is_completed: boolean
  order: number
  completed_at?: string
}

export interface LifecycleSummary {
  total_opportunities: number
  by_state: Record<string, number>
  recent_transitions: StateTransition[]
  avg_progress: number
}

export const LIFECYCLE_STATES = [
  { id: 'discovered', label: 'Discovered', icon: '🔍', color: '#94a3b8' },
  { id: 'saved', label: 'Saved', icon: '❤️', color: '#ef4444' },
  { id: 'analyzing', label: 'Analyzing', icon: '📊', color: '#f59e0b' },
  { id: 'planning', label: 'Planning', icon: '📋', color: '#8b5cf6' },
  { id: 'executing', label: 'Executing', icon: '⚙️', color: '#3b82f6' },
  { id: 'launched', label: 'Launched', icon: '🚀', color: '#10b981' },
  { id: 'paused', label: 'Paused', icon: '⏸️', color: '#f97316' },
  { id: 'archived', label: 'Archived', icon: '📦', color: '#6b7280' },
]

export function useOpportunityLifecycle(opportunityId: number) {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading, error } = useQuery<OpportunityLifecycle>({
    queryKey: ['lifecycle', opportunityId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/lifecycle`, {
        headers: headers(),
      })
      if (!res.ok) throw new Error('Failed to fetch lifecycle')
      return res.json()
    },
    enabled: !!token && !!opportunityId,
  })

  return {
    lifecycle: data,
    isLoading,
    error: error as Error | null,
  }
}

export function useTransitionLifecycleState() {
  const { token } = useAuthStore()
  const queryClient = useQueryClient()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const mutation = useMutation({
    mutationFn: async ({
      opportunityId,
      toState,
      reason,
    }: {
      opportunityId: number
      toState: string
      reason?: string
    }) => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/lifecycle/transition`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ to_state: toState, reason }),
      })
      if (!res.ok) throw new Error('Failed to transition state')
      return res.json()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['lifecycle', variables.opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['transitions', variables.opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['lifecycle-summary'] })
    },
  })

  return mutation
}

export function useLifecycleTransitions(opportunityId: number) {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading } = useQuery<StateTransition[]>({
    queryKey: ['transitions', opportunityId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/lifecycle/transitions`, {
        headers: headers(),
      })
      if (!res.ok) return []
      return res.json()
    },
    enabled: !!token && !!opportunityId,
  })

  return {
    transitions: data || [],
    isLoading,
  }
}

export function useUpdateLifecycleProgress() {
  const { token } = useAuthStore()
  const queryClient = useQueryClient()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const mutation = useMutation({
    mutationFn: async ({
      opportunityId,
      progress,
    }: {
      opportunityId: number
      progress: number
    }) => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/lifecycle/progress`, {
        method: 'PATCH',
        headers: headers(),
        body: JSON.stringify({ progress_percent: progress }),
      })
      if (!res.ok) throw new Error('Failed to update progress')
      return res.json()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['lifecycle', variables.opportunityId] })
    },
  })

  return mutation
}

export function useLifecycleMilestones(opportunityId: number, state?: string) {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading } = useQuery<Milestone[]>({
    queryKey: ['milestones', opportunityId, state],
    queryFn: async () => {
      const url = state
        ? `/api/v1/opportunities/${opportunityId}/lifecycle/milestones?state=${state}`
        : `/api/v1/opportunities/${opportunityId}/lifecycle/milestones`
      const res = await fetch(url, {
        headers: headers(),
      })
      if (!res.ok) return []
      return res.json()
    },
    enabled: !!token && !!opportunityId,
  })

  return {
    milestones: data || [],
    isLoading,
  }
}

export function useCompleteMilestone() {
  const { token } = useAuthStore()
  const queryClient = useQueryClient()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const mutation = useMutation({
    mutationFn: async ({
      opportunityId,
      milestoneId,
      isCompleted,
    }: {
      opportunityId: number
      milestoneId: number
      isCompleted: boolean
    }) => {
      const res = await fetch(
        `/api/v1/opportunities/${opportunityId}/lifecycle/milestones/${milestoneId}`,
        {
          method: 'PATCH',
          headers: headers(),
          body: JSON.stringify({ is_completed: isCompleted }),
        }
      )
      if (!res.ok) throw new Error('Failed to update milestone')
      return res.json()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['milestones', variables.opportunityId] })
    },
  })

  return mutation
}

export function useLifecycleSummary() {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading } = useQuery<LifecycleSummary>({
    queryKey: ['lifecycle-summary'],
    queryFn: async () => {
      const res = await fetch('/api/v1/opportunities/user/lifecycle-summary', {
        headers: headers(),
      })
      if (!res.ok) throw new Error('Failed to fetch summary')
      return res.json()
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    summary: data,
    isLoading,
  }
}
