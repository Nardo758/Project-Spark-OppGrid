import { X, CreditCard, Check, Loader2 } from 'lucide-react'
import { ReportType, REPORT_INFO } from './useReports'
import { useReportPayment } from './useReportPayment'

interface ReportPurchaseModalProps {
  isOpen: boolean
  onClose: () => void
  reportType: ReportType
  context: Record<string, unknown>
  onPurchaseComplete?: () => void
}

export function ReportPurchaseModal({
  isOpen,
  onClose,
  reportType,
  context,
  onPurchaseComplete,
}: ReportPurchaseModalProps) {
  const { initiatePayment, isProcessing, formatPrice, getReportPrice, checkTierAccess, userTier } = useReportPayment()

  if (!isOpen) return null

  const reportInfo = REPORT_INFO[reportType]
  const price = getReportPrice(reportType)
  const tierAccess = checkTierAccess(reportType)

  const handlePurchase = async () => {
    try {
      await initiatePayment(reportType, context)
      onPurchaseComplete?.()
    } catch (error) {
      console.error('Payment failed:', error)
    }
  }

  if (tierAccess.canGenerate) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl max-w-md w-full p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Generate Report</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg mb-4">
            <Check className="w-6 h-6 text-green-600" />
            <div>
              <p className="font-medium text-green-800">Included in your {userTier} plan</p>
              <p className="text-sm text-green-600">You can generate this report at no extra cost</p>
            </div>
          </div>
          <p className="text-gray-600 mb-4">{reportInfo?.description}</p>
          <button
            onClick={() => {
              onPurchaseComplete?.()
              onClose()
            }}
            className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg"
          >
            Generate {reportInfo?.name}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Unlock Report</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mb-6">
          <h4 className="font-semibold text-gray-900 mb-2">{reportInfo?.name}</h4>
          <p className="text-gray-600 text-sm">{reportInfo?.description}</p>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-gray-600">One-time purchase</span>
            <span className="text-2xl font-bold text-gray-900">{formatPrice(price)}</span>
          </div>
        </div>

        <div className="space-y-3 mb-6">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Check className="w-4 h-4 text-green-500" />
            <span>Instant access after payment</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Check className="w-4 h-4 text-green-500" />
            <span>Download as PDF</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Check className="w-4 h-4 text-green-500" />
            <span>Share with your team</span>
          </div>
        </div>

        <button
          onClick={handlePurchase}
          disabled={isProcessing}
          className="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white font-semibold rounded-lg flex items-center justify-center gap-2"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <CreditCard className="w-5 h-5" />
              Purchase for {formatPrice(price)}
            </>
          )}
        </button>

        <p className="text-xs text-gray-500 text-center mt-4">
          Or upgrade to {tierAccess.reason?.replace('Requires ', '')} to include this report
        </p>
      </div>
    </div>
  )
}
