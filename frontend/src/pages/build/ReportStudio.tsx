import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  FileText,
  BarChart3,
  DollarSign,
  MapPin,
  Target,
  Shield,
  Briefcase,
  Presentation,
  Sparkles,
  Loader2,
  CheckCircle,
  ArrowLeft,
  Lock,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface ReportProduct {
  id: string
  name: string
  description: string
  price_cents: number
  included_in_tier: string | null
}

const REPORT_ICONS: Record<string, React.ElementType> = {
  feasibility_study: Shield,
  business_plan: Briefcase,
  financial_model: DollarSign,
  market_analysis: BarChart3,
  strategic_assessment: Target,
  pestle_analysis: Shield,
  pitch_deck: Presentation,
  location_analysis: MapPin,
}

export default function ReportStudio() {
  const { type } = useParams<{ type?: string }>()
  const navigate = useNavigate()
  const { token, isAuthenticated } = useAuthStore()
  const [selectedReport, setSelectedReport] = useState(type || '')
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const [reports, setReports] = useState<ReportProduct[]>([
    { id: 'feasibility_study', name: 'Feasibility Study', description: 'Quick viability check with market validation', price_cents: 2500, included_in_tier: null },
    { id: 'business_plan', name: 'Business Plan', description: 'Comprehensive strategy document', price_cents: 14900, included_in_tier: 'pro' },
    { id: 'financial_model', name: 'Financial Model', description: '5-year projections and unit economics', price_cents: 12900, included_in_tier: 'pro' },
    { id: 'market_analysis', name: 'Market Analysis', description: 'TAM/SAM/SOM with competitive landscape', price_cents: 9900, included_in_tier: 'business' },
    { id: 'strategic_assessment', name: 'Strategic Assessment', description: 'SWOT analysis and strategic positioning', price_cents: 8900, included_in_tier: 'pro' },
    { id: 'pestle_analysis', name: 'PESTLE Analysis', description: 'Political, Economic, Social, Technological, Legal, Environmental factors', price_cents: 9900, included_in_tier: 'business' },
    { id: 'pitch_deck', name: 'Pitch Deck', description: 'Investor presentation outline and key slides', price_cents: 7900, included_in_tier: 'pro' },
    { id: 'location_analysis', name: 'Location Analysis', description: 'Top 5 locations ranked by 8 proprietary formulas', price_cents: 11900, included_in_tier: null },
  ])

  const handleGenerate = async () => {
    if (!selectedReport) return
    if (!isAuthenticated || !token) {
      setError('Please log in to generate reports.')
      return
    }
    setGenerating(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch('/api/v1/report-pricing/generate-free-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ report_type: selectedReport }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Failed to generate report'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      const data = await res.json()
      setResult(data)
    } catch (e: any) {
      setError(e.message || 'Failed to generate report')
    } finally {
      setGenerating(false)
    }
  }

  const selected = reports.find((r) => r.id === selectedReport)

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-white to-stone-100">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <button
            onClick={() => navigate('/build/consultant-studio')}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Consultant Studio
          </button>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-[#D97757] to-[#B85C3D] rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Report Studio</h1>
              <p className="text-sm text-gray-500">Generate professional business reports powered by AI</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Report Selection */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-4">Select Report</h2>
              <div className="space-y-3">
                {reports.map((report) => {
                  const Icon = REPORT_ICONS[report.id] || FileText
                  const isSelected = selectedReport === report.id
                  return (
                    <button
                      key={report.id}
                      onClick={() => {
                        setSelectedReport(report.id)
                        setResult(null)
                        setError(null)
                      }}
                      className={`w-full text-left p-4 rounded-lg border transition-all ${
                        isSelected
                          ? 'border-[#D97757] bg-[#D97757]/5'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          isSelected ? 'bg-[#D97757] text-white' : 'bg-gray-100 text-gray-500'
                        }`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className={`font-medium text-sm ${isSelected ? 'text-[#D97757]' : 'text-gray-900'}`}>
                              {report.name}
                            </span>
                            <span className="text-sm font-semibold text-gray-900">
                              ${(report.price_cents / 100).toFixed(0)}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">{report.description}</p>
                          {report.included_in_tier && (
                            <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs">
                              <CheckCircle className="w-3 h-3" />
                              Included in {report.included_in_tier}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Report Details / Generation */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              {!selectedReport ? (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Select a Report</h3>
                  <p className="text-gray-500">Choose a report type from the sidebar to get started.</p>
                </div>
              ) : selected ? (
                <div className="space-y-6">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-[#D97757] to-[#B85C3D] rounded-xl flex items-center justify-center">
                      {(REPORT_ICONS[selected.id] || FileText)({ className: 'w-6 h-6 text-white' })}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">{selected.name}</h2>
                      <p className="text-sm text-gray-600 mt-1">{selected.description}</p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-2xl font-bold text-gray-900">
                          ${(selected.price_cents / 100).toFixed(0)}
                        </span>
                        {selected.included_in_tier && (
                          <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded-full text-xs font-medium">
                            Included in {selected.included_in_tier} tier
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {!isAuthenticated && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-amber-700">
                        <Lock className="w-4 h-4" />
                        <span className="text-sm font-medium">Sign in to generate reports</span>
                      </div>
                    </div>
                  )}

                  <button
                    onClick={handleGenerate}
                    disabled={generating || !isAuthenticated}
                    className="w-full px-6 py-3 bg-[#D97757] text-white rounded-lg hover:bg-[#B85C3D] transition-colors disabled:opacity-50 flex items-center justify-center gap-2 font-medium"
                  >
                    {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    {generating ? 'Generating...' : 'Generate Report'}
                  </button>

                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
                      {error}
                    </div>
                  )}

                  {result && (
                    <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                      <div className="flex items-center gap-2 mb-4">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <h3 className="font-semibold text-gray-900">Report Generated</h3>
                      </div>
                      <pre className="text-xs text-gray-600 overflow-auto max-h-96 bg-white p-4 rounded border">
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
