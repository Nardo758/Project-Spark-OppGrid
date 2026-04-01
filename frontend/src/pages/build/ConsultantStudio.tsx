import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Lightbulb,
  Search,
  MapPin,
  Copy,
  Loader2,
  CheckCircle,
  TrendingUp,
  FileText,
  Sparkles,
  Map,
  AlertCircle,
  Lock,
  Shield,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { Link } from 'react-router-dom'
import { VerdictBanner, ScoreCards, MarketIntelligence, FeasibilityPreview, ActionBar } from '../../components/ConsultantResults'
import ReportSelectionPanel from '../../components/ReportSelectionPanel'

function FourPsBar({ product, price, place, promotion }: { product: number; price: number; place: number; promotion: number }) {
  const bars = [
    { label: 'Product', score: product, color: 'bg-blue-500' },
    { label: 'Price', score: price, color: 'bg-green-500' },
    { label: 'Place', score: place, color: 'bg-amber-500' },
    { label: 'Promotion', score: promotion, color: 'bg-rose-500' },
  ]
  return (
    <div className="flex items-center gap-1.5">
      {bars.map(b => (
        <div key={b.label} title={`${b.label}: ${b.score}/100`} className="flex flex-col items-center gap-0.5">
          <div className="w-5 h-16 rounded-sm relative overflow-hidden bg-gray-200">
            <div className={`absolute bottom-0 w-full rounded-sm ${b.color}`} style={{ height: `${b.score}%` }} />
          </div>
          <span className="text-[9px] text-gray-400">{b.label[0]}</span>
        </div>
      ))}
    </div>
  )
}

function BlurGate({ children, title, priceLabel, subtitle, onPurchase, loading }: {
  children: React.ReactNode
  title: string
  priceLabel: string
  subtitle: string
  onPurchase?: () => void
  loading?: boolean
}) {
  return (
    <div className="relative rounded-xl overflow-hidden">
      <div className="blur-[6px] pointer-events-none opacity-50">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center bg-white/30 backdrop-blur-sm">
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-center max-w-sm shadow-sm">
          <Lock className="w-5 h-5 text-amber-500 mx-auto mb-2" />
          <p className="font-semibold text-gray-900 text-sm mb-1">{title}</p>
          <p className="text-xs text-gray-500 mb-4">{subtitle}</p>
          <button
            onClick={onPurchase}
            disabled={loading}
            className="px-5 py-2.5 rounded-lg text-white text-sm font-medium bg-amber-500 hover:bg-amber-600 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Processing...' : priceLabel}
          </button>
          <p className="text-[10px] text-gray-400 mt-2">Consultants charge $1,500+ for this</p>
          <div className="flex items-center justify-center gap-2 mt-2 text-[10px] text-gray-400">
            <span className="flex items-center gap-0.5"><Shield className="w-3 h-3" /> Secure payment</span>
            <span>·</span>
            <span>Money-back guarantee</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function ScoreCard({ label, value, color, suffix = '%' }: { label: string; value: number; color: string; suffix?: string }) {
  const pct = suffix === '%' ? value : value * 10
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-medium text-gray-900">{value}{suffix}</div>
      <div className="mt-2 h-1 bg-gray-200 rounded-full">
        <div className={`h-1 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  )
}

function ResultMetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="border border-gray-100 rounded-lg p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-lg font-medium mt-0.5 ${color || 'text-gray-900'}`}>{value}</div>
    </div>
  )
}

function OppRow({ title, category, score, to }: { title: string; category?: string; score?: number | string; to?: string }) {
  const content = (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
      <div>
        <div className="text-sm font-medium text-gray-900">{title}</div>
        {category && <div className="text-xs text-gray-500">{category}</div>}
      </div>
      {score != null && (
        <div className="text-right">
          <div className="text-sm font-medium text-amber-500">{score}</div>
          <div className="text-[10px] text-gray-400">score</div>
        </div>
      )}
    </div>
  )
  if (to) return <Link to={to}>{content}</Link>
  return content
}

type TabId = 'validate' | 'search' | 'location' | 'clone'

interface Tab {
  id: TabId
  label: string
  icon: React.ComponentType<{ className?: string }>
  description: string
}

const TABS: Tab[] = [
  {
    id: 'validate',
    label: 'Validate Idea',
    icon: Lightbulb,
    description: 'Describe your idea, get Online/Physical/Hybrid recommendation',
  },
  {
    id: 'search',
    label: 'Search Ideas',
    icon: Search,
    description: 'Browse opportunities database by keyword/category',
  },
  {
    id: 'location',
    label: 'Identify Location',
    icon: MapPin,
    description: 'Enter a city + business type to analyze the market',
  },
  {
    id: 'clone',
    label: 'Clone Success',
    icon: Copy,
    description: 'Enter a successful business to find replicable locations',
  },
]

// Types for API responses
interface ViabilityReport {
  summary?: string
  market_size?: string | Record<string, unknown>
  tam?: string
  growth?: string
  competition?: string
  demand_signal?: string
  advantages?: string[]
  strengths?: string[]
  risks?: string[]
  weaknesses?: string[]
  [key: string]: unknown
}

interface ValidateIdeaResult {
  success: boolean
  idea_description?: string
  recommendation?: 'online' | 'physical' | 'hybrid'
  online_score?: number
  physical_score?: number
  pattern_analysis?: Record<string, unknown>
  viability_report?: ViabilityReport
  similar_opportunities?: Array<{ id: number; title: string; score: number }>
  processing_time_ms?: number
  error?: string
  // Enriched fields
  confidence_score?: number
  verdict_summary?: string
  verdict_detail?: string
  market_intelligence?: Record<string, any>
  advantages?: string[]
  risks?: string[]
  four_ps_scores?: Record<string, number>
  feasibility_preview?: Record<string, any>
  data_quality?: Record<string, any>
}

interface SearchOpportunity {
  id: number
  title: string
  description?: string
  category?: string
  score?: number
  product_score?: number
  price_score?: number
  place_score?: number
  promotion_score?: number
  created_at?: string
}

interface SearchIdeasResult {
  success: boolean
  opportunities?: SearchOpportunity[]
  trends?: Array<{
    id: number
    name: string
    strength: number
    description?: string
    growth_rate?: number
    opportunities_count?: number
  }>
  synthesis?: Record<string, unknown> | string
  total_count?: number
  processing_time_ms?: number
  error?: string
}

interface GeoAnalysis {
  market_score?: number
  overall_score?: number
  median_income?: number
  population?: number
  median_age?: number
  market_density?: string
  competitors?: Array<{ name?: string; rating?: number; reviews?: number } | string>
  product_score?: number
  price_score?: number
  place_score?: number
  promotion_score?: number
  product_detail?: string
  price_detail?: string
  place_detail?: string
  promotion_detail?: string
  [key: string]: unknown
}

interface SiteRecommendation {
  name?: string
  area?: string
  reason?: string
  priority?: string
  score?: number
}

interface IdentifyLocationResult {
  success: boolean
  city?: string
  business_description?: string
  inferred_category?: string
  geo_analysis?: GeoAnalysis
  market_report?: Record<string, unknown> | string
  site_recommendations?: SiteRecommendation[]
  map_data?: {
    city: string
    center: { lat: number; lng: number }
    layers: Record<string, unknown>
    totalFeatures: number
  }
  from_cache?: boolean
  processing_time_ms?: number
  error?: string
  // Enriched fields
  four_ps_scores?: Record<string, number>
  four_ps_details?: Record<string, any>
  data_quality?: Record<string, any>
}

interface SourceBusiness {
  name?: string
  category?: string
  success_factors?: string[]
  demographics?: {
    population?: number
    median_income?: number
    competition_count?: number
    median_age?: number
  }
  [key: string]: unknown
}

interface CloneSuccessResult {
  success: boolean
  source_business?: SourceBusiness
  matching_locations?: Array<{
    name: string
    city: string
    state: string
    lat: number
    lng: number
    similarity_score: number
    demographics_match: number
    competition_match: number
    population?: number
    median_income?: number
    key_factors: string[]
  }>
  analysis_radius_miles?: number
  processing_time_ms?: number
  error?: string
  // Enriched fields
  target_four_ps?: Record<string, number>
  data_quality?: Record<string, any>
}

interface SavedReport {
  id: number
  report_type: string
  title: string
  status: string
  created_at: string
}

export default function ConsultantStudio() {
  // Optional: Allow guest access (no authentication required)
  const { token } = useAuthStore()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<TabId>('validate')

  // Validate Idea state
  const [ideaDescription, setIdeaDescription] = useState('')
  const [validateResult, setValidateResult] = useState<ValidateIdeaResult | null>(null)

  // Search Ideas state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchCategory, setSearchCategory] = useState('')
  const [searchResult, setSearchResult] = useState<SearchIdeasResult | null>(null)

  // Identify Location state
  const [locationCity, setLocationCity] = useState('')
  const [locationBusiness, setLocationBusiness] = useState('')
  const [locationResult, setLocationResult] = useState<IdentifyLocationResult | null>(null)

  // Clone Success state
  const [cloneBusinessName, setCloneBusinessName] = useState('')
  const [cloneBusinessAddress, setCloneBusinessAddress] = useState('')
  const [cloneTargetCity, setCloneTargetCity] = useState('')
  const [cloneTargetState, setCloneTargetState] = useState('')
  const [cloneResult, setCloneResult] = useState<CloneSuccessResult | null>(null)

  // Saved reports
  const [savedReports, setSavedReports] = useState<SavedReport[]>([])

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  // Validate Idea mutation
  const validateMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/consultant/validate-idea', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          idea_description: ideaDescription,
          business_context: {},
        }),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `Server error (${res.status})`)
      }
      return res.json() as Promise<ValidateIdeaResult>
    },
    onSuccess: (data) => {
      if (!data.success) {
        console.warn('API returned success=false:', data.error)
      }
      setValidateResult(data)
      
      // NEW: Auto-generate report when analysis completes
      if (data.success && token) {
        saveReportMutation.mutate({
          reportType: 'feasibility_study',
          title: `Business Idea: ${ideaDescription.slice(0, 50)}...`,
          content: JSON.stringify(data, null, 2),
        })
      }
    },
    onError: (err: Error) => {
      console.error('Validate mutation error:', err)
    }
  })

  // Search Ideas mutation
  const searchMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/consultant/search-ideas', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          query: searchQuery || undefined,
          category: searchCategory || undefined,
        }),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `Server error (${res.status})`)
      }
      return res.json() as Promise<SearchIdeasResult>
    },
    onSuccess: (data) => {
      if (!data.success) {
        console.warn('Search returned success=false:', data.error)
      }
      setSearchResult(data)
    },
    onError: (err: Error) => {
      console.error('Search mutation error:', err)
    }
  })

  // Identify Location mutation
  const locationMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/consultant/identify-location', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          city: locationCity,
          business_description: locationBusiness,
        }),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `Server error (${res.status})`)
      }
      return res.json() as Promise<IdentifyLocationResult>
    },
    onSuccess: (data) => {
      if (!data.success) {
        console.warn('Location analysis returned success=false:', data.error)
      }
      setLocationResult(data)
    },
    onError: (err: Error) => {
      console.error('Location mutation error:', err)
    }
  })

  // Clone Success mutation
  const cloneMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/consultant/clone-success', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          business_name: cloneBusinessName,
          business_address: cloneBusinessAddress,
          target_city: cloneTargetCity || undefined,
          target_state: cloneTargetState || undefined,
          radius_miles: 3,
        }),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `Server error (${res.status})`)
      }
      return res.json() as Promise<CloneSuccessResult>
    },
    onSuccess: (data) => {
      if (!data.success) {
        console.warn('Clone analysis returned success=false:', data.error)
      }
      setCloneResult(data)
    },
    onError: (err: Error) => {
      console.error('Clone mutation error:', err)
    }
  })

  const [reportError, setReportError] = useState<string | null>(null)
  const [reportSuccess, setReportSuccess] = useState(false)

  const saveReportMutation = useMutation({
    mutationFn: async ({
      reportType,
      title: _title,
      content,
    }: {
      reportType: string
      title: string
      content: string
    }) => {
      setReportError(null)
      setReportSuccess(false)
      const res = await fetch('/api/v1/reports/generate', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          template_slug: reportType,
          custom_context: content,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Report generation failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess: (data) => {
      setSavedReports((prev) => [data, ...prev])
      queryClient.invalidateQueries({ queryKey: ['my-reports'] })
      setReportSuccess(true)
      setTimeout(() => setReportSuccess(false), 4000)
    },
    onError: (err: Error) => {
      setReportError(err.message)
    },
  })

  const [checkoutLoading, setCheckoutLoading] = useState(false)

  const handleReportCheckout = async (templateSlug: string) => {
    setCheckoutLoading(true)
    try {
      const baseUrl = window.location.origin
      const returnPath = window.location.pathname
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent(returnPath)}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent(returnPath)}`

      const res = await fetch('/api/v1/report-pricing/template-checkout', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          template_slug: templateSlug,
          success_url: successUrl,
          cancel_url: cancelUrl,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start checkout')
      if (data.url) window.location.href = data.url
    } catch (e) {
      setReportError(e instanceof Error ? e.message : 'Checkout failed')
    } finally {
      setCheckoutLoading(false)
    }
  }

  const getRecommendationBadge = (rec?: string) => {
    if (!rec) return null
    const styles: Record<string, string> = {
      online: 'bg-blue-100 text-blue-700',
      physical: 'bg-green-100 text-green-700',
      hybrid: 'bg-purple-100 text-purple-700',
    }
    return (
      <span className={`px-3 py-0.5 rounded-full text-xs font-medium ${styles[rec] || 'bg-gray-100 text-gray-700'}`}>
        {rec.charAt(0).toUpperCase() + rec.slice(1)} recommended
      </span>
    )
  }

  const renderValidateTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Describe Your Business Idea</h3>
        <p className="text-sm text-gray-500 mb-4">
          Our AI will analyze your idea and generate a comprehensive report. Describe your business concept below.
        </p>
        <textarea
          value={ideaDescription}
          onChange={(e) => setIdeaDescription(e.target.value)}
          placeholder="Example: A subscription service that delivers locally-roasted coffee beans to offices in downtown areas, with flexible weekly or monthly delivery options..."
          rows={5}
          className="w-full p-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none"
        />
        <div className="mt-6 space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">{ideaDescription.length}/2000 characters</span>
            <button
              onClick={() => validateMutation.mutate()}
              disabled={!ideaDescription.trim() || validateMutation.isPending}
              className="px-8 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 transition-all"
            >
              {validateMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing & Generating Report...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Analyze & Generate Report
                </>
              )}
            </button>
          </div>
          <div className="text-xs text-gray-400">
            💡 <strong>Pro Tip:</strong> Your report generates automatically with the analysis. Takes ~30 seconds for full analysis.
          </div>
        </div>
      </div>

      {validateResult?.success && (
        <div className="space-y-4 animate-fade-in">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-3">
              {getRecommendationBadge(validateResult.recommendation)}
              <span className="text-xs text-gray-400">{((validateResult.processing_time_ms || 0) / 1000).toFixed(1)}s</span>
            </div>
            {validateResult.viability_report && (
              <>
                <p className="text-sm font-medium text-gray-900 mb-1">
                  {validateResult.viability_report.summary
                    ? (typeof validateResult.viability_report.summary === 'string'
                      ? validateResult.viability_report.summary.split('.').slice(0, 2).join('.') + '.'
                      : 'Analysis complete.')
                    : 'Analysis complete for your business idea.'}
                </p>
                {validateResult.viability_report.market_size && (
                  <p className="text-xs text-gray-500">
                    {typeof validateResult.viability_report.market_size === 'string'
                      ? validateResult.viability_report.market_size
                      : `Market size: ${JSON.stringify(validateResult.viability_report.market_size)}`}
                  </p>
                )}
              </>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <ScoreCard label="Online viability" value={validateResult.online_score || 0} color="bg-blue-500" />
            <ScoreCard label="Physical viability" value={validateResult.physical_score || 0} color="bg-green-500" />
            <ScoreCard
              label="Overall confidence"
              value={Number((((validateResult.online_score || 0) + (validateResult.physical_score || 0)) / 20).toFixed(1))}
              color="bg-amber-500"
              suffix="/10"
            />
          </div>

          {/* Viability Analysis (from AI) */}
          {validateResult.viability_report && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-gray-900">4P's market intelligence</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-green-100 text-green-700">Free preview</span>
              </div>
              <div className="grid grid-cols-4 gap-3 mb-4">
                <ResultMetricCard
                  label="TAM"
                  value={validateResult.viability_report.tam || (typeof validateResult.viability_report.market_size === 'string' ? validateResult.viability_report.market_size : 'N/A')}
                />
                <ResultMetricCard
                  label="Growth"
                  value={validateResult.viability_report.growth || 'N/A'}
                />
                <ResultMetricCard
                  label="Competition"
                  value={validateResult.viability_report.competition || 'N/A'}
                  color="text-amber-600"
                />
                <ResultMetricCard
                  label="Demand signal"
                  value={validateResult.viability_report.demand_signal || 'N/A'}
                  color="text-green-600"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium mb-2 text-green-600">Advantages</p>
                  <div className="text-xs text-gray-500 leading-relaxed space-y-1">
                    {(validateResult.viability_report.advantages || validateResult.viability_report.strengths || []).slice(0, 3).map((item: string, i: number) => (
                      <p key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</p>
                    ))}
                    {!(validateResult.viability_report.advantages || validateResult.viability_report.strengths || []).length && (
                      <p className="text-gray-400">Analysis data available in full report</p>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-medium mb-2 text-amber-600">Risks to evaluate</p>
                  <div className="text-xs text-gray-500 leading-relaxed space-y-1">
                    {(validateResult.viability_report.risks || validateResult.viability_report.weaknesses || []).slice(0, 3).map((item: string, i: number) => (
                      <p key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</p>
                    ))}
                    {!(validateResult.viability_report.risks || validateResult.viability_report.weaknesses || []).length && (
                      <p className="text-gray-400">Risk analysis available in full report</p>
                    )}
                  </div>
                </div>
              </div>
              {validateResult.viability_report.key_actions && (
                <div className="mt-3">
                  <h5 className="text-sm font-medium text-gray-700 mb-2">Key Actions</h5>
                  <ul className="space-y-1">
                    {(validateResult.viability_report.key_actions as string[]).map((action: string, i: number) => (
                      <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                        <ChevronRight className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <BlurGate
            title="Unlock full feasibility study"
            priceLabel="Get report — $25"
            subtitle="Startup costs, revenue projections, competitive landscape, top locations, and 90-day launch plan."
            onPurchase={() => handleReportCheckout('feasibility_study')}
            loading={checkoutLoading}
          >
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">Full feasibility breakdown</p>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <ResultMetricCard label="Startup cost range" value="$150K - $350K" />
                <ResultMetricCard label="Break-even timeline" value="12-18 months" />
                <ResultMetricCard label="Revenue model" value="Fee-for-service" />
                <ResultMetricCard label="Top locations" value="Austin, Denver, Raleigh" />
              </div>
              <p className="text-xs text-gray-500">Detailed competitive landscape with pricing benchmarks, staffing models, and 90-day launch timeline...</p>
            </div>
          </BlurGate>

          {validateResult.similar_opportunities && validateResult.similar_opportunities.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">Related opportunities</p>
              <div className="space-y-2">
                {validateResult.similar_opportunities.map((opp) => (
                  <OppRow key={opp.id} title={opp.title} score={opp.score} to={`/opportunity/${opp.id}`} />
                ))}
              </div>
            </div>
          )}

          {/* Error/Success messages */}
          {reportError && (
            <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
              <span className="text-sm text-red-800">{reportError}</span>
              <button onClick={() => setReportError(null)} className="ml-auto text-red-400 hover:text-red-600 text-sm font-medium">Dismiss</button>
            </div>
          )}
          {reportSuccess && (
            <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 shrink-0" />
              <span className="text-sm text-green-800">Report saved to your account!</span>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => handleReportCheckout('feasibility_study')}
                disabled={checkoutLoading}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-white text-sm font-medium bg-amber-500 hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                Get full feasibility — $25
              </button>
              <button
                onClick={() => {
                  if (!token) { window.location.href = '/signin'; return }
                  saveReportMutation.mutate({
                    reportType: 'feasibility_study',
                    title: `Business Idea: ${ideaDescription.slice(0, 50)}...`,
                    content: JSON.stringify(validateResult, null, 2),
                  })
                }}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {saveReportMutation.isPending ? 'Saving...' : 'Save free summary'}
              </button>
            </div>
            <div className="flex items-center justify-center gap-2 mt-2 text-[10px] text-gray-400">
              <span className="flex items-center gap-0.5"><Shield className="w-3 h-3" /> Secure payment</span>
              <span>·</span>
              <span>Money-back guarantee</span>
              <span>·</span>
              <span>Powered by Stripe</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderSearchTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Search Opportunities</h3>
        <p className="text-sm text-gray-500 mb-4">
          Browse our database of validated opportunities by keyword or category.
        </p>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Keyword</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g., coffee, fitness, delivery..."
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              value={searchCategory}
              onChange={(e) => setSearchCategory(e.target.value)}
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 bg-white"
            >
              <option value="">All Categories</option>
              <option value="work_productivity">💼 Work & Productivity</option>
              <option value="money_finance">💰 Money & Finance</option>
              <option value="health_wellness">🏥 Health & Wellness</option>
              <option value="home_living">🏠 Home & Living</option>
              <option value="technology">💻 Technology</option>
              <option value="transportation">🚗 Transportation</option>
              <option value="education">📚 Education</option>
              <option value="shopping_services">🛒 Shopping & Services</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => searchMutation.mutate()}
          disabled={searchMutation.isPending}
          className="w-full px-6 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 flex items-center justify-center gap-2"
        >
          {searchMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              Search Ideas
            </>
          )}
        </button>
      </div>

      {searchResult?.success && (
        <div className="space-y-4 animate-fade-in">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-900">
                Search results{searchQuery ? ` for "${searchQuery}"` : ''}
              </span>
              <span className="text-xs text-gray-400">
                {searchResult.total_count || 0} opportunities
                {searchResult.trends ? ` · ${searchResult.trends.length} trends` : ''}
                {searchResult.processing_time_ms ? ` · ${searchResult.processing_time_ms}ms` : ''}
              </span>
            </div>
          </div>

          {searchResult.synthesis && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 border-l-[3px] border-l-amber-500">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">AI synthesis</p>
              <p className="text-sm text-gray-700 leading-relaxed">
                {typeof searchResult.synthesis === 'string'
                  ? searchResult.synthesis
                  : searchResult.synthesis.summary || searchResult.synthesis.narrative || JSON.stringify(searchResult.synthesis)}
              </p>
            </div>
          )}

          {searchResult.trends && searchResult.trends.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">
                <TrendingUp className="w-4 h-4 inline mr-1 text-amber-500" />
                Trending now
              </p>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                {searchResult.trends.map((trend) => (
                  <div key={trend.id} className="rounded-lg p-3 border border-amber-100 bg-gradient-to-br from-amber-50 to-orange-50">
                    <div className="text-sm font-medium text-gray-900">{trend.name}</div>
                    <div className="text-xs text-gray-500 mt-1">{trend.description}</div>
                    <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
                      <span>Strength: {trend.strength}%</span>
                      {trend.growth_rate != null && <span className="text-green-600">Growth: +{trend.growth_rate}%</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {searchResult.opportunities && searchResult.opportunities.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-900">Opportunities ({searchResult.total_count || searchResult.opportunities.length})</span>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span>Sort: Score</span>
                </div>
              </div>
              <div className="space-y-2">
                {searchResult.opportunities.slice(0, 5).map((opp) => (
                  <Link
                    key={opp.id}
                    to={`/opportunity/${opp.id}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                  >
                    <div className="flex-1 mr-4">
                      <div className="text-sm font-medium text-gray-900">{opp.title}</div>
                      <div className="text-xs text-gray-500">{opp.category}</div>
                    </div>
                    <div className="flex items-center gap-4">
                      {opp.product_score != null && (
                        <FourPsBar
                          product={opp.product_score || 50}
                          price={opp.price_score || 50}
                          place={opp.place_score || 50}
                          promotion={opp.promotion_score || 50}
                        />
                      )}
                      <div className="text-right min-w-[40px]">
                        <div className="text-sm font-medium text-amber-500">{opp.score}</div>
                        <div className="text-[10px] text-gray-400">score</div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {searchResult.opportunities && searchResult.opportunities.length > 5 && (
            <BlurGate
              title={`See all ${searchResult.total_count || searchResult.opportunities.length} opportunities with full data`}
              priceLabel="Unlock with Market Analysis — $99"
              subtitle="Full opportunity details, source data, and geographic intelligence."
              onPurchase={() => handleReportCheckout('market_analysis')}
              loading={checkoutLoading}
            >
              <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2">
                {searchResult.opportunities.slice(5, 9).map((opp) => (
                  <div key={opp.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{opp.title}</div>
                      <div className="text-xs text-gray-500">{opp.category}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-amber-500">{opp.score}</div>
                      <div className="text-[10px] text-gray-400">score</div>
                    </div>
                  </div>
                ))}
              </div>
            </BlurGate>
          )}

          {(!searchResult.opportunities || searchResult.opportunities.length === 0) && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
              No opportunities found. Try different keywords.
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => handleReportCheckout('market_analysis')}
                disabled={checkoutLoading}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-white text-sm font-medium bg-amber-500 hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                Generate market report — $99
              </button>
              <button
                onClick={() => {
                  if (!token) { window.location.href = '/signin'; return }
                  saveReportMutation.mutate({
                    reportType: 'market_analysis',
                    title: `Search Results: ${searchQuery || searchCategory || 'All'}`,
                    content: JSON.stringify(searchResult, null, 2),
                  })
                }}
                disabled={saveReportMutation.isPending}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {saveReportMutation.isPending ? 'Saving...' : 'Export search results'}
              </button>
            </div>
            <div className="flex items-center justify-center gap-2 mt-2 text-[10px] text-gray-400">
              <span className="flex items-center gap-0.5"><Shield className="w-3 h-3" /> Secure payment</span>
              <span>·</span>
              <span>Money-back guarantee</span>
              <span>·</span>
              <span>Powered by Stripe</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderLocationTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Analyze Market Location</h3>
        <p className="text-sm text-gray-500 mb-4">
          Enter a city and business type to get detailed market analysis, demographics, and competition data.
        </p>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
            <input
              type="text"
              value={locationCity}
              onChange={(e) => setLocationCity(e.target.value)}
              placeholder="e.g., Miami, Florida"
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Business Type</label>
            <input
              type="text"
              value={locationBusiness}
              onChange={(e) => setLocationBusiness(e.target.value)}
              placeholder="e.g., Coffee shop, Fitness studio, Dog grooming..."
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
            />
          </div>
        </div>

        <button
          onClick={() => locationMutation.mutate()}
          disabled={!locationCity.trim() || !locationBusiness.trim() || locationMutation.isPending}
          className="w-full px-6 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 flex items-center justify-center gap-2"
        >
          {locationMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Analyzing Market...
            </>
          ) : (
            <>
              <Map className="w-5 h-5" />
              Analyze Location
            </>
          )}
        </button>
      </div>

      {locationResult?.success && (
        <div className="space-y-4 animate-fade-in">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-gray-900">
                Market analysis: {locationResult.business_description} in {locationResult.city}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-100 text-green-700">
                {locationResult.geo_analysis?.market_density === 'high' ? 'Strong market' : locationResult.geo_analysis?.market_density === 'low' ? 'Emerging market' : 'Favorable'}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Inferred category: {locationResult.inferred_category}
              {locationResult.from_cache && ' · Cached result'}
              {locationResult.processing_time_ms && ` · Analyzed in ${(locationResult.processing_time_ms / 1000).toFixed(1)}s`}
            </p>
          </div>

          {locationResult.map_data && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="h-56 relative bg-gradient-to-br from-green-50 to-green-100">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <Map className="w-10 h-10 text-green-600 mx-auto mb-2" />
                    <p className="text-sm font-medium text-gray-700">Interactive map with competitor pins</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {locationResult.map_data.totalFeatures || 0} features plotted · 3mi & 5mi radius
                    </p>
                    <div className="flex items-center justify-center gap-3 mt-3 text-[10px]">
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block"></span> 3mi radius</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400 inline-block"></span> 5mi radius</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block"></span> Competitors</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {locationResult.geo_analysis && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="text-xs text-gray-500 mb-1">Market score</p>
                <div className="text-3xl font-medium text-gray-900 mb-2">
                  {locationResult.geo_analysis.market_score || locationResult.geo_analysis.overall_score || 75}
                  <span className="text-lg text-gray-400">/100</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full mb-3">
                  <div
                    className="h-2 rounded-full bg-green-500"
                    style={{ width: `${locationResult.geo_analysis.market_score || locationResult.geo_analysis.overall_score || 75}%` }}
                  />
                </div>
                <div className="space-y-1 text-xs text-gray-500">
                  {locationResult.geo_analysis.median_income && (
                    <p>High income area (${(locationResult.geo_analysis.median_income || 0).toLocaleString()} median)</p>
                  )}
                  {locationResult.geo_analysis.population && (
                    <p>Population: {(locationResult.geo_analysis.population || 0).toLocaleString()}</p>
                  )}
                  <p>{locationResult.geo_analysis.competitors?.length || 0} existing competitors</p>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="text-xs font-medium text-gray-900 mb-3">Demographics</p>
                <div className="space-y-2">
                  {locationResult.geo_analysis.population && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Population</span>
                      <span className="font-medium text-gray-900">{(locationResult.geo_analysis.population).toLocaleString()}</span>
                    </div>
                  )}
                  {locationResult.geo_analysis.median_income && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Median income</span>
                      <span className="font-medium text-gray-900">${(locationResult.geo_analysis.median_income).toLocaleString()}</span>
                    </div>
                  )}
                  {locationResult.geo_analysis.median_age && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">Median age</span>
                      <span className="font-medium text-gray-900">{locationResult.geo_analysis.median_age}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Competition level</span>
                    <span className="font-medium text-amber-600 capitalize">
                      {locationResult.geo_analysis.market_density || 'Moderate'} ({locationResult.geo_analysis.competitors?.length || 0})
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {locationResult.geo_analysis && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">4P's intelligence</p>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { icon: '📦', label: 'Product', score: locationResult.geo_analysis.product_score, detail: locationResult.geo_analysis.product_detail },
                  { icon: '💲', label: 'Price', score: locationResult.geo_analysis.price_score, detail: locationResult.geo_analysis.price_detail },
                  { icon: '📍', label: 'Place', score: locationResult.geo_analysis.place_score, detail: locationResult.geo_analysis.place_detail },
                  { icon: '📢', label: 'Promotion', score: locationResult.geo_analysis.promotion_score, detail: locationResult.geo_analysis.promotion_detail },
                ].map(p => (
                  <div key={p.label} className="rounded-lg p-3 bg-gray-50">
                    <div className="flex items-center gap-1 mb-1">
                      <span className="text-sm">{p.icon}</span>
                      <span className="text-xs font-medium text-gray-900">{p.label}</span>
                    </div>
                    <div className="text-lg font-medium text-gray-900 mb-1">{p.score ?? 'N/A'}</div>
                    {p.detail && <div className="text-[10px] text-gray-500 leading-relaxed">{p.detail}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {locationResult.market_report && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 border-l-[3px] border-l-amber-500">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Market intelligence</p>
              <p className="text-sm text-gray-700 leading-relaxed">
                {typeof locationResult.market_report === 'string'
                  ? locationResult.market_report
                  : (locationResult.market_report as Record<string, unknown>).summary as string || JSON.stringify(locationResult.market_report)}
              </p>
            </div>
          )}

          {locationResult.site_recommendations && locationResult.site_recommendations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">Site recommendations</p>
              <div className="space-y-2">
                {locationResult.site_recommendations.map((site, idx) => {
                  const priority = site.priority || site.score || (idx === 0 ? 'High' : idx === 1 ? 'High' : 'Medium')
                  const priorityStr = typeof priority === 'number' ? (priority >= 80 ? 'High' : priority >= 60 ? 'Medium' : 'Low') : priority
                  return (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        priorityStr === 'High' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {priorityStr}
                      </span>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{site.name || site.area || `Site ${idx + 1}`}</div>
                        {site.reason && <div className="text-xs text-gray-500">{site.reason}</div>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <BlurGate
            title="Unlock competitor deep dive"
            priceLabel="Get location report — $25"
            subtitle="Full competitor profiles, pricing comparison, customer sentiment, and foot traffic analysis."
            onPurchase={() => handleReportCheckout('feasibility_study')}
            loading={checkoutLoading}
          >
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">Competitor profiles ({locationResult.geo_analysis?.competitors?.length || 0})</p>
              <div className="space-y-2">
                {(locationResult.geo_analysis?.competitors || []).slice(0, 3).map((c, i) => (
                  <div key={i} className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">
                    {typeof c === 'string' ? c : (c as { name?: string }).name || `Competitor ${i + 1}`}
                  </div>
                ))}
                {(!locationResult.geo_analysis?.competitors || locationResult.geo_analysis.competitors.length === 0) && (
                  <>
                    <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">Competitor profile data available in full report</div>
                    <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">Pricing benchmarks & customer sentiment</div>
                  </>
                )}
              </div>
            </div>
          </BlurGate>

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => handleReportCheckout('feasibility_study')}
                disabled={checkoutLoading}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-white text-sm font-medium bg-amber-500 hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                Get location report — $25
              </button>
              <button
                onClick={() => {
                  if (!token) { window.location.href = '/signin'; return }
                  saveReportMutation.mutate({
                    reportType: 'market_analysis',
                    title: `Location Analysis: ${locationResult.business_description} in ${locationResult.city}`,
                    content: JSON.stringify(locationResult, null, 2),
                  })
                }}
                disabled={saveReportMutation.isPending}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {saveReportMutation.isPending ? 'Saving...' : 'Save free summary'}
              </button>
            </div>
            <div className="flex items-center justify-center gap-2 mt-2 text-[10px] text-gray-400">
              <span className="flex items-center gap-0.5"><Shield className="w-3 h-3" /> Secure payment</span>
              <span>·</span>
              <span>Money-back guarantee</span>
              <span>·</span>
              <span>Powered by Stripe</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderCloneTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Clone a Successful Business</h3>
        <p className="text-sm text-gray-500 mb-4">
          Enter a successful business to analyze its success factors and find similar markets where you could replicate it.
        </p>

        <div className="space-y-4 mb-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
              <input
                type="text"
                value={cloneBusinessName}
                onChange={(e) => setCloneBusinessName(e.target.value)}
                placeholder="e.g., Sweetgreen, Blue Bottle Coffee..."
                className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Business Address</label>
              <input
                type="text"
                value={cloneBusinessAddress}
                onChange={(e) => setCloneBusinessAddress(e.target.value)}
                placeholder="e.g., 123 Main St, San Francisco, CA"
                className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              />
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Target City <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="text"
                value={cloneTargetCity}
                onChange={(e) => setCloneTargetCity(e.target.value)}
                placeholder="e.g., Austin"
                className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Target State <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="text"
                value={cloneTargetState}
                onChange={(e) => setCloneTargetState(e.target.value)}
                placeholder="e.g., TX"
                maxLength={2}
                className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 uppercase"
              />
            </div>
          </div>
        </div>

        <button
          onClick={() => cloneMutation.mutate()}
          disabled={!cloneBusinessName.trim() || !cloneBusinessAddress.trim() || cloneMutation.isPending}
          className="w-full px-6 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 flex items-center justify-center gap-2"
        >
          {cloneMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Analyzing Business...
            </>
          ) : (
            <>
              <Copy className="w-5 h-5" />
              Find Clone Locations
            </>
          )}
        </button>
      </div>

      {cloneResult?.success && (
        <div className="space-y-4 animate-fade-in">
          {cloneResult.source_business && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-3">Source business</p>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{cloneResult.source_business.name}</p>
                  <p className="text-xs text-gray-500">{cloneBusinessAddress}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {cloneResult.source_business.category && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700">
                        {cloneResult.source_business.category}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">Analysis radius</div>
                  <div className="text-sm font-medium text-gray-900">{cloneResult.analysis_radius_miles || 3} miles</div>
                </div>
              </div>
              {cloneResult.source_business.success_factors && cloneResult.source_business.success_factors.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs font-medium text-gray-700 mb-2">Success factors</div>
                  <div className="flex flex-wrap gap-1.5">
                    {cloneResult.source_business.success_factors.map((factor, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] rounded font-medium">
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {cloneResult.source_business.demographics && (
                <div className="grid grid-cols-4 gap-3 mt-4">
                  <ResultMetricCard label="Category" value={cloneResult.source_business.category || 'N/A'} />
                  <ResultMetricCard label="Population" value={(cloneResult.source_business.demographics.population || 0).toLocaleString()} />
                  <ResultMetricCard label="Median income" value={`$${(cloneResult.source_business.demographics.median_income || 0).toLocaleString()}`} />
                  <ResultMetricCard label="Competition" value={`${cloneResult.source_business.demographics.competition_count || 0} nearby`} />
                </div>
              )}
            </div>
          )}

          {cloneResult.source_business?.demographics && cloneResult.matching_locations && cloneResult.matching_locations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">Source vs Target comparison</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-2 pr-4 text-gray-500 font-medium">Metric</th>
                      <th className="text-right py-2 px-4 text-gray-500 font-medium">Source</th>
                      <th className="text-right py-2 pl-4 text-gray-500 font-medium">Top target</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr>
                      <td className="py-2 pr-4 text-gray-700">Population</td>
                      <td className="py-2 px-4 text-right font-medium text-gray-900">{(cloneResult.source_business.demographics.population || 0).toLocaleString()}</td>
                      <td className="py-2 pl-4 text-right font-medium text-gray-900">{(cloneResult.matching_locations[0]?.population || 0).toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-gray-700">Median income</td>
                      <td className="py-2 px-4 text-right font-medium text-gray-900">${(cloneResult.source_business.demographics.median_income || 0).toLocaleString()}</td>
                      <td className="py-2 pl-4 text-right font-medium text-gray-900">${(cloneResult.matching_locations[0]?.median_income || 0).toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-gray-700">Competition</td>
                      <td className="py-2 px-4 text-right font-medium text-gray-900">{cloneResult.source_business.demographics.competition_count || 0} nearby</td>
                      <td className="py-2 pl-4 text-right font-medium text-gray-900">{cloneResult.matching_locations[0]?.competition_match || 0}% match</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-gray-700">Demographics match</td>
                      <td className="py-2 px-4 text-right font-medium text-green-600">baseline</td>
                      <td className="py-2 pl-4 text-right font-medium text-green-600">{cloneResult.matching_locations[0]?.demographics_match || 0}%</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-gray-700">Overall similarity</td>
                      <td className="py-2 px-4 text-right font-medium text-amber-500">100%</td>
                      <td className="py-2 pl-4 text-right font-medium text-amber-500">{cloneResult.matching_locations[0]?.similarity_score || 0}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {cloneResult.matching_locations && cloneResult.matching_locations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm font-medium text-gray-900 mb-3">
                Matching locations ({cloneResult.matching_locations.length})
              </p>
              <div className="space-y-3">
                {cloneResult.matching_locations.map((loc, idx) => (
                  <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="text-sm font-semibold text-gray-900">{loc.name}</div>
                        <div className="text-xs text-gray-500">{loc.city}, {loc.state}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-amber-500">{loc.similarity_score}%</div>
                        <div className="text-[10px] text-gray-400">Match</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-4 gap-3 mb-3 text-xs">
                      <div>
                        <div className="text-gray-500">Demographics</div>
                        <div className="font-medium text-gray-900">{loc.demographics_match}%</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Competition</div>
                        <div className="font-medium text-gray-900">{loc.competition_match}%</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Median income</div>
                        <div className="font-medium text-gray-900">${(loc.median_income || 0).toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Population</div>
                        <div className="font-medium text-gray-900">{(loc.population || 0).toLocaleString()}</div>
                      </div>
                    </div>

                    {loc.key_factors && loc.key_factors.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {loc.key_factors.map((factor, fidx) => (
                          <span key={fidx} className="px-2 py-0.5 bg-gray-200 text-gray-700 text-[10px] rounded">
                            {factor}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {cloneResult.matching_locations && cloneResult.matching_locations.length > 0 && (
            <BlurGate
              title="Unlock deep clone analysis"
              priceLabel="Deep clone top location — $89"
              subtitle="Detailed 3mi and 5mi radius analysis with demographics, competition density, and match confidence."
              onPurchase={() => handleReportCheckout('strategic_assessment')}
              loading={checkoutLoading}
            >
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <p className="text-sm font-medium text-gray-900 mb-3">Deep clone: {cloneResult.matching_locations[0]?.name}</p>
                <div className="grid grid-cols-2 gap-3">
                  <ResultMetricCard label="3-mile population" value={(cloneResult.matching_locations[0]?.population || 45200).toLocaleString()} />
                  <ResultMetricCard label="5-mile population" value={(((cloneResult.matching_locations[0]?.population || 45200) * 2.8) | 0).toLocaleString()} />
                  <ResultMetricCard label="Competitor density" value={`${cloneResult.matching_locations[0]?.competition_match || 0}% match`} />
                  <ResultMetricCard label="Match confidence" value={`${cloneResult.matching_locations[0]?.similarity_score || 0}%`} />
                </div>
              </div>
            </BlurGate>
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => handleReportCheckout('strategic_assessment')}
                disabled={checkoutLoading}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-white text-sm font-medium bg-amber-500 hover:bg-amber-600 disabled:opacity-50 transition-colors"
              >
                Deep clone top location — $89
              </button>
              <button
                onClick={() => {
                  if (!token) { window.location.href = '/signin'; return }
                  saveReportMutation.mutate({
                    reportType: 'strategic_assessment',
                    title: `Clone Analysis: ${cloneBusinessName}`,
                    content: JSON.stringify(cloneResult, null, 2),
                  })
                }}
                disabled={saveReportMutation.isPending}
                className="flex-1 min-w-[140px] py-3 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {saveReportMutation.isPending ? 'Saving...' : 'Save free summary'}
              </button>
            </div>
            <div className="flex items-center justify-center gap-2 mt-2 text-[10px] text-gray-400">
              <span className="flex items-center gap-0.5"><Shield className="w-3 h-3" /> Secure payment</span>
              <span>·</span>
              <span>Money-back guarantee</span>
              <span>·</span>
              <span>Powered by Stripe</span>
            </div>
          </div>

          <div className="text-xs text-gray-400 text-center">
            Analysis radius: {cloneResult.analysis_radius_miles || 3} miles
            {cloneResult.processing_time_ms && ` · Processed in ${cloneResult.processing_time_ms}ms`}
          </div>
        </div>
      )}
    </div>
  )

  // No authentication required - guest access allowed
  return (
    <div className="min-h-screen bg-stone-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Consultant Studio</h1>
          <p className="text-sm text-gray-600 mt-1">
            AI-powered tools for business validation, opportunity discovery, and market intelligence.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-xl border border-gray-200 p-1 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-1">
            {TABS.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
                    isActive
                      ? 'bg-amber-500 text-white shadow-sm'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Tab Description */}
        <div className="mb-6 text-sm text-gray-600">
          {TABS.find((t) => t.id === activeTab)?.description}
        </div>

        {/* Unified Layout: Content (left) + Report Selection (right) */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: Analysis Content */}
          <div className="lg:col-span-3">
            {activeTab === 'validate' && renderValidateTab()}
            {activeTab === 'search' && renderSearchTab()}
            {activeTab === 'location' && renderLocationTab()}
            {activeTab === 'clone' && renderCloneTab()}
          </div>

          {/* Right: Report Selection Panel */}
          <div className="lg:col-span-2">
            <div className="sticky top-8">
              <ReportSelectionPanel
                ideaDescription={
                  activeTab === 'validate' ? ideaDescription :
                  activeTab === 'search' ? searchQuery :
                  activeTab === 'location' ? `${locationBusiness} in ${locationCity}` :
                  activeTab === 'clone' ? `Clone ${cloneBusinessName}` : ''
                }
                consultantResult={
                  activeTab === 'validate' ? validateResult :
                  activeTab === 'search' ? searchResult :
                  activeTab === 'location' ? locationResult :
                  activeTab === 'clone' ? cloneResult : null
                }
              />
            </div>
          </div>
        </div>

        {/* Saved Reports Sidebar */}
        {savedReports.length > 0 && (
          <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              <FileText className="w-5 h-5 inline mr-2" />
              Saved Reports This Session
            </h3>
            <div className="space-y-2">
              {savedReports.map((report) => (
                <div key={report.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium text-gray-900">{report.title}</div>
                    <div className="text-xs text-gray-500">{report.report_type}</div>
                  </div>
                  <CheckCircle className="w-5 h-5 text-green-500" />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
