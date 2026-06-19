import { useState, useCallback } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { ReportType } from './useReports'

export interface ReportPricing {
  type: ReportType
  price: number
  included_in_tiers: string[]
  credits_required: number
}

export interface TierAccess {
  canGenerate: boolean
  reason?: string
  needsPayment: boolean
  price?: number
  creditsAvailable?: number
  creditsRequired?: number
}

const TIER_HIERARCHY = ['free', 'starter', 'growth', 'pro', 'team', 'business', 'enterprise']

const REPORT_PRICING: Record<ReportType, ReportPricing> = {
  'business-plan': { type: 'business-plan', price: 4900, included_in_tiers: ['pro', 'team', 'business', 'enterprise'], credits_required: 1 },
  'financials': { type: 'financials', price: 4900, included_in_tiers: ['pro', 'team', 'business', 'enterprise'], credits_required: 1 },
  'pitch-deck': { type: 'pitch-deck', price: 4900, included_in_tiers: ['pro', 'team', 'business', 'enterprise'], credits_required: 1 },
  'market-analysis': { type: 'market-analysis', price: 2900, included_in_tiers: ['growth', 'pro', 'team', 'business', 'enterprise'], credits_required: 1 },
  'strategic-assessment': { type: 'strategic-assessment', price: 2900, included_in_tiers: ['growth', 'pro', 'team', 'business', 'enterprise'], credits_required: 1 },
  'pestle': { type: 'pestle', price: 1900, included_in_tiers: ['starter', 'growth', 'pro', 'team', 'business', 'enterprise'], credits_required: 1 },
  'feasibility': { type: 'feasibility', price: 3900, included_in_tiers: ['growth', 'pro', 'team', 'business', 'enterprise'], credits_required: 1 },
}

export function useReportPayment() {
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const [isProcessing, setIsProcessing] = useState(false)

  const userTier = user?.tier?.toLowerCase() || 'free'

  const authHeaders = useCallback(() => {
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }
    return headers
  }, [token])

  const checkTierAccess = useCallback(
    (reportType: ReportType): TierAccess => {
      const pricing = REPORT_PRICING[reportType]
      if (!pricing) {
        return { canGenerate: false, reason: 'Unknown report type', needsPayment: false }
      }

      const userTierIndex = TIER_HIERARCHY.indexOf(userTier)
      const hasAccess = pricing.included_in_tiers.some(
        (tier) => TIER_HIERARCHY.indexOf(tier) <= userTierIndex
      )

      if (hasAccess) {
        return { canGenerate: true, needsPayment: false }
      }

      return {
        canGenerate: false,
        reason: `Requires ${pricing.included_in_tiers[0]} tier or higher`,
        needsPayment: true,
        price: pricing.price,
      }
    },
    [userTier]
  )

  const initiatePayment = useCallback(
    async (reportType: ReportType, context: Record<string, unknown>) => {
      setIsProcessing(true)
      try {
        const res = await fetch('/api/v1/report-pricing/checkout', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ report_type: reportType, context }),
        })

        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || 'Failed to initiate payment')
        }

        const data = await res.json()
        if (data.checkout_url) {
          window.location.href = data.checkout_url
        }
        return data
      } finally {
        setIsProcessing(false)
      }
    },
    [authHeaders]
  )

  const getReportPrice = useCallback((reportType: ReportType) => {
    return REPORT_PRICING[reportType]?.price || 0
  }, [])

  const formatPrice = useCallback((priceInCents: number) => {
    return `$${(priceInCents / 100).toFixed(2)}`
  }, [])

  return {
    checkTierAccess,
    initiatePayment,
    isProcessing,
    getReportPrice,
    formatPrice,
    userTier,
    REPORT_PRICING,
  }
}
