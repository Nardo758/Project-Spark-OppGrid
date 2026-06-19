import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/authStore'

export type ReportType = 
  | 'business-plan'
  | 'financials'
  | 'pitch-deck'
  | 'market-analysis'
  | 'strategic-assessment'
  | 'pestle'
  | 'feasibility'

export interface Report {
  id: string
  type: ReportType
  title: string
  status: 'pending' | 'generating' | 'completed' | 'failed'
  content?: string
  created_at: string
  context?: Record<string, unknown>
  source_feature?: 'validate' | 'search' | 'location' | 'clone'
}

export interface GenerateReportInput {
  type: ReportType
  context: Record<string, unknown>
  source_feature: 'validate' | 'search' | 'location' | 'clone'
}

export function useReports() {
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const queryClient = useQueryClient()
  const [generatingReportId, setGeneratingReportId] = useState<string | null>(null)

  const authHeaders = useCallback(() => {
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }
    return headers
  }, [token])

  const reportsQuery = useQuery({
    queryKey: ['user-reports'],
    queryFn: async () => {
      const res = await fetch('/api/v1/generated-reports', {
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error('Failed to fetch reports')
      const data = await res.json()
      return (data.reports || []).map((r: Record<string, unknown>) => ({
        id: String(r.id),
        type: r.report_type as ReportType,
        title: r.title as string,
        status: r.status as Report['status'],
        content: r.content as string | undefined,
        created_at: r.created_at as string,
        context: r.context as Record<string, unknown> | undefined,
        source_feature: r.source_feature as Report['source_feature'],
      })) as Report[]
    },
    enabled: !!token,
  })

  const generateMutation = useMutation({
    mutationFn: async (input: GenerateReportInput) => {
      const res = await fetch('/api/v1/generated-reports/generate', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(input),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to generate report')
      }
      return res.json() as Promise<Report>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-reports'] })
      setGeneratingReportId(null)
    },
    onError: () => {
      setGeneratingReportId(null)
    },
  })

  const generateReport = useCallback(
    (type: ReportType, context: Record<string, unknown>, sourceFeature: 'validate' | 'search' | 'location' | 'clone') => {
      const tempId = `temp-${Date.now()}`
      setGeneratingReportId(tempId)
      return generateMutation.mutateAsync({ type, context, source_feature: sourceFeature })
    },
    [generateMutation]
  )

  const downloadReport = useCallback(
    async (reportId: string) => {
      const res = await fetch(`/api/v1/generated-reports/${reportId}/download`, {
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error('Failed to download report')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${reportId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
    [authHeaders]
  )

  const shareReport = useCallback(
    async (reportId: string, email: string) => {
      const res = await fetch(`/api/v1/generated-reports/${reportId}/share`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ email }),
      })
      if (!res.ok) throw new Error('Failed to share report')
      return res.json()
    },
    [authHeaders]
  )

  const userTier = user?.tier || 'free'

  return {
    reports: reportsQuery.data || [],
    isLoading: reportsQuery.isLoading,
    error: reportsQuery.error,
    generateReport,
    isGenerating: generateMutation.isPending,
    generatingReportId,
    downloadReport,
    shareReport,
    userTier,
    refetch: reportsQuery.refetch,
  }
}

export const REPORT_INFO: Record<ReportType, { name: string; description: string; icon: string }> = {
  'business-plan': {
    name: 'Business Plan',
    description: 'Comprehensive business plan with executive summary, market analysis, and financial projections',
    icon: 'FileText',
  },
  'financials': {
    name: 'Financial Projections',
    description: 'Detailed 3-5 year financial forecasts including P&L, cash flow, and break-even analysis',
    icon: 'DollarSign',
  },
  'pitch-deck': {
    name: 'Pitch Deck',
    description: 'Investor-ready presentation with problem, solution, market, and business model slides',
    icon: 'Presentation',
  },
  'market-analysis': {
    name: 'Market Analysis',
    description: 'Deep dive into market size, trends, competition, and customer segments',
    icon: 'TrendingUp',
  },
  'strategic-assessment': {
    name: 'Strategic Assessment',
    description: 'SWOT analysis, competitive positioning, and strategic recommendations',
    icon: 'Target',
  },
  'pestle': {
    name: 'PESTLE Analysis',
    description: 'Political, Economic, Social, Technological, Legal, and Environmental analysis',
    icon: 'Globe',
  },
  'feasibility': {
    name: 'Feasibility Study',
    description: 'Comprehensive feasibility analysis covering market, technical, and financial viability',
    icon: 'CheckCircle',
  },
}
