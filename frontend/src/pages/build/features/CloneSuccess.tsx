import { useState, useEffect, Suspense, lazy } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Copy, Loader2, TrendingUp, Target, FileText, CheckCircle, MapPin, Star, Building, Library, AlertCircle } from 'lucide-react'
import { useConsultantApi } from '../hooks/useConsultantApi'
import { useAuthStore } from '@/stores/authStore'
import { useReports, ReportType } from '../reports/useReports'
import { useReportPayment } from '../reports/useReportPayment'
import { ReportPurchaseModal } from '../reports/ReportPurchaseModal'
import { ReportLibrary } from '../reports/ReportLibrary'
import type { CloneSuccessResult, MatchingLocation } from '../types/consultant'

const CloneBubbleMap = lazy(() => import('../../../components/CloneBubbleMap'))

interface CloneSuccessProps {
  onWorkspaceClick?: (context: Record<string, unknown>) => void
}

export function CloneSuccess({ onWorkspaceClick }: CloneSuccessProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuthStore()
  const { cloneSuccess } = useConsultantApi()
  const { generateReport, isGenerating } = useReports()
  const { checkTierAccess, formatPrice, getReportPrice } = useReportPayment()

  const [businessName, setBusinessName] = useState('')
  const [businessAddress, setBusinessAddress] = useState('')
  const [targetCity, setTargetCity] = useState('')
  const [targetState, setTargetState] = useState('')
  const [radiusMiles, setRadiusMiles] = useState(5)
  const [cloneResult, setCloneResult] = useState<CloneSuccessResult | null>(null)
  const [selectedLocation, setSelectedLocation] = useState<MatchingLocation | null>(null)
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

  const cloneMutation = useMutation({
    mutationFn: async (data: {
      business_name: string
      business_address: string
      target_city?: string
      target_state?: string
      radius_miles: number
    }) => {
      setIsAnalyzing(true)
      setAnalysisTimer(0)
      const response = await cloneSuccess(data)
      if (response.error) throw new Error(response.error)
      return response.data as unknown as CloneSuccessResult
    },
    onSuccess: (data) => {
      setIsAnalyzing(false)
      setCloneResult(data)
      if (data.matching_locations && data.matching_locations.length > 0) {
        setSelectedLocation(data.matching_locations[0])
      }
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
        source_business: cloneResult?.source_business,
        target_location: selectedLocation,
        matching_locations: cloneResult?.matching_locations,
      }, 'clone')
    } catch (error) {
      console.error('Failed to generate report:', error)
    }
  }

  const handlePurchaseComplete = () => {
    handleGenerateReport(purchaseReportType)
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Clone a Successful Business</h2>
        <p className="text-sm text-gray-500 mb-4">
          Find the best locations to replicate a proven business model
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
            <div className="relative">
              <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="e.g., Shake Shack, SoulCycle, Warby Parker"
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Business Address (Original Location)</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={businessAddress}
                onChange={(e) => setBusinessAddress(e.target.value)}
                placeholder="e.g., 691 Broadway, New York, NY"
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target City (Optional)</label>
              <input
                type="text"
                value={targetCity}
                onChange={(e) => setTargetCity(e.target.value)}
                placeholder="e.g., Austin"
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target State (Optional)</label>
              <input
                type="text"
                value={targetState}
                onChange={(e) => setTargetState(e.target.value)}
                placeholder="e.g., TX"
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search Radius</label>
            <div className="flex gap-2">
              {[3, 5, 10, 25].map((radius) => (
                <button
                  key={radius}
                  onClick={() => setRadiusMiles(radius)}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    radiusMiles === radius
                      ? 'bg-purple-600 text-white border-purple-600'
                      : 'bg-white text-gray-700 border-gray-200 hover:border-purple-300'
                  }`}
                >
                  {radius} miles
                </button>
              ))}
            </div>
          </div>
        </div>
        
        {!isAuthenticated && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-amber-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Please <button onClick={() => navigate('/auth/login')} className="font-semibold underline hover:text-amber-800">sign in</button> to find clone locations.</span>
          </div>
        )}
        <button
          onClick={() => cloneMutation.mutate({
            business_name: businessName,
            business_address: businessAddress,
            target_city: targetCity || undefined,
            target_state: targetState || undefined,
            radius_miles: radiusMiles,
          })}
          disabled={!businessName || !businessAddress || cloneMutation.isPending || !isAuthenticated}
          className="mt-4 w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center justify-center gap-2"
        >
          {cloneMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {`Analyzing Business... ${Math.floor(analysisTimer / 60)}:${(analysisTimer % 60).toString().padStart(2, '0')}`}
            </>
          ) : (
            <>
              <Copy className="w-5 h-5" />
              Find Clone Locations
            </>
          )}
        </button>
        {cloneMutation.isError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{cloneMutation.error?.message || 'Something went wrong. Please try again.'}</span>
          </div>
        )}
      </div>

      {cloneResult?.success && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-orange-500 to-red-500 p-4 text-white">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Clone Analysis Complete</span>
            </div>
          </div>
          <div className="p-6">
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <h4 className="font-medium text-gray-900 mb-2">Source Business</h4>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-lg font-semibold text-gray-900">{cloneResult.source_business?.name}</p>
                  <p className="text-sm text-gray-500">{cloneResult.source_business?.address}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                  <span className="font-medium">{cloneResult.source_business?.rating || 'N/A'}</span>
                  <span className="text-gray-400">({cloneResult.source_business?.reviews_count || 0} reviews)</span>
                </div>
              </div>
            </div>

            {cloneResult.matching_locations && cloneResult.matching_locations.length > 0 && (
              <div className="rounded-xl overflow-hidden border border-gray-200 mb-6">
                <Suspense fallback={
                  <div className="h-[350px] bg-gray-100 flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                }>
                  <CloneBubbleMap 
                    locations={cloneResult.matching_locations as any}
                    selectedLocation={selectedLocation as any}
                    onSelectLocation={(loc) => setSelectedLocation(loc as unknown as MatchingLocation)}
                  />
                </Suspense>
              </div>
            )}

            <h4 className="font-medium text-gray-900 mb-3">Matching Locations</h4>
            <div className="space-y-3 mb-6">
              {cloneResult.matching_locations?.map((loc, index) => (
                <div
                  key={index}
                  onClick={() => setSelectedLocation(loc)}
                  className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                    selectedLocation === loc
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-purple-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        index === 0 ? 'bg-yellow-100 text-yellow-700' :
                        index === 1 ? 'bg-gray-100 text-gray-700' :
                        index === 2 ? 'bg-orange-100 text-orange-700' :
                        'bg-gray-50 text-gray-500'
                      }`}>
                        #{index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{loc.city}, {loc.state}</p>
                        <p className="text-xs text-gray-500">Competition: {loc.competition_count || 'N/A'}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-purple-600">{Math.round(loc.similarity_score)}/100</div>
                      <div className="text-xs text-gray-500">Match Score</div>
                    </div>
                  </div>
                  {loc.key_factors && loc.key_factors.length > 0 && (
                    <p className="text-sm text-gray-600 mt-2">{loc.key_factors.join(', ')}</p>
                  )}
                </div>
              ))}
            </div>

            {selectedLocation && (
              <div className="mt-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-4 h-4 text-indigo-600" />
                  <h4 className="text-sm font-semibold text-gray-900">
                    Generate Reports for {selectedLocation.city}, {selectedLocation.state}
                  </h4>
                </div>
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
            )}

            <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
              <button
                onClick={() => {
                  const context = encodeURIComponent(JSON.stringify({
                    source_business: cloneResult.source_business,
                    target_location: selectedLocation,
                    matching_locations: cloneResult.matching_locations,
                  }))
                  navigate(`/build/reports?source=clone&context=${context}`)
                }}
                className="w-full py-3 bg-white border-2 border-purple-200 text-purple-700 font-semibold rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-all flex items-center justify-center gap-2"
              >
                <Library className="w-5 h-5" />
                View Full Report Library
              </button>
              {onWorkspaceClick && (
                <button
                  onClick={() => onWorkspaceClick({
                    source_business: cloneResult.source_business,
                    target_location: selectedLocation,
                    matching_locations: cloneResult.matching_locations,
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
        <ReportLibrary filterBySource="clone" compact />
      </div>

      <ReportPurchaseModal
        isOpen={showPurchaseModal}
        onClose={() => setShowPurchaseModal(false)}
        reportType={purchaseReportType}
        context={{
          source_business: cloneResult?.source_business,
          target_location: selectedLocation,
          matching_locations: cloneResult?.matching_locations,
        }}
        onPurchaseComplete={handlePurchaseComplete}
      />
    </div>
  )
}
