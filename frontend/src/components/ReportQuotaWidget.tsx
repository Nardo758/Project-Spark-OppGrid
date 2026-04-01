import { useReportQuota } from '../hooks/useReportQuota'
import { Zap, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

interface ReportQuotaWidgetProps {
  className?: string
  compact?: boolean
}

export default function ReportQuotaWidget({
  className = '',
  compact = false,
}: ReportQuotaWidgetProps) {
  const { token } = useAuthStore()
  const { quota, isLoading, remainingFree, usagePercent, tier } = useReportQuota()

  // Don't show if not authenticated
  if (!token) {
    return null
  }

  if (isLoading) {
    return (
      <div className={`bg-stone-50 border border-stone-200 rounded-lg p-4 ${className}`}>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-stone-300 rounded-full animate-pulse" />
          <span className="text-sm text-stone-600">Loading quota...</span>
        </div>
      </div>
    )
  }

  if (!quota) {
    return null
  }

  const isNearLimit = usagePercent >= 75
  const isAtLimit = usagePercent >= 100

  if (compact) {
    return (
      <div className={`flex items-center gap-2 text-xs ${className}`}>
        <Zap className={`w-4 h-4 ${isAtLimit ? 'text-red-500' : isNearLimit ? 'text-amber-500' : 'text-green-500'}`} />
        <span className="font-medium">
          {remainingFree > 0 ? `${remainingFree} free left` : 'Quota full'}
        </span>
      </div>
    )
  }

  return (
    <div className={`bg-gradient-to-br from-stone-50 to-stone-100 border border-stone-200 rounded-lg p-5 ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-amber-600" />
          <h3 className="font-semibold text-stone-900">Report Usage</h3>
        </div>
        <span className="text-xs font-medium px-2 py-1 bg-stone-200 text-stone-700 rounded">
          {tier.charAt(0).toUpperCase() + tier.slice(1)} Plan
        </span>
      </div>

      {/* Usage bar */}
      <div className="mb-3">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-stone-600">
            {quota.total_generated_this_month} / {quota.free_allocation + quota.paid_report_count} generated
          </span>
          <span className="text-xs font-medium text-stone-700">{Math.round(usagePercent)}%</span>
        </div>
        <div className="w-full bg-stone-200 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full transition-all ${
              isAtLimit ? 'bg-red-500' : isNearLimit ? 'bg-amber-500' : 'bg-green-500'
            }`}
            style={{ width: `${Math.min(usagePercent, 100)}%` }}
          />
        </div>
      </div>

      {/* Free allocation info */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-600" />
          <span className="text-xs text-stone-700">
            <span className="font-medium">{quota.free_allocation}</span> free reports per month
          </span>
        </div>
        {remainingFree > 0 && (
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span className="text-xs text-stone-700">
              <span className="font-medium">{remainingFree}</span> free reports remaining
            </span>
          </div>
        )}
        {quota.paid_report_count > 0 && (
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-600" />
            <span className="text-xs text-stone-700">
              <span className="font-medium">{quota.paid_report_count}</span> paid reports purchased
            </span>
          </div>
        )}
      </div>

      {/* Warning messages */}
      {isAtLimit && (
        <div className="bg-red-50 border border-red-200 rounded p-3 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-medium text-red-900 mb-1">Quota reached</p>
            <p className="text-xs text-red-700">
              Generate unlimited reports by purchasing additional reports or upgrading your plan.
            </p>
          </div>
        </div>
      )}

      {isNearLimit && !isAtLimit && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-medium text-amber-900 mb-1">Approaching quota limit</p>
            <p className="text-xs text-amber-700">
              You have {remainingFree} free reports remaining this month.
            </p>
          </div>
        </div>
      )}

      {/* Next reset info */}
      <div className="mt-4 pt-4 border-t border-stone-200">
        <p className="text-xs text-stone-600">
          Quota resets on <span className="font-medium">{quota.next_reset_date}</span>
        </p>
      </div>
    </div>
  )
}
