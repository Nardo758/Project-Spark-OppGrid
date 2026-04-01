import { useLifecycleSummary, LIFECYCLE_STATES } from '../hooks/useOpportunityLifecycle'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import { TrendingUp, Calendar, CheckCircle2 } from 'lucide-react'

interface OpportunityWithLifecycle {
  id: number
  title: string
  category?: string
  current_state: string
  progress_percent: number
  updated_at: string
}

export default function LifecycleDashboard() {
  const { token } = useAuthStore()
  const { summary, isLoading: summaryLoading } = useLifecycleSummary()

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  // Fetch all opportunities with their lifecycle states
  const { data: opportunities, isLoading: oppLoading } = useQuery({
    queryKey: ['all-opportunities-with-lifecycle'],
    queryFn: async () => {
      const res = await fetch('/api/v1/opportunities?limit=1000', {
        headers: headers(),
      })
      if (!res.ok) return []
      const data = await res.json()
      return Array.isArray(data) ? data : data.data || []
    },
    enabled: !!token,
  })

  const isLoading = summaryLoading || oppLoading

  if (!token) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center p-4">
        <div className="text-center">
          <TrendingUp className="w-12 h-12 text-stone-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-stone-900 mb-2">Sign in to view your journey</h1>
          <p className="text-stone-600">Track opportunities through 8 states from discovery to launch</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-stone-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-8 h-8 text-amber-600" />
            <h1 className="text-3xl font-bold text-stone-900">Opportunity Journey</h1>
          </div>
          <p className="text-stone-600">Track progress across 8 states: Discovered → Archived</p>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-stone-200 h-20 animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            {/* Summary Stats */}
            {summary && (
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
                <div className="bg-white rounded-lg border border-stone-200 p-4">
                  <p className="text-sm text-stone-600 mb-1">Total Opportunities</p>
                  <p className="text-3xl font-bold text-stone-900">{summary.total_opportunities}</p>
                </div>
                <div className="bg-white rounded-lg border border-stone-200 p-4">
                  <p className="text-sm text-stone-600 mb-1">Average Progress</p>
                  <p className="text-3xl font-bold text-amber-600">{Math.round(summary.avg_progress)}%</p>
                </div>
                <div className="bg-white rounded-lg border border-stone-200 p-4">
                  <p className="text-sm text-stone-600 mb-1">Currently Executing</p>
                  <p className="text-3xl font-bold text-blue-600">{summary.by_state.executing || 0}</p>
                </div>
                <div className="bg-white rounded-lg border border-stone-200 p-4">
                  <p className="text-sm text-stone-600 mb-1">Launched</p>
                  <p className="text-3xl font-bold text-green-600">{summary.by_state.launched || 0}</p>
                </div>
              </div>
            )}

            {/* State Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {LIFECYCLE_STATES.map((state) => {
                const count = summary?.by_state[state.id] || 0
                const stateOpportunities = (opportunities || []).filter(
                  (opp: any) => opp.current_state === state.id
                )

                return (
                  <div key={state.id} className="bg-white rounded-lg border border-stone-200 p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-2xl">{state.icon}</span>
                      <div>
                        <h3 className="font-semibold text-stone-900 text-sm">{state.label}</h3>
                        <p className="text-xs text-stone-600">{count} opportunity{count !== 1 ? 'ies' : ''}</p>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    {stateOpportunities.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs text-stone-600">
                          Avg: {Math.round(stateOpportunities.reduce((sum: number, opp: any) => sum + (opp.progress_percent || 0), 0) / stateOpportunities.length)}%
                        </div>
                        <div className="w-full bg-stone-200 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all`}
                            style={{
                              width: `${Math.round(stateOpportunities.reduce((sum: number, opp: any) => sum + (opp.progress_percent || 0), 0) / stateOpportunities.length)}%`,
                              backgroundColor: state.color,
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Mini List */}
                    {stateOpportunities.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-stone-200 space-y-1">
                        {stateOpportunities.slice(0, 3).map((opp: any) => (
                          <a
                            key={opp.id}
                            href={`/opportunity/${opp.id}`}
                            className="block text-xs text-blue-600 hover:underline truncate"
                          >
                            {opp.title}
                          </a>
                        ))}
                        {stateOpportunities.length > 3 && (
                          <p className="text-xs text-stone-600 italic">
                            +{stateOpportunities.length - 3} more
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Recent Activity */}
            {summary && summary.recent_transitions.length > 0 && (
              <div className="bg-white rounded-lg border border-stone-200 p-6">
                <h2 className="text-lg font-semibold text-stone-900 mb-4">Recent Activity</h2>
                <div className="space-y-3">
                  {summary.recent_transitions.slice(0, 5).map((transition) => {
                    const fromState = LIFECYCLE_STATES.find((s) => s.id === transition.from_state)
                    const toState = LIFECYCLE_STATES.find((s) => s.id === transition.to_state)

                    return (
                      <div key={transition.id} className="flex items-center gap-3 pb-3 border-b border-stone-200 last:border-b-0">
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-lg">{fromState?.icon}</span>
                          <span className="text-stone-600">→</span>
                          <span className="text-lg">{toState?.icon}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-stone-900">
                            <span className="font-medium">{fromState?.label}</span>
                            {' → '}
                            <span className="font-medium">{toState?.label}</span>
                          </p>
                          {transition.reason && <p className="text-xs text-stone-600">{transition.reason}</p>}
                        </div>
                        <p className="text-xs text-stone-600">
                          {new Date(transition.transitioned_at).toLocaleDateString()}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
