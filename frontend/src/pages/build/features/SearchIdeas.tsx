import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, ExternalLink, ChevronRight, Database, Library, AlertCircle } from 'lucide-react'
import { useConsultantApi, SearchIdeasResult } from '../hooks/useConsultantApi'
import { useAuthStore } from '@/stores/authStore'

interface SearchIdeasProps {
  onWorkspaceClick?: (context: Record<string, unknown>) => void
}

export function SearchIdeas({ onWorkspaceClick }: SearchIdeasProps) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const { searchIdeas } = useConsultantApi()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SearchIdeasResult | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const categories = [
    { value: '', label: 'All Categories' },
    { value: 'technology', label: 'Technology' },
    { value: 'healthcare', label: 'Healthcare' },
    { value: 'food', label: 'Food & Beverage' },
    { value: 'retail', label: 'Retail' },
    { value: 'services', label: 'Services' },
    { value: 'real_estate', label: 'Real Estate' },
    { value: 'finance', label: 'Finance' },
  ]

  const handleSearch = async () => {
    setLoading(true)
    setError(null)
    setSelectedId(null)

    const response = await searchIdeas(query || undefined, category || undefined)

    if (response.error) {
      setError(response.error)
    } else if (response.data) {
      setResult(response.data)
    }

    setLoading(false)
  }

  const handleOpportunityClick = (opp: SearchIdeasResult['opportunities'][0]) => {
    setSelectedId(opp.id)
  }

  const handleOpenInWorkHub = (opp: SearchIdeasResult['opportunities'][0]) => {
    if (onWorkspaceClick) {
      onWorkspaceClick({
        type: 'opportunity',
        opportunityId: opp.id,
        title: opp.title,
        description: opp.description,
        category: opp.category,
      })
    }
  }

  const selectedOpportunity = result?.opportunities.find(o => o.id === selectedId)

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
            <Database className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Search Opportunities</h2>
            <p className="text-sm text-gray-500">
              Explore our database of validated business opportunities
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search by keyword (e.g., coffee shop, SaaS, fitness)"
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="px-4 py-3 border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              {categories.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {!isAuthenticated && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-amber-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>Please <button onClick={() => navigate('/auth/login')} className="font-semibold underline hover:text-amber-800">sign in</button> to search opportunities.</span>
            </div>
          )}
          <button
            onClick={handleSearch}
            disabled={loading || !isAuthenticated}
            className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Search Database
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {result && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h3 className="font-semibold text-gray-900">
              Found {result.total || result.opportunities.length} Opportunities
            </h3>
          </div>

          {result.opportunities.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No opportunities found. Try a different search term or category.
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {result.opportunities.map((opp) => (
                <div
                  key={opp.id}
                  onClick={() => handleOpportunityClick(opp)}
                  className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                    selectedId === opp.id ? 'bg-purple-50 border-l-4 border-purple-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">{opp.title}</h4>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {opp.description || 'No description available'}
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
                          {opp.category}
                        </span>
                        {opp.score > 0 && (
                          <span className="text-xs text-purple-600 font-medium">
                            Score: {opp.score}/100
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {selectedOpportunity && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">
            Selected: {selectedOpportunity.title}
          </h3>
          <p className="text-gray-600 mb-4">
            {selectedOpportunity.description || 'No description available'}
          </p>
          <div className="space-y-3">
            <button
              onClick={() => {
                const context = encodeURIComponent(JSON.stringify({
                  title: selectedOpportunity.title,
                  description: selectedOpportunity.description,
                  category: selectedOpportunity.category,
                  opportunityId: selectedOpportunity.id,
                }))
                navigate(`/build/reports?source=search&context=${context}&opportunityId=${selectedOpportunity.id}`)
              }}
              className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Library className="w-5 h-5" />
              Generate Report
            </button>
            <button
              onClick={() => handleOpenInWorkHub(selectedOpportunity)}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <ExternalLink className="w-5 h-5" />
              Open in WorkHub
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
