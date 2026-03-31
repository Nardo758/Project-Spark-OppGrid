import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  FileText, 
  ChevronDown, 
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

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  popular: Sparkles,
  marketing: Megaphone,
  product: ClipboardList,
  business: BarChart3,
  research: SearchIcon,
}

const templateIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  ad_creatives: Megaphone,
  brand_package: Sparkles,
  landing_page: FileText,
  content_calendar: Calendar,
  email_funnel: Mail,
  email_sequence: Mail,
  lead_magnet: Target,
  sales_funnel: TrendingUp,
  seo_content: SearchIcon,
  tweet_landing: FileText,
  user_personas: Users,
  feature_specs: ClipboardList,
  mvp_roadmap: Target,
  prd: FileText,
  gtm_calendar: Calendar,
  gtm_strategy: TrendingUp,
  kpi_dashboard: BarChart3,
  pricing_strategy: DollarSign,
  competitive_analysis: SearchIcon,
  customer_interview: Users,
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
  const [generatingSlug, setGeneratingSlug] = useState<string | null>(null)
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null)
  const [contextInput, setContextInput] = useState(customContext || '')
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null)

  const [guestEmail, setGuestEmail] = useState('')
  const [purchaseLoading, setPurchaseLoading] = useState(false)
  const [purchaseError, setPurchaseError] = useState<string | null>(null)

  // Guest mode
  const isGuest = !isAuthenticated

  const { data: categories, isLoading } = useQuery<CategoryWithTemplates[]>({
    queryKey: ['report-templates', isGuest],
    queryFn: async () => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      const endpoint = isGuest ? '/api/v1/reports/templates/public' : '/api/v1/reports/templates'
      const res = await fetch(endpoint, { headers })
      if (!res.ok) throw new Error('Failed to fetch templates')
      return res.json()
    },
  })

  const generateMutation = useMutation({
    mutationFn: async ({ templateSlug }: { templateSlug: string }) => {
      setGeneratingSlug(templateSlug)
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      
      const res = await fetch('/api/v1/reports/generate', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          template_slug: templateSlug,
          opportunity_id: opportunityId,
          workspace_id: workspaceId,
          custom_context: contextInput || customContext,
        }),
      })
      
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to generate report')
      }
      
      return res.json() as Promise<GeneratedReport>
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

  const getTierBadge = (tier: string) => {
    const badges: Record<string, { text: string; className: string }> = {
      free: { text: 'FREE', className: 'bg-green-100 text-green-700' },
      pro: { text: 'PRO', className: 'bg-purple-100 text-purple-700' },
      business: { text: 'BUSINESS', className: 'bg-amber-100 text-amber-700' },
      enterprise: { text: 'ENTERPRISE', className: 'bg-gray-100 text-gray-700' },
    }
    return badges[tier] || { text: tier.toUpperCase(), className: 'bg-gray-100 text-gray-600' }
  }

  // Flatten all templates into a single list for dropdown
  const allTemplates = categories?.flatMap(cat => cat.templates) || []

  // Group templates by category for organized dropdown
  const groupedTemplates = categories?.reduce((acc, cat) => {
    acc[cat.display_name] = cat.templates
    return acc
  }, {} as Record<string, ReportTemplate[]>) || {}

  const hasContext = opportunityId || workspaceId || contextInput.trim()
  const canGenerate = hasContext && selectedTemplate

  const handleGenerate = () => {
    if (!selectedTemplate) return
    
    if (isGuest) {
      // Guest purchase flow
      if (!guestEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(guestEmail)) {
        setPurchaseError('Please enter a valid email address')
        return
      }
      handleGuestPurchase()
    } else {
      // Authenticated generate
      generateMutation.mutate({ templateSlug: selectedTemplate.slug })
    }
  }

  const handleGuestPurchase = async () => {
    if (!selectedTemplate) return
    
    setPurchaseLoading(true)
    setPurchaseError(null)
    try {
      const baseUrl = window.location.origin
      const res = await fetch('/api/v1/report-pricing/studio-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_type: selectedTemplate.slug,
          custom_context: contextInput,
          email: guestEmail,
          success_url: `${baseUrl}/billing/return?status=success`,
          cancel_url: `${baseUrl}/billing/return?status=canceled`,
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Checkout failed')
      if (data.url) {
        window.location.href = data.url
      }
    } catch (e) {
      setPurchaseError(e instanceof Error ? e.message : 'Checkout failed')
    } finally {
      setPurchaseLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-center gap-2 text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading report library...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Two-Column Input Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="grid md:grid-cols-2 gap-6">
          {/* LEFT: Business Context Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Business Context
            </label>
            <textarea
              value={contextInput}
              onChange={(e) => setContextInput(e.target.value)}
              placeholder="Describe your business idea, market, or opportunity..."
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none text-sm"
              rows={4}
            />
            <p className="text-xs text-gray-400 mt-1">{contextInput.length}/2000</p>
          </div>

          {/* RIGHT: Report Selection & Generate */}
          <div className="flex flex-col">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Report Type
            </label>
            <select
              value={selectedTemplate?.slug || ''}
              onChange={(e) => {
                const template = allTemplates.find(t => t.slug === e.target.value)
                setSelectedTemplate(template || null)
              }}
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 bg-white text-sm"
            >
              <option value="">Choose a report...</option>
              {Object.entries(groupedTemplates).map(([categoryName, templates]) => (
                <optgroup key={categoryName} label={categoryName}>
                  {templates.map(template => (
                    <option key={template.slug} value={template.slug}>
                      {template.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>

            {/* Selected template info */}
            {selectedTemplate && (
              <div className="mt-2 p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{selectedTemplate.name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${getTierBadge(selectedTemplate.min_tier).className}`}>
                    {getTierBadge(selectedTemplate.min_tier).text}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{selectedTemplate.description}</p>
              </div>
            )}

            {/* Guest email input */}
            {isGuest && selectedTemplate && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Mail className="w-3 h-3 inline mr-1" />
                  Email for delivery
                </label>
                <input
                  type="email"
                  value={guestEmail}
                  onChange={(e) => setGuestEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full p-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-sm"
                />
              </div>
            )}

            {purchaseError && (
              <div className="mt-2 p-2 bg-red-50 text-red-700 text-xs rounded-lg">
                {purchaseError}
              </div>
            )}

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={!canGenerate || generateMutation.isPending || purchaseLoading}
              className="mt-auto px-4 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {generateMutation.isPending || purchaseLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {isGuest ? 'Processing...' : 'Generating...'}
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  {isGuest ? 'Purchase Report' : 'Generate Report'}
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

      {/* Generated Report Output */}
      {generatedReport && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-fade-in">
          <div className="bg-gradient-to-r from-green-500 to-emerald-500 p-4 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">{generatedReport.title}</span>
              </div>
              <div className="flex items-center gap-2">
                <button className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-sm flex items-center gap-1">
                  <Download className="w-4 h-4" />
                  Export
                </button>
                <button
                  onClick={() => setGeneratedReport(null)}
                  className="text-white/80 hover:text-white text-sm"
                >
                  ✕ Close
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
            {generatedReport.confidence_score && (
              <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                <span>Confidence Score:</span>
                <span className="font-semibold text-purple-600">{generatedReport.confidence_score}%</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick Access Report Categories */}
      {!generatedReport && (
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {categories?.slice(0, 4).map((category) => {
            const CategoryIcon = categoryIcons[category.category] || FileText
            return (
              <button
                key={category.category}
                onClick={() => {
                  if (category.templates.length > 0) {
                    setSelectedTemplate(category.templates[0])
                  }
                }}
                className="p-4 bg-white rounded-xl border border-gray-200 hover:border-amber-300 hover:shadow-sm transition-all text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <CategoryIcon className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">{category.display_name}</div>
                    <div className="text-xs text-gray-500">{category.templates.length} reports</div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
