import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import DatasetCard from '../DatasetCard'

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

type SortOption = 'price_asc' | 'price_desc' | 'newest' | 'popular'

interface MarketplaceFilters {
  search: string
  category: string | null
  vertical: string | null
  city: string | null
  sortBy: SortOption
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'newest', label: 'Newest First' },
  { value: 'popular', label: 'Most Popular' },
  { value: 'price_asc', label: 'Price: Low to High' },
  { value: 'price_desc', label: 'Price: High to Low' },
]

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

export default function DatasetsTab() {
  const { isAuthenticated, token } = useAuthStore()
  const [filters, setFilters] = useState<MarketplaceFilters>({
    search: '',
    category: null,
    vertical: null,
    city: null,
    sortBy: 'newest',
  })

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

  const filteredDatasets = datasets.filter((ds) => ds.is_active)
  const hasActiveFilter =
    filters.search || filters.category || filters.vertical || filters.city

  const selectClass =
    'text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent'

  return (
    <div>
      {/* Compact filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search datasets..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
          />
        </div>
        <select
          value={filters.category ?? ''}
          onChange={(e) => setFilters({ ...filters, category: e.target.value || null })}
          className={selectClass}
        >
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          value={filters.vertical ?? ''}
          onChange={(e) => setFilters({ ...filters, vertical: e.target.value || null })}
          className={selectClass}
        >
          <option value="">All Verticals</option>
          {VERTICALS.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
        <select
          value={filters.city ?? ''}
          onChange={(e) => setFilters({ ...filters, city: e.target.value || null })}
          className={selectClass}
        >
          <option value="">All Cities</option>
          {CITIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={filters.sortBy}
          onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as SortOption })}
          className={selectClass}
        >
          {SORT_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        {hasActiveFilter && (
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
            className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2"
          >
            Clear
          </button>
        )}
      </div>

      {/* Result count */}
      <p className="text-sm text-gray-500 mb-4">
        {filteredDatasets.length} dataset{filteredDatasets.length !== 1 ? 's' : ''}
      </p>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-72 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Failed to load datasets. Please try again.
        </div>
      )}

      {!isLoading && filteredDatasets.length === 0 && (
        <div className="text-center py-12 bg-white border border-gray-200 rounded-xl">
          <p className="text-gray-600">No datasets found matching your filters.</p>
        </div>
      )}

      {!isLoading && filteredDatasets.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredDatasets.map((dataset) => (
            <DatasetCard key={dataset.id} dataset={dataset} />
          ))}
        </div>
      )}
    </div>
  )
}
