import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  FileText, 
  ChevronDown, 
  ChevronRight, 
  Loader2, 
  Lock, 
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
  ClipboardList
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
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['popular']))
  const [generatingSlug, setGeneratingSlug] = useState<string | null>(null)
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null)
  const [contextInput, setContextInput] = useState(customContext || '')

  const [guestEmail, setGuestEmail] = useState('')
  const [showPurchaseModal, setShowPurchaseModal] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null)
  const [purchaseLoading, setPurchaseLoading] = useState(false)
  const [purchaseError, setPurchaseError] = useState<string | null>(null)

  const { data: categories, isLoading } = useQuery<CategoryWithTemplates[]>({
    queryKey: ['report-templates', isGuest],
    queryFn: async () => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      // Use public endpoint for guests, authenticated endpoint for logged-in users
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
    onError: (error) => {
      setGeneratingSlug(null)
      alert(error instanceof Error ? error.message : 'Failed to generate report')
    },
  })

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  const getTierBadge = (tier: string) => {
    const badges: Record<string, { text: string; className: string }> = {
      pro: { text: 'PRO', className: 'bg-purple-100 text-purple-700' },
      business: { text: 'BUSINESS', className: 'bg-amber-100 text-amber-700' },
      enterprise: { text: 'ENTERPRISE', className: 'bg-gray-100 text-gray-700' },
    }
    return badges[tier] || { text: tier.toUpperCase(), className: 'bg-gray-100 text-gray-600' }
  }

  // Guest mode - show public pricing and allow purchases
  const isGuest = !isAuthenticated

  // Flatten all templates into a single list for dropdown
  const allTemplates = categories?.flatMap(cat => cat.templates) || []

  // Simplified guest UI
  if (isGuest) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Generate AI-Powered Reports</h2>
          <p className="text-sm text-gray-500 mb-6">
            Describe your business idea and select a report type. We'll generate a professional report and deliver it to your email.
          </p>

          {/* Idea Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Describe Your Business Idea
            </label>
            <textarea
              value={contextInput}
              onChange={(e) => setContextInput(e.target.value)}
              placeholder="Example: A mobile app that connects local dog walkers with busy pet owners in urban areas. Target market is working professionals aged 25-45 who own dogs but don't have time for midday walks..."
              className="w-full p-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none"
              rows={5}
            />
          </div>

          {/* Report Type Dropdown */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Report Type
            </label>
            <select
              value={selectedTemplate?.slug || ''}
              onChange={(e) => {
                const template = allTemplates.find(t => t.slug === e.target.value)
                setSelectedTemplate(template || null)
              }}
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 bg-white"
            >
              <option value="">Choose a report...</option>
              {allTemplates.map(template => (
                <option key={template.slug} value={template.slug}>
                  {template.name} — {template.description}
                </option>
              ))}
            </select>
          </div>

          {/* Email Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Mail className="w-4 h-4 inline mr-1" />
              Your Email Address
            </label>
            <input
              type="email"
              value={guestEmail}
              onChange={(e) => setGuestEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              We'll send your completed report to this email
            </p>
          </div>

          {purchaseError && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg">
              {purchaseError}
            </div>
          )}

          {/* Purchase Button */}
          <button
            onClick={async () => {
              if (!contextInput.trim()) {
                setPurchaseError('Please describe your business idea')
                return
              }
              if (!selectedTemplate) {
                setPurchaseError('Please select a report type')
                return
              }
              if (!guestEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(guestEmail)) {
                setPurchaseError('Please enter a valid email address')
                return
              }
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
            }}
            disabled={purchaseLoading || !contextInput.trim() || !selectedTemplate || !guestEmail}
            className="w-full py-4 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg"
          >
            {purchaseLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <DollarSign className="w-5 h-5" />
                Purchase Report
              </>
            )}
          </button>

          <p className="text-sm text-center text-gray-500 mt-4">
            Already have an account? <a href="/login" className="text-purple-600 hover:underline font-medium">Sign in</a> for member pricing & more features
          </p>
        </div>

        {isLoading && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-center gap-2 text-gray-500">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Loading reports...</span>
            </div>
          </div>
        )}
      </div>
    )
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

  if (generatedReport) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-green-500 to-emerald-500 p-4 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">{generatedReport.title}</span>
            </div>
            <button
              onClick={() => setGeneratedReport(null)}
              className="text-white/80 hover:text-white text-sm"
            >
              Generate Another
            </button>
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
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Report Library</h2>
        <p className="text-sm text-gray-500 mb-4">
          Generate AI-powered business reports using your opportunity context
        </p>
        
        {!opportunityId && !workspaceId && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Business Context
            </label>
            <textarea
              value={contextInput}
              onChange={(e) => setContextInput(e.target.value)}
              placeholder="Describe your business idea, market, or opportunity..."
              className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 resize-none"
              rows={3}
            />
          </div>
        )}
      </div>

      {categories?.map((category) => {
        const isExpanded = expandedCategories.has(category.category)
        const CategoryIcon = categoryIcons[category.category] || FileText
        
        return (
          <div key={category.category} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <button
              onClick={() => toggleCategory(category.category)}
              className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <CategoryIcon className="w-5 h-5 text-purple-600" />
                </div>
                <div className="text-left">
                  <div className="font-semibold text-gray-900">{category.display_name}</div>
                  <div className="text-xs text-gray-500">{category.templates.length} reports</div>
                </div>
              </div>
              {isExpanded ? (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-400" />
              )}
            </button>
            
            {isExpanded && (
              <div className="border-t border-gray-100">
                {category.templates.map((template) => {
                  const TemplateIcon = templateIcons[template.slug] || FileText
                  const tierBadge = getTierBadge(template.min_tier)
                  const isGenerating = generatingSlug === template.slug
                  const hasContext = opportunityId || workspaceId || contextInput.trim()
                  
                  return (
                    <div
                      key={template.id}
                      className="p-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3">
                          <TemplateIcon className="w-5 h-5 text-gray-400 mt-0.5" />
                          <div>
                            <div className="font-medium text-gray-900">{template.name}</div>
                            <div className="text-sm text-gray-500">{template.description}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${tierBadge.className}`}>
                            {tierBadge.text}
                          </span>
                          {isGuest ? (
                            <button
                              onClick={() => {
                                setSelectedTemplate(template)
                                setShowPurchaseModal(true)
                              }}
                              disabled={!hasContext}
                              className="px-3 py-1.5 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
                            >
                              <DollarSign className="w-4 h-4" />
                              Purchase
                            </button>
                          ) : (
                            <button
                              onClick={() => generateMutation.mutate({ templateSlug: template.slug })}
                              disabled={isGenerating || !hasContext}
                              className="px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
                            >
                              {isGenerating ? (
                                <>
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  Generating...
                                </>
                              ) : (
                                'Generate'
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}

      {/* Guest Purchase Modal */}
      {showPurchaseModal && selectedTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
            <div className="bg-gradient-to-r from-amber-500 to-orange-500 p-4 text-white">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Purchase Report</h3>
                <button 
                  onClick={() => {
                    setShowPurchaseModal(false)
                    setSelectedTemplate(null)
                    setPurchaseError(null)
                  }}
                  className="text-white/80 hover:text-white"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <div className="font-medium text-gray-900">{selectedTemplate.name}</div>
                <div className="text-sm text-gray-500">{selectedTemplate.description}</div>
              </div>
              
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Your Idea</div>
                <div className="text-sm text-gray-700">
                  {contextInput || 'No context provided'}
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Mail className="w-4 h-4 inline mr-1" />
                  Email Address
                </label>
                <input
                  type="email"
                  value={guestEmail}
                  onChange={(e) => setGuestEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full p-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  We'll send your report to this email
                </p>
              </div>

              {purchaseError && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg">
                  {purchaseError}
                </div>
              )}

              <button
                onClick={async () => {
                  if (!guestEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(guestEmail)) {
                    setPurchaseError('Please enter a valid email address')
                    return
                  }
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
                }}
                disabled={purchaseLoading}
                className="w-full py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 flex items-center justify-center gap-2"
              >
                {purchaseLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    Proceed to Checkout
                  </>
                )}
              </button>

              <p className="text-xs text-center text-gray-500 mt-4">
                Already have an account? <a href="/login" className="text-purple-600 hover:underline">Sign in</a> for member pricing
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
