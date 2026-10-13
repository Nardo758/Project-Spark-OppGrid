import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import { useUpgrade } from '../contexts/UpgradeContext'
import { useMemo, useEffect, useState } from 'react'
import { 
  Brain, Target, Lightbulb, Users, FileText, DollarSign, Zap, Loader2, Lock, Bookmark, ChevronRight, Briefcase, CheckCircle, X
} from 'lucide-react'
import type { AccessInfo } from '../types/paywall'
import { useInlinePayment } from '../hooks/useInlinePayment'
import PayPerUnlockModal from '../components/PayPerUnlockModal'

const quickActions = [
  { icon: Target, label: 'Find Opportunity', path: '/discover', color: 'bg-blue-500' },
  { icon: Lightbulb, label: 'My Projects', path: '/projects', color: 'bg-yellow-500' },
  { icon: FileText, label: 'Business Plan', path: '/build/business-plan', color: 'bg-purple-500' },
  { icon: Users, label: 'Find Expert Help', path: '/build/experts', color: 'bg-pink-500' },
  { icon: Briefcase, label: 'My Engagements', path: '/build/engagements', color: 'bg-violet-500' },
  { icon: DollarSign, label: 'Find Money', path: '/build/funding', color: 'bg-orange-500' },
]

type Opportunity = {
  id: number
  title: string
  category: string
  description?: string
  feasibility_score?: number
  created_at: string
  status?: string
  ai_competition_level?: string | null
  ai_market_size_estimate?: string | null
  ai_summary?: string | null
  validation_count?: number
  growth_rate?: number
  views?: number
  saves?: number
}

type OpportunityList = {
  opportunities: Opportunity[]
  total: number
}

function formatMarketSize(size?: string | null): string {
  if (!size) return '~$50M'
  const cleaned = size.replace(/\s/g, '')
  let value = cleaned
  if (cleaned.includes('-')) {
    value = cleaned.split('-')[0]
  }
  const match = value.match(/\$?([\d.]+)([BMK])?/i)
  if (match) {
    const num = Math.round(parseFloat(match[1]))
    const suffix = match[2]?.toUpperCase() || 'M'
    return `~$${num}${suffix}`
  }
  return size.startsWith('~') ? size : `~${size}`
}

export default function Dashboard() {
  const { user, token, isAuthenticated } = useAuthStore()
  const { showUpgradeModal } = useUpgrade()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [showSubscriptionSuccess, setShowSubscriptionSuccess] = useState(false)
  
  const { 
    state: paymentState, 
    startCheckout, 
    closePaymentModal, 
    handlePaymentConfirmed 
  } = useInlinePayment(undefined, '/dashboard')

  // Handle subscription success notification
  useEffect(() => {
    if (searchParams.get('subscription') === 'success') {
      setShowSubscriptionSuccess(true)
      setSearchParams({})
      // Auto-hide after 5 seconds
      const timer = setTimeout(() => setShowSubscriptionSuccess(false), 5000)
      return () => clearTimeout(timer)
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    const checkoutTier = searchParams.get('checkout')
    if (!checkoutTier) return
    
    if (!isAuthenticated) {
      navigate(`/login?next=${encodeURIComponent(`/dashboard?checkout=${checkoutTier}`)}`)
      return
    }
    
    if (paymentState.paymentModalOpen || paymentState.isLoading) return
    
    const normalizedTier = checkoutTier.toLowerCase()
    if (normalizedTier === 'monthly') {
      setSearchParams({})
      startCheckout('monthly')
    }
  }, [searchParams, isAuthenticated, paymentState.paymentModalOpen, paymentState.isLoading, startCheckout, setSearchParams, navigate])

  const { data: opportunities, isLoading, isError: opportunitiesError } = useQuery({
    queryKey: ['dashboard-opportunities', { isAuthenticated }],
    queryFn: async (): Promise<OpportunityList> => {
      const headers: Record<string, string> = {}
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch('/api/v1/opportunities/?limit=5&sort_by=recent', { headers })
      if (!res.ok) throw new Error('Failed to load opportunities')
      return res.json()
    },
  })

  const { data: userStats } = useQuery({
    queryKey: ['user-report-stats', { isAuthenticated }],
    enabled: isAuthenticated,
    queryFn: async () => {
      const headers: Record<string, string> = {}
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch('/api/v1/reports/my-stats', { headers })
      if (!res.ok) return null
      return res.json()
    },
  })

  const { data: consultantStats } = useQuery({
    queryKey: ['consultant-stats', { isAuthenticated }],
    queryFn: async () => {
      const headers: Record<string, string> = {}
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch('/api/v1/consultant/stats', { headers })
      if (!res.ok) return null
      return res.json()
    },
  })

  const topOpportunities = opportunities?.opportunities?.slice(0, 3) || []
  const avgMatch = topOpportunities.length > 0 
    ? Math.round(topOpportunities.reduce((acc, o) => acc + (o.feasibility_score || 75), 0) / topOpportunities.length)
    : 0

  const opportunityIds = useMemo(() => 
    topOpportunities.map(o => o.id),
    [topOpportunities]
  )

  const { data: accessInfoData } = useQuery({
    queryKey: ['dashboard-batch-access', opportunityIds],
    enabled: opportunityIds.length > 0,
    queryFn: async (): Promise<Record<number, AccessInfo>> => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch('/api/v1/opportunities/batch-access', {
        method: 'POST',
        headers,
        body: JSON.stringify(opportunityIds),
      })
      if (!res.ok) return {}
      return res.json()
    },
    staleTime: 60 * 1000,
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {showSubscriptionSuccess && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <div>
              <p className="font-medium text-green-900">Subscription activated!</p>
              <p className="text-sm text-green-700">Welcome to your new plan. Enjoy your premium features!</p>
            </div>
          </div>
          <button 
            onClick={() => setShowSubscriptionSuccess(false)}
            className="p-1 hover:bg-green-100 rounded-full transition-colors"
          >
            <X className="w-4 h-4 text-green-600" />
          </button>
        </div>
      )}
      
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-2xl p-6 mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">
              Welcome back, {user?.name || 'Entrepreneur'}!
            </h1>
            <p className="text-gray-300">
              Your AI Match Score: <span className="text-green-400 font-semibold">{avgMatch}%</span> • 
              {opportunities?.total || 0} opportunities available
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex gap-3">
            <Link
              to="/brain"
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
            >
              <Brain className="w-5 h-5" />
              AI Co-founder
            </Link>
            <button
              onClick={() => showUpgradeModal('general', 'Dashboard')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-amber-400 hover:bg-amber-500 text-gray-900 rounded-lg font-medium"
            >
              <DollarSign className="w-5 h-5" />
              Upgrade plan
            </button>
          </div>
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {quickActions.map((action, i) => (
            <Link
              key={i}
              to={action.path}
              className="bg-white p-4 rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all text-center"
            >
              <div className={`w-10 h-10 ${action.color} rounded-lg flex items-center justify-center mx-auto mb-3`}>
                <action.icon className="w-5 h-5 text-white" />
              </div>
              <span className="text-sm font-medium text-gray-700">{action.label}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">AI-Curated Opportunities</h2>
            <Link to="/discover" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              View All →
            </Link>
          </div>
          <div className="space-y-4">
            {isLoading ? (
              <div className="bg-white p-8 rounded-xl border border-gray-200 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                <span className="ml-2 text-gray-500">Loading opportunities...</span>
              </div>
            ) : opportunitiesError ? (
              <div className="bg-red-50 p-6 rounded-xl border border-red-200 text-red-700">
                <p className="font-medium">Unable to load opportunities</p>
                <p className="text-sm mt-1">Please try refreshing the page.</p>
              </div>
            ) : topOpportunities.length > 0 ? (
              <div className="grid md:grid-cols-2 gap-4">
                {topOpportunities.map((opp) => {
                  const score = opp.feasibility_score || (70 + (opp.id % 20))
                  const growth = opp.growth_rate || (5 + (opp.id % 25))
                  const signals = opp.validation_count || (2 + (opp.id % 18))
                  const marketSize = formatMarketSize(opp.ai_market_size_estimate)
                  const accessInfo = accessInfoData?.[opp.id]
                  const isAccessible = accessInfo?.is_accessible ?? true
                  
                  return (
                    <div 
                      key={opp.id} 
                      onClick={() => navigate(`/opportunity/${opp.id}`)}
                      className="bg-white p-5 rounded-xl border-2 border-stone-200 hover:border-stone-900 transition-all cursor-pointer group"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-stone-500 uppercase">{opp.category}</span>
                          {!isAccessible && (
                            <span className="flex items-center gap-1 bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full text-xs font-medium">
                              <Lock className="w-3 h-3" />
                              Upgrade for Premium
                            </span>
                          )}
                          {isAccessible && (
                            <span className="flex items-center gap-1 bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-xs font-medium">
                              Unlocked
                            </span>
                          )}
                        </div>
                        <div className="bg-emerald-100 text-emerald-700 px-3 py-2 rounded-full flex-shrink-0">
                          <div className="text-2xl font-bold leading-none">{score}</div>
                        </div>
                      </div>
                      
                      <h3 className="font-semibold text-stone-900 text-lg mb-1 group-hover:text-violet-600 transition-colors">{opp.title}</h3>
                      <p className="text-sm text-stone-500 mb-4 line-clamp-2">
                        {(() => {
                          const desc = opp.description?.replace(/\*\*/g, '').split('\n').filter(l => l.trim() && !l.includes('Market Opportunity Overview'))[0]
                          const summary = opp.ai_summary?.replace(/\*\*/g, '')
                          return desc || summary || 'Analysis pending...'
                        })()}
                      </p>
                      
                      <div className="grid grid-cols-3 gap-3 mb-4">
                        <div className="bg-stone-50 rounded-lg p-3">
                          <div className="text-xs text-stone-500 mb-1">Signals</div>
                          <div className="text-lg font-bold text-stone-900">{signals}</div>
                        </div>
                        <div className="bg-stone-50 rounded-lg p-3">
                          <div className="text-xs text-stone-500 mb-1">Market</div>
                          <div className="text-lg font-bold text-stone-900">{marketSize}</div>
                        </div>
                        <div className="bg-stone-50 rounded-lg p-3">
                          <div className="text-xs text-stone-500 mb-1">Growth</div>
                          <div className="text-lg font-bold text-emerald-600">+{growth}%</div>
                        </div>
                      </div>
                      
                      <div className="pt-4 border-t border-stone-200 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <button 
                            onClick={(e) => { e.stopPropagation(); navigate(`/build/reports?opp=${opp.id}`) }}
                            className="flex items-center gap-1 text-sm text-stone-600 hover:text-violet-600"
                          >
                            <FileText className="w-4 h-4" /> Report
                          </button>
                          <button className="flex items-center gap-1 text-sm text-stone-600 hover:text-violet-600">
                            <Bookmark className="w-4 h-4" /> Save
                          </button>
                        </div>
                        <div className="flex items-center gap-1 text-sm text-stone-600 group-hover:text-violet-600 transition-colors">
                          <span>View full analysis</span>
                          <ChevronRight className="w-4 h-4" />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="bg-white p-8 rounded-xl border border-gray-200 text-center">
                <p className="text-gray-500">No opportunities found yet.</p>
                <Link to="/discover" className="text-blue-600 font-medium hover:text-blue-700 mt-2 inline-block">
                  Explore All Opportunities →
                </Link>
              </div>
            )}
          </div>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Progress Tracker</h2>
          <div className="bg-white p-5 rounded-xl border border-gray-200 mb-6">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Reports Generated</span>
                  <span className="font-semibold text-gray-900">{userStats?.total_reports || 0}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full">
                  <div className="h-2 bg-blue-500 rounded-full" style={{ width: `${Math.min((userStats?.total_reports || 0) * 10, 100)}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Ideas Validated</span>
                  <span className="font-semibold text-gray-900">{consultantStats?.validate_idea_count || 0}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full">
                  <div className="h-2 bg-green-500 rounded-full" style={{ width: `${Math.min((consultantStats?.validate_idea_count || 0) * 10, 100)}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Locations Analyzed</span>
                  <span className="font-semibold text-gray-900">{consultantStats?.identify_location_count || 0}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full">
                  <div className="h-2 bg-purple-500 rounded-full" style={{ width: `${Math.min((consultantStats?.identify_location_count || 0) * 10, 100)}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Recommendations</h2>
          <div className="bg-gradient-to-br from-purple-50 to-indigo-50 p-5 rounded-xl border border-purple-200">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Train Your AI Co-founder</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Upload your business documents to get more personalized recommendations.
                </p>
                <Link to="/brain" className="text-sm text-purple-600 font-medium hover:text-purple-700">
                  Start Training →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {paymentState.paymentModalOpen && paymentState.publishableKey && paymentState.clientSecret && (
        <PayPerUnlockModal
          publishableKey={paymentState.publishableKey}
          clientSecret={paymentState.clientSecret}
          amountLabel={paymentState.priceLabel || ''}
          title={`Subscribe to ${paymentState.selectedTier?.charAt(0).toUpperCase()}${paymentState.selectedTier?.slice(1) || ''}`}
          contextLabel="Subscription"
          confirmLabel={`Subscribe ${paymentState.priceLabel}`}
          footnote="Your subscription will begin immediately after payment."
          onClose={closePaymentModal}
          onConfirmed={handlePaymentConfirmed}
        />
      )}
    </div>
  )
}
