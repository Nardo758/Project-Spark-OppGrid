import { useOpportunityLifecycle, useTransitionLifecycleState, useLifecycleMilestones, useCompleteMilestone, LIFECYCLE_STATES } from '../hooks/useOpportunityLifecycle'
import { ChevronRight, CheckCircle2, Circle } from 'lucide-react'
import { useState } from 'react'

interface LifecycleJourneyProps {
  opportunityId: number
}

export default function LifecycleJourney({ opportunityId }: LifecycleJourneyProps) {
  const { lifecycle, isLoading } = useOpportunityLifecycle(opportunityId)
  const { mutate: transitionState, isPending: isTransitioning } = useTransitionLifecycleState()
  const { milestones } = useLifecycleMilestones(opportunityId, lifecycle?.current_state)
  const { mutate: completeMilestone } = useCompleteMilestone()
  const [expandedState, setExpandedState] = useState<string | null>(null)

  if (isLoading) {
    return <div className="bg-stone-50 rounded-lg p-6 animate-pulse h-96" />
  }

  if (!lifecycle) {
    return null
  }

  const currentStateIndex = LIFECYCLE_STATES.findIndex((s) => s.id === lifecycle.current_state)
  const currentStateInfo = LIFECYCLE_STATES[currentStateIndex]

  return (
    <div className="bg-white rounded-lg border border-stone-200 p-6 space-y-6">
      {/* Title */}
      <div>
        <h3 className="text-lg font-semibold text-stone-900 mb-2">Opportunity Journey</h3>
        <p className="text-sm text-stone-600">Track your progress from discovery to launch</p>
      </div>

      {/* Current State Card */}
      <div className="bg-gradient-to-r from-stone-50 to-stone-100 rounded-lg p-4 border border-stone-200">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">{currentStateInfo.icon}</span>
          <div>
            <p className="text-xs text-stone-600 uppercase tracking-wide">Current State</p>
            <p className="text-xl font-bold text-stone-900">{currentStateInfo.label}</p>
          </div>
        </div>
        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-stone-600">Progress</span>
            <span className="font-medium">{lifecycle.progress_percent}%</span>
          </div>
          <div className="w-full bg-stone-300 rounded-full h-2">
            <div
              className="bg-amber-500 rounded-full h-2 transition-all"
              style={{ width: `${lifecycle.progress_percent}%` }}
            />
          </div>
        </div>
      </div>

      {/* State Journey Timeline */}
      <div className="space-y-2">
        <h4 className="font-semibold text-stone-900 text-sm mb-4">Full Journey</h4>
        <div className="space-y-3">
          {LIFECYCLE_STATES.map((state, index) => {
            const isCompleted = currentStateIndex > index
            const isCurrent = state.id === lifecycle.current_state
            const stateTime = lifecycle[`${state.id}_at` as keyof typeof lifecycle]

            return (
              <div key={state.id}>
                {/* State Button */}
                <button
                  onClick={() => setExpandedState(expandedState === state.id ? null : state.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-left ${
                    isCurrent
                      ? 'bg-blue-50 border-2 border-blue-200'
                      : isCompleted
                        ? 'bg-green-50 border border-green-200'
                        : 'bg-stone-50 border border-stone-200 opacity-60'
                  }`}
                >
                  <div className="flex-shrink-0">
                    {isCompleted || isCurrent ? (
                      <CheckCircle2
                        className={`w-5 h-5 ${isCurrent ? 'text-blue-600' : 'text-green-600'}`}
                      />
                    ) : (
                      <Circle className="w-5 h-5 text-stone-400" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{state.icon}</span>
                      <span className="font-medium text-stone-900">{state.label}</span>
                    </div>
                    {stateTime && (
                      <p className="text-xs text-stone-600 mt-1">
                        {new Date(stateTime as string).toLocaleDateString()}
                      </p>
                    )}
                  </div>

                  {expandedState === state.id && <ChevronRight className="w-5 h-5 text-stone-400 rotate-90" />}
                </button>

                {/* Expanded Milestones */}
                {expandedState === state.id && (
                  <div className="mt-2 ml-8 space-y-2 pb-2">
                    {milestones.length === 0 ? (
                      <p className="text-xs text-stone-600 italic">No milestones for this state</p>
                    ) : (
                      milestones.map((milestone) => (
                        <div
                          key={milestone.id}
                          className="flex items-start gap-2 p-2 bg-stone-50 rounded"
                        >
                          <input
                            type="checkbox"
                            checked={milestone.is_completed}
                            onChange={(e) =>
                              completeMilestone({
                                opportunityId,
                                milestoneId: milestone.id,
                                isCompleted: e.target.checked,
                              })
                            }
                            className="mt-1 w-4 h-4 rounded"
                          />
                          <div className="flex-1 min-w-0">
                            <p
                              className={`text-sm font-medium ${
                                milestone.is_completed
                                  ? 'text-stone-500 line-through'
                                  : 'text-stone-900'
                              }`}
                            >
                              {milestone.title}
                            </p>
                            {milestone.description && (
                              <p className="text-xs text-stone-600 mt-1">{milestone.description}</p>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* State Transition Actions */}
      {!isTransitioning && (
        <div className="border-t border-stone-200 pt-4">
          <p className="text-xs text-stone-600 mb-3 font-medium">Next Steps</p>
          <div className="grid grid-cols-2 gap-2">
            {LIFECYCLE_STATES.map((state) => {
              const canTransition =
                lifecycle.current_state !== state.id && 
                [
                  'discovered',
                  'saved',
                  'archived',
                ].includes(state.id)

              return (
                canTransition && (
                  <button
                    key={state.id}
                    onClick={() =>
                      transitionState({
                        opportunityId,
                        toState: state.id,
                      })
                    }
                    className="px-3 py-2 text-xs font-medium rounded-lg border border-stone-200 hover:bg-stone-50 transition-colors text-stone-700"
                  >
                    {state.icon} {state.label}
                  </button>
                )
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
