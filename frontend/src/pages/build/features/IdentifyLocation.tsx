import { useState, useEffect, Suspense, lazy } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { MapPin, Loader2, TrendingUp, Globe, FileText, Target, CheckCircle, Building, Users, DollarSign, Store, BarChart3, Library, AlertCircle } from 'lucide-react'
import { useConsultantApi } from '../hooks/useConsultantApi'
import { useAuthStore } from '@/stores/authStore'
import { useReports, ReportType } from '../reports/useReports'
import { useReportPayment } from '../reports/useReportPayment'
import { ReportPurchaseModal } from '../reports/ReportPurchaseModal'
import { ReportLibrary } from '../reports/ReportLibrary'
import type { IdentifyLocationResult, MapData } from '../types/consultant'

const ConsultantMap = lazy(() => import('../../../components/ConsultantMap'))


interface IdentifyLocationProps {
  onWorkspaceClick?: (context: Record<string, unknown>) => void
}

export function IdentifyLocation({ onWorkspaceClick }: IdentifyLocationProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuthStore()
  const { identifyLocation } = useConsultantApi()
  const { generateReport, isGenerating } = useReports()
  const { checkTierAccess, formatPrice, getReportPrice } = useReportPayment()

  const [city, setCity] = useState('')
  const [businessDescription, setBusinessDescription] = useState('')
  const [locationResult, setLocationResult] = useState<IdentifyLocationResult | null>(null)
  const [analysisTimer, setAnalysisTimer] = useState(0)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const [showPurchaseModal, setShowPurchaseModal] = useState(false)
  const [purchaseReportType, setPurchaseReportType] = useState<ReportType>('market-analysis')

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isAnalyzing) {
      interval = setInterval(() => {
        setAnalysisTimer((prev) => prev + 1)
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isAnalyzing])

  const locationMutation = useMutation({
    mutationFn: async (data: { city: string; business_description: string }) => {
      setIsAnalyzing(true)
      setAnalysisTimer(0)
      const response = await identifyLocation(data.city, data.business_description)
      if (response.error) throw new Error(response.error)
      return response.data as unknown as IdentifyLocationResult
    },
    onSuccess: (data) => {
      setIsAnalyzing(false)
      setLocationResult(data)
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
        city: locationResult?.city || city,
        business_description: locationResult?.business_description || businessDescription,
        inferred_category: locationResult?.inferred_category,
        geo_analysis: locationResult?.geo_analysis,
        market_report: locationResult?.market_report,
        site_recommendations: locationResult?.site_recommendations,
      }, 'location')
    } catch (error) {
      console.error('Failed to generate report:', error)
    }
  }

  const handlePurchaseComplete = () => {
    handleGenerateReport(purchaseReportType)
  }

  const demographics = locationResult?.geo_analysis?.demographics
  const marketReport = locationResult?.market_report
  const competitors = locationResult?.geo_analysis?.competitors || []

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Identify Best Location</h2>
        <p className="text-sm text-gray-500 mb-4">
          AI analyzes demographics, competition, and market potential for your business location
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Business Type</label>
            <div className="relative">
              <Store className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={businessDescription}
                onChange={(e) => setBusinessDescription(e.target.value)}
                placeholder="e.g., Self Storage, Coffee Shop, Auto Repair, Gym..."
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">City or Location</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="e.g., Miami, FL or Denver, CO"
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
        
        {!isAuthenticated && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-amber-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Please <button onClick={() => navigate('/auth/login')} className="font-semibold underline hover:text-amber-800">sign in</button> to analyze locations.</span>
          </div>
        )}
        <button
          onClick={() => locationMutation.mutate({ city, business_description: businessDescription })}
          disabled={!city || !businessDescription || locationMutation.isPending || !isAuthenticated}
          className="mt-4 w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center justify-center gap-2"
        >
          {locationMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {`Analyzing Location... ${Math.floor(analysisTimer / 60)}:${(analysisTimer % 60).toString().padStart(2, '0')}`}
            </>
          ) : (
            <>
              <MapPin className="w-5 h-5" />
              Analyze Location
            </>
          )}
        </button>
        {locationMutation.isError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{locationMutation.error?.message || 'Something went wrong. Please try again.'}</span>
          </div>
        )}
      </div>

      {locationResult?.success && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-500 to-indigo-500 p-4 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Location Analysis Complete</span>
              </div>
              {locationResult.processing_time_ms && (
                <span className="text-xs text-blue-100">
                  {(locationResult.processing_time_ms / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          </div>
          
          <div className="p-6 space-y-6">
            <div className="flex items-center gap-4">
              <div className="px-6 py-3 bg-blue-100 rounded-xl text-center">
                <div className="text-lg font-bold text-blue-700 flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  {locationResult.city}{locationResult.state && `, ${locationResult.state}`}
                </div>
                <div className="text-xs text-blue-600 mt-1">
                  {locationResult.inferred_category || 'Business Location'}
                </div>
              </div>
              
              <div className="flex-1 grid grid-cols-3 gap-3">
                {demographics?.population && (
                  <div className="bg-gray-50 p-3 rounded-lg text-center">
                    <Users className="w-4 h-4 mx-auto text-gray-500 mb-1" />
                    <div className="text-xl font-bold text-gray-700">
                      {demographics.population.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Population</div>
                  </div>
                )}
                {demographics?.median_income && (
                  <div className="bg-green-50 p-3 rounded-lg text-center">
                    <DollarSign className="w-4 h-4 mx-auto text-green-500 mb-1" />
                    <div className="text-xl font-bold text-green-600">
                      ${demographics.median_income.toLocaleString()}
                    </div>
                    <div className="text-xs text-green-600">Median Income</div>
                  </div>
                )}
                {competitors.length > 0 && (
                  <div className="bg-orange-50 p-3 rounded-lg text-center">
                    <Store className="w-4 h-4 mx-auto text-orange-500 mb-1" />
                    <div className="text-xl font-bold text-orange-600">
                      {competitors.length}
                    </div>
                    <div className="text-xs text-orange-600">Competitors</div>
                  </div>
                )}
              </div>
            </div>

            {locationResult.map_data && (
              <div className="rounded-xl overflow-hidden border border-gray-200">
                <Suspense fallback={
                  <div className="h-[400px] bg-gray-100 flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                }>
                  <ConsultantMap 
                    mapData={locationResult.map_data as MapData | null} 
                    city={locationResult.city}
                    isLoading={false}
                  />
                </Suspense>
              </div>
            )}

            {marketReport && (
              <div className="bg-gradient-to-br from-gray-50 to-blue-50 rounded-xl p-5 border border-gray-200">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="w-5 h-5 text-blue-600" />
                  <h4 className="font-semibold text-gray-900">Market Analysis</h4>
                  {marketReport.market_score && (
                    <span className={`ml-auto px-3 py-1 rounded-full text-sm font-medium ${
                      marketReport.market_score >= 70 ? 'bg-green-100 text-green-700' :
                      marketReport.market_score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      Score: {marketReport.market_score}/100
                    </span>
                  )}
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  {marketReport.competition_level && (
                    <div className="bg-white p-3 rounded-lg">
                      <div className="text-xs text-gray-500 mb-1">Competition</div>
                      <div className={`font-semibold capitalize ${
                        marketReport.competition_level === 'low' ? 'text-green-600' :
                        marketReport.competition_level === 'moderate' ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {marketReport.competition_level}
                      </div>
                    </div>
                  )}
                  {marketReport.competitor_count !== undefined && (
                    <div className="bg-white p-3 rounded-lg">
                      <div className="text-xs text-gray-500 mb-1">Competitors Found</div>
                      <div className="font-semibold text-gray-800">{marketReport.competitor_count}</div>
                    </div>
                  )}
                  {marketReport.recommendation && (
                    <div className="bg-white p-3 rounded-lg col-span-2">
                      <div className="text-xs text-gray-500 mb-1">Recommendation</div>
                      <div className={`font-semibold capitalize ${
                        marketReport.recommendation === 'favorable' ? 'text-green-600' :
                        marketReport.recommendation === 'moderate' ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {marketReport.recommendation}
                      </div>
                    </div>
                  )}
                </div>

                {marketReport.key_insights && marketReport.key_insights.length > 0 && (
                  <div className="bg-white rounded-lg p-4">
                    <h5 className="text-sm font-medium text-gray-700 mb-2">Key Insights</h5>
                    <ul className="space-y-2">
                      {marketReport.key_insights.map((insight, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                          <span className="text-blue-500 mt-0.5">•</span>
                          {insight}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {locationResult.site_recommendations && locationResult.site_recommendations.length > 0 && (
              <div className="bg-blue-50 rounded-xl p-5 border border-blue-200">
                <h4 className="text-sm font-semibold text-blue-800 mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Site Recommendations
                </h4>
                <div className="grid gap-3">
                  {locationResult.site_recommendations.map((rec, i) => (
                    <div key={i} className="bg-white p-3 rounded-lg flex items-center gap-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        rec.priority === 'high' ? 'bg-green-100 text-green-700' :
                        rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {rec.priority}
                      </span>
                      <div>
                        <div className="font-medium text-gray-800">{rec.type}</div>
                        <div className="text-sm text-gray-500">{rec.reason}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Building className="w-4 h-4 text-indigo-600" />
                <h4 className="text-sm font-semibold text-gray-900">Generate Location Reports</h4>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  onClick={() => handleGenerateReport('feasibility')}
                  disabled={isGenerating}
                  className="flex items-center justify-between p-3 bg-white border border-indigo-200 rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm font-medium text-gray-900">Feasibility Study</span>
                  </div>
                  <span className="text-xs text-gray-500">{formatPrice(getReportPrice('feasibility'))}</span>
                </button>
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
                  onClick={() => handleGenerateReport('pestle')}
                  disabled={isGenerating}
                  className="flex items-center justify-between p-3 bg-white border border-indigo-200 rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-indigo-600" />
                    <span className="text-sm font-medium text-gray-900">PESTLE Analysis</span>
                  </div>
                  <span className="text-xs text-gray-500">{formatPrice(getReportPrice('pestle'))}</span>
                </button>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100 space-y-3">
              <button
                onClick={() => {
                  const context = encodeURIComponent(JSON.stringify({
                    city: locationResult.city,
                    state: locationResult.state,
                    business_description: businessDescription,
                    inferred_category: locationResult.inferred_category,
                    market_report: locationResult.market_report,
                  }))
                  navigate(`/build/reports?source=location&context=${context}`)
                }}
                className="w-full py-3 bg-white border-2 border-purple-200 text-purple-700 font-semibold rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-all flex items-center justify-center gap-2"
              >
                <Library className="w-5 h-5" />
                View Full Report Library
              </button>
              {onWorkspaceClick && (
                <button
                  onClick={() => onWorkspaceClick({
                    city: locationResult.city,
                    state: locationResult.state,
                    business_description: businessDescription,
                    business_type: locationResult.inferred_category,
                    location_data: locationResult,
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
        <ReportLibrary filterBySource="location" compact />
      </div>

      <ReportPurchaseModal
        isOpen={showPurchaseModal}
        onClose={() => setShowPurchaseModal(false)}
        reportType={purchaseReportType}
        context={{
          city: locationResult?.city || city,
          business_description: locationResult?.business_description || businessDescription,
          inferred_category: locationResult?.inferred_category,
          geo_analysis: locationResult?.geo_analysis,
          market_report: locationResult?.market_report,
          site_recommendations: locationResult?.site_recommendations,
        }}
        onPurchaseComplete={handlePurchaseComplete}
      />
    </div>
  )
}
