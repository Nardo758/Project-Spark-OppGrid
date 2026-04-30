import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, ChevronDown } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import DatasetCard from '../components/DatasetCard'
import { useNavigate } from 'react-router-dom'

interface Dataset {
  id: string
  name: string
  description: string
  dataset_type: 'opportunities' | 'markets' | 'trends' | 'raw_data'
  vertical?: string | null
  city?: string | null
  price_cents: number
  record_count: number
  data_freshness: string
  created_at: string
  is_active: boolean
}

interface MarketplaceFilters {
  search: string
  category: string | null
  vertical: string | null
  city: string | null
  sortBy: 'price_asc' | 'price_desc' | 'newest' | 'popular'
}

const CATEGORIES = [
  { value: 'opportunities', label: 'Opportunities' },
  { value: 'markets', label: 'Markets' },
  { value: 'trends', label: 'Trends' },
  { value: 'raw_data', label: 'Raw Data' },
]

const VERTICALS = [
  'Coffee',
  'Coworking',
  'Gyms',
  'Fitness',
  'Restaurants',
  'Retail',
  'Tech',
  'Healthcare',
  'Finance',
  'Education',
]

const CITIES = [
  'San Francisco',
  'New York',
  'Los Angeles',
  'Austin',
  'Chicago',
  'Boston',
  'Seattle',
  'Miami',
  'Denver',
  'Portland',
]

export default function Marketplace() {
  const navigate = useNavigate()
  const { isAuthenticated, token } = useAuthStore()
  const [filters, setFilters] = useState<MarketplaceFilters>({
    search: '',
    category: null,
    vertical: null,
    city: null,
    sortBy: 'newest',
  })
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)

  // Fetch datasets
  const { data: datasets = [], isLoading, error } = useQuery({
    queryKey: ['datasets', filters],
    queryFn: async (): Promise<Dataset[]> => {
      const params = new URLSearchParams()
      if (filters.search) params.append('search', filters.search)
      if (filters.category) params.append('dataset_type', filters.category)
      if (filters.vertical) params.append('vertical', filters.vertical)
      if (filters.city) params.append('city', filters.city)
      params.append('sort_by', filters.sortBy)

      const url = `/api/v1/datasets?${params.toString()}`
      const headers: HeadersInit = {}
      if (isAuthenticated && token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const res = await fetch(url, { headers })
      if (!res.ok) throw new Error('Failed to load datasets')
      return res.json()
    },
  })

  // Filter and sort datasets
  const filteredDatasets = datasets.filter(ds => ds.is_active)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 border-b border-gray-700 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-white mb-2">Dataset Marketplace</h1>
          <p className="text-gray-400 text-lg">
            Discover, preview, and purchase verified market intelligence datasets
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar Filters */}
          <div className="lg:w-72 flex-shrink-0">
            <div className="sticky top-20 space-y-6">
              {/* Search */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="relative">
                  <Search className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search datasets..."
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Category Filter */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'category' ? null : 'category')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Filter className="w-4 h-4" />
                    Category
                  </h3>
                  <ChevronDown
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      openDropdown === 'category' ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {openDropdown === 'category' && (
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="radio"
                        name="category"
                        value=""
                        checked={filters.category === null}
                        onChange={() => setFilters({ ...filters, category: null })}
                        className="w-4 h-4"
                      />
                      <span className="text-sm text-gray-300 group-hover:text-white">All Categories</span>
                    </label>
                    {CATEGORIES.map((cat) => (
                      <label key={cat.value} className="flex items-center gap-2 cursor-pointer group">
                        <input
                          type="radio"
                          name="category"
                          value={cat.value}
                          checked={filters.category === cat.value}
                          onChange={() => setFilters({ ...filters, category: cat.value })}
                          className="w-4 h-4"
                        />
                        <span className="text-sm text-gray-300 group-hover:text-white">{cat.label}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Vertical Filter */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'vertical' ? null : 'vertical')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-sm font-semibold text-white">Vertical</h3>
                  <ChevronDown
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      openDropdown === 'vertical' ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {openDropdown === 'vertical' && (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="radio"
                        name="vertical"
                        value=""
                        checked={filters.vertical === null}
                        onChange={() => setFilters({ ...filters, vertical: null })}
                        className="w-4 h-4"
                      />
                      <span className="text-sm text-gray-300 group-hover:text-white">All Verticals</span>
                    </label>
                    {VERTICALS.map((vert) => (
                      <label key={vert} className="flex items-center gap-2 cursor-pointer group">
                        <input
                          type="radio"
                          name="vertical"
                          value={vert}
                          checked={filters.vertical === vert}
                          onChange={() => setFilters({ ...filters, vertical: vert })}
                          className="w-4 h-4"
                        />
                        <span className="text-sm text-gray-300 group-hover:text-white">{vert}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* City Filter */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'city' ? null : 'city')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-sm font-semibold text-white">City</h3>
                  <ChevronDown
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      openDropdown === 'city' ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {openDropdown === 'city' && (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="radio"
                        name="city"
                        value=""
                        checked={filters.city === null}
                        onChange={() => setFilters({ ...filters, city: null })}
                        className="w-4 h-4"
                      />
                      <span className="text-sm text-gray-300 group-hover:text-white">All Cities</span>
                    </label>
                    {CITIES.map((city) => (
                      <label key={city} className="flex items-center gap-2 cursor-pointer group">
                        <input
                          type="radio"
                          name="city"
                          value={city}
                          checked={filters.city === city}
                          onChange={() => setFilters({ ...filters, city })}
                          className="w-4 h-4"
                        />
                        <span className="text-sm text-gray-300 group-hover:text-white">{city}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Sort By */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'sort' ? null : 'sort')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-sm font-semibold text-white">Sort By</h3>
                  <ChevronDown
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      openDropdown === 'sort' ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {openDropdown === 'sort' && (
                  <div className="space-y-2">
                    {[
                      { value: 'newest', label: 'Newest First' },
                      { value: 'popular', label: 'Most Popular' },
                      { value: 'price_asc', label: 'Price: Low to High' },
                      { value: 'price_desc', label: 'Price: High to Low' },
                    ].map((opt) => (
                      <label key={opt.value} className="flex items-center gap-2 cursor-pointer group">
                        <input
                          type="radio"
                          name="sort"
                          value={opt.value}
                          checked={filters.sortBy === opt.value}
                          onChange={() => setFilters({ ...filters, sortBy: opt.value as any })}
                          className="w-4 h-4"
                        />
                        <span className="text-sm text-gray-300 group-hover:text-white">{opt.label}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {/* Results Header */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white">
                {filteredDatasets.length} Dataset{filteredDatasets.length !== 1 ? 's' : ''} Available
              </h2>
              {filters.search && (
                <p className="text-sm text-gray-400 mt-1">
                  Results for: <span className="font-medium">{filters.search}</span>
                </p>
              )}
            </div>

            {/* Loading State */}
            {isLoading && (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-96 bg-gray-800 rounded-lg animate-pulse" />
                ))}
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-300">
                Failed to load datasets. Please try again.
              </div>
            )}

            {/* Empty State */}
            {!isLoading && filteredDatasets.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-400 text-lg">No datasets found matching your filters.</p>
                <button
                  onClick={() =>
                    setFilters({
                      search: '',
                      category: null,
                      vertical: null,
                      city: null,
                      sortBy: 'newest',
                    })
                  }
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            )}

            {/* Datasets Grid */}
            {!isLoading && filteredDatasets.length > 0 && (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {filteredDatasets.map((dataset) => (
                  <DatasetCard key={dataset.id} dataset={dataset} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
