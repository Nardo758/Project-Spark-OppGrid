import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'

export interface ReportUsageStatus {
  user_id: number
  total_generated_this_month: number
  free_allocation: number
  paid_report_count: number
  remaining_free: number
  usage_percent: number
  tier: string
  next_reset_date: string
}

export function useReportQuota() {
  const { token } = useAuthStore()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data, isLoading, error } = useQuery<ReportUsageStatus>({
    queryKey: ['report-quota'],
    queryFn: async () => {
      const res = await fetch('/api/v1/report-pricing/usage', {
        method: 'GET',
        headers: headers(),
      })

      if (!res.ok) {
        throw new Error('Failed to fetch report quota')
      }

      return res.json()
    },
    // Only run if authenticated
    enabled: !!token,
    // Refetch every 5 minutes
    staleTime: 5 * 60 * 1000,
  })

  return {
    quota: data,
    isLoading,
    error: error as Error | null,
    remainingFree: data?.remaining_free ?? 0,
    usagePercent: data?.usage_percent ?? 0,
    tier: data?.tier ?? 'explorer',
  }
}
