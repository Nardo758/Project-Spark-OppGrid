import { useState } from 'react'
import { useSavedOpportunities } from '../hooks/useSavedOpportunities'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import { Heart, Star, Search, Filter, ArrowUpDown } from 'lucide-react'

interface SavedOppWithDetails extends Record<string, any> {
  id: number
  opportunity_id: number
  priority: number
  saved_at: string
  title?: string
  category?: string
  severity?: number
}

export default function MyIdeas() {
  const { token } = useAuthStore()
  const [sortBy, setSortBy] = useState<'priority' | 'date' | 'alpha'>('priority')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { saved: savedData, isLoading } = useSavedOpportunities(sortBy)

  // Fetch full opportunity details for saved items
  const { data: opportunities } = useQuery({
    queryKey: ['opportunities-details', savedData],
    queryFn: async () => {
      if (!savedData || savedData.length === 0) return []

      const oppIds = savedData.map((s) => s.opportunity_id).join(',')
      const res = await fetch(`/api/v1/opportunities?ids=${oppIds}`, {
        headers: headers(),
      })
      if (!res.ok) return []
      const data = await res.json()
      return Array.isArray(data) ? data : data.data || []
    },
    enabled: !!token && savedData.length > 0,
  })

  // Merge saved metadata with opportunity details
  const merged: SavedOppWithDetails[] = (savedData || []).map((saved) => {
    const opp = opportunities?.find((o) => o.id === saved.opportunity_id) || {}
    return {
      ...saved,
      ...opp,
    }
  })

  // Filter
  const filtered = merged.filter((item) => {
    if (searchQuery && !item.title?.toLowerCase().includes(searchQuery.toLowerCase())) return false
    if (selectedCategory && item.category !== selectedCategory) return false
    return true
  })

  const categories = [...new Set(merged.map((m) => m.category))].filter(Boolean)

  if (!token) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center p-4">
        <div className="text-center">
          <Heart className="w-12 h-12 text-stone-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-stone-900 mb-2">Sign in to save ideas</h1>
          <p className="text-stone-600">Create your personal collection of opportunities</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-stone-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Heart className="w-8 h-8 text-red-600 fill-current" />
            <h1 className="text-3xl font-bold text-stone-900">My Ideas</h1>
          </div>
          <p className="text-stone-600">
            {filtered.length} saved opportunity{filtered.length !== 1 ? 'ies' : ''}
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white rounded-lg border border-stone-200 p-4 mb-6 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-stone-400" />
            <input
              type="text"
              placeholder="Search ideas..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
            />
          </div>

          {/* Filters & Sort */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Category Filter */}
            {categories.length > 0 && (
              <div>
                <label className="text-sm font-medium text-stone-700 mb-1 block">Category</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400 text-sm"
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Sort */}
            <div>
              <label className="text-sm font-medium text-stone-700 mb-1 block">Sort by</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400 text-sm"
              >
                <option value="priority">Priority (High to Low)</option>
                <option value="date">Recently Saved</option>
                <option value="alpha">Alphabetical</option>
              </select>
            </div>
          </div>
        </div>

        {/* List */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-stone-200 p-4 animate-pulse">
                <div className="h-6 bg-stone-200 rounded w-1/3 mb-2" />
                <div className="h-4 bg-stone-100 rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <Heart className="w-12 h-12 text-stone-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-stone-900 mb-2">No saved ideas yet</h2>
            <p className="text-stone-600">Start exploring opportunities and save your favorites</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((idea) => (
              <a
                key={idea.opportunity_id}
                href={`/opportunity/${idea.opportunity_id}`}
                className="block bg-white rounded-lg border border-stone-200 p-4 hover:border-stone-300 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-stone-900 truncate">{idea.title}</h3>
                    <p className="text-sm text-stone-600 mt-1 line-clamp-2">{idea.description}</p>
                    <div className="flex items-center gap-4 mt-3">
                      {idea.category && (
                        <span className="inline-block px-2 py-1 text-xs font-medium bg-stone-100 text-stone-700 rounded">
                          {idea.category}
                        </span>
                      )}
                      {idea.severity && (
                        <span className="text-xs text-stone-600">
                          {idea.severity === 1 ? '🟢' : idea.severity === 2 ? '🟡' : '🔴'} Severity: {idea.severity}/3
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Priority Stars */}
                  <div className="flex-shrink-0 flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`w-4 h-4 ${
                          idea.priority >= star ? 'fill-amber-400 text-amber-400' : 'text-stone-300'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
