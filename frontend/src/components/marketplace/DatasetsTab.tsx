import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Eye, ShoppingCart, Star, Database, ArrowUpDown, TrendingUp, Zap, BarChart3, MapPin, Globe, AlertCircle, CheckCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import DatasetPreview from '../DatasetPreview'

interface Dataset {
  id: string
  name: string
  description: string
  dataset_type: 'opportunities' | 'markets' | 'trends' | 'raw_data' | 'opportunity_signals' | 'market_intelligence' | 'economic_intelligence' | 'competition_intelligence'
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
  { value: 'opportunity_signals', label: 'Signal Feed' },
  { value: 'market_intelligence', label: "4P's Market Intelligence" },
  { value: 'economic_intelligence', label: 'Economic Intelligence' },
  { value: 'competition_intelligence', label: 'Competition Map' },
]

const CATEGORY_COLORS: Record<string, { bg: string; text: string; icon: string; border: string }> = {
  opportunities: { bg: 'bg-purple-50', text: 'text-purple-700', icon: '💡', border: 'border-purple-200' },
  markets: { bg: 'bg-blue-50', text: 'text-blue-700', icon: '📊', border: 'border-blue-200' },
  trends: { bg: 'bg-green-50', text: 'text-green-700', icon: '📈', border: 'border-green-200' },
  raw_data: { bg: 'bg-orange-50', text: 'text-orange-700', icon: '📦', border: 'border-orange-200' },
  opportunity_signals: { bg: 'bg-red-50', text: 'text-red-700', icon: '📡', border: 'border-red-200' },
  market_intelligence: { bg: 'bg-indigo-50', text: 'text-indigo-700', icon: '🧠', border: 'border-indigo-200' },
  economic_intelligence: { bg: 'bg-teal-50', text: 'text-teal-700', icon: '💰', border: 'border-teal-200' },
  competition_intelligence: { bg: 'bg-rose-50', text: 'text-rose-700', icon: '🗺️', border: 'border-rose-200' },
}

const CATEGORY_LABELS: Record<string, string> = {
  opportunities: 'Opportunities',
  markets: 'Markets',
  trends: 'Trends',
  raw_data: 'Raw Data',
  opportunity_signals: 'Signal Feed',
  market_intelligence: "4P's Market Intelligence",
  economic_intelligence: 'Economic Intelligence',
  competition_intelligence: 'Competition Map',
}

const VERTICALS: { value: string; label: string }[] = [
  { value: 'coffee', label: 'Coffee' },
  { value: 'location_analysis', label: 'Location Analysis' },
  { value: 'multi_vertical', label: 'Multi-Vertical' },
  { value: '4ps_framework', label: "4P's Framework" },
  { value: 'b2b_services', label: 'B2B Services' },
  { value: 'consumer_services', label: 'Consumer Services' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'technology', label: 'Technology' },
  { value: 'technology_&_software', label: 'Technology & Software' },
]

const CITIES = [
  'San Francisco', 'New York', 'Los Angeles', 'Austin', 'Chicago', 'Boston',
  'Seattle', 'Miami', 'Denver', 'Portland', 'Bay Area', 'Dallas', 'Atlanta',
  'San Diego', 'Houston', 'Nashville', 'Bend', 'Boise', 'Salt Lake City',
  'Philadelphia', 'Phoenix', 'Tampa',
]

const TIER_MIN_ROWS: Record<string, number> = {
  competition_intelligence: 100,
  raw_data: 100,
  markets: 50,
  market_intelligence: 50,
  opportunities: 25,
  opportunity_signals: 25,
  trends: 30,
  economic_intelligence: 30,
}

function getQualityPill(dataset: Dataset) {
  const min = TIER_MIN_ROWS[dataset.dataset_type] ?? 25
  if (dataset.record_count === 0) {
    return { label: 'No Data', icon: <AlertCircle className="w-3 h-3" />, cls: 'bg-red-50 text-red-600 border-red-200' }
  }
  if (dataset.record_count < min) {
    return { label: 'Limited Data', icon: <AlertCircle className="w-3 h-3" />, cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' }
  }
  return { label: 'Verified', icon: <CheckCircle className="w-3 h-3" />, cls: 'bg-green-50 text-green-700 border-green-200' }
}

function MiniDatasetCard({ dataset, onPreview, onBuy }: { dataset: Dataset; onPreview: () => void; onBuy: () => void }) {
  const cat = CATEGORY_COLORS[dataset.dataset_type] || CATEGORY_COLORS.raw_data
  const label = CATEGORY_LABELS[dataset.dataset_type] || 'Data'
  const quality = getQualityPill(dataset)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:border-gray-300 hover:shadow-sm transition-all flex flex-col h-full">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 leading-snug">
          {dataset.name}
        </h3>
        <span className={`shrink-0 ${cat.bg} ${cat.text} ${cat.border} border px-2 py-0.5 rounded-full text-[11px] font-medium`}>
          {cat.icon} {label}
        </span>
      </div>
      <p className="text-xs text-gray-600 line-clamp-2 mb-2 flex-1">
        {dataset.description || 'High-quality market intelligence dataset'}
      </p>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Database className="w-3.5 h-3.5" />
          {dataset.record_count} rows
        </div>
        <span className={`flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border ${quality.cls}`}>
          {quality.icon}
          {quality.label}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2 pt-3 border-t border-gray-100">
        <div className="text-lg font-bold text-gray-900">
          ${(dataset.price_cents / 100).toFixed(0)}
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={onPreview}
            className="flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-900 transition-colors"
          >
            <Eye className="w-3.5 h-3.5" />
            Preview
          </button>
          <button
            onClick={onBuy}
            className="flex items-center gap-1 text-xs font-medium px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            Buy
          </button>
        </div>
      </div>
    </div>
  )
}

export default function DatasetsTab() {
  const { isAuthenticated, token } = useAuthStore()
  const navigate = useNavigate()
  const [filters, setFilters] = useState<MarketplaceFilters>({
    search: '',
    category: null,
    vertical: null,
    city: null,
    sortBy: 'newest',
  })
  const [previewDataset, setPreviewDataset] = useState<Dataset | null>(null)

  const { data: datasets = [], isLoading, error } = useQuery({
    queryKey: ['datasets', filters.category, filters.vertical, filters.city],
    queryFn: async (): Promise<Dataset[]> => {
      const params = new URLSearchParams()
      if (filters.category) params.append('dataset_type', filters.category)
      if (filters.vertical) params.append('vertical', filters.vertical)
      if (filters.city) params.append('city', filters.city)

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

  // Client-side search filtering
  const searchFiltered = datasets.filter((ds) => {
    if (!filters.search) return true
    const q = filters.search.toLowerCase()
    return (
      ds.name.toLowerCase().includes(q) ||
      (ds.description || '').toLowerCase().includes(q) ||
      (ds.city || '').toLowerCase().includes(q) ||
      (ds.vertical || '').toLowerCase().includes(q)
    )
  })

  // Client-side sorting
  const sorted = [...searchFiltered].sort((a, b) => {
    switch (filters.sortBy) {
      case 'price_asc': return a.price_cents - b.price_cents
      case 'price_desc': return b.price_cents - a.price_cents
      case 'newest': return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      case 'popular': return b.record_count - a.record_count
      default: return 0
    }
  })

  const filteredDatasets = sorted.filter((ds) => ds.is_active)
  const hasActiveFilter =
    filters.search || filters.category || filters.vertical || filters.city

  // Pick one highlight per tier for the hero section
  const tierHighlights = [
    datasets.find((d) => d.dataset_type === 'opportunity_signals'),
    datasets.find((d) => d.dataset_type === 'market_intelligence'),
    datasets.find((d) => d.dataset_type === 'economic_intelligence'),
    datasets.find((d) => d.dataset_type === 'competition_intelligence'),
  ].filter(Boolean) as Dataset[]

  const selectClass =
    'text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent'

  return (
    <div>
      {/* Hero — show one dataset from each tier at the top */}
      {tierHighlights.length > 0 && !filters.search && !hasActiveFilter && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" />
            Explore Our Data Tiers
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {tierHighlights.map((ds) => (
              <div
                key={ds.id}
                onClick={() => setFilters({ ...filters, category: ds.dataset_type })}
                className="cursor-pointer bg-white border border-gray-200 rounded-xl p-4 hover:border-emerald-300 hover:shadow-sm transition-all"
              >
                <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium mb-2 ${CATEGORY_COLORS[ds.dataset_type]?.bg} ${CATEGORY_COLORS[ds.dataset_type]?.text}`}>
                  {CATEGORY_COLORS[ds.dataset_type]?.icon} {CATEGORY_LABELS[ds.dataset_type]}
                </div>
                <p className="text-xs font-semibold text-gray-900 mb-1">
                  {ds.name}
                </p>
                <p className="text-xs text-gray-500">
                  {ds.record_count} records · ${(ds.price_cents / 100).toFixed(0)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compact filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search datasets..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
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
            <option key={v.value} value={v.value}>
              {v.label}
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
        {hasActiveFilter && ' matching your filters'}
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
            <MiniDatasetCard
              key={dataset.id}
              dataset={dataset}
              onPreview={() => setPreviewDataset(dataset)}
              onBuy={() => navigate(`/datasets/${dataset.id}/checkout`)}
            />
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {previewDataset && (
        <DatasetPreview
          datasetId={previewDataset.id}
          datasetName={previewDataset.name}
          onClose={() => setPreviewDataset(null)}
          onCheckout={() => {
            setPreviewDataset(null)
            navigate(`/datasets/${previewDataset.id}/checkout`)
          }}
        />
      )}
    </div>
  )
}
