import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  FileText, 
  Loader2, 
  CheckCircle,
  Sparkles,
  BarChart3,
  Target,
  Users,
  TrendingUp,
  Mail,
  Search as SearchIcon,
  Calendar,
  DollarSign,
  Megaphone,
  ClipboardList,
  Wand2,
  Download,
  Lightbulb,
  MapPin,
  Copy,
  Globe,
  Store,
  Building2,
  Briefcase,
  PieChart,
  LineChart,
  Presentation,
  FileSpreadsheet,
  Shield,
  Package,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

type ReportTemplate = {
  id: number
  slug: string
  name: string
  description: string
  category: string
  min_tier: string
  display_order: number
}

type CategoryWithTemplates = {
  category: string
  display_name: string
  templates: ReportTemplate[]
}

type GeneratedReport = {
  id: number
  report_type: string
  status: string
  title?: string
  summary?: string
  content?: string
  confidence_score?: number
  created_at: string
  completed_at?: string
}

type InputMode = 'validate' | 'search' | 'location' | 'clone'

type ConsultantStudioReport = {
  id: string
  name: string
  description: string
  price: number
  included_in_tier: string | null
}

type Bundle = {
  id: string
  name: string
  description: string
  price: number
  reports: string[]
  savings: number
}

const INPUT_MODES = [
  {
    id: 'validate' as InputMode,
    label: 'Validate Idea',
    icon: Lightbulb,
    description: 'Describe your business idea and get an Online/Physical/Hybrid recommendation with viability analysis.',
  },
  {
    id: 'search' as InputMode,
    label: 'Search Ideas',
    icon: SearchIcon,
    description: 'Browse our database of validated opportunities by keyword or category to find inspiration.',
  },
  {
    id: 'location' as InputMode,
    label: 'Identify Location',
    icon: MapPin,
    description: 'Enter a city + business type to get market analysis, demographics, and competition data.',
  },
  {
    id: 'clone' as InputMode,
    label: 'Clone Success',
    icon: Copy,
    description: 'Analyze a successful business and find similar markets where you could replicate it.',
  },
]

// Icons for Consultant Studio reports
const studioReportIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  feasibility_study: Target,
  pitch_deck: Presentation,
  strategic_assessment: Briefcase,
  market_analysis: PieChart,
  pestle_analysis: Shield,
  financial_model: LineChart,
  business_plan: FileSpreadsheet,
}

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  popular: Sparkles,
  marketing: Megaphone,
  product: ClipboardList,
  business: BarChart3,
  research: SearchIcon,
}

interface ReportLibraryProps {
  opportunityId?: number
  workspaceId?: number
  customContext?: string
  onReportGenerated?: (report: GeneratedReport) => void
}

export default function ReportLibrary({ 
  opportunityId, 
  workspaceId, 
  customContext,
  onReportGenerated 
}: ReportLibraryProps) {
  const { isAuthenticated, token } = useAuthStore()
  const queryClient = useQueryClient()
  
  // Input mode state
  const [inputMode, setInputMode] = useState<InputMode>('validate')
  
  // Validate Idea inputs
  const [ideaDescription, setIdeaDescription] = useState(customContext || '')
  
  // Search Ideas inputs
  const [searchQuery, setSearchQuery] = useState('')
  const [searchCategory, setSearchCategory] = useState('')
  
  // Identify Location inputs
  const [locationCity, setLocationCity] = useState('')
  const [locationBusiness, setLocationBusiness] = useState('')
  
  // Clone Success inputs
  const [cloneBusinessName, setCloneBusinessName] = useState('')
  const [cloneBusinessAddress, setCloneBusinessAddress] = useState('')
  const [cloneTargetCity, setCloneTargetCity] = useState('')
  
  // Report generation state
  const [selectedReport, setSelectedReport] = useState<{ type: 'studio' | 'template'; slug: string; name: string } | null>(null)
  const [generatingSlug, setGeneratingSlug] = useState<string | null>(null)
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null)
  
  // Consultant results
  const [consultantResult, setConsultantResult] = useState<any>(null)
  const [consultantLoading, setConsultantLoading] = useState(false)

  // Guest state
  const [guestEmail, setGuestEmail] = useState('')
  const [purchaseLoading, setPurchaseLoading] = useState(false)
  const [purchaseError, setPurchaseError] = useState<string | null>(null)

  // Report section toggle
  const [showBundles, setShowBundles] = useState(false)

  const isGuest = !isAuthenticated

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  // Fetch Consultant Studio reports (original 7)
  const { data: studioReports } = useQuery<{ reports: ConsultantStudioReport[]; bundles: Bundle[] }>({
    queryKey: ['studio-reports'],
    queryFn: async () => {
      const res = await fetch('/api/v1/report-pricing/public')
      if (!res.ok) throw new Error('Failed to fetch studio reports')
      return res.json()
    },
  })

  // Fetch Template reports (20+)
  const { data: categories, isLoading } = useQuery<CategoryWithTemplates[]>({
    queryKey: ['report-templates', isGuest],
    queryFn: async () => {
      const hdrs: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) hdrs['Authorization'] = `Bearer ${token}`
      const endpoint = isGuest ? '/api/v1/reports/templates/public' : '/api/v1/reports/templates'
      const res = await fetch(endpoint, { headers: hdrs })
      if (!res.ok) throw new Error('Failed to fetch templates')
      return res.json()
    },
  })

  const generateMutation = useMutation({
    mutationFn: async ({ reportType, context, isStudio }: { reportType: string; context: string; isStudio: boolean }) => {
      setGeneratingSlug(reportType)
      
      if (isStudio) {
        // Use studio report generation endpoint
        const res = await fetch('/api/v1/report-pricing/generate-free-report', {
          method: 'POST',
          headers: headers(),
          body: JSON.stringify({
            report_type: reportType,
            idea_description: context,
            opportunity_id: opportunityId,
          }),
        })
        if (!res.ok) {
          const error = await res.json()
          throw new Error(error.detail || 'Failed to generate report')
        }
        return res.json()
      } else {
        // Use template generation endpoint
        const res = await fetch('/api/v1/reports/generate', {
          method: 'POST',
          headers: headers(),
          body: JSON.stringify({
            template_slug: reportType,
            opportunity_id: opportunityId,
            workspace_id: workspaceId,
            custom_context: context,
          }),
        })
        if (!res.ok) {
          const error = await res.json()
          throw new Error(error.detail || 'Failed to generate report')
        }
        return res.json() as Promise<GeneratedReport>
      }
    },
    onSuccess: (report) => {
      setGeneratingSlug(null)
      setGeneratedReport(report)
      queryClient.invalidateQueries({ queryKey: ['my-reports'] })
      onReportGenerated?.(report)
    },
    onError: () => {
      setGeneratingSlug(null)
    },
  })

  // Run consultant analysis
  const runConsultantAnalysis = async () => {
    setConsultantLoading(true)
    setConsultantResult(null)
    
    try {
      let endpoint = ''
      let body: any = {}
      
      switch (inputMode) {
        case 'validate':
          endpoint = '/api/v1/consultant/validate-idea'
          body = { idea_description: ideaDescription, business_context: {} }
          break
        case 'search':
          endpoint = '/api/v1/consultant/search-ideas'
          body = { query: searchQuery || undefined, category: searchCategory || undefined }
          break
        case 'location':
          endpoint = '/api/v1/consultant/identify-location'
          body = { city: locationCity, business_description: locationBusiness }
          break
        case 'clone':
          endpoint = '/api/v1/consultant/clone-success'
          body = { 
            business_name: cloneBusinessName, 
            business_address: cloneBusinessAddress,
            target_city: cloneTargetCity || undefined,
            radius_miles: 3
          }
          break
      }
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      })
      
      if (!res.ok) throw new Error('Analysis failed')
      const result = await res.json()
      setConsultantResult(result)
    } catch (e) {
      console.error(e)
    } finally {
      setConsultantLoading(false)
    }
  }

  const formatPrice = (cents: number) => {
    return `$${(cents / 100).toFixed(0)}`
  }

  const getTierBadge = (tier: string | null) => {
    if (!tier) return { text: 'PAY', className: 'bg-amber-100 text-amber-700' }
    const badges: Record<string, { text: string; className: string }> = {
      free: { text: 'FREE', className: 'bg-green-100 text-green-700' },
      pro: { text: 'PRO', className: 'bg-purple-100 text-purple-700' },
      business: { text: 'BIZ', className: 'bg-blue-100 text-blue-700' },
      enterprise: { text: 'ENT', className: 'bg-gray-100 text-gray-700' },
    }
    return badges[tier] || { text: tier.toUpperCase(), className: 'bg-gray-100 text-gray-600' }
  }

  const allTemplates = categories?.flatMap(cat => cat.templates) || []

  const getContextForReport = () => {
    switch (inputMode) {
      case 'validate':
        return consultantResult 
          ? `Idea: ${ideaDescription}\n\nAnalysis: ${JSON.stringify(consultantResult, null, 2)}`
          : ideaDescription
      case 'search':
        return consultantResult
          ? `Search: ${searchQuery} (${searchCategory})\n\nResults: ${JSON.stringify(consultantResult, null, 2)}`
          : `Search query: ${searchQuery}, Category: ${searchCategory}`
      case 'location':
        return consultantResult
          ? `Location: ${locationBusiness} in ${locationCity}\n\nAnalysis: ${JSON.stringify(consultantResult, null, 2)}`
          : `${locationBusiness} in ${locationCity}`
      case 'clone':
        return consultantResult
          ? `Clone: ${cloneBusinessName}\n\nAnalysis: ${JSON.stringify(consultantResult, null, 2)}`
          : `Clone ${cloneBusinessName} at ${cloneBusinessAddress}`
      default:
        return ''
    }
  }

  const canAnalyze = () => {
    switch (inputMode) {
      case 'validate': return ideaDescription.trim().length > 10
      case 'search': return searchQuery.trim() || searchCategory
      case 'location': return locationCity.trim() && locationBusiness.trim()
      case 'clone': return cloneBusinessName.trim() && cloneBusinessAddress.trim()
      default: return false
    }
  }

  const canGenerateReport = selectedReport && (consultantResult || canAnalyze())

  const handleGenerateReport = () => {
    if (!selectedReport) return
    const context = getContextForReport()
    generateMutation.mutate({ 
      reportType: selectedReport.slug, 
      context,
      isStudio: selectedReport.type === 'studio'
    })
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-center gap-2 text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Two-Column Layout */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="grid md:grid-cols-2 gap-6">
          
          {/* LEFT: Business Context with 4 Modes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Business Context
            </label>
            
            {/* Mode Tabs */}
            <div className="flex flex-wrap gap-1 mb-4 p-1 bg-gray-100 rounded-lg">
              {INPUT_MODES.map((mode) => {
                const Icon = mode.icon
                const isActive = inputMode === mode.id
                return (
                  <button
                    key={mode.id}
                    onClick={() => {
                      setInputMode(mode.id)
                      setConsultantResult(null)
                    }}
                    className={`flex-1 min-w-0 flex items-center justify-center gap-1 px-2 py-2 rounded-md text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate hidden sm:inline">{mode.label}</span>
                  </button>
                )
              })}
            </div>

            {/* Mode Description */}
            <p className="text-xs text-gray-500 mb-3">
              {INPUT_MODES.find(m => m.id === inputMode)?.description}
            </p>

            {/* Mode-Specific Inputs */}
            {inputMode === 'validate' && (
              <textarea
                value={ideaDescription}
                onChange={(e) => setIdeaDescription(e.target.value)}
                placeholder="Describe your business idea in detail..."
                className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none text-sm"
                rows={4}
              />
            )}

            {inputMode === 'search' && (
              <div className="space-y-3">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Keyword (e.g., coffee, fitness...)"
                  className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 text-sm"
                />
                <select
                  value={searchCategory}
                  onChange={(e) => setSearchCategory(e.target.value)}
                  className="w-full p-3 border border-gray-200 rounded-lg bg-white text-sm"
                >
                  <option value="">All Categories</option>
                  <option value="work_productivity">💼 Work & Productivity</option>
                  <option value="money_finance">💰 Money & Finance</option>
                  <option value="health_wellness">🏥 Health & Wellness</option>
                  <option value="technology">💻 Technology</option>
                </select>
              </div>
            )}

            {inputMode === 'location' && (
              <div className="space-y-3">
                <input
                  type="text"
                  value={locationCity}
                  onChange={(e) => setLocationCity(e.target.value)}
                  placeholder="City (e.g., Miami, Florida)"
                  className="w-full p-3 border border-gray-200 rounded-lg text-sm"
                />
                <input
                  type="text"
                  value={locationBusiness}
                  onChange={(e) => setLocationBusiness(e.target.value)}
                  placeholder="Business type (e.g., Coffee shop)"
                  className="w-full p-3 border border-gray-200 rounded-lg text-sm"
                />
              </div>
            )}

            {inputMode === 'clone' && (
              <div className="space-y-3">
                <input
                  type="text"
                  value={cloneBusinessName}
                  onChange={(e) => setCloneBusinessName(e.target.value)}
                  placeholder="Business name (e.g., Sweetgreen)"
                  className="w-full p-3 border border-gray-200 rounded-lg text-sm"
                />
                <input
                  type="text"
                  value={cloneBusinessAddress}
                  onChange={(e) => setCloneBusinessAddress(e.target.value)}
                  placeholder="Business address"
                  className="w-full p-3 border border-gray-200 rounded-lg text-sm"
                />
                <input
                  type="text"
                  value={cloneTargetCity}
                  onChange={(e) => setCloneTargetCity(e.target.value)}
                  placeholder="Target city (optional)"
                  className="w-full p-3 border border-gray-200 rounded-lg text-sm"
                />
              </div>
            )}

            {/* Analyze Button */}
            <button
              onClick={runConsultantAnalysis}
              disabled={!canAnalyze() || consultantLoading}
              className="mt-3 w-full px-4 py-2.5 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
            >
              {consultantLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Analyze
                </>
              )}
            </button>
          </div>

          {/* RIGHT: Report Selection */}
          <div className="flex flex-col">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Select Report Type
            </label>
            
            <select
              value={selectedReport ? `${selectedReport.type}:${selectedReport.slug}` : ''}
              onChange={(e) => {
                if (!e.target.value) {
                  setSelectedReport(null)
                  return
                }
                const [type, slug] = e.target.value.split(':')
                if (type === 'studio') {
                  const report = studioReports?.reports.find(r => r.id === slug)
                  setSelectedReport({ type: 'studio', slug, name: report?.name || slug })
                } else {
                  const template = allTemplates.find(t => t.slug === slug)
                  setSelectedReport({ type: 'template', slug, name: template?.name || slug })
                }
              }}
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 bg-white text-sm"
            >
              <option value="">Choose a report...</option>
              
              {/* Consultant Studio Reports (Original 7) */}
              <optgroup label="📊 Consultant Studio Reports">
                {studioReports?.reports.map(report => (
                  <option key={report.id} value={`studio:${report.id}`}>
                    {report.name} — {formatPrice(report.price)}
                  </option>
                ))}
              </optgroup>
              
              {/* Template Reports */}
              {categories?.map(cat => (
                <optgroup key={cat.category} label={`📝 ${cat.display_name}`}>
                  {cat.templates.map(template => (
                    <option key={template.slug} value={`template:${template.slug}`}>
                      {template.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>

            {/* Selected Report Info */}
            {selectedReport && (
              <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                {selectedReport.type === 'studio' ? (
                  <>
                    {(() => {
                      const report = studioReports?.reports.find(r => r.id === selectedReport.slug)
                      const Icon = studioReportIcons[selectedReport.slug] || FileText
                      return (
                        <>
                          <div className="flex items-center gap-2 mb-2">
                            <Icon className="w-5 h-5 text-purple-600" />
                            <span className="font-medium text-gray-900">{report?.name}</span>
                            <span className={`ml-auto px-2 py-0.5 rounded text-xs font-bold ${getTierBadge(report?.included_in_tier || null).className}`}>
                              {report?.included_in_tier ? getTierBadge(report.included_in_tier).text : formatPrice(report?.price || 0)}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500">{report?.description}</p>
                        </>
                      )
                    })()}
                  </>
                ) : (
                  <>
                    {(() => {
                      const template = allTemplates.find(t => t.slug === selectedReport.slug)
                      return (
                        <>
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-gray-900">{template?.name}</span>
                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${getTierBadge(template?.min_tier || null).className}`}>
                              {getTierBadge(template?.min_tier || null).text}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500">{template?.description}</p>
                        </>
                      )
                    })()}
                  </>
                )}
              </div>
            )}

            {/* Bundles Toggle */}
            {studioReports?.bundles && studioReports.bundles.length > 0 && (
              <button
                onClick={() => setShowBundles(!showBundles)}
                className="mt-3 text-xs text-purple-600 hover:text-purple-700 flex items-center gap-1"
              >
                <Package className="w-3 h-3" />
                {showBundles ? 'Hide bundles' : 'View bundle deals (save up to 45%)'}
              </button>
            )}

            {showBundles && studioReports?.bundles && (
              <div className="mt-2 space-y-2">
                {studioReports.bundles.map(bundle => (
                  <div key={bundle.id} className="p-2 bg-purple-50 rounded-lg border border-purple-100">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-purple-900 text-sm">{bundle.name}</span>
                      <span className="text-purple-700 font-bold text-sm">{formatPrice(bundle.price)}</span>
                    </div>
                    <p className="text-xs text-purple-600">{bundle.description}</p>
                    <p className="text-xs text-green-600 mt-1">Save {formatPrice(bundle.savings)}</p>
                  </div>
                ))}
              </div>
            )}

            {isGuest && selectedReport && (
              <div className="mt-3">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  <Mail className="w-3 h-3 inline mr-1" />
                  Email for delivery
                </label>
                <input
                  type="email"
                  value={guestEmail}
                  onChange={(e) => setGuestEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full p-2 border border-gray-200 rounded-lg text-sm"
                />
              </div>
            )}

            {purchaseError && (
              <div className="mt-2 p-2 bg-red-50 text-red-700 text-xs rounded-lg">
                {purchaseError}
              </div>
            )}

            <button
              onClick={handleGenerateReport}
              disabled={!canGenerateReport || generateMutation.isPending}
              className="mt-auto px-4 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  Generate Report
                </>
              )}
            </button>

            {isGuest && (
              <p className="text-xs text-center text-gray-500 mt-2">
                <a href="/login" className="text-purple-600 hover:underline">Sign in</a> for member pricing
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Consultant Analysis Results */}
      {consultantResult && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">
              {INPUT_MODES.find(m => m.id === inputMode)?.label} Results
            </h3>
            <button onClick={() => setConsultantResult(null)} className="text-gray-400 hover:text-gray-600 text-sm">
              ✕
            </button>
          </div>

          {inputMode === 'validate' && consultantResult.success && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">Recommendation:</span>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold ${
                  consultantResult.recommendation === 'online' ? 'bg-blue-100 text-blue-700' :
                  consultantResult.recommendation === 'physical' ? 'bg-green-100 text-green-700' :
                  'bg-purple-100 text-purple-700'
                }`}>
                  {consultantResult.recommendation === 'online' && <Globe className="w-4 h-4" />}
                  {consultantResult.recommendation === 'physical' && <Store className="w-4 h-4" />}
                  {consultantResult.recommendation === 'hybrid' && <Building2 className="w-4 h-4" />}
                  {consultantResult.recommendation?.charAt(0).toUpperCase() + consultantResult.recommendation?.slice(1)}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 rounded-lg p-3">
                  <div className="text-xs text-blue-600 mb-1">Online Score</div>
                  <div className="text-2xl font-bold text-blue-700">{consultantResult.online_score}%</div>
                </div>
                <div className="bg-green-50 rounded-lg p-3">
                  <div className="text-xs text-green-600 mb-1">Physical Score</div>
                  <div className="text-2xl font-bold text-green-700">{consultantResult.physical_score}%</div>
                </div>
              </div>
            </div>
          )}

          {inputMode === 'search' && consultantResult.success && (
            <div className="space-y-3">
              <div className="text-sm text-gray-600">Found {consultantResult.total_count || 0} opportunities</div>
              {consultantResult.opportunities?.slice(0, 5).map((opp: any) => (
                <div key={opp.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="font-medium text-gray-900">{opp.title}</div>
                </div>
              ))}
            </div>
          )}

          {inputMode === 'location' && consultantResult.success && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-500">Competition</div>
                <div className="text-lg font-bold">{consultantResult.geo_analysis?.competitors?.length || 0}</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-500">Density</div>
                <div className="text-lg font-bold capitalize">{consultantResult.geo_analysis?.market_density || 'N/A'}</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <div className="text-xs text-gray-500">Category</div>
                <div className="text-lg font-bold">{consultantResult.inferred_category || 'N/A'}</div>
              </div>
            </div>
          )}

          {inputMode === 'clone' && consultantResult.success && (
            <div className="space-y-3">
              <div className="text-sm text-gray-600">
                Found {consultantResult.matching_locations?.length || 0} matching locations
              </div>
              {consultantResult.matching_locations?.slice(0, 3).map((loc: any, idx: number) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg flex justify-between">
                  <div>
                    <div className="font-medium">{loc.name}</div>
                    <div className="text-xs text-gray-500">{loc.city}, {loc.state}</div>
                  </div>
                  <div className="text-lg font-bold text-amber-600">{loc.similarity_score}%</div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-3 text-xs text-gray-400">
            Processed in {consultantResult.processing_time_ms}ms
          </div>
        </div>
      )}

      {/* Generated Report Output */}
      {generatedReport && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-fade-in">
          <div className="bg-gradient-to-r from-green-500 to-emerald-500 p-4 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">{generatedReport.title || 'Report Generated'}</span>
              </div>
              <div className="flex items-center gap-2">
                <button className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-sm flex items-center gap-1">
                  <Download className="w-4 h-4" />
                  Export
                </button>
                <button onClick={() => setGeneratedReport(null)} className="text-white/80 hover:text-white">
                  ✕
                </button>
              </div>
            </div>
          </div>
          <div className="p-6">
            {generatedReport.summary && (
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <div className="text-sm font-medium text-gray-700 mb-1">Summary</div>
                <p className="text-sm text-gray-600">{generatedReport.summary}</p>
              </div>
            )}
            {generatedReport.content && (
              <div className="prose prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-gray-800 text-sm leading-relaxed">
                  {generatedReport.content}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
