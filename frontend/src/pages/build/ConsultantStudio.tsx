import { useState, useEffect, useRef, type React } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Lightbulb,
  Search,
  MapPin,
  Copy,
  Loader2,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  BarChart3,
  Sparkles,
  Zap,
  Globe,
  Store,
  ChevronRight,
  Star,
  Target,
  Building2,
  Users,
  DollarSign,
  FileText,
  Shield,
  Briefcase,
  Presentation,
  Lock,
  ShoppingCart,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

type TabId = 'validate' | 'search' | 'location' | 'clone'

interface ValidateResult {
  success: boolean
  idea_description?: string
  recommendation?: string
  online_score?: number
  physical_score?: number
  verdict_summary?: string
  verdict_detail?: string
  advantages?: string[]
  risks?: string[]
  four_ps_scores?: Record<string, number>
  narrative_verdict?: string
  validation_score?: number
  competition_level?: string
  key_competitors?: string[]
  market_heat_sources?: string[]
  data_quality?: {
    completeness?: number
    sources?: string[]
    confidence?: string
    recommendation?: string
  }
  error?: string
}

interface SearchResult {
  success: boolean
  opportunities?: Array<{
    id: number
    title: string
    category: string
    score: number
    description?: string
  }>
  trends?: Array<{
    name: string
    category: string
    momentum: number
  }>
  narrative_summary?: string
  narrative_verdict?: string
  signal_surge_pct?: number
  top_signals_this_week?: Array<Record<string, any>>
  is_preview_mode?: boolean
  error?: string
}

interface LocationResult {
  success: boolean
  city?: string
  inferred_category?: string
  narrative_summary?: string
  proceed_recommendation?: string
  avg_rating?: number
  foot_traffic_growth?: number
  supply_label?: string
  demographic_snapshot?: Record<string, any>
  micro_markets?: Array<Record<string, any>>
  error?: string
}

interface CloneResult {
  success: boolean
  source_business?: Record<string, any>
  matching_locations?: Array<{
    name: string
    city: string
    state: string
    similarity_score: number
    demographics_match: number
    competition_match: number
    population?: number
    median_income?: number
  }>
  narrative_summary?: string
  replicability_label?: string
  why_it_works?: string[]
  error?: string
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-green-600 bg-green-50'
  if (score >= 60) return 'text-amber-600 bg-amber-50'
  return 'text-red-600 bg-red-50'
}

const getRecommendationIcon = (rec?: string) => {
  if (rec === 'online') return <Globe className="w-5 h-5 text-blue-500" />
  if (rec === 'physical') return <Store className="w-5 h-5 text-emerald-500" />
  return <Zap className="w-5 h-5 text-purple-500" />
}

const getRecommendationLabel = (rec?: string) => {
  if (rec === 'online') return 'Online Business'
  if (rec === 'physical') return 'Physical Location'
  return 'Hybrid Model'
}

export default function ConsultantStudio() {
  const { token, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>('validate')

  const [ideaInput, setIdeaInput] = useState('')
  const [validating, setValidating] = useState(false)
  const [validateResult, setValidateResult] = useState<ValidateResult | null>(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [searchCategory, setSearchCategory] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null)

  const [locCity, setLocCity] = useState('')
  const [locBusiness, setLocBusiness] = useState('')
  const [locating, setLocating] = useState(false)
  const [locResult, setLocResult] = useState<LocationResult | null>(null)

  const [cloneName, setCloneName] = useState('')
  const [cloneAddress, setCloneAddress] = useState('')
  const [cloneTargetCity, setCloneTargetCity] = useState('')
  const [cloneTargetState, setCloneTargetState] = useState('')
  const [cloning, setCloning] = useState(false)
  const [cloneResult, setCloneResult] = useState<CloneResult | null>(null)

  // Report generation state
  const [selectedReport, setSelectedReport] = useState('')
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportResult, setReportResult] = useState<any>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  const [reportElapsed, setReportElapsed] = useState(0)

  // Clear report state when switching tabs to prevent cross-tab state leaks
  useEffect(() => {
    setSelectedReport('')
    setGeneratingReport(false)
    setReportResult(null)
    setReportError(null)
    setReportElapsed(0)
  }, [activeTab])

  // Count elapsed seconds while generating a report
  useEffect(() => {
    if (!generatingReport) {
      setReportElapsed(0)
      return
    }
    const interval = setInterval(() => setReportElapsed((prev) => prev + 1), 1000)
    return () => clearInterval(interval)
  }, [generatingReport])

  // Ref to hold the AbortController for cancelling in-flight report requests
  const reportAbortRef = useRef<AbortController | null>(null)

  const REPORTS = [
    { id: 'feasibility_study', name: 'Feasibility Study', description: 'Quick viability check with market validation', price_cents: 2500, icon: Shield },
    { id: 'business_plan', name: 'Business Plan', description: 'Comprehensive strategy document', price_cents: 14900, icon: Briefcase },
    { id: 'financial_model', name: 'Financial Model', description: '5-year projections and unit economics', price_cents: 12900, icon: DollarSign },
    { id: 'market_analysis', name: 'Market Analysis', description: 'TAM/SAM/SOM with competitive landscape', price_cents: 9900, icon: BarChart3 },
    { id: 'strategic_assessment', name: 'Strategic Assessment', description: 'SWOT analysis and strategic positioning', price_cents: 8900, icon: Target },
    { id: 'pestle_analysis', name: 'PESTLE Analysis', description: 'Political, Economic, Social, Technological, Legal, Environmental factors', price_cents: 9900, icon: Shield },
    { id: 'pitch_deck', name: 'Pitch Deck', description: 'Investor presentation outline and key slides', price_cents: 7900, icon: Presentation },
    { id: 'location_analysis', name: 'Location Analysis', description: 'Top 5 locations ranked by 8 proprietary formulas', price_cents: 11900, icon: MapPin },
  ]

  const handleGenerateReport = async (reportType: string, ideaDescription: string) => {
    if (!isAuthenticated || !token) {
      setReportError('Sign in to generate professional reports.')
      return
    }
    setSelectedReport(reportType)
    setGeneratingReport(true)
    setReportError(null)
    setReportResult(null)
    setReportElapsed(0)
    const controller = new AbortController()
    reportAbortRef.current = controller
    try {
      const res = await fetch('/api/v1/report-pricing/generate-free-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ report_type: reportType, idea_description: ideaDescription }),
        signal: controller.signal,
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Failed to generate report'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      const data = await res.json()
      setReportResult(data)
    } catch (e: any) {
      if (e.name === 'AbortError') {
        setReportError('Report generation was cancelled.')
      } else if (e.message?.toLowerCase().includes('timeout') || e.message?.toLowerCase().includes('abort')) {
        setReportError('Report generation timed out. Please try again — it may take 30–60 seconds.')
      } else {
        setReportError(e instanceof Error ? e.message : 'Failed to generate report')
      }
    } finally {
      setGeneratingReport(false)
      reportAbortRef.current = null
    }
  }

  const ReportPanel = ({ ideaDescription }: { ideaDescription?: string }) => (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mt-6 relative">
      {generatingReport && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm rounded-xl flex items-center justify-center z-10">
          <div className="text-center p-6">
            <Loader2 className="w-8 h-8 animate-spin text-[#D97757] mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-900 mb-1">
              Generating {REPORTS.find(r => r.id === selectedReport)?.name || 'Report'}...
            </p>
            <p className="text-xs text-gray-500">
              Elapsed {reportElapsed}s · This may take 30–60 seconds
            </p>
            {reportElapsed >= 20 && (
              <p className="text-xs text-amber-600 mt-2">
                Still working — our AI is analyzing market data deeply.
              </p>
            )}
            <button
              type="button"
              onClick={() => reportAbortRef.current?.abort()}
              className="mt-3 px-3 py-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-[#D97757]" />
        <h3 className="font-semibold text-gray-900">Generate Professional Report</h3>
      </div>
      <p className="text-sm text-gray-600 mb-4">
        Turn your analysis into a comprehensive, investor-ready document.
      </p>
      <div className="grid md:grid-cols-2 gap-3">
        {REPORTS.map((r) => {
          const Icon = r.icon
          const isSelected = selectedReport === r.id
          const isGenerated = isSelected && !!reportResult
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => handleGenerateReport(r.id, ideaDescription || '')}
              disabled={generatingReport}
              className={`text-left p-4 rounded-lg border transition-all ${
                isGenerated
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-200 hover:border-[#D97757] hover:bg-[#D97757]/5'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-gray-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-gray-900">{r.name}</span>
                    <span className="text-sm font-semibold text-gray-900">${(r.price_cents / 100).toFixed(0)}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{r.description}</p>
                  {isGenerated && (
                    <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-2">
                      <CheckCircle className="w-3 h-3" />
                      Generated
                    </span>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>
      {reportError && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {reportError}
          {!isAuthenticated && (
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => navigate('/login')} className="text-sm underline font-medium">Sign In</button>
              <span className="text-gray-400">or</span>
              <button type="button" onClick={() => navigate('/signup')} className="text-sm underline font-medium">Create Account</button>
            </div>
          )}
        </div>
      )}
      {reportResult && (
        <div className="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-sm font-medium text-gray-900">Report Generated</span>
          </div>
          <pre className="text-xs text-gray-600 overflow-auto max-h-48 bg-white p-3 rounded border">
            {JSON.stringify(reportResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const handleValidate = async () => {
    if (!ideaInput.trim() || ideaInput.length < 10) return
    setValidating(true)
    setValidateResult(null)
    try {
      const res = await fetch('/api/v1/consultant/validate-idea', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ idea_description: ideaInput }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Request failed'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      const data = await res.json()
      setValidateResult(data)
    } catch (e: any) {
      setValidateResult({ success: false, error: e instanceof Error ? e.message : 'An error occurred.' })
    } finally {
      setValidating(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    setSearchResult(null)
    try {
      const body: Record<string, any> = { query: searchQuery }
      if (searchCategory) body.category = searchCategory
      const res = await fetch('/api/v1/consultant/search-ideas', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Request failed'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      const data = await res.json()
      setSearchResult(data)
    } catch (e: any) {
      setSearchResult({ success: false, error: e instanceof Error ? e.message : 'An error occurred.' })
    } finally {
      setSearching(false)
    }
  }

  const handleLocation = async () => {
    if (!locCity.trim() || !locBusiness.trim()) return
    setLocating(true)
    setLocResult(null)
    try {
      const res = await fetch('/api/v1/consultant/identify-location', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ city: locCity, business_description: locBusiness }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Request failed'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      const data = await res.json()
      setLocResult(data)
    } catch (e: any) {
      setLocResult({ success: false, error: e instanceof Error ? e.message : 'An error occurred.' })
    } finally {
      setLocating(false)
    }
  }

  const handleClone = async () => {
    if (!cloneName.trim() || !cloneAddress.trim()) return
    setCloning(true)
    setCloneResult(null)
    try {
      const body: Record<string, any> = { business_name: cloneName, business_address: cloneAddress }
      if (cloneTargetCity) body.target_city = cloneTargetCity
      if (cloneTargetState) body.target_state = cloneTargetState
      const res = await fetch('/api/v1/consultant/clone-success', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Request failed'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      const data = await res.json()
      setCloneResult(data)
    } catch (e: any) {
      setCloneResult({ success: false, error: e instanceof Error ? e.message : 'An error occurred.' })
    } finally {
      setCloning(false)
    }
  }

  const TABS: { id: TabId; label: string; icon: React.ElementType; description: string }[] = [
    { id: 'validate', label: 'Validate Idea', icon: Lightbulb, description: 'AI-powered viability analysis' },
    { id: 'search', label: 'Search Ideas', icon: Search, description: 'Discover market opportunities' },
    { id: 'location', label: 'Identify Location', icon: MapPin, description: 'Geographic intelligence' },
    { id: 'clone', label: 'Clone Success', icon: Copy, description: 'Replicate winning models' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-white to-stone-100">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-[#D97757] to-[#B85C3D] rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Consultant Studio</h1>
              <p className="text-sm text-gray-500">AI-powered business intelligence and validation</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1" role="tablist">
            {TABS.map((tab) => {
              const Icon = tab.icon
              const isActive = tab.id === activeTab
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                    isActive
                      ? 'border-[#D97757] text-[#D97757]'
                      : 'border-transparent text-gray-500 hover:text-gray-900 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'validate' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-[#D97757]" />
                Validate Your Business Idea
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Describe your business idea and our AI will analyze market viability, competition, and recommend the best model (online, physical, or hybrid).
              </p>
              <textarea
                value={ideaInput}
                onChange={(e) => setIdeaInput(e.target.value)}
                placeholder="e.g., A subscription-based meal prep service targeting busy professionals in urban areas..."
                className="w-full h-32 p-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent resize-none text-sm"
              />
              <div className="flex items-center justify-between mt-4">
                <span className="text-xs text-gray-400">{ideaInput.length} characters (min 10)</span>
                <button
                  onClick={handleValidate}
                  disabled={validating || ideaInput.length < 10}
                  className="px-6 py-2 bg-[#D97757] text-white rounded-lg hover:bg-[#B85C3D] transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {validating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {validating ? 'Analyzing...' : 'Validate Idea'}
                </button>
              </div>
            </div>

            {validateResult && (
              <div className="space-y-4">
                {validateResult.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                    <div className="flex items-center gap-2 text-red-700">
                      <AlertTriangle className="w-5 h-5" />
                      <span className="font-medium">{validateResult.error}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="bg-white rounded-xl border border-gray-200 p-6">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#D97757] to-[#B85C3D] flex items-center justify-center flex-shrink-0">
                          {getRecommendationIcon(validateResult.recommendation)}
                        </div>
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {validateResult.verdict_summary || validateResult.narrative_verdict || 'Analysis Complete'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {validateResult.verdict_detail || 'AI has analyzed your idea across multiple market dimensions.'}
                          </p>
                          <div className="flex items-center gap-4 mt-3 flex-wrap">
                            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(validateResult.validation_score ?? 50)}`}>
                              <Star className="w-3.5 h-3.5" />
                              Score: {validateResult.validation_score ?? 'N/A'}/100
                            </span>
                            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700">
                              {getRecommendationIcon(validateResult.recommendation)}
                              {getRecommendationLabel(validateResult.recommendation)}
                            </span>
                            {validateResult.data_quality && (
                              <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${
                                (validateResult.data_quality.completeness ?? 0) > 0.6
                                  ? 'bg-green-50 text-green-700'
                                  : (validateResult.data_quality.completeness ?? 0) > 0.3
                                  ? 'bg-amber-50 text-amber-700'
                                  : 'bg-gray-50 text-gray-600'
                              }`}>
                                <BarChart3 className="w-3 h-3" />
                                Data Quality: {Math.round((validateResult.data_quality.completeness ?? 0) * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {validateResult.four_ps_scores && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-4">Four P's Analysis</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {Object.entries(validateResult.four_ps_scores).map(([key, score]) => (
                            <div key={key} className="text-center p-4 bg-gray-50 rounded-lg">
                              <div className="text-2xl font-bold text-gray-900">{score}</div>
                              <div className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="grid md:grid-cols-2 gap-4">
                      {validateResult.advantages && validateResult.advantages.length > 0 && (
                        <div className="bg-green-50 rounded-xl border border-green-200 p-6">
                          <h3 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4" />
                            Advantages
                          </h3>
                          <ul className="space-y-2">
                            {validateResult.advantages.map((a, i) => (
                              <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                                <span className="text-green-500 mt-0.5">•</span>
                                {a}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {validateResult.risks && validateResult.risks.length > 0 && (
                        <div className="bg-red-50 rounded-xl border border-red-200 p-6">
                          <h3 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4" />
                            Risks
                          </h3>
                          <ul className="space-y-2">
                            {validateResult.risks.map((r, i) => (
                              <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                                <span className="text-red-500 mt-0.5">•</span>
                                {r}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {validateResult.key_competitors && validateResult.key_competitors.length > 0 && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-3">Key Competitors</h3>
                        <div className="flex flex-wrap gap-2">
                          {validateResult.key_competitors.map((c, i) => (
                            <span key={i} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {validateResult.data_quality && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                          <BarChart3 className="w-4 h-4 text-[#D97757]" />
                          Data Intelligence
                        </h3>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">Data Completeness</span>
                            <div className="flex items-center gap-2">
                              <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    (validateResult.data_quality.completeness ?? 0) > 0.6
                                      ? 'bg-green-500'
                                      : (validateResult.data_quality.completeness ?? 0) > 0.3
                                      ? 'bg-amber-500'
                                      : 'bg-gray-400'
                                  }`}
                                  style={{ width: `${Math.round((validateResult.data_quality.completeness ?? 0) * 100)}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium text-gray-900">
                                {Math.round((validateResult.data_quality.completeness ?? 0) * 100)}%
                              </span>
                            </div>
                          </div>
                          {validateResult.data_quality.sources && validateResult.data_quality.sources.length > 0 && (
                            <div>
                              <span className="text-sm text-gray-600">Sources:</span>
                              <div className="flex flex-wrap gap-2 mt-1">
                                {validateResult.data_quality.sources.map((source, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-stone-100 text-stone-700 rounded text-xs">
                                    {source}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {validateResult.data_quality.recommendation && (
                            <p className="text-xs text-gray-500 mt-2">
                              {validateResult.data_quality.recommendation}
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                    <ReportPanel ideaDescription={ideaInput} />
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'search' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Search className="w-5 h-5 text-[#D97757]" />
                Search Market Opportunities
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Discover trending business opportunities with AI-powered market signals.
              </p>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by keyword, industry, or trend..."
                    className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
                <select
                  value={searchCategory}
                  onChange={(e) => setSearchCategory(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white"
                >
                  <option value="">All Categories</option>
                  <option value="saas">SaaS</option>
                  <option value="healthcare">Healthcare</option>
                  <option value="ecommerce">E-commerce</option>
                  <option value="fintech">FinTech</option>
                  <option value="food">Food & Dining</option>
                  <option value="services">Services</option>
                </select>
                <button
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="px-6 py-2 bg-[#D97757] text-white rounded-lg hover:bg-[#B85C3D] transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>

            {searchResult && (
              <div className="space-y-4">
                {searchResult.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                    <div className="flex items-center gap-2 text-red-700">
                      <AlertTriangle className="w-5 h-5" />
                      <span className="font-medium">{searchResult.error}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    {(searchResult.narrative_summary || searchResult.narrative_verdict) && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <div className="flex items-start gap-3">
                          <TrendingUp className="w-5 h-5 text-[#D97757] mt-0.5" />
                          <div>
                            <h3 className="font-semibold text-gray-900">Market Intelligence</h3>
                            <p className="text-sm text-gray-600 mt-1">
                              {searchResult.narrative_summary || searchResult.narrative_verdict}
                            </p>
                            {searchResult.signal_surge_pct && (
                              <span className="inline-flex items-center gap-1 mt-2 px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm font-medium">
                                <Zap className="w-3.5 h-3.5" />
                                Signal surge: +{searchResult.signal_surge_pct}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {searchResult.opportunities && searchResult.opportunities.length > 0 && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                          <Target className="w-4 h-4 text-[#D97757]" />
                          Opportunities ({searchResult.opportunities.length})
                        </h3>
                        <div className="space-y-3">
                          {searchResult.opportunities.map((opp) => (
                            <div
                              key={opp.id}
                              className="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                              onClick={() => navigate(`/opportunities/${opp.id}`)}
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <h4 className="font-medium text-gray-900">{opp.title}</h4>
                                  <p className="text-sm text-gray-500">{opp.category}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getScoreColor(opp.score)}`}>
                                    {opp.score}/100
                                  </span>
                                  <ChevronRight className="w-4 h-4 text-gray-400" />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {searchResult.trends && searchResult.trends.length > 0 && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                          <BarChart3 className="w-4 h-4 text-[#D97757]" />
                          Trending Signals
                        </h3>
                        <div className="flex flex-wrap gap-2">
                          {searchResult.trends.map((t, i) => (
                            <span key={i} className="px-3 py-1.5 bg-stone-100 text-stone-700 rounded-full text-sm flex items-center gap-1">
                              <TrendingUp className="w-3 h-3" />
                              {t.name}
                              <span className="text-stone-400">({t.momentum})</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {searchResult.is_preview_mode && (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
                        <p className="text-sm text-amber-700">
                          Showing preview results. <button className="underline font-medium" onClick={() => navigate('/signup')}>Sign up</button> for full access.
                        </p>
                      </div>
                    )}
                    <ReportPanel ideaDescription={searchQuery} />
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'location' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-[#D97757]" />
                Identify Location
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Analyze any city for business viability. Our AI evaluates demographics, competition, foot traffic, and market gaps.
              </p>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={locCity}
                    onChange={(e) => setLocCity(e.target.value)}
                    placeholder="e.g., Austin, TX"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Type</label>
                  <input
                    type="text"
                    value={locBusiness}
                    onChange={(e) => setLocBusiness(e.target.value)}
                    placeholder="e.g., coffee shop with drive-thru"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
              </div>
              <button
                onClick={handleLocation}
                disabled={locating || !locCity.trim() || !locBusiness.trim()}
                className="px-6 py-2 bg-[#D97757] text-white rounded-lg hover:bg-[#B85C3D] transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {locating ? <Loader2 className="w-4 h-4 animate-spin" /> : <MapPin className="w-4 h-4" />}
                {locating ? 'Analyzing...' : 'Analyze Location'}
              </button>
            </div>

            {locResult && (
              <div className="space-y-4">
                {locResult.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                    <div className="flex items-center gap-2 text-red-700">
                      <AlertTriangle className="w-5 h-5" />
                      <span className="font-medium">{locResult.error}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="bg-white rounded-xl border border-gray-200 p-6">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-[#D97757] to-[#B85C3D] rounded-lg flex items-center justify-center flex-shrink-0">
                          <MapPin className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">
                            {locResult.city} — {locResult.inferred_category || 'Business Analysis'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {locResult.narrative_summary || 'Location analysis complete.'}
                          </p>
                          <div className="flex items-center gap-3 mt-3">
                            {locResult.avg_rating && (
                              <span className="inline-flex items-center gap-1 px-3 py-1 bg-amber-50 text-amber-700 rounded-full text-sm">
                                <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                                Avg Rating: {locResult.avg_rating.toFixed(1)}
                              </span>
                            )}
                            {locResult.foot_traffic_growth && (
                              <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm">
                                <TrendingUp className="w-3.5 h-3.5" />
                                Traffic: +{locResult.foot_traffic_growth}%
                              </span>
                            )}
                            {locResult.supply_label && (
                              <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">
                                <Building2 className="w-3.5 h-3.5" />
                                Supply: {locResult.supply_label}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {locResult.demographic_snapshot && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-4">Demographic Snapshot</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          {Object.entries(locResult.demographic_snapshot).map(([key, value]) => (
                            <div key={key} className="text-center p-4 bg-gray-50 rounded-lg">
                              <div className="text-lg font-bold text-gray-900">
                                {typeof value === 'number' ? value.toLocaleString() : String(value)}
                              </div>
                              <div className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {locResult.micro_markets && locResult.micro_markets.length > 0 && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-4">Micro Markets</h3>
                        <div className="space-y-3">
                          {locResult.micro_markets.map((m, i) => (
                            <div key={i} className="p-4 bg-gray-50 rounded-lg">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-gray-900">{m.name || `Market ${i + 1}`}</span>
                                {m.score && (
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getScoreColor(m.score)}`}>
                                    {m.score}/100
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <ReportPanel ideaDescription={locBusiness} />
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'clone' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Copy className="w-5 h-5 text-[#D97757]" />
                Clone Success
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Find a successful business and discover similar markets where the same model could thrive.
              </p>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
                  <input
                    type="text"
                    value={cloneName}
                    onChange={(e) => setCloneName(e.target.value)}
                    placeholder="e.g., Joe's Coffee House"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Address</label>
                  <input
                    type="text"
                    value={cloneAddress}
                    onChange={(e) => setCloneAddress(e.target.value)}
                    placeholder="e.g., 123 Main St, Austin, TX 78701"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target City (optional)</label>
                  <input
                    type="text"
                    value={cloneTargetCity}
                    onChange={(e) => setCloneTargetCity(e.target.value)}
                    placeholder="e.g., Denver"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target State (optional)</label>
                  <input
                    type="text"
                    value={cloneTargetState}
                    onChange={(e) => setCloneTargetState(e.target.value)}
                    placeholder="e.g., CO"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#D97757] focus:border-transparent text-sm"
                  />
                </div>
              </div>
              <button
                onClick={handleClone}
                disabled={cloning || !cloneName.trim() || !cloneAddress.trim()}
                className="px-6 py-2 bg-[#D97757] text-white rounded-lg hover:bg-[#B85C3D] transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {cloning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                {cloning ? 'Analyzing...' : 'Find Similar Markets'}
              </button>
            </div>

            {cloneResult && (
              <div className="space-y-4">
                {cloneResult.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                    <div className="flex items-center gap-2 text-red-700">
                      <AlertTriangle className="w-5 h-5" />
                      <span className="font-medium">{cloneResult.error}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="bg-white rounded-xl border border-gray-200 p-6">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-[#D97757] to-[#B85C3D] rounded-lg flex items-center justify-center flex-shrink-0">
                          <Copy className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">
                            {cloneResult.source_business?.name || 'Clone Analysis'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {cloneResult.narrative_summary || 'Market replication analysis complete.'}
                          </p>
                          {cloneResult.replicability_label && (
                            <span className={`inline-flex items-center gap-1 mt-2 px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(cloneResult.replicability_label === 'High' ? 85 : 50)}`}>
                              Replicability: {cloneResult.replicability_label}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {cloneResult.why_it_works && cloneResult.why_it_works.length > 0 && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-3">Why This Model Works</h3>
                        <ul className="space-y-2">
                          {cloneResult.why_it_works.map((w, i) => (
                            <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                              {w}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {cloneResult.matching_locations && cloneResult.matching_locations.length > 0 && (
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h3 className="font-semibold text-gray-900 mb-4">
                          Similar Markets ({cloneResult.matching_locations.length})
                        </h3>
                        <div className="space-y-3">
                          {cloneResult.matching_locations.map((loc, i) => (
                            <div key={i} className="p-4 bg-gray-50 rounded-lg">
                              <div className="flex items-center justify-between">
                                <div>
                                  <h4 className="font-medium text-gray-900">{loc.name}</h4>
                                  <p className="text-sm text-gray-500">{loc.city}, {loc.state}</p>
                                </div>
                                <div className="flex items-center gap-3">
                                  <div className="text-center">
                                    <div className="text-sm font-bold text-gray-900">{loc.similarity_score}%</div>
                                    <div className="text-xs text-gray-400">Match</div>
                                  </div>
                                  <div className="text-center">
                                    <div className="text-sm font-bold text-gray-900">{loc.demographics_match}%</div>
                                    <div className="text-xs text-gray-400">Demo</div>
                                  </div>
                                </div>
                              </div>
                              {loc.population && loc.median_income && (
                                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                                  <span className="flex items-center gap-1">
                                    <Users className="w-3 h-3" />
                                    {loc.population.toLocaleString()}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <DollarSign className="w-3 h-3" />
                                    ${loc.median_income.toLocaleString()}
                                  </span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <ReportPanel ideaDescription={cloneName} />
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
  const ReportPanel = ({ ideaDescription }: { ideaDescription?: string }) => (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mt-6 relative">
      {generatingReport && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm rounded-xl flex items-center justify-center z-10">
          <div className="text-center p-6">
            <Loader2 className="w-8 h-8 animate-spin text-[#D97757] mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-900 mb-1">
              Generating {REPORTS.find(r => r.id === selectedReport)?.name || 'Report'}...
            </p>
            <p className="text-xs text-gray-500">
              Elapsed {reportElapsed}s · This may take 30–60 seconds
            </p>
            {reportElapsed >= 20 && (
              <p className="text-xs text-amber-600 mt-2">
                Still working — our AI is analyzing market data deeply.
              </p>
            )}
            <button
              type="button"
              onClick={() => reportAbortRef.current?.abort()}
              className="mt-3 px-3 py-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-[#D97757]" />
        <h3 className="font-semibold text-gray-900">Generate Professional Report</h3>
      </div>
      <p className="text-sm text-gray-600 mb-4">
        Turn your analysis into a comprehensive, investor-ready document.
      </p>
      <div className="grid md:grid-cols-2 gap-3">
        {REPORTS.map((r) => {
          const Icon = r.icon
          const isSelected = selectedReport === r.id
          const isGenerated = isSelected && !!reportResult
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => handleGenerateReport(r.id, ideaDescription || '')}
              disabled={generatingReport}
              className={`text-left p-4 rounded-lg border transition-all ${
                isGenerated
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-200 hover:border-[#D97757] hover:bg-[#D97757]/5'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-gray-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-gray-900">{r.name}</span>
                    <span className="text-sm font-semibold text-gray-900">${(r.price_cents / 100).toFixed(0)}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{r.description}</p>
                  {isGenerated && (
                    <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-2">
                      <CheckCircle className="w-3 h-3" />
                      Generated
                    </span>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>
      {reportError && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {reportError}
          {!isAuthenticated && (
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => navigate('/login')} className="text-sm underline font-medium">Sign In</button>
              <span className="text-gray-400">or</span>
              <button type="button" onClick={() => navigate('/signup')} className="text-sm underline font-medium">Create Account</button>
            </div>
          )}
        </div>
      )}
      {reportResult && (
        <div className="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-sm font-medium text-gray-900">Report Generated</span>
          </div>
          <pre className="text-xs text-gray-600 overflow-auto max-h-48 bg-white p-3 rounded border">
            {JSON.stringify(reportResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
