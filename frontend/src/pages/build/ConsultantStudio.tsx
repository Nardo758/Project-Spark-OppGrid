import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Lightbulb,
  Search,
  MapPin,
  Copy,
  Loader2,
  CheckCircle,
  TrendingUp,
  Building2,
  Globe,
  Store,
  FileText,
  Download,
  ChevronRight,
  Sparkles,
  Target,
  BarChart3,
  Map,
  Users,
  DollarSign,
  AlertCircle,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { Link } from 'react-router-dom'

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
interface ValidateIdeaResult {
  success: boolean
  idea_description?: string
  recommendation?: 'online' | 'physical' | 'hybrid'
  online_score?: number
  physical_score?: number
  pattern_analysis?: Record<string, any>
  viability_report?: Record<string, any>
  similar_opportunities?: Array<{ id: number; title: string; score: number }>
  processing_time_ms?: number
  error?: string
}

interface SearchIdeasResult {
  success: boolean
  opportunities?: Array<{
    id: number
    title: string
    description?: string
    category?: string
    score?: number
    created_at?: string
  }>
  trends?: Array<{
    id: number
    name: string
    strength: number
    description?: string
    growth_rate?: number
    opportunities_count?: number
  }>
  synthesis?: Record<string, any>
  total_count?: number
  processing_time_ms?: number
  error?: string
}

interface IdentifyLocationResult {
  success: boolean
  city?: string
  business_description?: string
  inferred_category?: string
  geo_analysis?: Record<string, any>
  market_report?: Record<string, any>
  site_recommendations?: Array<Record<string, any>>
  map_data?: {
    city: string
    center: { lat: number; lng: number }
    layers: Record<string, any>
    totalFeatures: number
  }
  from_cache?: boolean
  processing_time_ms?: number
  error?: string
}

interface CloneSuccessResult {
  success: boolean
  source_business?: Record<string, any>
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
}

interface SavedReport {
  id: number
  report_type: string
  title: string
  status: string
  created_at: string
}

export default function ConsultantStudio() {
  const { token, isAuthenticated } = useAuthStore()
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
      if (!res.ok) throw new Error('Failed to validate idea')
      return res.json() as Promise<ValidateIdeaResult>
    },
    onSuccess: (data) => setValidateResult(data),
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
      if (!res.ok) throw new Error('Failed to search ideas')
      return res.json() as Promise<SearchIdeasResult>
    },
    onSuccess: (data) => setSearchResult(data),
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
      if (!res.ok) throw new Error('Failed to analyze location')
      return res.json() as Promise<IdentifyLocationResult>
    },
    onSuccess: (data) => setLocationResult(data),
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
      if (!res.ok) throw new Error('Failed to analyze business')
      return res.json() as Promise<CloneSuccessResult>
    },
    onSuccess: (data) => setCloneResult(data),
  })

  const [reportError, setReportError] = useState<string | null>(null)
  const [reportSuccess, setReportSuccess] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)

  const saveReportMutation = useMutation({
    mutationFn: async ({
      reportType,
      title,
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

  const getRecommendationBadge = (rec?: string) => {
    if (!rec) return null
    const styles: Record<string, string> = {
      online: 'bg-blue-100 text-blue-700',
      physical: 'bg-green-100 text-green-700',
      hybrid: 'bg-purple-100 text-purple-700',
    }
    const icons: Record<string, React.ReactNode> = {
      online: <Globe className="w-4 h-4" />,
      physical: <Store className="w-4 h-4" />,
      hybrid: <Building2 className="w-4 h-4" />,
    }
    return (
      <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold ${styles[rec] || 'bg-gray-100 text-gray-700'}`}>
        {icons[rec]}
        {rec.charAt(0).toUpperCase() + rec.slice(1)}
      </span>
    )
  }

  const handleExportPdf = async (data: Record<string, any>, title: string, reportType: string) => {
    setExportingPdf(true)
    try {
      // Convert JSON data to readable HTML for the PDF
      const htmlContent = jsonToHtml(data)
      const res = await fetch('/api/v1/reports/export/pdf', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ content: htmlContent, title, report_type: reportType }),
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `OppGrid - ${title.slice(0, 60)}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setReportError('Failed to export PDF. Please try again.')
    } finally {
      setExportingPdf(false)
    }
  }

  const jsonToHtml = (data: Record<string, any>): string => {
    const sections: string[] = []
    for (const [key, value] of Object.entries(data)) {
      if (value === null || value === undefined) continue
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
      if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        sections.push(`<p><strong>${label}:</strong> ${String(value)}</p>`)
      } else if (Array.isArray(value)) {
        const items = value.map((v) =>
          typeof v === 'object' ? `<li>${Object.entries(v).map(([k, val]) => `<strong>${k}:</strong> ${val}`).join(' | ')}</li>` : `<li>${v}</li>`
        ).join('')
        sections.push(`<h3>${label}</h3><ul>${items}</ul>`)
      } else if (typeof value === 'object') {
        const rows = Object.entries(value).map(([k, v]) =>
          `<tr><td><strong>${k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</strong></td><td>${typeof v === 'object' ? JSON.stringify(v) : v}</td></tr>`
        ).join('')
        sections.push(`<h3>${label}</h3><table><tbody>${rows}</tbody></table>`)
      }
    }
    return sections.join('\n')
  }

  const renderValidateTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Describe Your Business Idea</h3>
        <p className="text-sm text-gray-500 mb-4">
          Our AI will analyze your idea and recommend whether it's best suited for online, physical, or hybrid operation.
        </p>
        <textarea
          value={ideaDescription}
          onChange={(e) => setIdeaDescription(e.target.value)}
          placeholder="Example: A subscription service that delivers locally-roasted coffee beans to offices in downtown areas, with flexible weekly or monthly delivery options..."
          rows={5}
          className="w-full p-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none"
        />
        <div className="mt-4 flex justify-between items-center">
          <span className="text-sm text-gray-500">{ideaDescription.length}/2000</span>
          <button
            onClick={() => validateMutation.mutate()}
            disabled={!ideaDescription.trim() || validateMutation.isPending}
            className="px-6 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {validateMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Validate Idea
              </>
            )}
          </button>
        </div>
      </div>

      {validateResult?.success && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Validation Results</h3>
            {getRecommendationBadge(validateResult.recommendation)}
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Globe className="w-5 h-5 text-blue-600" />
                <span className="font-medium text-blue-900">Online Score</span>
              </div>
              <div className="text-3xl font-bold text-blue-700">{validateResult.online_score}%</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Store className="w-5 h-5 text-green-600" />
                <span className="font-medium text-green-900">Physical Score</span>
              </div>
              <div className="text-3xl font-bold text-green-700">{validateResult.physical_score}%</div>
            </div>
          </div>

          {validateResult.viability_report && (
            <div className="mb-6">
              <h4 className="font-medium text-gray-900 mb-3">Viability Analysis</h4>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
                {validateResult.viability_report.summary || JSON.stringify(validateResult.viability_report, null, 2)}
              </div>
            </div>
          )}

          {validateResult.similar_opportunities && validateResult.similar_opportunities.length > 0 && (
            <div className="mb-6">
              <h4 className="font-medium text-gray-900 mb-3">Similar Opportunities</h4>
              <div className="space-y-2">
                {validateResult.similar_opportunities.map((opp) => (
                  <Link
                    key={opp.id}
                    to={`/opportunity/${opp.id}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="text-gray-900">{opp.title}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">Score: {opp.score}</span>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {reportError && (
            <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
              <span className="text-sm text-red-800">{reportError}</span>
              <button onClick={() => setReportError(null)} className="ml-auto text-red-400 hover:text-red-600 text-sm">Dismiss</button>
            </div>
          )}
          {reportSuccess && (
            <div className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 shrink-0" />
              <span className="text-sm text-green-800">Report saved successfully!</span>
            </div>
          )}
          <div className="flex gap-3">
            <button
              onClick={() =>
                saveReportMutation.mutate({
                  reportType: 'feasibility_study',
                  title: `Idea Validation: ${ideaDescription.slice(0, 50)}...`,
                  content: JSON.stringify(validateResult, null, 2),
                })
              }
              disabled={saveReportMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50"
            >
              <FileText className="w-4 h-4" />
              {saveReportMutation.isPending ? 'Generating...' : 'Save as Report'}
            </button>
            <button
              onClick={() => handleExportPdf(validateResult!, `Idea Validation: ${ideaDescription.slice(0, 50)}`, 'Feasibility Study')}
              disabled={exportingPdf}
              className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50"
            >
              {exportingPdf ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {exportingPdf ? 'Exporting...' : 'Export PDF'}
            </button>
          </div>

          <div className="mt-4 text-xs text-gray-400">
            Processed in {validateResult.processing_time_ms}ms
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
        <div className="space-y-6 animate-fade-in">
          {searchResult.trends && searchResult.trends.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                <TrendingUp className="w-5 h-5 inline mr-2 text-amber-500" />
                Trending Now
              </h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {searchResult.trends.map((trend) => (
                  <div key={trend.id} className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg p-4 border border-amber-100">
                    <div className="font-medium text-gray-900">{trend.name}</div>
                    <div className="text-sm text-gray-600 mt-1">{trend.description}</div>
                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                      <span>Strength: {trend.strength}%</span>
                      {trend.growth_rate && <span>Growth: +{trend.growth_rate}%</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Opportunities ({searchResult.total_count || 0})
              </h3>
              <button
                onClick={() =>
                  saveReportMutation.mutate({
                    reportType: 'market_analysis',
                    title: `Search Results: ${searchQuery || searchCategory || 'All'}`,
                    content: JSON.stringify(searchResult, null, 2),
                  })
                }
                disabled={saveReportMutation.isPending}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <FileText className="w-4 h-4" />
                Save Report
              </button>
            </div>

            {searchResult.opportunities && searchResult.opportunities.length > 0 ? (
              <div className="space-y-3">
                {searchResult.opportunities.map((opp) => (
                  <Link
                    key={opp.id}
                    to={`/opportunity/${opp.id}`}
                    className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium text-gray-900">{opp.title}</div>
                        {opp.description && (
                          <div className="text-sm text-gray-600 mt-1 line-clamp-2">{opp.description}</div>
                        )}
                        {opp.category && (
                          <span className="inline-block mt-2 px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded">
                            {opp.category}
                          </span>
                        )}
                      </div>
                      {opp.score && (
                        <div className="text-right">
                          <div className="text-lg font-bold text-amber-600">{opp.score}</div>
                          <div className="text-xs text-gray-500">Score</div>
                        </div>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">No opportunities found. Try different keywords.</div>
            )}
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
        <div className="space-y-6 animate-fade-in">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {locationResult.business_description} in {locationResult.city}
                </h3>
                <p className="text-sm text-gray-500">
                  Category: {locationResult.inferred_category}
                  {locationResult.from_cache && ' • Cached result'}
                </p>
              </div>
              <button
                onClick={() =>
                  saveReportMutation.mutate({
                    reportType: 'market_analysis',
                    title: `Location Analysis: ${locationResult.business_description} in ${locationResult.city}`,
                    content: JSON.stringify(locationResult, null, 2),
                  })
                }
                disabled={saveReportMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium"
              >
                <FileText className="w-4 h-4" />
                Save Report
              </button>
            </div>

            {locationResult.geo_analysis && (
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-5 h-5 text-blue-600" />
                    <span className="font-medium text-blue-900">Competition</span>
                  </div>
                  <div className="text-2xl font-bold text-blue-700">
                    {locationResult.geo_analysis.competitors?.length || 0}
                  </div>
                  <div className="text-sm text-blue-600">nearby competitors</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign className="w-5 h-5 text-green-600" />
                    <span className="font-medium text-green-900">Median Income</span>
                  </div>
                  <div className="text-2xl font-bold text-green-700">
                    ${(locationResult.geo_analysis.median_income || 0).toLocaleString()}
                  </div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-5 h-5 text-purple-600" />
                    <span className="font-medium text-purple-900">Market Density</span>
                  </div>
                  <div className="text-2xl font-bold text-purple-700 capitalize">
                    {locationResult.geo_analysis.market_density || 'Medium'}
                  </div>
                </div>
              </div>
            )}

            {locationResult.market_report && (
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <h4 className="font-medium text-gray-900 mb-2">Market Report</h4>
                <div className="text-sm text-gray-700 whitespace-pre-wrap">
                  {typeof locationResult.market_report === 'string'
                    ? locationResult.market_report
                    : locationResult.market_report.summary || JSON.stringify(locationResult.market_report, null, 2)}
                </div>
              </div>
            )}

            {locationResult.site_recommendations && locationResult.site_recommendations.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Site Recommendations</h4>
                <div className="space-y-2">
                  {locationResult.site_recommendations.map((site, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <MapPin className="w-5 h-5 text-amber-500" />
                      <div>
                        <div className="font-medium text-gray-900">{site.name || site.area || `Site ${idx + 1}`}</div>
                        {site.reason && <div className="text-sm text-gray-600">{site.reason}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-4 text-xs text-gray-400">
              Processed in {locationResult.processing_time_ms}ms
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
        <div className="space-y-6 animate-fade-in">
          {cloneResult.source_business && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Source Business Analysis
                </h3>
                <button
                  onClick={() =>
                    saveReportMutation.mutate({
                      reportType: 'strategic_assessment',
                      title: `Clone Analysis: ${cloneBusinessName}`,
                      content: JSON.stringify(cloneResult, null, 2),
                    })
                  }
                  disabled={saveReportMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium"
                >
                  <FileText className="w-4 h-4" />
                  Save Report
                </button>
              </div>

              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="text-sm text-gray-500">Business</div>
                  <div className="font-medium text-gray-900">{cloneResult.source_business.name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Category</div>
                  <div className="font-medium text-gray-900">{cloneResult.source_business.category}</div>
                </div>
              </div>

              {cloneResult.source_business.success_factors && (
                <div>
                  <div className="text-sm font-medium text-gray-700 mb-2">Success Factors</div>
                  <div className="flex flex-wrap gap-2">
                    {cloneResult.source_business.success_factors.map((factor: string, idx: number) => (
                      <span key={idx} className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {cloneResult.matching_locations && cloneResult.matching_locations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Matching Locations ({cloneResult.matching_locations.length})
              </h3>

              <div className="space-y-4">
                {cloneResult.matching_locations.map((loc, idx) => (
                  <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="font-semibold text-gray-900">{loc.name}</div>
                        <div className="text-sm text-gray-600">
                          {loc.city}, {loc.state}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-amber-600">{loc.similarity_score}%</div>
                        <div className="text-xs text-gray-500">Match Score</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
                      <div>
                        <div className="text-gray-500">Demographics</div>
                        <div className="font-medium">{loc.demographics_match}%</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Competition</div>
                        <div className="font-medium">{loc.competition_match}%</div>
                      </div>
                      <div>
                        <div className="text-gray-500">Median Income</div>
                        <div className="font-medium">${(loc.median_income || 0).toLocaleString()}</div>
                      </div>
                    </div>

                    {loc.key_factors && loc.key_factors.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {loc.key_factors.map((factor, fidx) => (
                          <span key={fidx} className="px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded">
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

          <div className="text-xs text-gray-400 text-center">
            Analysis radius: {cloneResult.analysis_radius_miles} miles • 
            Processed in {cloneResult.processing_time_ms}ms
          </div>
        </div>
      )}
    </div>
  )

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-stone-50 py-12">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <div className="w-16 h-16 bg-amber-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <BarChart3 className="w-8 h-8 text-amber-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Consultant Studio</h1>
          <p className="text-lg text-gray-600 mb-8">
            AI-powered business validation, market analysis, and location intelligence.
          </p>
          <Link
            to="/login?next=/build/consultant-studio"
            className="inline-flex items-center gap-2 px-8 py-4 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600"
          >
            Sign in to Access
            <ChevronRight className="w-5 h-5" />
          </Link>
        </div>
      </div>
    )
  }

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

        {/* Tab Content */}
        {activeTab === 'validate' && renderValidateTab()}
        {activeTab === 'search' && renderSearchTab()}
        {activeTab === 'location' && renderLocationTab()}
        {activeTab === 'clone' && renderCloneTab()}

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
