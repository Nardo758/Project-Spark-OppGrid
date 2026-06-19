import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { 
  Search, Star, Clock, DollarSign, CheckCircle, Loader2, 
  User, Briefcase, X, MapPin, Award, Users,
  MessageSquare, ChevronDown, Filter, Building2, ExternalLink
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

type ExpertProfile = {
  id: number
  user_id: number | null
  title: string | null
  location: string | null
  timezone: string | null
  primary_category: string | null
  category: string | null
  specializations: string[]
  industries: string[]
  stage_expertise: string[]
  years_experience: number | null
  portfolio_highlights: string | null
  education: string | null
  certifications: string | null
  availability_description: string | null
  availability_hours_per_week: number | null
  engagement_types: string[]
  hourly_rate_cents: number | null
  project_rate_min_cents: number | null
  project_rate_max_cents: number | null
  retainer_rate_cents: number | null
  response_time: string | null
  is_verified: boolean
  is_accepting_clients: boolean
  projects_completed: number
  avg_rating: number | null
  total_reviews: number
  user_name: string | null
  user_avatar: string | null
  created_at: string
  external_id: string | null
  external_source: string | null
  external_url: string | null
  external_name: string | null
  skills: string[]
}

type ExpertCategory = {
  value: string
  label: string
}

type EngagementFormData = {
  engagement_type: string
  title: string
  description: string
  request_message: string
  for_consultation_duration_minutes?: number
  for_project_duration_weeks?: number
  for_retainer_months?: number
}

function formatCents(cents: number): string {
  return `$${(cents / 100).toLocaleString()}`
}

function formatCentsRange(min: number | null, max: number | null): string {
  if (min && max) {
    return `${formatCents(min)} - ${formatCents(max)}`
  }
  if (min) return `From ${formatCents(min)}`
  if (max) return `Up to ${formatCents(max)}`
  return ''
}

function getCategoryIcon(category: string | null) {
  switch (category) {
    case 'business_consultant': return <Briefcase className="w-4 h-4" />
    case 'technical_advisor': return <Building2 className="w-4 h-4" />
    case 'industry_specialist': return <Award className="w-4 h-4" />
    case 'growth_marketing': return <Users className="w-4 h-4" />
    case 'financial_advisor': return <DollarSign className="w-4 h-4" />
    case 'legal_compliance': return <CheckCircle className="w-4 h-4" />
    default: return <User className="w-4 h-4" />
  }
}

export default function ExpertMarketplace() {
  const { token, isAuthenticated } = useAuthStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedExpert, setSelectedExpert] = useState<ExpertProfile | null>(null)
  const [showEngagementModal, setShowEngagementModal] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [engagementForm, setEngagementForm] = useState<EngagementFormData>({
    engagement_type: 'consultation',
    title: '',
    description: '',
    request_message: '',
    for_consultation_duration_minutes: 60,
    for_project_duration_weeks: 4,
    for_retainer_months: 3
  })
  const [engagementSuccess, setEngagementSuccess] = useState(false)

  const { data: categories } = useQuery({
    queryKey: ['expert-categories'],
    queryFn: async (): Promise<ExpertCategory[]> => {
      const res = await fetch('/api/v1/expert-network/categories')
      if (!res.ok) throw new Error('Failed to load categories')
      return res.json()
    }
  })

  const { data: experts, isLoading, error } = useQuery({
    queryKey: ['expert-profiles', selectedCategory, searchQuery],
    queryFn: async (): Promise<ExpertProfile[]> => {
      const params = new URLSearchParams()
      if (selectedCategory) params.append('category', selectedCategory)
      if (searchQuery) params.append('search', searchQuery)
      const url = `/api/v1/expert-network/experts${params.toString() ? '?' + params : ''}`
      const res = await fetch(url)
      if (!res.ok) throw new Error('Failed to load experts')
      return res.json()
    }
  })

  const engagementMutation = useMutation({
    mutationFn: async (expertId: number) => {
      if (!token) {
        throw new Error('Please log in to request an engagement')
      }
      const res = await fetch('/api/v1/expert-network/engagements', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          expert_profile_id: expertId,
          engagement_type: engagementForm.engagement_type,
          title: engagementForm.title || `Engagement with expert`,
          description: engagementForm.description,
          request_message: engagementForm.request_message,
          for_consultation_duration_minutes: engagementForm.engagement_type === 'consultation' ? engagementForm.for_consultation_duration_minutes : undefined,
          for_project_duration_weeks: engagementForm.engagement_type === 'project' ? engagementForm.for_project_duration_weeks : undefined,
          for_retainer_months: engagementForm.engagement_type === 'retainer' ? engagementForm.for_retainer_months : undefined
        })
      })
      if (res.status === 401 || res.status === 403) {
        throw new Error('Please log in to request an engagement')
      }
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to request engagement')
      }
      return res.json()
    },
    onSuccess: () => {
      setEngagementSuccess(true)
      setTimeout(() => {
        setShowEngagementModal(false)
        setEngagementSuccess(false)
        setEngagementForm({ 
          engagement_type: 'consultation', 
          title: '', 
          description: '', 
          request_message: '',
          for_consultation_duration_minutes: 60,
          for_project_duration_weeks: 4,
          for_retainer_months: 3
        })
      }, 3000)
    }
  })

  const openEngagement = (expert: ExpertProfile) => {
    setSelectedExpert(expert)
    setShowEngagementModal(true)
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="bg-gradient-to-br from-violet-900 via-purple-900 to-indigo-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold mb-4">Expert Network</h1>
            <p className="text-xl text-purple-200 max-w-2xl mx-auto">
              Connect with vetted industry experts to accelerate your business journey. 
              Get strategic guidance, technical expertise, and insider connections.
            </p>
          </div>

          <div className="max-w-3xl mx-auto">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-purple-300" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by name, skill, industry..."
                    className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-white/30"
                  />
                </div>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-white/10 border border-white/20 rounded-xl hover:bg-white/20 transition-colors"
                >
                  <Filter className="w-5 h-5" />
                  Filters
                  <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {showFilters && (
                <div className="mt-4 pt-4 border-t border-white/20">
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setSelectedCategory('')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        !selectedCategory 
                          ? 'bg-white text-purple-900' 
                          : 'bg-white/10 text-white hover:bg-white/20'
                      }`}
                    >
                      All Categories
                    </button>
                    {categories?.map((cat) => (
                      <button
                        key={cat.value}
                        onClick={() => setSelectedCategory(cat.value)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          selectedCategory === cat.value 
                            ? 'bg-white text-purple-900' 
                            : 'bg-white/10 text-white hover:bg-white/20'
                        }`}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {isLoading && (
          <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
            <Loader2 className="w-10 h-10 animate-spin text-purple-600 mx-auto mb-4" />
            <p className="text-gray-500">Loading expert profiles...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-700 p-6 rounded-2xl border border-red-200">
            Failed to load experts. Please try again later.
          </div>
        )}

        {!isLoading && !error && experts?.length === 0 && (
          <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
            <User className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Experts Found</h3>
            <p className="text-gray-500 mb-6">
              {searchQuery || selectedCategory 
                ? 'Try adjusting your filters or search terms.' 
                : 'Expert profiles will be listed here once available.'}
            </p>
            {isAuthenticated && (
              <Link
                to="/build/expert-apply"
                className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 transition-colors"
              >
                <Award className="w-5 h-5" />
                Apply to Become an Expert
              </Link>
            )}
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {experts?.map((expert) => (
            <div 
              key={expert.id} 
              className="bg-white rounded-2xl border border-gray-200 overflow-hidden hover:border-purple-300 hover:shadow-lg transition-all group"
            >
              <div className="p-6">
                <div className="flex items-start gap-4 mb-4">
                  {(expert.user_avatar) ? (
                    <img 
                      src={expert.user_avatar} 
                      alt={expert.external_name || expert.user_name || ''} 
                      className="w-16 h-16 rounded-full object-cover"
                    />
                  ) : (
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-bold ${
                      expert.external_source === 'sample'
                        ? 'bg-gradient-to-br from-amber-400 to-orange-500'
                        : expert.external_source
                          ? 'bg-gradient-to-br from-green-500 to-teal-600'
                          : 'bg-gradient-to-br from-purple-500 to-indigo-600'
                    }`}>
                      {(expert.external_name || expert.user_name || 'E').charAt(0)}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-lg text-gray-900 truncate">
                        {expert.external_name || expert.user_name || 'Expert'}
                      </h3>
                      {expert.external_source === 'upwork' && expert.external_url && (
                        <a
                          href={expert.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full hover:bg-green-200 transition-colors"
                          title="View on Upwork"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Upwork
                        </a>
                      )}
                    </div>
                    {expert.title && (
                      <p className="text-purple-600 font-medium text-sm line-clamp-1">{expert.title}</p>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      {expert.external_source === 'sample' && (
                        <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                          <ExternalLink className="w-3.5 h-3.5" />
                          Sample
                        </span>
                      )}
                      {expert.is_verified && expert.external_source !== 'sample' && (
                        <span className="flex items-center gap-1 text-xs text-green-600">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Verified
                        </span>
                      )}
                      {expert.external_source && !expert.is_verified && expert.external_source !== 'sample' && (
                        <span className="flex items-center gap-1 text-xs text-blue-600">
                          <ExternalLink className="w-3.5 h-3.5" />
                          External
                        </span>
                      )}
                      {expert.avg_rating && (
                        <span className="flex items-center gap-1 text-xs text-amber-600">
                          <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                          {expert.avg_rating.toFixed(1)}
                          <span className="text-gray-400">({expert.total_reviews})</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {expert.location && (
                  <div className="flex items-center gap-2 text-sm text-gray-500 mb-3">
                    <MapPin className="w-4 h-4" />
                    {expert.location}
                  </div>
                )}

                {(expert.primary_category || expert.category) && (
                  <div className="flex items-center gap-2 mb-3">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium">
                      {getCategoryIcon(expert.primary_category || expert.category || '')}
                      {(expert.primary_category || expert.category || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </div>
                )}

                <div className="flex flex-wrap gap-3 text-sm">
                  {expert.hourly_rate_cents && (
                    <div className="flex items-center gap-1 text-gray-600">
                      <Clock className="w-4 h-4 text-gray-400" />
                      {formatCents(expert.hourly_rate_cents)}/hr
                    </div>
                  )}
                  {expert.projects_completed > 0 && (
                    <div className="flex items-center gap-1 text-gray-600">
                      <CheckCircle className="w-4 h-4 text-gray-400" />
                      {expert.projects_completed} projects
                    </div>
                  )}
                </div>
              </div>

              <div className="px-6 pb-6">
                {expert.external_source === 'upwork' && expert.external_url ? (
                  <div className="space-y-2">
                    <a
                      href={expert.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full py-3 bg-gradient-to-r from-green-500 to-teal-500 text-white rounded-xl font-semibold hover:from-green-600 hover:to-teal-600 transition-all flex items-center justify-center gap-2 group-hover:shadow-lg"
                    >
                      <ExternalLink className="w-5 h-5" />
                      Contact on Upwork
                    </a>
                    <p className="text-xs text-center text-gray-500">
                      This expert is available through Upwork
                    </p>
                  </div>
                ) : expert.external_source === 'sample' ? (
                  <div className="space-y-2">
                    <button
                      disabled
                      className="w-full py-3 bg-gray-100 text-gray-400 rounded-xl font-semibold cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      <MessageSquare className="w-5 h-5" />
                      Coming Soon
                    </button>
                    <p className="text-xs text-center text-gray-500">
                      This expert profile is for demonstration
                    </p>
                  </div>
                ) : isAuthenticated ? (
                  <button
                    onClick={() => openEngagement(expert)}
                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 group-hover:shadow-lg"
                  >
                    <MessageSquare className="w-5 h-5" />
                    Request Consultation
                  </button>
                ) : (
                  <Link
                    to="/login?next=/build/experts"
                    className="block w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all text-center"
                  >
                    Sign In to Connect
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {showEngagementModal && selectedExpert && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Request Engagement</h2>
              <button
                onClick={() => setShowEngagementModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="p-6">
              {engagementSuccess ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">Request Sent!</h3>
                  <p className="text-gray-600 mb-4">
                    {selectedExpert.user_name} will review your request and respond soon.
                  </p>
                  <p className="text-sm text-gray-500">
                    You'll receive a notification when they respond.
                  </p>
                </div>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); engagementMutation.mutate(selectedExpert.id) }}>
                  <div className="flex items-center gap-4 mb-6 p-4 bg-purple-50 rounded-xl">
                    {selectedExpert.user_avatar ? (
                      <img 
                        src={selectedExpert.user_avatar} 
                        alt={selectedExpert.user_name || ''} 
                        className="w-14 h-14 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-xl font-bold">
                        {(selectedExpert.user_name || 'E').charAt(0)}
                      </div>
                    )}
                    <div>
                      <p className="font-bold text-gray-900">{selectedExpert.user_name}</p>
                      <p className="text-sm text-purple-600">{selectedExpert.title}</p>
                    </div>
                  </div>

                  <div className="space-y-5">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Engagement Type</label>
                      <div className="grid grid-cols-2 gap-3">
                        {[
                          { value: 'consultation', label: 'Consultation', desc: '1-hour session', price: selectedExpert.hourly_rate_cents ? formatCents(selectedExpert.hourly_rate_cents) : '$150-500' },
                          { value: 'project', label: 'Project', desc: '2-8 weeks', price: formatCentsRange(selectedExpert.project_rate_min_cents, selectedExpert.project_rate_max_cents) || '$2,500-50,000' },
                          { value: 'retainer', label: 'Retainer', desc: 'Monthly advisor', price: selectedExpert.retainer_rate_cents ? `${formatCents(selectedExpert.retainer_rate_cents)}/mo` : '$2,000-10,000/mo' },
                          { value: 'hourly', label: 'Hourly', desc: 'As needed', price: selectedExpert.hourly_rate_cents ? `${formatCents(selectedExpert.hourly_rate_cents)}/hr` : '$100-500/hr' }
                        ].map((type) => (
                          <button
                            key={type.value}
                            type="button"
                            onClick={() => setEngagementForm({ ...engagementForm, engagement_type: type.value })}
                            className={`p-3 rounded-xl border text-left transition-all ${
                              engagementForm.engagement_type === type.value
                                ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200'
                                : 'border-gray-200 hover:border-purple-300'
                            }`}
                          >
                            <p className="font-semibold text-gray-900">{type.label}</p>
                            <p className="text-xs text-gray-500">{type.desc}</p>
                            <p className="text-xs text-purple-600 font-medium mt-1">{type.price}</p>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Project Title</label>
                      <input
                        type="text"
                        required
                        value={engagementForm.title}
                        onChange={(e) => setEngagementForm({ ...engagementForm, title: e.target.value })}
                        placeholder="e.g., SaaS Pricing Strategy Review"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">What do you need help with?</label>
                      <textarea
                        required
                        value={engagementForm.request_message}
                        onChange={(e) => setEngagementForm({ ...engagementForm, request_message: e.target.value })}
                        placeholder="Describe your project, goals, and what expertise you need. Be specific about your challenges and what outcome you're looking for..."
                        rows={4}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Additional Context (Optional)</label>
                      <textarea
                        value={engagementForm.description}
                        onChange={(e) => setEngagementForm({ ...engagementForm, description: e.target.value })}
                        placeholder="Any relevant background, timeline constraints, budget considerations..."
                        rows={2}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                      />
                    </div>
                  </div>

                  {engagementMutation.error && (
                    <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-xl text-sm">
                      {engagementMutation.error.message}
                    </div>
                  )}

                  <div className="flex gap-3 mt-6">
                    <button
                      type="button"
                      onClick={() => setShowEngagementModal(false)}
                      className="flex-1 py-3 border border-gray-200 rounded-xl font-semibold hover:bg-gray-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={engagementMutation.isPending || !engagementForm.title || !engagementForm.request_message}
                      className="flex-1 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all"
                    >
                      {engagementMutation.isPending ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <MessageSquare className="w-5 h-5" />
                          Send Request
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
