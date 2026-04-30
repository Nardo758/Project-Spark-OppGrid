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
  opportunities: { bg: 'bg-purple-900/30', text: 'text-purple-300', icon: '💡' },
  markets: { bg: 'bg-blue-900/30', text: 'text-blue-300', icon: '📊' },
  trends: { bg: 'bg-green-900/30', text: 'text-green-300', icon: '📈' },
  raw_data: { bg: 'bg-orange-900/30', text: 'text-orange-300', icon: '📦' },
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
  const [isHovered, setIsHovered] = useState(false)

  const categoryColor = CATEGORY_COLORS[dataset.dataset_type] || CATEGORY_COLORS.raw_data
  const categoryLabel = CATEGORY_LABELS[dataset.dataset_type] || 'Data'

  const formatPrice = (cents: number) => {
    return `$${(cents / 100).toFixed(2)}`
  }

  const formatRecordCount = (count: number) => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M records`
    }
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K records`
    }
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
      <div
        className="h-full flex flex-col bg-gray-800 border border-gray-700 rounded-lg overflow-hidden hover:border-gray-600 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Header with Category Badge */}
        <div className="relative bg-gradient-to-r from-gray-700 to-gray-800 p-4 pb-6">
          <div className={`absolute top-4 right-4 ${categoryColor.bg} ${categoryColor.text} px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1`}>
            <span>{categoryColor.icon}</span>
            {categoryLabel}
          </div>
          
          {/* Title */}
          <h3 className="text-lg font-bold text-white pr-24 line-clamp-2">
            {dataset.name}
          </h3>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col p-4 space-y-3">
          {/* Description */}
          <p className="text-sm text-gray-300 line-clamp-2">
            {dataset.description || 'High-quality market intelligence dataset'}
          </p>

          {/* Metadata */}
          <div className="space-y-2 text-sm">
            {/* Record Count */}
            <div className="flex items-center gap-2 text-gray-400">
              <Database className="w-4 h-4" />
              <span>{formatRecordCount(dataset.record_count)}</span>
            </div>

            {/* Freshness */}
            <div className="flex items-center gap-2 text-gray-400">
              <TrendingUp className="w-4 h-4" />
              <span>Updated {formatFreshness(dataset.data_freshness)}</span>
            </div>

            {/* Location if available */}
            {(dataset.vertical || dataset.city) && (
              <div className="flex items-center gap-2 text-gray-400">
                <span className="text-xs">
                  {[dataset.vertical, dataset.city].filter(Boolean).join(' • ')}
                </span>
              </div>
            )}
          </div>

          {/* Rating (Optional) */}
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <Star
                key={i}
                className={`w-3 h-3 ${i < 4 ? 'fill-yellow-500 text-yellow-500' : 'text-gray-600'}`}
              />
            ))}
            <span className="text-xs text-gray-500 ml-1">(124 purchases)</span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Price */}
          <div className="border-t border-gray-700 pt-3">
            <div className="text-2xl font-bold text-white">
              {formatPrice(dataset.price_cents)}
            </div>
            <p className="text-xs text-gray-500">One-time purchase</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="border-t border-gray-700 p-4 space-y-2">
          <button
            onClick={handlePreview}
            className={`w-full flex items-center justify-center gap-2 py-2 rounded-lg font-medium transition-all duration-200 ${
              isHovered
                ? 'bg-gray-700 text-white'
                : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700 hover:text-white'
            }`}
          >
            <Eye className="w-4 h-4" />
            Preview
          </button>
          <button
            onClick={handlePurchase}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors"
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
