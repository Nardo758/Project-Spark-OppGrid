import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { 
  Bookmark, CheckCircle2, Lock, TrendingUp, Users, 
  FileText, Target, 
  ChevronRight, ArrowRight,
  Zap, Share2, Star, Rocket, Briefcase,
  AlertTriangle
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useUpgrade } from '../contexts/UpgradeContext'
import PayPerUnlockModal from '../components/PayPerUnlockModal'
import EnterpriseContactModal from '../components/EnterpriseContactModal'
import ReportViewer from '../components/ReportViewer'
import OpportunityMap from '../components/OpportunityMap'
import { FourPsPanel } from '../components/FourPs'
import type { AccessInfo } from '../types/paywall'

type Opportunity = {
  id: number
  title: string
  description: string
  category: string
  subcategory?: string | null
  severity: number
  market_size?: string | null
  feasibility_score?: number | null
  validation_count: number
  created_at?: string
  growth_rate?: number
  geographic_scope?: string
  country?: string
  region?: string
  city?: string

  is_authenticated: boolean
  is_unlocked: boolean
  access_info?: AccessInfo | null

  ai_analyzed?: boolean
  ai_summary?: string | null
  ai_market_size_estimate?: string | null
  ai_competition_level?: string | null
  ai_target_audience?: string | null
  ai_urgency_level?: string | null
  ai_pain_intensity?: number | null
  ai_problem_statement?: string | null

  ai_business_model_suggestions?: string[] | null
  ai_competitive_advantages?: string[] | null
  ai_key_risks?: string[] | null
  ai_next_steps?: string[] | null
}

type WatchlistCheck = { in_watchlist: boolean; watchlist_item_id: number | null }
type WatchlistItem = { id: number; opportunity_id: number }
type Validation = { id: number; user_id: number; opportunity_id: number }

type RecommendedExpert = {
  id: number
  name: string
  headline: string | null
  avatar_url: string | null
  skills: string[]
  specialization: string[]
  categories: string[]
  avg_rating: number | null
  total_reviews: number
  completed_projects: number
  success_rate: number | null
  is_available: boolean
  hourly_rate_cents: number | null
  pricing_model: string | null
  match_score: number
  match_reason: string
}

type DemographicsData = {
  opportunity_id: number
  demographics: {
    population?: number
    median_income?: number
    median_age?: number
    total_households?: number
    poverty_count?: number
    unemployment_count?: number
    home_value?: number
    median_rent?: number
    bachelors_degree_holders?: number
    commute_public_transit?: number
    source?: string
    fetched_at?: string
  } | null
  search_trends: {
    keyword?: string
    interest_over_time?: number[]
    related_queries?: string[]
    trending_topics?: string[]
  } | null
  enhanced_score: number | null
  original_score: number | null
  fetched_at: string | null
  census_configured: boolean
  trends_configured: boolean
}

function fmtCents(cents?: number | null) {
  if (!cents) return null
  return `$${(cents / 100).toFixed(0)}`
}

const regions = ['US National', 'Southwest', 'Northeast', 'Midwest', 'West Coast', 'Southeast']

export default function OpportunityDetail() {
  const { id } = useParams()
  const opportunityId = Number(id)
  const location = useLocation()
  const navigate = useNavigate()

  const { token, isAuthenticated, user } = useAuthStore()
  const { showUpgradeModal } = useUpgrade()
  const queryClient = useQueryClient()
  
  const [activeTab, setActiveTab] = useState('validation')
  const [selectedRegion, setSelectedRegion] = useState('US National')

  const opportunityQuery = useQuery({
    queryKey: ['opportunity', opportunityId, isAuthenticated, token?.slice(-8)],
    enabled: Number.isFinite(opportunityId),
    queryFn: async (): Promise<Opportunity> => {
      const headers: Record<string, string> = {}
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch(`/api/v1/opportunities/${opportunityId}`, { headers })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || 'Failed to load opportunity')
      return data as Opportunity
    },
  })

  const watchlistCheckQuery = useQuery({
    queryKey: ['watchlist-check', opportunityId],
    enabled: isAuthenticated && Boolean(token) && Number.isFinite(opportunityId),
    queryFn: async (): Promise<WatchlistCheck> => {
      const res = await fetch(`/api/v1/watchlist/check/${opportunityId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to check watchlist')
      return (await res.json()) as WatchlistCheck
    },
  })

  const validationsQuery = useQuery({
    queryKey: ['validations', opportunityId],
    enabled: Number.isFinite(opportunityId),
    queryFn: async (): Promise<Validation[]> => {
      const res = await fetch(`/api/v1/validations/opportunity/${opportunityId}`)
      if (!res.ok) return []
      return (await res.json()) as Validation[]
    },
  })

  const expertsQuery = useQuery({
    queryKey: ['opportunity-experts', opportunityId],
    enabled: Number.isFinite(opportunityId),
    queryFn: async (): Promise<{ experts: RecommendedExpert[]; total: number }> => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/experts?limit=5`)
      if (!res.ok) return { experts: [], total: 0 }
      return await res.json()
    },
  })

  type WorkspaceCheck = { has_workspace: boolean; workspace_id: number | null }
  const _workspaceCheckQuery = useQuery({
    queryKey: ['workspace-check', opportunityId],
    enabled: isAuthenticated && Boolean(token) && Number.isFinite(opportunityId),
    queryFn: async (): Promise<WorkspaceCheck> => {
      const res = await fetch(`/api/v1/workspaces/check/${opportunityId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return { has_workspace: false, workspace_id: null }
      return (await res.json()) as WorkspaceCheck
    },
  })
  void _workspaceCheckQuery

  const userTierFromQuery = user?.tier?.toLowerCase() || 'free'
  const isBusinessTier = userTierFromQuery === 'business' || userTierFromQuery === 'enterprise'

  const demographicsQuery = useQuery({
    queryKey: ['demographics', opportunityId],
    enabled: isAuthenticated && Boolean(token) && Number.isFinite(opportunityId) && isBusinessTier,
    queryFn: async (): Promise<DemographicsData> => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/demographics`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.detail || 'Failed to load demographics')
      }
      return (await res.json()) as DemographicsData
    },
    staleTime: 30 * 60 * 1000,
  })

  const demographics = demographicsQuery.data?.demographics
  const _searchTrends = demographicsQuery.data?.search_trends
  void _searchTrends

  const myValidation = useMemo(() => {
    const uid = user?.id
    if (!uid) return null
    return (validationsQuery.data ?? []).find((v) => v.user_id === uid) ?? null
  }, [user?.id, validationsQuery.data])

  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/watchlist/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ opportunity_id: opportunityId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || 'Failed to save')
      return data as WatchlistItem
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      queryClient.invalidateQueries({ queryKey: ['watchlist-check', opportunityId] })
    },
  })

  const unsaveMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/v1/watchlist/opportunity/${opportunityId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok && res.status !== 204) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.detail || 'Failed to remove')
      }
      return true
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      queryClient.invalidateQueries({ queryKey: ['watchlist-check', opportunityId] })
    },
  })

  const validateMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/validations/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ opportunity_id: opportunityId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || 'Failed to validate')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validations', opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId] })
    },
  })

  const unvalidateMutation = useMutation({
    mutationFn: async (validationId: number) => {
      const res = await fetch(`/api/v1/validations/${validationId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok && res.status !== 204) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.detail || 'Failed to remove validation')
      }
      return true
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validations', opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId] })
    },
  })

  const [ppuOpen, setPpuOpen] = useState(false)
  const [enterpriseModalOpen, setEnterpriseModalOpen] = useState(false)
  const [reportViewerOpen, setReportViewerOpen] = useState(false)
  const [ppuClientSecret, setPpuClientSecret] = useState<string | null>(null)
  const [ppuPublishableKey, setPpuPublishableKey] = useState<string | null>(null)
  const [ppuAmountLabel, setPpuAmountLabel] = useState<string>('$15')
  const [ppuError, setPpuError] = useState<string | null>(null)
  const autoUnlockStartedRef = useRef(false)

  const payPerUnlockMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error('Not authenticated')
      if (!Number.isFinite(opportunityId)) throw new Error('Invalid opportunity id')
      const keyRes = await fetch('/api/v1/subscriptions/stripe-key')
      const keyData = await keyRes.json().catch(() => ({}))
      if (!keyRes.ok) throw new Error(keyData?.detail || 'Stripe not configured')

      const res = await fetch('/api/v1/subscriptions/pay-per-unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ opportunity_id: opportunityId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || 'Unable to start payment')

      return {
        publishableKey: String(keyData.publishable_key),
        clientSecret: String(data.client_secret),
        amountCents: Number(data.amount),
      }
    },
    onSuccess: (data) => {
      setPpuError(null)
      setPpuPublishableKey(data.publishableKey)
      setPpuClientSecret(data.clientSecret)
      setPpuAmountLabel(fmtCents(data.amountCents) || '$15')
      setPpuOpen(true)
    },
    onError: (e) => {
      setPpuError(e instanceof Error ? e.message : 'Unable to start payment')
    },
  })

  const opp = opportunityQuery.data
  const access = opp?.access_info
  const saved = watchlistCheckQuery.data?.in_watchlist ?? false

  const shouldAutoUnlock = useMemo(() => {
    const params = new URLSearchParams(location.search)
    return params.get('unlock') === '1'
  }, [location.search])

  useEffect(() => {
    if (!shouldAutoUnlock) return
    if (!isAuthenticated) return
    if (!opp) return
    if (autoUnlockStartedRef.current) return
    if (access?.is_accessible) return
    if (!access?.can_pay_to_unlock) return
    autoUnlockStartedRef.current = true
    payPerUnlockMutation.mutate()
  }, [shouldAutoUnlock, isAuthenticated, opp, access?.is_accessible, access?.can_pay_to_unlock, payPerUnlockMutation])

  if (!Number.isFinite(opportunityId)) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <p className="text-stone-700">Invalid opportunity id.</p>
      </div>
    )
  }

  if (opportunityQuery.isLoading) {
    return <div className="max-w-6xl mx-auto px-4 py-10 text-stone-600">Loading opportunity...</div>
  }

  if (opportunityQuery.isError || !opp) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <p className="text-red-700">Failed to load opportunity.</p>
        <button className="mt-4 text-violet-600 font-medium" onClick={() => navigate(-1)}>
          Go back
        </button>
      </div>
    )
  }

  const userTier = access?.user_tier?.toLowerCase() || 'free'
  const hasPro = userTier === 'pro' || userTier === 'business' || userTier === 'enterprise'

  const titleCase = (s: string) => s.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ')
  
  const score = opp.feasibility_score || (70 + (opp.id % 20))
  const growthRate = opp.growth_rate || 12
  const marketSize = opp.ai_market_size_estimate || opp.market_size || '$50M'
  const urgency = titleCase(opp.ai_urgency_level || 'Medium')
  const competition = titleCase(opp.ai_competition_level || 'Medium')

  async function confirmPayPerUnlock(paymentIntentId: string) {
    if (!token) throw new Error('Not authenticated')
    const res = await fetch(`/api/v1/subscriptions/confirm-pay-per-unlock?payment_intent_id=${encodeURIComponent(paymentIntentId)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data?.detail || 'Failed to confirm unlock')
    await queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId] })
    await queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId, { authed: Boolean(token) }] })
  }

  const painPoints = [
    { quote: opp.ai_problem_statement || "Users consistently report frustration with current solutions in this space...", severity: 'CRITICAL' },
    { quote: "Finding reliable providers is challenging and time-consuming...", severity: 'HIGH' },
    { quote: "Pricing transparency is a major concern for consumers...", severity: 'MEDIUM' },
  ]

  const researchTabs = [
    { id: 'validation', label: 'Market Validation' },
    { id: 'four-ps', label: '4 P\'s Intelligence' },
    { id: 'geographic', label: 'Geographic' },
    { id: 'problem', label: 'Problem Analysis' },
    { id: 'sizing', label: 'Market Sizing' },
    { id: 'solutions', label: 'Solution Pathways' },
  ]

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-6">
          <Link to="/discover" className="text-sm text-violet-600 hover:text-violet-700 font-medium flex items-center gap-1">
            <ChevronRight className="w-4 h-4 rotate-180" />
            Back to Discover
          </Link>
        </div>

        {/* Header Section */}
        <div className="bg-white rounded-xl border-2 border-stone-200 p-8 mb-6">
          <div className="flex items-start justify-between gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-xs font-medium text-stone-500 uppercase tracking-wide">{opp.category}</span>
                {access?.freshness_badge && (
                  <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    access.freshness_badge.color === 'red' ? 'bg-red-100 text-red-700' :
                    access.freshness_badge.color === 'orange' ? 'bg-orange-100 text-orange-700' :
                    access.freshness_badge.color === 'yellow' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-stone-100 text-stone-700'
                  }`}>
                    <Zap className="w-3 h-3" />
                    {access.freshness_badge.label}
                  </span>
                )}
                {access && !access.is_accessible ? (
                  <span className="flex items-center gap-1 bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full text-xs font-medium">
                    <Lock className="w-3 h-3" />
                    Upgrade for Premium
                  </span>
                ) : access?.is_accessible ? (
                  <span className="flex items-center gap-1 bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">
                    Unlocked
                  </span>
                ) : null}
              </div>
              <h1 className="text-3xl font-bold text-stone-900 mb-3">{opp.title}</h1>
              <p className="text-stone-600 text-lg leading-relaxed">
                {(() => {
                  const desc = opp.description?.replace(/\*\*/g, '').split('\n').filter(l => l.trim() && !l.includes('Market Opportunity Overview'))[0]
                  return desc || opp.ai_summary?.replace(/\*\*/g, '') || 'Analysis pending...'
                })()}
              </p>
            </div>
            
            <div className="flex flex-col items-end gap-3">
              <div className="bg-emerald-100 text-emerald-700 px-6 py-4 rounded-2xl text-center">
                <div className="text-4xl font-bold">{Math.round(score)}</div>
                <div className="text-xs font-medium mt-1">Score</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    if (!isAuthenticated) return navigate(`/login?next=${encodeURIComponent(`/opportunity/${opp.id}`)}`)
                    if (saved) unsaveMutation.mutate()
                    else saveMutation.mutate()
                  }}
                  disabled={saveMutation.isPending || unsaveMutation.isPending}
                  className={`p-2 rounded-lg border-2 transition-all ${
                    saved ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-white border-stone-200 text-stone-600 hover:border-stone-400'
                  }`}
                >
                  <Bookmark className={`w-5 h-5 ${saved ? 'fill-amber-500' : ''}`} />
                </button>
                <button
                  onClick={() => {
                    if (!isAuthenticated) return navigate(`/login?next=${encodeURIComponent(`/opportunity/${opp.id}`)}`)
                    if (myValidation) unvalidateMutation.mutate(myValidation.id)
                    else validateMutation.mutate()
                  }}
                  disabled={validateMutation.isPending || unvalidateMutation.isPending}
                  className={`p-2 rounded-lg border-2 transition-all ${
                    myValidation ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-white border-stone-200 text-stone-600 hover:border-stone-400'
                  }`}
                >
                  <CheckCircle2 className="w-5 h-5" />
                </button>
              </div>
              {!isAuthenticated ? (
                <Link
                  to={`/login?next=${encodeURIComponent(`/opportunity/${opp.id}`)}`}
                  className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg font-medium hover:bg-violet-700 transition-colors"
                >
                  <Rocket className="w-4 h-4" />
                  Sign in to Continue
                </Link>
              ) : access?.is_accessible ? (
                <button
                  onClick={() => navigate(`/opportunity/${opp.id}/hub`)}
                  className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg font-medium hover:bg-violet-700 transition-colors"
                >
                  <Rocket className="w-4 h-4" />
                  Deep Dive WorkHub
                </button>
              ) : access?.can_pay_to_unlock ? (
                <button
                  onClick={() => payPerUnlockMutation.mutate()}
                  disabled={payPerUnlockMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50"
                >
                  <Lock className="w-4 h-4" />
                  {payPerUnlockMutation.isPending ? 'Processing...' : `Unlock Now (${fmtCents(access?.unlock_price) || '$15'})`}
                </button>
              ) : access?.days_until_unlock ? (
                <Link
                  to="/pricing"
                  className="flex items-center gap-2 px-4 py-2 bg-stone-900 text-white rounded-lg font-medium hover:bg-stone-800 transition-colors"
                >
                  Get Earlier Access
                </Link>
              ) : null}
            </div>
          </div>
        </div>

        {/* Problem Statement Section */}
        <div className="bg-violet-50 rounded-xl border-2 border-violet-200 p-8 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-violet-600 rounded-lg flex items-center justify-center">
              <Target className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-bold text-stone-900">Problem Statement</h2>
          </div>
          <p className="text-stone-700 text-lg leading-relaxed">
            {(() => {
              if (opp.ai_problem_statement) return opp.ai_problem_statement
              if (opp.ai_summary) return opp.ai_summary.replace(/\*\*/g, '')
              const desc = opp.description?.replace(/\*\*/g, '').split('\n').filter(l => l.trim() && !l.includes('Market Opportunity Overview'))[0]
              return desc || 'No problem statement available.'
            })()}
          </p>
        </div>

        {/* TIER 1: Problem Detail (FREE) - Empathize + Define */}
        <div className="bg-white rounded-xl border-2 border-emerald-200 p-8 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-emerald-600 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-stone-900">Problem Detail</h2>
              <p className="text-stone-500 text-sm">Empathize + Define</p>
            </div>
            <span className="ml-auto bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold">FREE</span>
          </div>

          {/* Geographic Market Selector */}
          <div className="mb-8">
            <h3 className="text-lg font-bold text-stone-900 mb-4">Geographic Market</h3>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
              {regions.map((region) => (
                <button
                  key={region}
                  onClick={() => setSelectedRegion(region)}
                  className={`p-3 rounded-lg border-2 text-sm font-medium transition-all ${
                    selectedRegion === region 
                      ? 'border-violet-600 bg-violet-50 text-violet-700' 
                      : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300'
                  }`}
                >
                  {region}
                </button>
              ))}
            </div>
            <div className="bg-stone-50 rounded-lg border border-stone-200 p-4">
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <div className="text-sm text-stone-500 mb-1">Market Size</div>
                  <div className="text-2xl font-bold text-stone-900">{marketSize}</div>
                </div>
                <div>
                  <div className="text-sm text-stone-500 mb-1">Signals</div>
                  <div className="text-2xl font-bold text-stone-900">{opp.validation_count.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-sm text-stone-500 mb-1">Growth</div>
                  <div className="text-2xl font-bold text-emerald-600">+{growthRate}%</div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Validation Metrics */}
          <div className="mb-8">
            <h3 className="text-lg font-bold text-stone-900 mb-4">Quick Validation Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-[1fr_1fr_1.5fr_0.75fr] gap-4">
              <div className="bg-stone-50 rounded-lg border border-stone-200 p-4 text-center">
                <div className="text-xs text-stone-500 uppercase tracking-wide mb-2">Urgency</div>
                <div className={`text-xl font-bold ${urgency === 'High' ? 'text-orange-600' : urgency === 'Critical' ? 'text-red-600' : 'text-stone-900'}`}>
                  {urgency}
                </div>
              </div>
              <div className="bg-stone-50 rounded-lg border border-stone-200 p-4 text-center">
                <div className="text-xs text-stone-500 uppercase tracking-wide mb-2">Competition</div>
                <div className={`text-xl font-bold ${competition === 'Low' ? 'text-emerald-600' : competition === 'High' ? 'text-red-600' : 'text-stone-900'}`}>
                  {competition}
                </div>
              </div>
              <div className="bg-stone-50 rounded-lg border border-stone-200 p-4 text-center">
                <div className="text-xs text-stone-500 uppercase tracking-wide mb-2">Target Audience</div>
                <div className="text-xl font-bold text-stone-900">{opp.ai_target_audience ? titleCase(opp.ai_target_audience) : 'Consumers'}</div>
              </div>
              <div className="bg-stone-50 rounded-lg border border-stone-200 p-4 text-center">
                <div className="text-xs text-stone-500 uppercase tracking-wide mb-2">Feasibility</div>
                <div className="text-xl font-bold text-violet-600">{Math.round(score)}%</div>
              </div>
            </div>
          </div>

          {/* Pain Points - Empathize */}
          <div className="mb-8">
            <h3 className="text-lg font-bold text-stone-900 mb-4">Top Pain Points</h3>
            <div className="space-y-3">
              {painPoints.map((point, idx) => (
                <div 
                  key={idx} 
                  className={`bg-white rounded-lg p-4 border-l-4 ${
                    point.severity === 'CRITICAL' ? 'border-red-500' : 
                    point.severity === 'HIGH' ? 'border-orange-500' : 'border-yellow-500'
                  }`}
                >
                  <p className="text-stone-800 italic text-sm">"{point.quote}"</p>
                  <span className={`inline-block mt-2 px-2 py-1 rounded text-xs font-bold ${
                    point.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' : 
                    point.severity === 'HIGH' ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {point.severity}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* TIER 2: Research Dashboard (PRO) - Ideate + Deep Dive CTA */}
        <div className="relative">
          {!hasPro && (
            <div className="absolute inset-0 bg-white/80 backdrop-blur-sm rounded-xl flex items-center justify-center z-10">
              <div className="text-center p-8">
                <Lock className="w-12 h-12 text-stone-400 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-stone-900 mb-2">Unlock Research Dashboard</h3>
                <p className="text-stone-600 mb-4">Get market analysis, demographics, and competitive landscape</p>
                <button 
                  onClick={() => showUpgradeModal('opportunity', opportunityQuery.data?.title)} 
                  className="inline-flex items-center gap-2 bg-stone-900 text-white px-6 py-3 rounded-lg font-medium hover:bg-stone-800"
                >
                  Upgrade to Unlock
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          <div className={`bg-white rounded-xl border-2 ${hasPro ? 'border-blue-200' : 'border-stone-200'} p-8 mb-6`}>
          
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-stone-900">Research Dashboard</h2>
              <p className="text-stone-500 text-sm">Ideate - Market Analysis</p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <button 
                onClick={() => setReportViewerOpen(true)}
                className="flex items-center gap-2 px-3 py-2 border border-violet-200 bg-violet-50 rounded-lg text-sm font-medium text-violet-700 hover:bg-violet-100"
              >
                <FileText className="w-4 h-4" />
                Generate Report
              </button>
              <button 
                onClick={async () => {
                  const shareUrl = window.location.href;
                  const shareTitle = opportunityQuery.data?.title || 'Business Opportunity';
                  if (navigator.share) {
                    try {
                      await navigator.share({ title: shareTitle, url: shareUrl });
                    } catch (e) {
                      if ((e as Error).name !== 'AbortError') {
                        navigator.clipboard.writeText(shareUrl);
                        alert('Link copied to clipboard!');
                      }
                    }
                  } else {
                    navigator.clipboard.writeText(shareUrl);
                    alert('Link copied to clipboard!');
                  }
                }}
                className="flex items-center gap-2 px-3 py-2 border border-stone-200 rounded-lg text-sm font-medium text-stone-700 hover:bg-stone-50"
              >
                <Share2 className="w-4 h-4" />
                Share
              </button>
              <Link 
                to="/network" 
                className="flex items-center gap-2 px-3 py-2 border border-stone-200 rounded-lg text-sm font-medium text-stone-700 hover:bg-stone-50"
              >
                <Users className="w-4 h-4" />
                Find Expert
              </Link>
              <Link 
                to={`/opportunity/${id}/hub`}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700"
              >
                <Rocket className="w-4 h-4" />
                Deep Dive WorkHub
              </Link>
            </div>
          </div>

          {/* Tabs */}
          <div className="mb-6 bg-stone-100 rounded-lg p-1.5 flex gap-1 overflow-x-auto">
            {researchTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                  activeTab === tab.id 
                    ? 'bg-blue-600 text-white shadow' 
                    : 'text-stone-600 hover:bg-stone-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="space-y-4">
            {activeTab === 'validation' && (
              <>
                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Demand Signals</h3>
                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <div className="text-sm text-stone-500">Search Volume</div>
                      <div className="text-3xl font-bold text-stone-900">127K/mo</div>
                    </div>
                    <div>
                      <div className="text-sm text-stone-500">YoY Growth</div>
                      <div className="text-3xl font-bold text-emerald-600">+{growthRate + 20}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-stone-500">Social Mentions</div>
                      <div className="text-3xl font-bold text-stone-900">89K/mo</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Competitive Landscape</h3>
                  <div className="space-y-3">
                    {(opp.ai_competitive_advantages || ['Market leader gap exists', 'Fragmented competitor landscape', 'No dominant solution']).map((comp, idx) => (
                      <div key={idx} className="bg-stone-50 rounded-lg p-4">
                        <div className="font-semibold text-stone-900">{typeof comp === 'string' ? comp : JSON.stringify(comp)}</div>
                        <div className="text-sm text-stone-600 mt-1">Key opportunity for differentiation</div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeTab === 'four-ps' && (
              <div className="space-y-4">
                <FourPsPanel 
                  opportunityId={opp.id}
                  showQuality={true}
                  defaultExpanded={false}
                />
              </div>
            )}

            {activeTab === 'solutions' && (
              <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                <h3 className="text-lg font-bold text-stone-900 mb-4">Solution Pathways</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {(opp.ai_business_model_suggestions || ['SaaS Platform', 'Marketplace Model', 'On-Demand Service', 'Subscription Box']).map((model, idx) => (
                    <div key={idx} className="bg-gradient-to-br from-violet-50 to-blue-50 rounded-lg p-4 border-2 border-violet-100">
                      <div className="flex items-center gap-2 mb-2">
                        <Zap className="w-5 h-5 text-violet-600" />
                        <span className="font-bold text-stone-900">{typeof model === 'string' ? model : JSON.stringify(model)}</span>
                      </div>
                      <p className="text-sm text-stone-600">Viable approach based on market analysis</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'geographic' && (
              <div className="space-y-4">
                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Geographic Distribution</h3>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <OpportunityMap 
                        opportunityId={opp.id} 
                        height="350px"
                        showControls={true}
                        initialZoom={8}
                      />
                    </div>
                    <div className="space-y-3">
                      <div className="bg-stone-50 rounded-lg p-4">
                        <div className="text-sm text-stone-500">Geographic Scope</div>
                        <div className="text-xl font-bold text-stone-900 capitalize">{opp.geographic_scope || 'National'}</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-4">
                        <div className="text-sm text-stone-500">Primary Region</div>
                        <div className="text-xl font-bold text-stone-900">{opp.region || opp.country || 'United States'}</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-4">
                        <div className="text-sm text-stone-500">Primary City</div>
                        <div className="text-xl font-bold text-stone-900">{opp.city || 'Multiple Locations'}</div>
                      </div>
                      <div className="bg-stone-50 rounded-lg p-4">
                        <div className="text-sm text-stone-500">Market Coverage</div>
                        <div className="text-xl font-bold text-emerald-600">High Density</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Regional Demographics</h3>
                  {!isBusinessTier ? (
                    <div className="bg-stone-50 rounded-lg p-4 text-center">
                      <Lock className="w-6 h-6 text-stone-400 mx-auto mb-2" />
                      <p className="text-sm text-stone-600 mb-2">Census data requires Business tier</p>
                      <button onClick={() => showUpgradeModal('analysis', 'Census Demographics')} className="text-violet-600 font-medium text-sm hover:underline">
                        Upgrade to Business
                      </button>
                    </div>
                  ) : demographicsQuery.isLoading ? (
                    <div className="grid grid-cols-4 gap-4">
                      {[1,2,3,4].map(i => (
                        <div key={i} className="bg-stone-50 rounded-lg p-4 text-center animate-pulse">
                          <div className="h-8 bg-stone-200 rounded mb-2"></div>
                          <div className="h-3 bg-stone-200 rounded w-16 mx-auto"></div>
                        </div>
                      ))}
                    </div>
                  ) : demographics ? (
                    <>
                      <p className="text-xs text-stone-500 mb-4">Census ACS 5-Year Data • {demographics.source || 'US Census Bureau'}</p>
                      <div className="grid grid-cols-4 gap-4">
                        <div className="bg-blue-50 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-blue-600">
                            {demographics.population ? (demographics.population >= 1000000 
                              ? `${(demographics.population / 1000000).toFixed(1)}M`
                              : demographics.population >= 1000 
                                ? `${(demographics.population / 1000).toFixed(0)}K`
                                : demographics.population.toLocaleString()) : '--'}
                          </div>
                          <div className="text-xs text-stone-500">Population</div>
                        </div>
                        <div className="bg-emerald-50 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-emerald-600">
                            {demographics.median_income ? `$${(demographics.median_income / 1000).toFixed(0)}K` : '--'}
                          </div>
                          <div className="text-xs text-stone-500">Median Income</div>
                        </div>
                        <div className="bg-violet-50 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-violet-600">
                            {demographics.bachelors_degree_holders && demographics.population 
                              ? `${((demographics.bachelors_degree_holders / demographics.population) * 100).toFixed(0)}%` 
                              : '--'}
                          </div>
                          <div className="text-xs text-stone-500">College Educated</div>
                        </div>
                        <div className="bg-amber-50 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-amber-600">
                            {demographics.median_age ? demographics.median_age.toFixed(0) : '--'}
                          </div>
                          <div className="text-xs text-stone-500">Median Age</div>
                        </div>
                      </div>
                      {demographics.total_households && (
                        <div className="mt-4 grid grid-cols-3 gap-4">
                          <div className="bg-stone-50 rounded-lg p-3 text-center">
                            <div className="text-lg font-bold text-stone-700">
                              {demographics.total_households >= 1000 
                                ? `${(demographics.total_households / 1000).toFixed(0)}K` 
                                : demographics.total_households.toLocaleString()}
                            </div>
                            <div className="text-xs text-stone-500">Households</div>
                          </div>
                          <div className="bg-stone-50 rounded-lg p-3 text-center">
                            <div className="text-lg font-bold text-stone-700">
                              {demographics.home_value ? `$${(demographics.home_value / 1000).toFixed(0)}K` : '--'}
                            </div>
                            <div className="text-xs text-stone-500">Home Value</div>
                          </div>
                          <div className="bg-stone-50 rounded-lg p-3 text-center">
                            <div className="text-lg font-bold text-stone-700">
                              {demographics.median_rent ? `$${demographics.median_rent.toLocaleString()}` : '--'}
                            </div>
                            <div className="text-xs text-stone-500">Median Rent</div>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="bg-amber-50 rounded-lg p-4 text-center border border-amber-200">
                      <p className="text-sm text-amber-700">
                        {demographicsQuery.data?.census_configured 
                          ? 'No demographic data available for this location yet'
                          : 'Census API not configured - contact admin to enable demographics'}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'problem' && (
              <div className="space-y-4">
                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Problem Statement</h3>
                  <div className="bg-gradient-to-r from-violet-50 to-blue-50 rounded-lg p-6 border-2 border-violet-200">
                    <p className="text-lg text-stone-800 leading-relaxed">
                      {opp.ai_problem_statement || opp.description}
                    </p>
                  </div>
                </div>

                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Pain Point Severity</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-stone-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-red-600">{opp.ai_pain_intensity || opp.severity}/10</div>
                      <div className="text-sm text-stone-500">Pain Intensity</div>
                    </div>
                    <div className="bg-stone-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-amber-600 capitalize">{opp.ai_urgency_level || 'Medium'}</div>
                      <div className="text-sm text-stone-500">Urgency Level</div>
                    </div>
                    <div className="bg-stone-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-emerald-600">{opp.validation_count}</div>
                      <div className="text-sm text-stone-500">Validations</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Key Risks</h3>
                  <div className="space-y-2">
                    {(opp.ai_key_risks || ['Market timing uncertainty', 'Regulatory considerations', 'Competition from incumbents']).map((risk, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-100">
                        <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <span className="text-stone-700">{typeof risk === 'string' ? risk : JSON.stringify(risk)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'sizing' && (
              <div className="space-y-4">
                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Market Size Analysis</h3>
                  <div className="grid grid-cols-3 gap-6">
                    <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-6 text-white">
                      <div className="text-sm opacity-80 mb-1">TAM (Total)</div>
                      <div className="text-3xl font-bold">{opp.ai_market_size_estimate || opp.market_size || '$1B+'}</div>
                      <div className="text-xs opacity-60 mt-2">Total Addressable Market</div>
                    </div>
                    <div className="bg-gradient-to-br from-violet-500 to-violet-600 rounded-lg p-6 text-white">
                      <div className="text-sm opacity-80 mb-1">SAM (Serviceable)</div>
                      <div className="text-3xl font-bold">~$500M</div>
                      <div className="text-xs opacity-60 mt-2">Geographic Focus</div>
                    </div>
                    <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg p-6 text-white">
                      <div className="text-sm opacity-80 mb-1">SOM (Obtainable)</div>
                      <div className="text-3xl font-bold">~$50M</div>
                      <div className="text-xs opacity-60 mt-2">Year 1 Target</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg border-2 border-stone-200 p-6">
                  <h3 className="text-lg font-bold text-stone-900 mb-4">Target Demographics</h3>
                  <div className="bg-stone-50 rounded-lg p-4 mb-4">
                    <div className="text-sm text-stone-500 mb-1">Primary Target</div>
                    <div className="text-lg font-semibold text-stone-900">{opp.ai_target_audience || 'General consumers with specific pain point'}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="text-sm text-stone-500 mb-1">Competition Level</div>
                      <div className="text-lg font-bold text-blue-600 capitalize">{opp.ai_competition_level || 'Medium'}</div>
                    </div>
                    <div className="bg-emerald-50 rounded-lg p-4">
                      <div className="text-sm text-stone-500 mb-1">Growth Rate</div>
                      <div className="text-lg font-bold text-emerald-600">+{growthRate}% YoY</div>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-stone-50 to-blue-50 rounded-lg border-2 border-stone-200 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <TrendingUp className="w-5 h-5 text-blue-600" />
                    <h3 className="font-bold text-stone-900">Purchasing Power Estimate</h3>
                  </div>
                  <p className="text-sm text-stone-600 mb-4">Based on target demographic income levels and market penetration assumptions</p>
                  {!isBusinessTier ? (
                    <div className="flex items-center gap-2 text-stone-500">
                      <Lock className="w-4 h-4" />
                      <span className="text-sm">Upgrade to Business for Census-powered estimates</span>
                    </div>
                  ) : demographicsQuery.isLoading ? (
                    <div className="h-8 bg-stone-200 rounded w-48 animate-pulse"></div>
                  ) : demographics?.median_income && demographics?.total_households ? (
                    <div className="space-y-2">
                      <div className="text-2xl font-bold text-stone-900">
                        ${((demographics.median_income * demographics.total_households) / 1000000000).toFixed(1)}B Total Purchasing Power
                      </div>
                      <div className="text-sm text-stone-600">
                        Based on {demographics.total_households.toLocaleString()} households × ${demographics.median_income.toLocaleString()} median income
                      </div>
                      {demographicsQuery.data?.enhanced_score && demographicsQuery.data.original_score && (
                        <div className="mt-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                          <div className="text-sm font-medium text-emerald-700">
                            Demographics-Enhanced Score: {demographicsQuery.data.enhanced_score.toFixed(0)} 
                            <span className="text-stone-500 ml-1">(base: {demographicsQuery.data.original_score})</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-stone-500 text-sm">
                      {demographicsQuery.data?.census_configured 
                        ? 'Demographic data not yet available for this location'
                        : 'Census API integration pending'}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Expert Preview - Tier 2 */}
          <div className="mt-6 pt-6 border-t-2 border-stone-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-stone-900 flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-600" />
                Recommended Experts
              </h3>
              <span className="text-xs text-stone-500">
                {expertsQuery.isLoading ? 'Loading...' : `${expertsQuery.data?.total || 0} experts matched`}
              </span>
            </div>
            
            <div className="grid md:grid-cols-3 gap-4 mb-4">
              {(expertsQuery.data?.experts || []).slice(0, 3).map((expert) => (
                <div key={expert.id} className="bg-stone-50 rounded-lg p-4 border border-stone-200 hover:border-blue-300 transition-colors">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-violet-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                      {(expert.name || '').split(' ').filter(n => n).map(n => n[0]).join('').slice(0, 2) || '?'}
                    </div>
                    <div>
                      <div className="font-semibold text-stone-900 text-sm">{expert.name}</div>
                      <div className="text-xs text-stone-500">{expert.headline}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-stone-600 mb-3">
                    {expert.avg_rating && (
                      <span className="flex items-center gap-1">
                        <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                        {expert.avg_rating.toFixed(1)}
                      </span>
                    )}
                    <span>{expert.completed_projects} projects</span>
                    <span className="text-emerald-600 font-medium">{expert.match_score}% match</span>
                  </div>
                  <div className="text-xs text-stone-500 mb-2">{expert.match_reason}</div>
                  {expert.categories?.[0] && (
                    <div className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded inline-block">
                      {expert.categories[0]}
                    </div>
                  )}
                </div>
              ))}
              {expertsQuery.isLoading && (
                <>
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="bg-stone-50 rounded-lg p-4 border border-stone-200 animate-pulse">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 bg-stone-300 rounded-full"></div>
                        <div className="space-y-2">
                          <div className="h-4 w-24 bg-stone-300 rounded"></div>
                          <div className="h-3 w-32 bg-stone-200 rounded"></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>

            <div className="bg-gradient-to-r from-blue-50 to-violet-50 rounded-lg p-4 border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-stone-900">Ready to work with an expert?</p>
                  <p className="text-sm text-stone-600">Upgrade to Business for direct messaging and collaboration</p>
                </div>
                <Link 
                  to="/pricing"
                  className="flex items-center gap-2 bg-stone-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-stone-800"
                >
                  Request Consultation
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* CTA: Deep Dive WorkHub */}
        <div className="bg-gradient-to-r from-violet-600 to-purple-600 rounded-xl p-8 mt-6 text-white">
          <div className="flex items-center justify-between gap-6">
            <div className="flex items-center gap-4 flex-1">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <Rocket className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold mb-1">Ready to Deep Dive?</h2>
                <p className="text-violet-100">Take action in our WorkHub with AI-powered planning, task management, and expert collaboration.</p>
              </div>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              {!isAuthenticated ? (
                <Link 
                  to={`/login?next=${encodeURIComponent(`/opportunity/${id}`)}`}
                  className="flex items-center gap-2 px-6 py-3 bg-white text-violet-700 rounded-lg font-medium hover:bg-violet-50 transition-colors"
                >
                  <Rocket className="w-5 h-5" />
                  Sign in to Start
                </Link>
              ) : access?.is_accessible ? (
                <Link 
                  to={`/opportunity/${id}/hub`}
                  className="flex items-center gap-2 px-6 py-3 bg-white text-violet-700 rounded-lg font-medium hover:bg-violet-50 transition-colors"
                >
                  <Briefcase className="w-5 h-5" />
                  Deep Dive WorkHub
                </Link>
              ) : access?.can_pay_to_unlock ? (
                <button
                  onClick={() => payPerUnlockMutation.mutate()}
                  disabled={payPerUnlockMutation.isPending}
                  className="flex items-center gap-2 px-6 py-3 bg-white text-violet-700 rounded-lg font-medium hover:bg-violet-50 transition-colors disabled:opacity-50"
                >
                  <Lock className="w-5 h-5" />
                  {payPerUnlockMutation.isPending ? 'Processing...' : `Unlock Now (${fmtCents(access?.unlock_price) || '$15'})`}
                </button>
              ) : access?.days_until_unlock ? (
                <Link 
                  to="/pricing"
                  className="flex items-center gap-2 px-6 py-3 bg-white text-violet-700 rounded-lg font-medium hover:bg-violet-50 transition-colors"
                >
                  <Rocket className="w-5 h-5" />
                  Upgrade for Earlier Access
                </Link>
              ) : (
                <Link 
                  to="/pricing"
                  className="flex items-center gap-2 px-6 py-3 bg-white text-violet-700 rounded-lg font-medium hover:bg-violet-50 transition-colors"
                >
                  <Rocket className="w-5 h-5" />
                  Upgrade to Access WorkHub
                </Link>
              )}
            </div>
          </div>
        </div>
        </div>

        {ppuError && (
          <div className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            {ppuError}
          </div>
        )}
      </div>

      {ppuOpen && ppuClientSecret && ppuPublishableKey && (
        <PayPerUnlockModal
          onClose={() => setPpuOpen(false)}
          publishableKey={ppuPublishableKey}
          clientSecret={ppuClientSecret}
          amountLabel={ppuAmountLabel}
          onConfirmed={confirmPayPerUnlock}
        />
      )}
      {enterpriseModalOpen && (
        <EnterpriseContactModal onClose={() => setEnterpriseModalOpen(false)} />
      )}
      <ReportViewer
        opportunityId={opportunityId}
        opportunityTitle={opp?.title || 'Opportunity Report'}
        userTier={userTierFromQuery}
        isOpen={reportViewerOpen}
        onClose={() => setReportViewerOpen(false)}
        hasUnlockedAccess={opp?.is_unlocked || access?.is_unlocked || false}
      />
    </div>
  )
}
