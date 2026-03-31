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
  Zap,
  Star,
  Lock,
  Clock,
  TrendingDown,
  Gift,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

type ReportTemplate = {
  id: number
  slug: string
  name: string
  description: string
  category: string
  min_tier: string
  price_cents?: number
  display_order: number
}

// Fallback prices for templates (in cents) - used if API doesn't have price_cents
const TEMPLATE_PRICES: Record<string, number> = {
  ad_creatives: 4900,
  brand_package: 5900,
  landing_page: 4900,
  content_calendar: 3900,
  email_funnel: 4900,
  email_sequence: 2900,
  lead_magnet: 2900,
  sales_funnel: 3900,
  seo_content: 3900,
  tweet_landing: 1900,
  user_personas: 2900,
  feature_specs: 4900,
  mvp_roadmap: 5900,
  prd: 7900,
  gtm_calendar: 4900,
  gtm_strategy: 6900,
  kpi_dashboard: 3900,
  pricing_strategy: 5900,
  competitive_analysis: 4900,
  customer_interview: 2900,
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
  consultant_price?: string
  included_in_tier: string | null
}

type Bundle = {
  id: string
  name: string
  description: string
  price: number
  reports: string[]
  savings: number
  consultant_value?: string
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

// Consultant pricing for comparison (what firms typically charge)
const CONSULTANT_PRICES: Record<string, string> = {
  feasibility_study: '$1,500 - $15,000',
  pitch_deck: '$2,000 - $5,000',
  strategic_assessment: '$1,500 - $5,000',
  market_analysis: '$2,000 - $8,000',
  pestle_analysis: '$1,500 - $5,000',
  financial_model: '$2,500 - $10,000',
  business_plan: '$3,000 - $15,000',
}

// Sample preview content for each report type
const REPORT_PREVIEWS: Record<string, { sections: string[]; sampleInsight: string }> = {
  feasibility_study: {
    sections: ['Executive Summary', 'Market Opportunity', 'Technical Feasibility', 'Financial Viability', 'Risk Assessment', 'Recommendation'],
    sampleInsight: 'Based on 47 comparable businesses in your target market, the projected success rate is 73%...',
  },
  market_analysis: {
    sections: ['Market Size (TAM/SAM/SOM)', 'Growth Trends', 'Customer Segments', 'Competitive Landscape', 'Market Entry Strategy', 'Revenue Projections'],
    sampleInsight: 'Your total addressable market is estimated at $4.2B with a 12% CAGR...',
  },
  business_plan: {
    sections: ['Executive Summary', 'Company Description', 'Market Analysis', 'Organization & Management', 'Product/Service Line', 'Marketing Strategy', 'Financial Projections'],
    sampleInsight: 'With the proposed go-to-market strategy, break-even is projected within 18 months...',
  },
  financial_model: {
    sections: ['Revenue Model', 'Cost Structure', 'Unit Economics', 'Cash Flow Projections', '5-Year P&L', 'Sensitivity Analysis'],
    sampleInsight: 'Customer LTV:CAC ratio of 4.2x indicates strong unit economics...',
  },
  pitch_deck: {
    sections: ['Problem', 'Solution', 'Market Size', 'Business Model', 'Traction', 'Team', 'Financials', 'Ask'],
    sampleInsight: 'Recommended ask: $1.5M at $8M pre-money valuation based on comparable raises...',
  },
  strategic_assessment: {
    sections: ['SWOT Analysis', 'Competitive Positioning', 'Value Proposition', 'Strategic Options', 'Recommended Strategy'],
    sampleInsight: 'Key differentiator identified: 3x faster delivery than nearest competitor...',
  },
  pestle_analysis: {
    sections: ['Political Factors', 'Economic Factors', 'Social Factors', 'Technological Factors', 'Legal Factors', 'Environmental Factors'],
    sampleInsight: 'Regulatory tailwind: New legislation expected to increase market by 25%...',
  },
}

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

  const formatPrice = (cents: number) => `$${(cents / 100).toFixed(0)}`
  
  const calculateSavingsPercent = (yourPrice: number, consultantPrice: string) => {
    // Extract lower bound from consultant price range
    const match = consultantPrice.match(/\$([0-9,]+)/)
    if (!match) return 90
    const consultantLow = parseInt(match[1].replace(',', ''))
    const savings = Math.round((1 - (yourPrice / 100) / consultantLow) * 100)
    return Math.min(99, Math.max(80, savings))
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
      {/* Social Proof Banner */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl p-4 text-white">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-300" />
              <span className="font-semibold">2,847 reports generated this month</span>
            </div>
            <div className="hidden sm:flex items-center gap-2">
              <Star className="w-4 h-4 text-yellow-300 fill-yellow-300" />
              <span className="text-sm">Trusted by founders from YC, Techstars & 500 Startups</span>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full text-sm">
            <Gift className="w-4 h-4" />
            <span>First report FREE for new users</span>
          </div>
        </div>
      </div>

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
                  className="w-full p-3 border border-gray-200 rounded-lg text-sm"
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
              
              <optgroup label="📊 Consultant Studio Reports">
                {studioReports?.reports.map(report => (
                  <option key={report.id} value={`studio:${report.id}`}>
                    {report.name} — {formatPrice(report.price)}
                  </option>
                ))}
              </optgroup>
              
              {categories?.map(cat => (
                <optgroup key={cat.category} label={`📝 ${cat.display_name}`}>
                  {cat.templates.map(template => {
                    const price = template.price_cents || TEMPLATE_PRICES[template.slug] || 4900
                    return (
                      <option key={template.slug} value={`template:${template.slug}`}>
                        {template.name} — {formatPrice(price)}
                      </option>
                    )
                  })}
                </optgroup>
              ))}
            </select>

            {/* Selected Report Info with Value Comparison */}
            {selectedReport && selectedReport.type === 'studio' && (
              <>
                {(() => {
                  const report = studioReports?.reports.find(r => r.id === selectedReport.slug)
                  const Icon = studioReportIcons[selectedReport.slug] || FileText
                  const consultantPrice = CONSULTANT_PRICES[selectedReport.slug] || '$2,000 - $10,000'
                  const savingsPercent = calculateSavingsPercent(report?.price || 0, consultantPrice)
                  const preview = REPORT_PREVIEWS[selectedReport.slug]
                  
                  return (
                    <div className="mt-3 space-y-3">
                      {/* Value Comparison Card */}
                      <div className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border border-green-200">
                        <div className="flex items-center gap-2 mb-3">
                          <Icon className="w-5 h-5 text-green-600" />
                          <span className="font-semibold text-gray-900">{report?.name}</span>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-3 mb-3">
                          <div className="text-center p-2 bg-white rounded border border-gray-200">
                            <div className="text-xs text-gray-500 line-through">Consultants charge</div>
                            <div className="font-semibold text-gray-700">{consultantPrice}</div>
                          </div>
                          <div className="text-center p-2 bg-green-600 rounded text-white">
                            <div className="text-xs opacity-90">Your price</div>
                            <div className="font-bold text-lg">{formatPrice(report?.price || 0)}</div>
                          </div>
                        </div>
                        
                        <div className="flex items-center justify-center gap-2 text-green-700 font-semibold">
                          <TrendingDown className="w-4 h-4" />
                          <span>Save {savingsPercent}%+</span>
                        </div>
                      </div>
                      
                      {/* Preview Card */}
                      {preview && (
                        <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex items-center gap-2 mb-2">
                            <Lock className="w-4 h-4 text-gray-400" />
                            <span className="text-xs font-medium text-gray-600">What you'll get:</span>
                          </div>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {preview.sections.slice(0, 4).map((section, i) => (
                              <span key={i} className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs text-gray-600">
                                {section}
                              </span>
                            ))}
                            {preview.sections.length > 4 && (
                              <span className="px-2 py-0.5 text-xs text-gray-400">
                                +{preview.sections.length - 4} more
                              </span>
                            )}
                          </div>
                          <div className="p-2 bg-white rounded border border-dashed border-gray-300">
                            <p className="text-xs text-gray-500 italic blur-[2px] select-none">
                              {preview.sampleInsight}
                            </p>
                          </div>
                          <div className="mt-2 flex items-center gap-1 text-xs text-amber-600">
                            <Clock className="w-3 h-3" />
                            <span>Generated in under 60 seconds</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })()}
              </>
            )}

            {selectedReport && selectedReport.type === 'template' && (
              <div className="mt-3 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                {(() => {
                  const template = allTemplates.find(t => t.slug === selectedReport.slug)
                  const price = template?.price_cents || TEMPLATE_PRICES[selectedReport.slug] || 4900
                  return (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-gray-900">{template?.name}</span>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${getTierBadge(template?.min_tier || null).className}`}>
                            {getTierBadge(template?.min_tier || null).text}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-gray-600 mb-3">{template?.description}</p>
                      <div className="flex items-center justify-between p-2 bg-white rounded border border-blue-100">
                        <div className="text-center">
                          <div className="text-xs text-gray-500 line-through">Agency cost</div>
                          <div className="font-medium text-gray-600">$500+</div>
                        </div>
                        <div className="text-center px-4 py-1 bg-blue-600 rounded text-white">
                          <div className="text-xs opacity-90">Your price</div>
                          <div className="font-bold">{formatPrice(price)}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-green-600">You save</div>
                          <div className="font-semibold text-green-600">90%+</div>
                        </div>
                      </div>
                      <div className="mt-2 flex items-center gap-1 text-xs text-blue-600">
                        <Clock className="w-3 h-3" />
                        <span>Ready in 60 seconds</span>
                      </div>
                    </>
                  )
                })()}
              </div>
            )}

            {/* Bundles Section */}
            <button
              onClick={() => setShowBundles(!showBundles)}
              className="mt-3 text-xs text-purple-600 hover:text-purple-700 flex items-center gap-1"
            >
              <Package className="w-3 h-3" />
              {showBundles ? 'Hide bundles' : 'View bundle deals (save up to 45%)'}
            </button>

            {showBundles && studioReports?.bundles && (
              <div className="mt-2 space-y-2">
                {studioReports.bundles.map((bundle, idx) => (
                  <div 
                    key={bundle.id} 
                    className={`p-3 rounded-lg border ${idx === 0 ? 'bg-amber-50 border-amber-300 ring-2 ring-amber-200' : 'bg-purple-50 border-purple-100'}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900 text-sm">{bundle.name}</span>
                        {idx === 0 && (
                          <span className="px-2 py-0.5 bg-amber-500 text-white text-xs font-bold rounded">
                            ⭐ MOST POPULAR
                          </span>
                        )}
                      </div>
                      <span className="text-lg font-bold text-gray-900">{formatPrice(bundle.price)}</span>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">{bundle.description}</p>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-green-600 font-medium">
                        Save {formatPrice(bundle.savings)} ({Math.round(bundle.savings / (bundle.price + bundle.savings) * 100)}%)
                      </span>
                      <span className="text-gray-500">
                        {bundle.reports.length} reports included
                      </span>
                    </div>
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
              className="mt-4 px-4 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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

            {/* Trust Signals */}
            <div className="mt-3 flex flex-col items-center gap-2">
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  Secure payment
                </span>
                <span className="flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  Money-back guarantee
                </span>
              </div>
              {/* Stripe Badge */}
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 rounded-full">
                <svg className="w-8 h-3.5" viewBox="0 0 60 25" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M59.64 14.28c0-4.98-2.41-8.91-7.02-8.91-4.63 0-7.44 3.93-7.44 8.87 0 5.85 3.31 8.81 8.06 8.81 2.32 0 4.07-.52 5.39-1.26v-3.89c-1.32.66-2.84 1.07-4.77 1.07-1.89 0-3.56-.66-3.78-2.96h9.52c0-.25.04-1.26.04-1.73zm-9.62-1.85c0-2.2 1.34-3.11 2.57-3.11 1.19 0 2.46.91 2.46 3.11h-5.03z" fill="#635BFF"/>
                  <path d="M38.99 5.37c-1.91 0-3.14.9-3.82 1.52l-.25-1.21h-4.28v22.83l4.86-1.03.01-5.54c.7.5 1.72 1.22 3.42 1.22 3.45 0 6.6-2.78 6.6-8.9-.02-5.6-3.21-8.89-6.54-8.89zm-1.15 13.68c-1.14 0-1.81-.41-2.28-.91l-.02-7.18c.5-.56 1.19-.95 2.3-.95 1.76 0 2.97 1.97 2.97 4.51 0 2.59-1.19 4.53-2.97 4.53z" fill="#635BFF"/>
                  <path d="M28.24 4.18l4.88-1.05V0l-4.88 1.03v3.15zM28.24 5.68h4.88v17.22h-4.88V5.68z" fill="#635BFF"/>
                  <path d="M23.24 6.97l-.31-1.29h-4.2v17.22h4.86V11.3c1.15-1.5 3.09-1.22 3.7-1.01V5.68c-.63-.24-2.92-.68-4.05 1.29z" fill="#635BFF"/>
                  <path d="M13.54 2.12l-4.75 1.01-.02 15.76c0 2.91 2.18 5.05 5.1 5.05 1.61 0 2.79-.3 3.44-.65v-3.95c-.63.25-3.74 1.15-3.74-1.74V9.56h3.74V5.68h-3.74l-.03-3.56z" fill="#635BFF"/>
                  <path d="M4.87 9.83c0-.76.63-1.05 1.66-1.05 1.49 0 3.37.45 4.86 1.26V5.54c-1.63-.65-3.24-.9-4.86-.9C2.64 4.64 0 6.61 0 9.99c0 5.27 7.26 4.43 7.26 6.7 0 .9-.78 1.19-1.88 1.19-1.63 0-3.71-.67-5.36-1.57v4.57c1.82.78 3.67 1.12 5.36 1.12 3.97 0 6.7-1.96 6.7-5.39-.02-5.69-7.31-4.68-7.31-6.78z" fill="#635BFF"/>
                </svg>
                <span className="text-xs text-gray-500">Powered by Stripe</span>
              </div>
            </div>
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
