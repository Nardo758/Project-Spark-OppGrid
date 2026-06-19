import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Lightbulb, Loader2, CheckCircle, Laptop, Warehouse, Globe, Target, TrendingUp, Sparkles, FileText, Library, AlertCircle } from 'lucide-react'
import { useConsultantApi } from '../hooks/useConsultantApi'
import { useAuthStore } from '@/stores/authStore'
import { useReports, ReportType } from '../reports/useReports'
import { useReportPayment } from '../reports/useReportPayment'
import { ReportPurchaseModal } from '../reports/ReportPurchaseModal'
import { ReportLibrary } from '../reports/ReportLibrary'
import type { ValidateIdeaResult } from '../types/consultant'

interface ValidateIdeaProps {
  onWorkspaceClick?: (context: Record<string, unknown>) => void
}

export function ValidateIdea({ onWorkspaceClick }: ValidateIdeaProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuthStore()
  const { validateIdea } = useConsultantApi()
  const { generateReport, isGenerating } = useReports()
  const { checkTierAccess, formatPrice, getReportPrice } = useReportPayment()

  const [ideaDescription, setIdeaDescription] = useState('')
  const [validateResult, setValidateResult] = useState<ValidateIdeaResult | null>(null)
  const [analysisTimer, setAnalysisTimer] = useState(0)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const [showPurchaseModal, setShowPurchaseModal] = useState(false)
  const [purchaseReportType, setPurchaseReportType] = useState<ReportType>('market-analysis')
  const [isGeneratingFeasibility, setIsGeneratingFeasibility] = useState(false)

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isAnalyzing) {
      interval = setInterval(() => {
        setAnalysisTimer((prev) => prev + 1)
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isAnalyzing])

  const validateMutation = useMutation({
    mutationFn: async (data: { idea_description: string }) => {
      setIsAnalyzing(true)
      setAnalysisTimer(0)
      const response = await validateIdea(data.idea_description)
      if (response.error) throw new Error(response.error)
      return response.data as unknown as ValidateIdeaResult
    },
    onSuccess: (data) => {
      setIsAnalyzing(false)
      setValidateResult(data)
      queryClient.invalidateQueries({ queryKey: ['consultant-stats'] })
    },
    onError: () => {
      setIsAnalyzing(false)
    },
  })

  const handleGenerateReport = async (type: ReportType) => {
    const access = checkTierAccess(type)
    if (!access.canGenerate) {
      setPurchaseReportType(type)
      setShowPurchaseModal(true)
      return
    }

    try {
      await generateReport(type, {
        idea: ideaDescription,
        recommendation: validateResult?.recommendation,
        viability_report: validateResult?.viability_report,
      }, 'validate')
    } catch (error) {
      console.error('Failed to generate report:', error)
    }
  }

  const handleFeasibilityGenerate = async () => {
    setIsGeneratingFeasibility(true)
    try {
      await generateReport('feasibility', {
        idea: ideaDescription,
        recommendation: validateResult?.recommendation,
        viability_report: validateResult?.viability_report,
      }, 'validate')
    } finally {
      setIsGeneratingFeasibility(false)
    }
  }

  const handlePurchaseComplete = () => {
    handleGenerateReport(purchaseReportType)
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Validate Your Idea</h2>
        <p className="text-sm text-gray-500 mb-4">
          AI analyzes your idea and recommends: Online, Physical, or Hybrid business model
        </p>
        <textarea
          value={ideaDescription}
          onChange={(e) => setIdeaDescription(e.target.value)}
          placeholder="Describe your business idea in detail..."
          className="w-full h-32 p-4 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
        />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" className="rounded text-purple-600" />
            <span>Digital Product/Service</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" className="rounded text-purple-600" />
            <span>Physical Delivery Required</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" className="rounded text-purple-600" />
            <span>Location Dependent</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" className="rounded text-purple-600" />
            <span>Global Scalability</span>
          </label>
        </div>
        {!isAuthenticated && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-amber-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Please <button onClick={() => navigate('/auth/login')} className="font-semibold underline hover:text-amber-800">sign in</button> to validate your idea.</span>
          </div>
        )}
        <button
          onClick={() => validateMutation.mutate({ idea_description: ideaDescription })}
          disabled={!ideaDescription || validateMutation.isPending || !isAuthenticated}
          className="mt-4 w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center justify-center gap-2"
        >
          {validateMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {`Analyzing... ${Math.floor(analysisTimer / 60)}:${(analysisTimer % 60).toString().padStart(2, '0')}`}
            </>
          ) : (
            <>
              <Lightbulb className="w-5 h-5" />
              Validate Idea
            </>
          )}
        </button>
        {validateMutation.isError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{validateMutation.error?.message || 'Something went wrong. Please try again.'}</span>
          </div>
        )}
      </div>

      {validateResult?.success && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-emerald-500 to-teal-500 p-4 text-white">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Validation Complete</span>
            </div>
          </div>
          <div className="p-6">
            <div className="flex items-center gap-4 mb-6">
              <div className={`px-6 py-3 rounded-xl text-center ${
                validateResult.recommendation === 'ONLINE' 
                  ? 'bg-blue-100 text-blue-700 border-2 border-blue-300' 
                  : validateResult.recommendation === 'PHYSICAL'
                  ? 'bg-orange-100 text-orange-700 border-2 border-orange-300'
                  : 'bg-purple-100 text-purple-700 border-2 border-purple-300'
              }`}>
                <div className="text-lg font-bold flex items-center gap-2">
                  {validateResult.recommendation === 'ONLINE' && <Laptop className="w-5 h-5" />}
                  {validateResult.recommendation === 'PHYSICAL' && <Warehouse className="w-5 h-5" />}
                  {validateResult.recommendation === 'HYBRID' && <Globe className="w-5 h-5" />}
                  {validateResult.recommendation}
                </div>
                <div className="text-xs mt-1">Recommended Model</div>
              </div>
              <div className="flex-1 grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-3 rounded-lg text-center">
                  <div className="text-2xl font-bold text-blue-600">{validateResult.online_score}</div>
                  <div className="text-xs text-blue-600">Online Score</div>
                </div>
                <div className="bg-orange-50 p-3 rounded-lg text-center">
                  <div className="text-2xl font-bold text-orange-600">{validateResult.physical_score}</div>
                  <div className="text-xs text-orange-600">Physical Score</div>
                </div>
              </div>
            </div>
            
            {validateResult.viability_report && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-sm font-medium text-green-800 mb-2">Strengths</div>
                  <ul className="text-xs text-green-700 space-y-1">
                    {validateResult.viability_report.strengths?.map((s, i) => (
                      <li key={i}>• {s}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-sm font-medium text-red-800 mb-2">Weaknesses</div>
                  <ul className="text-xs text-red-700 space-y-1">
                    {validateResult.viability_report.weaknesses?.map((w, i) => (
                      <li key={i}>• {w}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-sm font-medium text-blue-800 mb-2">Opportunities</div>
                  <ul className="text-xs text-blue-700 space-y-1">
                    {validateResult.viability_report.opportunities?.map((o, i) => (
                      <li key={i}>• {o}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-amber-50 p-4 rounded-lg">
                  <div className="text-sm font-medium text-amber-800 mb-2">Threats</div>
                  <ul className="text-xs text-amber-700 space-y-1">
                    {validateResult.viability_report.threats?.map((t, i) => (
                      <li key={i}>• {t}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
            
            <div className="mt-4 flex items-center justify-between p-4 bg-purple-50 rounded-xl">
              <span className="text-sm text-purple-700">AI Confidence Score</span>
              <span className="text-lg font-bold text-purple-700">
                {validateResult.viability_report?.confidence_score || 75}%
              </span>
            </div>

            <div className="mt-6 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-bold">FREE</div>
                <h4 className="text-sm font-semibold text-gray-900">Your Feasibility Study is Ready</h4>
              </div>
              <p className="text-xs text-gray-600 mb-4">
                Score: {validateResult.viability_report?.confidence_score || 75}/100. Now take it further with professional reports.
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleFeasibilityGenerate}
                  disabled={isGeneratingFeasibility || isGenerating}
                  className="inline-flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  {isGeneratingFeasibility ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4" />
                      View Feasibility Study - FREE
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="mt-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <h4 className="text-sm font-semibold text-gray-900">Recommended Reports for Your Idea</h4>
              </div>
              <p className="text-xs text-gray-600 mb-4">
                Get deeper insights with AI-powered analysis tailored to your business concept.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  onClick={() => handleGenerateReport('market-analysis')}
                  disabled={isGenerating}
                  className="flex items-center justify-between p-3 bg-white border border-indigo-200 rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm font-medium text-gray-900">Market Analysis</span>
                  </div>
                  <span className="text-xs text-gray-500">{formatPrice(getReportPrice('market-analysis'))}</span>
                </button>
                <button
                  onClick={() => handleGenerateReport('strategic-assessment')}
                  disabled={isGenerating}
                  className="flex items-center justify-between p-3 bg-white border border-indigo-200 rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm font-medium text-gray-900">Strategic Assessment</span>
                  </div>
                  <span className="text-xs text-gray-500">{formatPrice(getReportPrice('strategic-assessment'))}</span>
                </button>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
              <button
                onClick={() => {
                  const context = encodeURIComponent(JSON.stringify({
                    idea: ideaDescription,
                    recommendation: validateResult.recommendation,
                    viability_report: validateResult.viability_report,
                  }))
                  navigate(`/build/reports?source=validate&context=${context}`)
                }}
                className="w-full py-3 bg-white border-2 border-purple-200 text-purple-700 font-semibold rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-all flex items-center justify-center gap-2"
              >
                <Library className="w-5 h-5" />
                View Full Report Library
              </button>
              {onWorkspaceClick && (
                <button
                  onClick={() => onWorkspaceClick({
                    idea: ideaDescription,
                    recommendation: validateResult.recommendation,
                    viability_report: validateResult.viability_report,
                  })}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2"
                >
                  <FileText className="w-5 h-5" />
                  Open in WorkHub
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Your Reports</h3>
        <ReportLibrary filterBySource="validate" compact />
      </div>

      <ReportPurchaseModal
        isOpen={showPurchaseModal}
        onClose={() => setShowPurchaseModal(false)}
        reportType={purchaseReportType}
        context={{
          idea: ideaDescription,
          recommendation: validateResult?.recommendation,
          viability_report: validateResult?.viability_report,
        }}
        onPurchaseComplete={handlePurchaseComplete}
      />
    </div>
  )
}
