import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, ShoppingCart, Star, TrendingUp, Database } from 'lucide-react'
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

  const formatPrice = (cents: number) => `$${(cents / 100).toFixed(2)}`

  const formatRecordCount = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M records`
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K records`
    return `${count} records`
  }

  const formatFreshness = (freshness: string) => {
    const now = new Date()
    const dataDate = new Date(freshness)
    const diffMs = now.getTime() - dataDate.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffHours < 1) return 'Just now'
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
      <div className="h-full flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg hover:border-gray-300 transition-all duration-200">
        {/* Header with Category Badge */}
        <div className="relative p-4 pb-4 border-b border-gray-100">
          <div className={`absolute top-4 right-4 ${categoryColor.bg} ${categoryColor.text} px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1`}>
            <span>{categoryColor.icon}</span>
            {categoryLabel}
          </div>
          <h3 className="text-lg font-semibold text-gray-900 pr-24 line-clamp-2">
            {dataset.name}
          </h3>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col p-4 space-y-3">
          <p className="text-sm text-gray-600 line-clamp-2">
            {dataset.description || 'High-quality market intelligence dataset'}
          </p>

          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-gray-600">
              <Database className="w-4 h-4" />
              <span>{formatRecordCount(dataset.record_count)}</span>
            </div>

            <div className="flex items-center gap-2 text-gray-600">
              <TrendingUp className="w-4 h-4" />
              <span>Updated {formatFreshness(dataset.data_freshness)}</span>
            </div>

            {(dataset.vertical || dataset.city) && (
              <div className="flex items-center gap-2 text-gray-500">
                <span className="text-xs">
                  {[dataset.vertical, dataset.city].filter(Boolean).join(' • ')}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={`w-3 h-3 ${i < 4 ? 'fill-amber-500 text-amber-500' : 'text-gray-300'}`}
              />
            ))}
            <span className="text-xs text-gray-500 ml-1">(124 purchases)</span>
          </div>

          <div className="flex-1" />

          <div className="border-t border-gray-100 pt-3">
            <div className="text-2xl font-bold text-gray-900">
              {formatPrice(dataset.price_cents)}
            </div>
            <p className="text-xs text-gray-500">One-time purchase</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="border-t border-gray-100 p-4 space-y-2">
          <button
            onClick={handlePreview}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg font-medium bg-gray-100 hover:bg-gray-200 text-gray-900 transition-colors"
          >
            <Eye className="w-4 h-4" />
            Preview
          </button>
          <button
            onClick={handlePurchase}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg font-medium bg-black hover:bg-gray-800 text-white transition-colors"
          >
            <ShoppingCart className="w-4 h-4" />
            Purchase
          </button>
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
