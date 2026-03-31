/**
 * WorkspaceIntelligence - Smart task suggestions for workspaces
 * 
 * Shows AI-powered task recommendations to guide workflow.
 * Data-driven suggestions without exposing the underlying framework.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Lightbulb, Plus, CheckCircle2, AlertTriangle,
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

// Priority-based styling (no pillar labels exposed)
const PRIORITY_BG = {
  high: 'bg-red-50 border-red-200',
  medium: 'bg-amber-50 border-amber-200',
  low: 'bg-stone-50 border-stone-200',
}

const PRIORITY_BADGE = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-stone-100 text-stone-600',
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

  const taskCount = data?.suggested_tasks?.length || 0

  return (
    <div className={`bg-white rounded-xl border border-stone-200 overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-stone-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          <span className="font-medium text-stone-900 text-sm">Suggested Tasks</span>
          {taskCount > 0 && (
            <span className="bg-violet-100 text-violet-700 text-xs px-1.5 py-0.5 rounded-full font-medium">
              {taskCount}
            </span>
          )}
        </div>
        {isExpanded ? <ChevronUp className="w-4 h-4 text-stone-400" /> : <ChevronDown className="w-4 h-4 text-stone-400" />}
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {/* Suggested tasks - simple list */}
          {taskCount > 0 ? (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {data!.suggested_tasks.slice(0, 6).map((task, idx) => {
                const isAdding = addingTask === `${task.pillar}-${idx}`
                
                return (
                  <div
                    key={`${task.pillar}-${idx}`}
                    className={`p-2.5 rounded-lg border ${PRIORITY_BG[task.priority] || PRIORITY_BG.medium}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <h5 className="font-medium text-stone-900 text-sm truncate">{task.title}</h5>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${PRIORITY_BADGE[task.priority]}`}>
                            {task.priority}
                          </span>
                        </div>
                        <p className="text-xs text-stone-500 line-clamp-1">{task.description}</p>
                      </div>
                      <button
                        onClick={() => {
                          setAddingTask(`${task.pillar}-${idx}`)
                          addTaskMutation.mutate(task)
                        }}
                        disabled={isAdding || addTaskMutation.isPending}
                        className="p-1 rounded hover:bg-white/60 text-stone-400 hover:text-violet-600 transition-colors disabled:opacity-50 flex-shrink-0"
                        title="Add to tasks"
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
          ) : (
            <div className="text-center py-4">
              <p className="text-xs text-stone-400">
                {hasData ? 'Looking good! No urgent tasks.' : 'Complete research to unlock suggestions'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
