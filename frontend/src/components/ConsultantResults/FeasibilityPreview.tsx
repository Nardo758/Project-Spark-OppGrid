import { DollarSign, Clock, TrendingUp } from 'lucide-react'
import BlurWall from './BlurWall'

interface FeasibilityPreviewProps {
  feasibilityPreview?: {
    market_size_estimate?: string
    capital_required?: number
    revenue_benchmark?: number
    time_to_breakeven?: string
    monthly_revenue_projection?: string
  }
  onUnlock?: () => void
}

export default function FeasibilityPreview({ feasibilityPreview, onUnlock }: FeasibilityPreviewProps) {
  if (!feasibilityPreview) return null

  const fp = feasibilityPreview

  return (
    <div>
      {/* Visible teaser row */}
      {fp.market_size_estimate && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-3">
          <div className="text-xs text-gray-500 mb-1">Estimated Market Size</div>
          <div className="text-lg font-bold text-gray-900">{fp.market_size_estimate}</div>
        </div>
      )}

      {/* Blurred premium data */}
      <BlurWall
        title="Unlock Financial Projections"
        description="Startup costs, breakeven timeline, and monthly revenue projections based on real market data."
        ctaText="Get Feasibility Report"
        price="$25"
        onUnlock={onUnlock}
      >
        <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
          <div className="text-center">
            <DollarSign className="w-6 h-6 text-green-500 mx-auto mb-1" />
            <div className="text-lg font-bold text-gray-900">$XX,XXX</div>
            <div className="text-xs text-gray-500">Startup Capital</div>
          </div>
          <div className="text-center">
            <Clock className="w-6 h-6 text-blue-500 mx-auto mb-1" />
            <div className="text-lg font-bold text-gray-900">X-X mo</div>
            <div className="text-xs text-gray-500">Breakeven</div>
          </div>
          <div className="text-center">
            <TrendingUp className="w-6 h-6 text-amber-500 mx-auto mb-1" />
            <div className="text-lg font-bold text-gray-900">$X,XXX</div>
            <div className="text-xs text-gray-500">Monthly Rev</div>
          </div>
        </div>
      </BlurWall>
    </div>
  )
}
