import { useState } from 'react'
import { ChevronDown, Lock, Sparkles, DollarSign, CheckCircle } from 'lucide-react'
import { useStudioReportCheckout } from '../hooks/useStudioReportCheckout'
import { useAuthStore } from '../stores/authStore'

interface StudioReportButtonProps {
  reportType: string
  reportName: string
  description?: string
  priceCents: number
  isIncluded?: boolean
  isPurchased?: boolean
  isLoading?: boolean
  disabled?: boolean
  onClick?: () => void
  reportContext?: Record<string, any>
  guestEmail?: string
  compact?: boolean
}

const formatPrice = (cents: number): string => {
  return `$${(cents / 100).toFixed(0)}`
}

export default function StudioReportButton({
  reportType,
  reportName,
  description,
  priceCents,
  isIncluded = false,
  isPurchased = false,
  isLoading = false,
  disabled = false,
  onClick,
  reportContext,
  guestEmail,
  compact = false,
}: StudioReportButtonProps) {
  const { token } = useAuthStore()
  const [showDropdown, setShowDropdown] = useState(false)
  const { startCheckout, loading: checkoutLoading, error: checkoutError } = useStudioReportCheckout()

  const price = formatPrice(priceCents)
  const canCheckout = !isIncluded && !isPurchased && !isLoading && !checkoutLoading
  const isCheckingOut = checkoutLoading

  const handleCheckout = async () => {
    try {
      setShowDropdown(false)
      await startCheckout(reportType, reportContext, guestEmail)
    } catch (e) {
      console.error('Checkout failed:', e)
    }
  }

  if (compact) {
    return (
      <div className="relative inline-block">
        <button
          onClick={onClick || (canCheckout ? () => setShowDropdown(!showDropdown) : undefined)}
          disabled={disabled || isLoading || checkoutLoading}
          className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isIncluded
              ? 'bg-green-50 text-green-700 border border-green-200'
              : isPurchased
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : canCheckout
                  ? 'bg-stone-100 text-stone-900 border border-stone-200 hover:bg-stone-200'
                  : 'bg-stone-50 text-stone-500 border border-stone-200 cursor-not-allowed'
          }`}
        >
          {isIncluded && <CheckCircle className="w-4 h-4" />}
          {isPurchased && <CheckCircle className="w-4 h-4" />}
          {!isIncluded && !isPurchased && (
            <>
              <DollarSign className="w-4 h-4" />
              <span>{price}</span>
            </>
          )}
          {isIncluded && <span>Included</span>}
          {isPurchased && <span>Purchased</span>}
        </button>

        {/* Dropdown menu for compact mode */}
        {showDropdown && canCheckout && (
          <div className="absolute right-0 mt-2 w-48 bg-white border border-stone-200 rounded-lg shadow-lg z-10 p-3">
            <p className="text-xs text-stone-600 mb-3">{reportName}</p>
            {description && <p className="text-xs text-stone-500 mb-3">{description}</p>}
            <button
              onClick={handleCheckout}
              disabled={isCheckingOut}
              className="w-full bg-stone-900 text-white py-2 rounded-lg text-sm font-medium hover:bg-stone-800 disabled:opacity-50"
            >
              {isCheckingOut ? 'Processing...' : `Get Now — ${price}`}
            </button>
            {checkoutError && <p className="text-xs text-red-600 mt-2">{checkoutError}</p>}
          </div>
        )}
      </div>
    )
  }

  // Full-size button
  return (
    <div className="relative">
      <button
        onClick={onClick || (canCheckout ? () => setShowDropdown(!showDropdown) : undefined)}
        disabled={disabled || isLoading || checkoutLoading}
        className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border transition-all ${
          isIncluded
            ? 'bg-green-50 border-green-200 text-green-900 hover:bg-green-100'
            : isPurchased
              ? 'bg-blue-50 border-blue-200 text-blue-900 hover:bg-blue-100'
              : canCheckout
                ? 'bg-white border-stone-200 text-stone-900 hover:bg-stone-50 hover:border-stone-300'
                : 'bg-stone-50 border-stone-200 text-stone-500 cursor-not-allowed'
        }`}
      >
        <div className="flex items-start gap-3">
          <div className="mt-1">
            {isIncluded ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : isPurchased ? (
              <CheckCircle className="w-5 h-5 text-blue-600" />
            ) : canCheckout ? (
              <DollarSign className="w-5 h-5 text-amber-600" />
            ) : (
              <Lock className="w-5 h-5 text-stone-400" />
            )}
          </div>
          <div className="text-left">
            <h4 className="font-semibold text-sm">{reportName}</h4>
            {description && <p className="text-xs text-stone-600 mt-1">{description}</p>}
          </div>
        </div>

        <div className="flex items-center gap-3 ml-4 flex-shrink-0">
          {isIncluded && <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded">Included</span>}
          {isPurchased && <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-1 rounded">✓ Purchased</span>}
          {!isIncluded && !isPurchased && (
            <>
              <span className="text-lg font-bold text-amber-600">{price}</span>
              {canCheckout && <ChevronDown className={`w-5 h-5 text-stone-400 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />}
            </>
          )}
        </div>
      </button>

      {/* Checkout dropdown */}
      {showDropdown && canCheckout && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-stone-200 rounded-lg shadow-lg z-10 p-4">
          <div className="space-y-3">
            {description && <p className="text-sm text-stone-600">{description}</p>}

            <button
              onClick={handleCheckout}
              disabled={isCheckingOut}
              className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors ${
                isCheckingOut
                  ? 'bg-stone-300 text-stone-600 cursor-not-allowed'
                  : 'bg-amber-600 text-white hover:bg-amber-700'
              }`}
            >
              {isCheckingOut ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Get Now — {price}
                </>
              )}
            </button>

            {!token && (
              <p className="text-xs text-stone-600 text-center">
                Sign in to save your reports for later
              </p>
            )}

            {checkoutError && (
              <div className="bg-red-50 border border-red-200 rounded p-3">
                <p className="text-sm text-red-700">{checkoutError}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
