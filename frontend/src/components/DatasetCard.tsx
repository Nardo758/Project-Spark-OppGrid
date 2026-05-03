import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, ShoppingCart, Star, Database } from 'lucide-react'
import DatasetPreview from './DatasetPreview'
import { useAuthStore } from '../stores/authStore'

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

const CATEGORY_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  opportunities: { bg: 'bg-purple-100', text: 'text-purple-700', icon: '💡' },
  markets: { bg: 'bg-blue-100', text: 'text-blue-700', icon: '📊' },
  trends: { bg: 'bg-green-100', text: 'text-green-700', icon: '📈' },
  raw_data: { bg: 'bg-orange-100', text: 'text-orange-700', icon: '📦' },
}

const CATEGORY_LABELS: Record<string, string> = {
  opportunities: 'Opportunities',
  markets: 'Markets',
  trends: 'Trends',
  raw_data: 'Raw Data',
}

export default function DatasetCard({ dataset }: { dataset: Dataset }) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [showPreview, setShowPreview] = useState(false)

  const categoryColor = CATEGORY_COLORS[dataset.dataset_type] || CATEGORY_COLORS.raw_data
  const categoryLabel = CATEGORY_LABELS[dataset.dataset_type] || 'Data'

  const formatPrice = (cents: number) => `$${(cents / 100).toFixed(0)}`

  const formatRecordCount = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`
    return `${count}`
  }

  const formatFreshness = (freshness: string) => {
    const now = new Date()
    const dataDate = new Date(freshness)
    const diffMs = now.getTime() - dataDate.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffHours < 1) return 'just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 30) return `${diffDays}d ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`
    return `${Math.floor(diffDays / 365)}y ago`
  }

  const handlePreview = () => {
    if (!isAuthenticated) {
      navigate('/signin')
      return
    }
    setShowPreview(true)
  }

  const handlePurchase = () => {
    if (!isAuthenticated) {
      navigate('/signin')
      return
    }
    navigate(`/datasets/${dataset.id}/checkout`)
  }

  return (
    <>
      <div className="h-full flex flex-col bg-white border border-gray-200 rounded-xl p-4 hover:border-gray-300 hover:shadow-sm transition-all">
        {/* Top: badge + title */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 leading-snug">
            {dataset.name}
          </h3>
          <span
            className={`shrink-0 ${categoryColor.bg} ${categoryColor.text} px-2 py-0.5 rounded-full text-[11px] font-medium`}
          >
            {categoryColor.icon} {categoryLabel}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-gray-600 line-clamp-2 mb-3">
          {dataset.description || 'High-quality market intelligence dataset'}
        </p>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 mb-3">
          <span className="flex items-center gap-1">
            <Database className="w-3.5 h-3.5" />
            {formatRecordCount(dataset.record_count)} rows
          </span>
          <span>· Updated {formatFreshness(dataset.data_freshness)}</span>
          {(dataset.vertical || dataset.city) && (
            <span>· {[dataset.vertical, dataset.city].filter(Boolean).join(' • ')}</span>
          )}
        </div>

        {/* Rating */}
        <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
          <Star className="w-3 h-3 fill-amber-500 text-amber-500" />
          <span>4.0</span>
          <span className="text-gray-400">· 124 purchases</span>
        </div>

        <div className="flex-1" />

        {/* Footer: price + actions */}
        <div className="flex items-center justify-between gap-2 pt-3 border-t border-gray-100">
          <div>
            <div className="text-lg font-bold text-gray-900 leading-none">
              {formatPrice(dataset.price_cents)}
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">one-time</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handlePreview}
              className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-900 transition-colors"
            >
              <Eye className="w-3.5 h-3.5" />
              Preview
            </button>
            <button
              onClick={handlePurchase}
              className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
            >
              <ShoppingCart className="w-3.5 h-3.5" />
              Buy
            </button>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <DatasetPreview
          datasetId={dataset.id}
          datasetName={dataset.name}
          onClose={() => setShowPreview(false)}
          onCheckout={handlePurchase}
        />
      )}
    </>
  )
}
