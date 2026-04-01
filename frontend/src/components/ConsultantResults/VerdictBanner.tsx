import { CheckCircle, AlertTriangle, XCircle, Globe, Store, Building2 } from 'lucide-react'

interface VerdictBannerProps {
  recommendation: string
  confidenceScore?: number
  verdictSummary?: string
  verdictDetail?: string
}

const recConfig: Record<string, { bg: string; border: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
  online: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: Globe },
  physical: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: Store },
  hybrid: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', icon: Building2 },
}

const verdictIcon = (score?: number) => {
  if (!score) return <AlertTriangle className="w-5 h-5 text-amber-500" />
  if (score >= 75) return <CheckCircle className="w-5 h-5 text-green-500" />
  if (score >= 50) return <AlertTriangle className="w-5 h-5 text-amber-500" />
  return <XCircle className="w-5 h-5 text-red-500" />
}

export default function VerdictBanner({
  recommendation,
  confidenceScore,
  verdictSummary,
  verdictDetail,
}: VerdictBannerProps) {
  const rec = recommendation?.toLowerCase() || 'hybrid'
  const config = recConfig[rec] || recConfig.hybrid
  const Icon = config.icon

  return (
    <div className={`${config.bg} ${config.border} border rounded-xl p-5`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg ${config.bg} flex items-center justify-center`}>
            <Icon className={`w-6 h-6 ${config.text}`} />
          </div>
          <div>
            <span className={`text-lg font-bold ${config.text}`}>
              {rec === 'online' ? 'Online Business' : rec === 'physical' ? 'Physical Business' : 'Hybrid Model'}
            </span>
            {verdictSummary && verdictSummary !== rec.toUpperCase() && (
              <span className={`ml-2 text-sm ${config.text} opacity-80`}>
                — {verdictSummary}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {verdictIcon(confidenceScore)}
          {confidenceScore && (
            <span className="text-sm font-semibold text-gray-700">{confidenceScore}% confidence</span>
          )}
        </div>
      </div>
      {verdictDetail && (
        <p className="text-sm text-gray-700 leading-relaxed">{verdictDetail}</p>
      )}
    </div>
  )
}
