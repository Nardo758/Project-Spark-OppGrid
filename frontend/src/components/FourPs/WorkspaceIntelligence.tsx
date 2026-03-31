/**
 * WorkspaceIntelligence - 4 P's powered workspace panel
 * 
 * Shows smart task suggestions and market intelligence
 * to guide workspace workflow based on 4 P's analysis.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Lightbulb, Plus, CheckCircle2, AlertTriangle,
  Package, DollarSign, MapPin, Megaphone,
  ChevronDown, ChevronUp, Loader2, Sparkles
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface WorkspaceIntelligenceProps {
  workspaceId: number
  className?: string
}

interface FocusArea {
  pillar: string
  score: number
  status: 'critical' | 'needs_work' | 'improving'
}

interface SuggestedTask {
  pillar: string
  pillar_score: number
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
}

interface SmartTasksResponse {
  workspace_id: number
  opportunity_id: number
  four_ps_scores: Record<string, number> | null
  overall_score: number
  data_quality: number
  focus_areas: FocusArea[]
  suggested_tasks: SuggestedTask[]
  recommendations: string[]
  message: string
}

const PILLAR_ICONS = {
  PRODUCT: Package,
  PRICE: DollarSign,
  PLACE: MapPin,
  PROMOTION: Megaphone,
}

const PILLAR_COLORS = {
  PRODUCT: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', bar: 'bg-blue-500' },
  PRICE: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', bar: 'bg-emerald-500' },
  PLACE: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', bar: 'bg-amber-500' },
  PROMOTION: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', bar: 'bg-purple-500' },
}

const PRIORITY_STYLES = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-stone-100 text-stone-600 border-stone-200',
}

export default function WorkspaceIntelligence({ workspaceId, className = '' }: WorkspaceIntelligenceProps) {
  const { token } = useAuthStore()
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(true)
  const [addingTask, setAddingTask] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['workspace-smart-tasks', workspaceId],
    queryFn: async (): Promise<SmartTasksResponse> => {
      const res = await fetch(`/api/v1/enhanced-workspaces/${workspaceId}/smart-tasks`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to fetch smart tasks')
      return res.json()
    },
    enabled: !!token && !!workspaceId,
    staleTime: 5 * 60 * 1000,
  })

  const addTaskMutation = useMutation({
    mutationFn: async (task: SuggestedTask) => {
      const res = await fetch(`/api/v1/enhanced-workspaces/${workspaceId}/smart-tasks/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          task_title: task.title,
          task_description: task.description,
          task_priority: task.priority,
          pillar: task.pillar
        })
      })
      if (!res.ok) throw new Error('Failed to add task')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] })
      setAddingTask(null)
    }
  })

  if (isLoading) {
    return (
      <div className={`bg-white rounded-xl border border-stone-200 p-4 ${className}`}>
        <div className="flex items-center gap-2 text-stone-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Analyzing market intelligence...</span>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className={`bg-stone-50 rounded-xl border border-stone-200 p-4 ${className}`}>
        <div className="flex items-center gap-2 text-stone-500">
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm">Unable to load market intelligence</span>
        </div>
      </div>
    )
  }

  const hasData = data.four_ps_scores !== null

  return (
    <div className={`bg-white rounded-xl border border-stone-200 overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-stone-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-stone-900">Smart Task Suggestions</h3>
            <p className="text-xs text-stone-500">Powered by 4 P's Market Intelligence</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {hasData && (
            <div className="text-right">
              <div className="text-lg font-bold text-stone-900">{data.overall_score}</div>
              <div className="text-xs text-stone-500">Overall Score</div>
            </div>
          )}
          {isExpanded ? <ChevronUp className="text-stone-400" /> : <ChevronDown className="text-stone-400" />}
        </div>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Score bars */}
          {hasData && data.four_ps_scores && (
            <div className="grid grid-cols-4 gap-2">
              {Object.entries(data.four_ps_scores).map(([pillar, score]) => {
                const colors = PILLAR_COLORS[pillar.toUpperCase() as keyof typeof PILLAR_COLORS] || PILLAR_COLORS.PRODUCT
                const Icon = PILLAR_ICONS[pillar.toUpperCase() as keyof typeof PILLAR_ICONS] || Package
                
                return (
                  <div key={pillar} className="text-center">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Icon className={`w-3 h-3 ${colors.text}`} />
                      <span className="text-xs font-medium text-stone-500 uppercase">{pillar}</span>
                    </div>
                    <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${colors.bar} rounded-full transition-all`}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                    <div className="text-xs font-semibold text-stone-700 mt-0.5">{score}</div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Focus areas */}
          {data.focus_areas.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Focus Areas</h4>
              <div className="flex flex-wrap gap-2">
                {data.focus_areas.map((area) => {
                  const colors = PILLAR_COLORS[area.pillar as keyof typeof PILLAR_COLORS] || PILLAR_COLORS.PRODUCT
                  
                  return (
                    <div
                      key={area.pillar}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text} border ${colors.border}`}
                    >
                      {area.pillar} ({area.score})
                      {area.status === 'critical' && <span className="ml-1">⚠️</span>}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Suggested tasks */}
          {data.suggested_tasks.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
                Suggested Tasks ({data.suggested_tasks.length})
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {data.suggested_tasks.map((task, idx) => {
                  const colors = PILLAR_COLORS[task.pillar as keyof typeof PILLAR_COLORS] || PILLAR_COLORS.PRODUCT
                  const isAdding = addingTask === `${task.pillar}-${idx}`
                  
                  return (
                    <div
                      key={`${task.pillar}-${idx}`}
                      className={`p-3 rounded-lg border ${colors.border} ${colors.bg}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs font-medium ${colors.text}`}>{task.pillar}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded border ${PRIORITY_STYLES[task.priority]}`}>
                              {task.priority}
                            </span>
                          </div>
                          <h5 className="font-medium text-stone-900 text-sm">{task.title}</h5>
                          <p className="text-xs text-stone-600 mt-0.5">{task.description}</p>
                        </div>
                        <button
                          onClick={() => {
                            setAddingTask(`${task.pillar}-${idx}`)
                            addTaskMutation.mutate(task)
                          }}
                          disabled={isAdding || addTaskMutation.isPending}
                          className="p-1.5 rounded-lg hover:bg-white/60 text-stone-600 hover:text-violet-600 transition-colors disabled:opacity-50"
                          title="Add to workspace"
                        >
                          {isAdding ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Plus className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* No data state */}
          {!hasData && (
            <div className="text-center py-6">
              <Lightbulb className="w-8 h-8 text-stone-300 mx-auto mb-2" />
              <p className="text-sm text-stone-500">
                Generate a 4 P's analysis to get personalized task suggestions
              </p>
            </div>
          )}

          {/* Recommendations */}
          {data.recommendations.length > 0 && (
            <div className="bg-violet-50 rounded-lg p-3 border border-violet-200">
              <h4 className="text-xs font-semibold text-violet-700 mb-1">💡 Recommendations</h4>
              <ul className="space-y-1">
                {data.recommendations.slice(0, 2).map((rec, idx) => (
                  <li key={idx} className="text-xs text-violet-600">• {rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
