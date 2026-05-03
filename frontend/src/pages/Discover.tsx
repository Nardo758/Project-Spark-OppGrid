/**
 * OppGrid Discovery Feed - Main Page
 * Assembles all discovery components into complete feature
 */

import { useEffect } from 'react'
import '../styles/discovery-theme.css'
import {
  FilterBar,
  OpportunityGrid,
  Pagination,
} from '../components/DiscoveryFeed'
import { useDiscoveryStore } from '../stores/discoveryStore'
import { useAuthStore } from '../stores/authStore'

export default function Discover() {
  const {
    // State
    opportunities: opportunitiesRaw,
    recommendedOpportunities: recommendedRaw,
    filters,
    page,
    pageSize,
    total,
    selectedOpportunityIds: selectedIdsRaw,
    loading,
    error,
    isGated,
    gatedMessage,
    fullTotal,
    
    // Actions
    initializeFromUrl,
    setFilters,
    setPage,
    quickValidate,
    toggleSave,
    clearSelection,
  } = useDiscoveryStore()
  const { isAuthenticated } = useAuthStore()

  // Defensive guards: Zustand devtools middleware can restore stale state
  // from a previous Redux DevTools session that may be missing array fields
  const opportunities = opportunitiesRaw ?? []
  const recommendedOpportunities = recommendedRaw ?? []
  const selectedOpportunityIds = selectedIdsRaw ?? []

  // Initialize from URL on mount
  useEffect(() => {
    initializeFromUrl()
  }, [initializeFromUrl])

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Discover Validated Opportunities
          </h1>
          <p className="text-gray-600">
            Browse real-world problems validated by the community
          </p>
        </div>

        {/* Filters */}
        <div className="mb-8">
          <FilterBar
            filters={{
              search: filters.search || '',
              category: filters.category || null,
              feasibility: null,
              location: filters.geographic_scope || null,
              sortBy: filters.sort_by || 'feasibility',
              maxDaysOld: filters.max_age_days ?? null,
              myAccessOnly: filters.my_access_only || false,
            }}
            onFiltersChange={(newFilters) => setFilters({
              search: newFilters.search,
              category: newFilters.category || undefined,
              geographic_scope: newFilters.location || undefined,
              sort_by: newFilters.sortBy,
              max_age_days: newFilters.maxDaysOld ?? undefined,
              my_access_only: newFilters.myAccessOnly,
            })}
            resultsCount={total}
          />
        </div>

        {/* Personalized Recommendations (Compact Carousel)
            - Logged out: show low-feasibility teaser ideas only (don't give away the good ones)
            - Logged in: show real personalized recommendations, top 6 */}
        {(() => {
          const trending = isAuthenticated
            ? recommendedOpportunities.slice(0, 6)
            : recommendedOpportunities
                .filter((opp) => (opp.feasibility_score ?? 0) < 50)
                .slice(0, 6)
          if (trending.length === 0) return null
          return (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <span className="text-purple-600">✨</span>
                {isAuthenticated ? 'Recommended for You' : 'Trending Opportunities'}
                <span className="text-xs text-gray-500 font-normal">
                  {isAuthenticated
                    ? '(based on your past interactions)'
                    : '(sign in for personalized picks)'}
                </span>
              </h2>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-2 hide-scrollbar">
              {trending.map((opp) => (
                <div
                  key={opp.id}
                  className="min-w-[280px] bg-gradient-to-br from-purple-50 to-white border border-purple-100 rounded-lg p-4 cursor-pointer hover:border-purple-300 transition-all"
                  onClick={() => window.location.href = `/opportunity/${opp.id}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs font-semibold text-purple-600">{opp.category}</span>
                    <span className="text-lg font-bold text-purple-600">{opp.feasibility_score}</span>
                  </div>
                  <h3 className="font-semibold text-sm text-gray-900 mb-1 line-clamp-2">
                    {opp.title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-gray-600">
                    <span>✅ {opp.match_score}% match</span>
                    <span>{opp.validation_count} validations</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          )
        })()}

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Gating Banner for Free Users */}
        {isGated && (
          <div className="mb-6 p-6 bg-gradient-to-r from-violet-50 to-purple-50 border border-violet-200 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-violet-900 mb-1">
                  Unlock All {fullTotal} Opportunities
                </h3>
                <p className="text-sm text-violet-700">
                  {gatedMessage || `You're viewing a preview. Subscribe to access all opportunities with higher feasibility scores.`}
                </p>
              </div>
              <a
                href="/pricing"
                className="px-6 py-3 bg-violet-600 text-white font-semibold rounded-lg hover:bg-violet-700 transition-colors whitespace-nowrap"
              >
                View Plans
              </a>
            </div>
          </div>
        )}

        {/* Opportunity Grid (with built-in loading + empty states) */}
        {(loading || opportunities.length > 0) && (
          <OpportunityGrid
            opportunities={opportunities}
            isLoading={loading}
            viewMode="grid"
            onValidate={quickValidate}
            onSave={toggleSave}
          />
        )}

        {/* Pagination */}
        {opportunities.length > 0 && (
          <Pagination
            pagination={{
              currentPage: page,
              totalItems: total,
              pageSize: pageSize,
              totalPages: Math.ceil(total / pageSize) || 1,
            }}
            onPageChange={setPage}
          />
        )}

        {/* Empty State (when no results) */}
        {!loading && opportunities.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No opportunities found
            </h3>
            <p className="text-gray-600 mb-6">
              Try adjusting your filters or search terms
            </p>
            <button
              onClick={() => setFilters({})}
              className="px-6 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        )}
      </div>

      {/* Floating Comparison Panel */}
      {selectedOpportunityIds.length > 0 && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {selectedOpportunityIds.length} selected
          </span>
          <button
            onClick={clearSelection}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  )
}
