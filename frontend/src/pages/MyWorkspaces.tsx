import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { 
  Briefcase, ChevronRight, Clock, Loader2, Plus, Rocket, Target, TrendingUp
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { launchFlags } from '../config/launchFlags'

type WorkspaceStatus = 'researching' | 'validating' | 'planning' | 'building' | 'launched' | 'paused' | 'archived'

type Opportunity = {
  id: number
  title: string
  category: string
  feasibility_score: number | null
}

type Workspace = {
  id: number
  opportunity_id: number
  status: WorkspaceStatus
  progress_percent: number
  custom_title: string | null
  created_at: string
  last_activity_at: string | null
  opportunity: Opportunity | null
  tasks: { id: number; is_completed: boolean }[]
}

type WorkspaceList = {
  workspaces: Workspace[]
  total: number
}

const statusLabels: Record<WorkspaceStatus, { label: string; color: string }> = {
  researching: { label: 'Researching', color: 'bg-blue-100 text-blue-700' },
  validating: { label: 'Validating', color: 'bg-amber-100 text-amber-700' },
  planning: { label: 'Planning', color: 'bg-purple-100 text-purple-700' },
  building: { label: 'Building', color: 'bg-emerald-100 text-emerald-700' },
  launched: { label: 'Launched', color: 'bg-green-100 text-green-700' },
  paused: { label: 'Paused', color: 'bg-stone-100 text-stone-700' },
  archived: { label: 'Archived', color: 'bg-stone-100 text-stone-500' },
}

export default function MyWorkspaces() {
  const { token, isAuthenticated, user } = useAuthStore()

  const workspacesQuery = useQuery({
    queryKey: ['workspaces', { authed: Boolean(token) }],
    enabled: isAuthenticated && Boolean(token),
    queryFn: async (): Promise<WorkspaceList> => {
      const res = await fetch('/api/v1/workspaces/', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to load workspaces')
      return await res.json()
    },
  })

  const workspaces = workspacesQuery.data?.workspaces || []

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <Briefcase className="w-16 h-16 text-stone-300 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-stone-900 mb-2">Sign in to view your workspaces</h2>
          <p className="text-stone-600 mb-4">Track and manage opportunities you're working on.</p>
          <Link to="/login" className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white rounded-lg font-medium hover:bg-violet-700">
            Sign In
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">My Workspaces</h1>
            <p className="text-stone-600">Track and manage opportunities you're working on</p>
          </div>
          <Link 
            to="/discover"
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700"
          >
            <Plus className="w-4 h-4" />
            Find New Opportunity
          </Link>
        </div>

        {workspacesQuery.isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-violet-600" />
          </div>
        ) : workspaces.length === 0 ? (
          <div className="bg-white rounded-xl border border-stone-200 p-12 text-center">
            <Rocket className="w-16 h-16 text-stone-300 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-stone-900 mb-2">No workspaces yet</h2>
            <p className="text-stone-600 mb-6 max-w-md mx-auto">
              When you find an opportunity you want to pursue, click "Start Working on This" 
              to create a dedicated workspace for it.
            </p>
            <Link 
              to="/discover"
              className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 text-white rounded-lg font-medium hover:bg-violet-700"
            >
              <Target className="w-5 h-5" />
              Discover Opportunities
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workspaces.map((ws) => {
              const statusInfo = statusLabels[ws.status]
              const completedTasks = ws.tasks?.filter(t => t.is_completed).length || 0
              const totalTasks = ws.tasks?.length || 0
              
              return (
                <Link
                  key={ws.id}
                  to={(launchFlags.workhub || user?.is_admin) ? `/opportunity/${ws.opportunity_id}/hub` : `/opportunity/${ws.opportunity_id}`}
                  className="bg-white rounded-xl border border-stone-200 p-5 hover:border-violet-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between mb-3">
                    <span className={`text-xs font-medium px-2 py-1 rounded ${statusInfo.color}`}>
                      {statusInfo.label}
                    </span>
                    {ws.opportunity?.feasibility_score && (
                      <div className="flex items-center gap-1 text-emerald-600">
                        <TrendingUp className="w-4 h-4" />
                        <span className="text-sm font-medium">{Math.round(ws.opportunity.feasibility_score)}%</span>
                      </div>
                    )}
                  </div>
                  
                  <h3 className="font-semibold text-stone-900 mb-1 line-clamp-2">
                    {ws.custom_title || ws.opportunity?.title || 'Untitled Workspace'}
                  </h3>
                  <p className="text-sm text-stone-500 mb-4">{ws.opportunity?.category}</p>

                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-stone-600">Progress</span>
                      <span className="font-medium text-stone-900">{ws.progress_percent}%</span>
                    </div>
                    <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-violet-500 to-purple-500"
                        style={{ width: `${ws.progress_percent}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-stone-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {ws.last_activity_at 
                        ? `Updated ${new Date(ws.last_activity_at).toLocaleDateString()}`
                        : `Created ${new Date(ws.created_at).toLocaleDateString()}`
                      }
                    </span>
                    <span>{completedTasks}/{totalTasks} tasks</span>
                  </div>

                  <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-end">
                    <ChevronRight className="w-4 h-4 text-violet-600 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
