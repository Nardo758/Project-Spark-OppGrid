import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ShoppingCart, 
  Check, 
  Download, 
  AlertCircle, 
  Clock,
  Lock,
  Database
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

interface Dataset {
  id: string
  name: string
  description: string
  dataset_type: string
  vertical?: string | null
  city?: string | null
  price_cents: number
  record_count: number
  data_freshness: string
}

interface PurchaseResponse {
  purchase_id: string
  dataset_id: string
  download_url: string
  expires_at: string
  status: string
}

const TERMS_OF_USE = `
1. License Grant
You are granted a non-exclusive, non-transferable license to use this dataset for your internal business purposes only.

2. Restrictions
- You may not resell, redistribute, or share the dataset with third parties
- You may not use the dataset for commercial services without explicit permission
- You may not reverse engineer or derive competitive datasets from this data

3. Data Accuracy
While we strive for accuracy, this dataset is provided "as-is" without warranties. We are not responsible for decisions made based on this data.

4. Expiration
Download access expires 30 days after purchase. After expiration, you will not be able to download the dataset.

5. Support
For data questions or technical support, contact our team at support@oppgrid.com
`

export default function DatasetCheckout() {
  const { datasetId } = useParams<{ datasetId: string }>()
  const navigate = useNavigate()
  const { token, isAuthenticated } = useAuthStore()
  const [agreeToTerms, setAgreeToTerms] = useState(false)
  const [showTermsModal, setShowTermsModal] = useState(false)
  const [purchaseComplete, setPurchaseComplete] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState('')
  const [expiresAt, setExpiresAt] = useState('')

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/signin')
    }
  }, [isAuthenticated, navigate])

  // Fetch dataset details
  const { data: dataset, isLoading, error } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: async (): Promise<Dataset> => {
      const res = await fetch(`/api/v1/datasets/${datasetId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok) throw new Error('Failed to load dataset')
      return res.json()
    },
    enabled: !!datasetId && !!token,
  })

  // Purchase mutation
  const purchaseMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/v1/datasets/${datasetId}/purchase`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          payment_method: 'stripe', // Will be integrated later
        }),
      })
      if (!res.ok) throw new Error('Failed to complete purchase')
      return (await res.json()) as PurchaseResponse
    },
    onSuccess: (data) => {
      setPurchaseComplete(true)
      setDownloadUrl(data.download_url)
      setExpiresAt(data.expires_at)
    },
  })

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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-gray-700 border-t-blue-500 rounded-full animate-spin mx-auto" />
          <p className="text-gray-400 mt-4">Loading checkout...</p>
        </div>
      </div>
    )
  }

  if (error || !dataset) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 py-12">
        <div className="max-w-2xl mx-auto px-4">
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 text-red-300">
            <h1 className="font-semibold text-lg">Failed to Load Dataset</h1>
            <p className="mt-2">Please try again or return to the marketplace.</p>
            <button
              onClick={() => navigate('/marketplace')}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Back to Marketplace
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 border-b border-gray-700 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <ShoppingCart className="w-8 h-8 text-blue-400" />
            <h1 className="text-3xl font-bold text-white">Checkout</h1>
          </div>
          <p className="text-gray-400 mt-2">Complete your dataset purchase</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="md:col-span-2 space-y-6">
            {/* Order Summary */}
            {!purchaseComplete && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <h2 className="text-xl font-bold text-white mb-4">Order Summary</h2>
                <div className="space-y-4">
                  {/* Dataset Info */}
                  <div className="flex gap-4 pb-4 border-b border-gray-700">
                    <div className="flex-1">
                      <h3 className="font-semibold text-white">{dataset.name}</h3>
                      <p className="text-sm text-gray-400 mt-1">{dataset.description}</p>
                      <div className="flex gap-4 mt-3 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Database className="w-3 h-3" />
                          {formatRecordCount(dataset.record_count)}
                        </span>
                        {dataset.vertical && <span>{dataset.vertical}</span>}
                        {dataset.city && <span>{dataset.city}</span>}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white">
                        {formatPrice(dataset.price_cents)}
                      </div>
                      <p className="text-xs text-gray-400 mt-1">One-time purchase</p>
                    </div>
                  </div>

                  {/* Pricing Breakdown */}
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Subtotal</span>
                      <span className="text-white font-medium">{formatPrice(dataset.price_cents)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Tax</span>
                      <span className="text-white font-medium">Calculated at checkout</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Terms Section */}
            {!purchaseComplete && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <h2 className="text-lg font-bold text-white mb-4">Terms of Use</h2>
                <div className="bg-gray-900 rounded p-4 h-40 overflow-y-auto text-sm text-gray-400 mb-4 border border-gray-700">
                  {TERMS_OF_USE}
                </div>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={agreeToTerms}
                    onChange={(e) => setAgreeToTerms(e.target.checked)}
                    className="w-5 h-5 mt-1 rounded accent-blue-600"
                  />
                  <span className="text-sm text-gray-300">
                    I agree to the{' '}
                    <button
                      onClick={() => setShowTermsModal(true)}
                      className="text-blue-400 hover:text-blue-300 underline"
                    >
                      terms of use
                    </button>
                  </span>
                </label>
              </div>
            )}

            {/* Payment Section */}
            {!purchaseComplete && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
                <h2 className="text-lg font-bold text-white mb-4">Payment Method</h2>
                <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 mb-4 flex items-center gap-3">
                  <Lock className="w-5 h-5 text-green-400" />
                  <div>
                    <p className="text-sm font-medium text-white">Secure Stripe Payment</p>
                    <p className="text-xs text-gray-400">Your payment information is encrypted and secure</p>
                  </div>
                </div>
              </div>
            )}

            {/* Success State */}
            {purchaseComplete && (
              <div className="bg-green-900/20 border border-green-800 rounded-lg p-8 text-center">
                <div className="flex justify-center mb-4">
                  <div className="bg-green-500 rounded-full p-3">
                    <Check className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-green-400 mb-2">Purchase Complete!</h2>
                <p className="text-green-300 mb-6">
                  Your dataset is ready to download. Access expires on{' '}
                  <span className="font-semibold">{formatDate(expiresAt)}</span>
                </p>
                <div className="bg-gray-800 rounded-lg p-4 mb-6 text-left">
                  <h3 className="font-semibold text-white mb-2">Download Information</h3>
                  <ul className="text-sm text-gray-300 space-y-1">
                    <li>✓ Dataset: {dataset.name}</li>
                    <li>✓ Records: {formatRecordCount(dataset.record_count)}</li>
                    <li>✓ Format: CSV</li>
                    <li>✓ Expires: {formatDate(expiresAt)}</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div>
            {/* Purchase Button */}
            {!purchaseComplete && (
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 sticky top-20">
                <div className="mb-6">
                  <p className="text-sm text-gray-400 mb-1">Total Price</p>
                  <div className="text-3xl font-bold text-white">
                    {formatPrice(dataset.price_cents)}
                  </div>
                </div>

                <button
                  onClick={() => purchaseMutation.mutate()}
                  disabled={!agreeToTerms || purchaseMutation.isPending}
                  className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors mb-3 ${
                    agreeToTerms && !purchaseMutation.isPending
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {purchaseMutation.isPending ? (
                    <>
                      <div className="w-4 h-4 border-2 border-blue-300 border-t-white rounded-full animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <ShoppingCart className="w-5 h-5" />
                      Complete Purchase
                    </>
                  )}
                </button>

                {purchaseMutation.error && (
                  <div className="bg-red-900/20 border border-red-800 rounded p-3 text-sm text-red-300">
                    {purchaseMutation.error.message}
                  </div>
                )}

                <button
                  onClick={() => navigate('/marketplace')}
                  className="w-full py-2 text-gray-300 hover:text-white text-sm font-medium"
                >
                  Continue Shopping
                </button>

                {/* Trust Badges */}
                <div className="mt-6 space-y-3 border-t border-gray-700 pt-6">
                  <div className="flex items-start gap-2 text-xs text-gray-400">
                    <Lock className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                    <span>256-bit SSL encryption</span>
                  </div>
                  <div className="flex items-start gap-2 text-xs text-gray-400">
                    <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                    <span>Instant download</span>
                  </div>
                  <div className="flex items-start gap-2 text-xs text-gray-400">
                    <Clock className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                    <span>30-day access window</span>
                  </div>
                </div>
              </div>
            )}

            {/* Success Sidebar */}
            {purchaseComplete && (
              <div className="bg-green-900/20 border border-green-800 rounded-lg p-6">
                <h3 className="font-semibold text-green-300 mb-4">What's Next?</h3>
                <a
                  href={downloadUrl}
                  className="block w-full mb-3 py-3 rounded-lg font-semibold text-white bg-green-600 hover:bg-green-700 transition-colors text-center flex items-center justify-center gap-2"
                >
                  <Download className="w-5 h-5" />
                  Download Dataset
                </a>
                <button
                  onClick={() => navigate('/marketplace')}
                  className="block w-full py-2 text-green-300 hover:text-green-200 text-sm font-medium"
                >
                  Browse More Datasets
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Terms Modal */}
      {showTermsModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-lg shadow-2xl max-w-2xl w-full border border-gray-700">
            <div className="p-6 border-b border-gray-700 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Terms of Use</h2>
              <button
                onClick={() => setShowTermsModal(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="p-6 max-h-96 overflow-y-auto text-gray-300 text-sm whitespace-pre-wrap">
              {TERMS_OF_USE}
            </div>
            <div className="p-6 border-t border-gray-700">
              <button
                onClick={() => setShowTermsModal(false)}
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
