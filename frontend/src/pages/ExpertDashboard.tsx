import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { 
  DollarSign, Users, TrendingUp, Clock, CheckCircle, Loader2,
  Briefcase, CreditCard, AlertCircle, ChevronRight, Calendar
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

type Engagement = {
  id: number
  user_id: number
  engagement_type: string
  status: string
  title: string | null
  description: string | null
  proposed_amount_cents: number | null
  final_amount_cents: number | null
  platform_fee_cents: number | null
  expert_payout_cents: number | null
  created_at: string
  accepted_at: string | null
  completed_at: string | null
  client_name: string | null
  client_email: string | null
  is_reviewed: boolean
}

type ConnectStatus = {
  connected: boolean
  onboarding_complete: boolean
  payouts_enabled: boolean
  account_id: string | null
  charges_enabled?: boolean
  error?: string
}

type Earnings = {
  total_earned_cents: number
  total_platform_fees_cents: number
  pending_earnings_cents: number
  completed_engagements: number
  active_engagements: number
  payouts_enabled: boolean
}

function formatCents(cents: number | null): string {
  if (!cents) return '—'
  return `$${(cents / 100).toLocaleString()}`
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString()
}

function getStatusBadge(status: string) {
  const config: Record<string, { bg: string, text: string, label: string }> = {
    request_sent: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'New Request' },
    proposal_sent: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Proposal Sent' },
    negotiating: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Negotiating' },
    accepted: { bg: 'bg-green-100', text: 'text-green-700', label: 'Accepted' },
    in_progress: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'In Progress' },
    paused: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Paused' },
    completed: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Completed' },
    declined: { bg: 'bg-red-100', text: 'text-red-700', label: 'Declined' },
    cancelled: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Cancelled' }
  }
  const cfg = config[status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: status }
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  )
}

export default function ExpertDashboard() {
  const { token, isAuthenticated } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'overview' | 'clients' | 'earnings'>('overview')
  const location = useLocation()
  const queryClient = useQueryClient()
  
  const isConnectCallback = location.pathname.includes('/expert/connect/')
  
  useEffect(() => {
    if (isConnectCallback) {
      queryClient.invalidateQueries({ queryKey: ['connect-status'] })
      if (location.pathname.includes('/complete')) {
        setActiveTab('earnings')
      }
    }
  }, [isConnectCallback, location.pathname, queryClient])

  const { data: connectStatus } = useQuery<ConnectStatus>({
    queryKey: ['connect-status'],
    queryFn: async () => {
      const res = await fetch('/api/v1/expert-network/connect/status', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to fetch Connect status')
      return res.json()
    },
    enabled: isAuthenticated
  })

  const { data: earnings, isLoading: loadingEarnings } = useQuery<Earnings>({
    queryKey: ['expert-earnings'],
    queryFn: async () => {
      const res = await fetch('/api/v1/expert-network/connect/earnings', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to fetch earnings')
      return res.json()
    },
    enabled: isAuthenticated
  })

  const { data: engagements, isLoading: loadingEngagements } = useQuery<Engagement[]>({
    queryKey: ['expert-engagements'],
    queryFn: async () => {
      const res = await fetch('/api/v1/expert-network/engagements?role=expert', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to fetch engagements')
      return res.json()
    },
    enabled: isAuthenticated
  })

  const startOnboardingMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/expert-network/connect/onboarding', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to start onboarding')
      return res.json()
    },
    onSuccess: (data) => {
      if (data.url) {
        window.location.href = data.url
      }
    }
  })

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-stone-600 mb-4">Please sign in to access your expert dashboard</p>
          <Link to="/login" className="text-blue-600 hover:underline">Sign In</Link>
        </div>
      </div>
    )
  }

  const pendingRequests = engagements?.filter(e => e.status === 'request_sent') || []
  const activeEngagements = engagements?.filter(e => ['accepted', 'in_progress', 'proposal_sent'].includes(e.status)) || []
  const completedEngagements = engagements?.filter(e => e.status === 'completed') || []

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-stone-900">Expert Dashboard</h1>
          <p className="text-stone-600 mt-2">Manage your clients, engagements, and earnings</p>
        </div>

        {!connectStatus?.payouts_enabled && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-medium text-amber-800">Complete Payment Setup</h3>
                <p className="text-amber-700 text-sm mt-1">
                  {!connectStatus?.connected 
                    ? "Set up your payment account to receive payouts from your engagements."
                    : "Complete your payment account verification to enable payouts."}
                </p>
                <button
                  onClick={() => startOnboardingMutation.mutate()}
                  disabled={startOnboardingMutation.isPending}
                  className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition disabled:opacity-50"
                >
                  {startOnboardingMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CreditCard className="w-4 h-4" />
                  )}
                  {connectStatus?.connected ? 'Complete Setup' : 'Set Up Payments'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-green-100 rounded-lg">
                <DollarSign className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-stone-900">
              {loadingEarnings ? '...' : formatCents(earnings?.total_earned_cents || 0)}
            </p>
            <p className="text-sm text-stone-600">Total Earned</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Clock className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-stone-900">
              {loadingEarnings ? '...' : formatCents(earnings?.pending_earnings_cents || 0)}
            </p>
            <p className="text-sm text-stone-600">Pending Earnings</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-stone-900">
              {loadingEarnings ? '...' : earnings?.active_engagements || 0}
            </p>
            <p className="text-sm text-stone-600">Active Clients</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-stone-900">
              {loadingEarnings ? '...' : earnings?.completed_engagements || 0}
            </p>
            <p className="text-sm text-stone-600">Completed</p>
          </div>
        </div>

        <div className="flex gap-2 mb-6 border-b">
          {(['overview', 'clients', 'earnings'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 font-medium text-sm capitalize border-b-2 transition ${
                activeTab === tab 
                  ? 'border-blue-600 text-blue-600' 
                  : 'border-transparent text-stone-600 hover:text-stone-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-stone-900">New Requests</h2>
                <span className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-1 rounded-full">
                  {pendingRequests.length}
                </span>
              </div>
              {loadingEngagements ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
                </div>
              ) : pendingRequests.length === 0 ? (
                <p className="text-stone-500 text-center py-8">No new requests</p>
              ) : (
                <div className="space-y-3">
                  {pendingRequests.slice(0, 5).map(eng => (
                    <Link 
                      key={eng.id} 
                      to={`/build/engagements?id=${eng.id}`}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-stone-50 transition"
                    >
                      <div>
                        <p className="font-medium text-stone-900">{eng.title || 'Untitled Request'}</p>
                        <p className="text-sm text-stone-600">{eng.client_name || 'Client'}</p>
                      </div>
                      <ChevronRight className="w-5 h-5 text-stone-400" />
                    </Link>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-stone-900">Active Engagements</h2>
                <span className="bg-green-100 text-green-700 text-xs font-medium px-2 py-1 rounded-full">
                  {activeEngagements.length}
                </span>
              </div>
              {loadingEngagements ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
                </div>
              ) : activeEngagements.length === 0 ? (
                <p className="text-stone-500 text-center py-8">No active engagements</p>
              ) : (
                <div className="space-y-3">
                  {activeEngagements.slice(0, 5).map(eng => (
                    <Link 
                      key={eng.id} 
                      to={`/build/engagements?id=${eng.id}`}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-stone-50 transition"
                    >
                      <div>
                        <p className="font-medium text-stone-900">{eng.title || 'Engagement'}</p>
                        <div className="flex items-center gap-2 mt-1">
                          {getStatusBadge(eng.status)}
                          <span className="text-xs text-stone-500">{eng.client_name}</span>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-stone-400" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'clients' && (
          <div className="bg-white rounded-xl shadow-sm border">
            <div className="p-6 border-b">
              <h2 className="font-semibold text-stone-900">All Clients & Engagements</h2>
            </div>
            {loadingEngagements ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
              </div>
            ) : !engagements || engagements.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-12 h-12 text-stone-300 mx-auto mb-4" />
                <p className="text-stone-600">No clients yet</p>
                <p className="text-stone-500 text-sm mt-1">Your client engagements will appear here</p>
              </div>
            ) : (
              <div className="divide-y">
                {engagements.map(eng => (
                  <div key={eng.id} className="p-4 hover:bg-stone-50 transition">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <p className="font-medium text-stone-900">{eng.title || 'Engagement'}</p>
                          {getStatusBadge(eng.status)}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-stone-600">
                          <span className="flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            {eng.client_name || 'Client'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-4 h-4" />
                            {eng.engagement_type.replace('_', ' ')}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {formatDate(eng.created_at)}
                          </span>
                          {eng.expert_payout_cents && (
                            <span className="flex items-center gap-1 text-green-600 font-medium">
                              <DollarSign className="w-4 h-4" />
                              {formatCents(eng.expert_payout_cents)}
                            </span>
                          )}
                        </div>
                      </div>
                      <Link 
                        to={`/build/engagements?id=${eng.id}`}
                        className="px-3 py-1.5 text-sm bg-stone-100 hover:bg-stone-200 rounded-lg transition"
                      >
                        View
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'earnings' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="font-semibold text-stone-900 mb-4">Earnings Summary</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-stone-600 mb-1">Total Earned (after fees)</p>
                  <p className="text-3xl font-bold text-green-600">
                    {formatCents(earnings?.total_earned_cents || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-stone-600 mb-1">Pending Payouts</p>
                  <p className="text-3xl font-bold text-blue-600">
                    {formatCents(earnings?.pending_earnings_cents || 0)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-stone-600 mb-1">Platform Fees Paid</p>
                  <p className="text-3xl font-bold text-stone-400">
                    {formatCents(earnings?.total_platform_fees_cents || 0)}
                  </p>
                  <p className="text-xs text-stone-500 mt-1">15% platform fee</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="font-semibold text-stone-900 mb-4">Payment Account Status</h2>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-full ${connectStatus?.payouts_enabled ? 'bg-green-100' : 'bg-amber-100'}`}>
                  {connectStatus?.payouts_enabled ? (
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  ) : (
                    <AlertCircle className="w-6 h-6 text-amber-600" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-stone-900">
                    {connectStatus?.payouts_enabled ? 'Payouts Enabled' : 'Setup Required'}
                  </p>
                  <p className="text-sm text-stone-600">
                    {connectStatus?.payouts_enabled 
                      ? 'Your payment account is active and ready to receive funds'
                      : 'Complete account verification to receive payouts'}
                  </p>
                </div>
                {!connectStatus?.payouts_enabled && (
                  <button
                    onClick={() => startOnboardingMutation.mutate()}
                    disabled={startOnboardingMutation.isPending}
                    className="ml-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    {startOnboardingMutation.isPending ? 'Loading...' : 'Complete Setup'}
                  </button>
                )}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border">
              <div className="p-6 border-b">
                <h2 className="font-semibold text-stone-900">Completed Engagements</h2>
              </div>
              {completedEngagements.length === 0 ? (
                <div className="text-center py-12">
                  <TrendingUp className="w-12 h-12 text-stone-300 mx-auto mb-4" />
                  <p className="text-stone-600">No completed engagements yet</p>
                </div>
              ) : (
                <div className="divide-y">
                  {completedEngagements.map(eng => (
                    <div key={eng.id} className="p-4 flex items-center justify-between">
                      <div>
                        <p className="font-medium text-stone-900">{eng.title || 'Engagement'}</p>
                        <div className="flex items-center gap-3 text-sm text-stone-600 mt-1">
                          <span>{eng.client_name}</span>
                          <span>{formatDate(eng.completed_at)}</span>
                          {!eng.is_reviewed && (
                            <span className="text-amber-600 text-xs">Pending review</span>
                          )}
                        </div>
                      </div>
                      <p className="text-lg font-semibold text-green-600">
                        {formatCents(eng.expert_payout_cents)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
