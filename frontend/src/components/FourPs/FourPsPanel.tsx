/**
 * FourPsPanel - Full expandable 4 P's panel for detail pages
 * 
 * Shows comprehensive PRODUCT, PRICE, PLACE, PROMOTION data
 * with expandable sections and quality indicators.
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Package, DollarSign, MapPin, Megaphone,
  ChevronDown, ChevronUp, AlertTriangle, CheckCircle2,
  TrendingUp, TrendingDown, Minus, Loader2, Info
} from 'lucide-react'

interface FourPsPanelProps {
  opportunityId: number
  showQuality?: boolean
  defaultExpanded?: boolean
  className?: string
}

interface PillarQuality {
  completeness: number
  confidence: number
}

interface DataQuality {
  completeness: number
  confidence: number
  report_readiness: number
  weakest_pillar: string | null
  recommended_actions: string[]
  pillar_quality: {
    product: PillarQuality
    price: PillarQuality
    place: PillarQuality
    promotion: PillarQuality
  }
}

interface FourPsData {
  opportunity_id: number
  city: string
  state: string
  business_type: string | null
  scores: {
    product: number
    price: number
    place: number
    promotion: number
  }
  overall: number
  product: Record<string, unknown>
  price: Record<string, unknown>
  place: Record<string, unknown>
  promotion: Record<string, unknown>
  data_quality: DataQuality
  fetched_at: string
}

const PILLAR_CONFIG = {
  product: {
    label: 'PRODUCT',
    title: 'Demand Validation',
    icon: Package,
    color: 'blue',
    fields: [
      { key: 'opportunity_score', label: 'Opportunity Score', format: 'score' },
      { key: 'pain_intensity', label: 'Pain Intensity', format: 'intensity' },
      { key: 'urgency_level', label: 'Urgency Level', format: 'level' },
      { key: 'trend_strength', label: 'Trend Strength', format: 'percent' },
      { key: 'target_audience', label: 'Target Audience', format: 'text' },
      { key: 'google_trends_interest', label: 'Search Interest', format: 'score' },
      { key: 'google_trends_direction', label: 'Trend Direction', format: 'direction' },
    ],
  },
  price: {
    label: 'PRICE',
    title: 'Market Economics',
    icon: DollarSign,
    color: 'emerald',
    fields: [
      { key: 'market_size_estimate', label: 'Market Size', format: 'text' },
      { key: 'median_income', label: 'Median Income', format: 'currency' },
      { key: 'addressable_market_value', label: 'Addressable Market', format: 'currency' },
      { key: 'income_growth_rate', label: 'Income Growth', format: 'percent' },
      { key: 'median_rent', label: 'Median Rent', format: 'currency' },
      { key: 'zillow_home_value', label: 'Home Value', format: 'currency' },
      { key: 'spending_power_index', label: 'Spending Power', format: 'score' },
    ],
  },
  place: {
    label: 'PLACE',
    title: 'Location Intelligence',
    icon: MapPin,
    color: 'amber',
    fields: [
      { key: 'growth_score', label: 'Growth Score', format: 'score' },
      { key: 'growth_category', label: 'Growth Category', format: 'text' },
      { key: 'population', label: 'Population', format: 'number' },
      { key: 'population_growth_rate', label: 'Population Growth', format: 'percent' },
      { key: 'job_growth_rate', label: 'Job Growth', format: 'percent' },
      { key: 'unemployment_rate', label: 'Unemployment', format: 'percent' },
      { key: 'job_postings_count', label: 'Job Postings', format: 'number' },
    ],
  },
  promotion: {
    label: 'PROMOTION',
    title: 'Competition & Reach',
    icon: Megaphone,
    color: 'purple',
    fields: [
      { key: 'competition_level', label: 'Competition Level', format: 'level' },
      { key: 'competitor_count', label: 'Competitor Count', format: 'number' },
      { key: 'avg_competitor_rating', label: 'Avg Competitor Rating', format: 'rating' },
      { key: 'competitive_advantages', label: 'Advantages', format: 'list' },
      { key: 'key_risks', label: 'Key Risks', format: 'list' },
      { key: 'success_factors', label: 'Success Factors', format: 'list' },
    ],
  },
}

function formatValue(value: unknown, format: string): string {
  if (value === null || value === undefined) return '—'
  
  switch (format) {
    case 'score':
      return `${value}/100`
    case 'intensity':
      return `${value}/10`
    case 'percent':
      return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : String(value)
    case 'currency':
      return typeof value === 'number' 
        ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
        : String(value)
    case 'number':
      return typeof value === 'number' 
        ? new Intl.NumberFormat('en-US').format(value)
        : String(value)
    case 'rating':
      return typeof value === 'number' ? `${value.toFixed(1)}★` : String(value)
    case 'level':
      return String(value).charAt(0).toUpperCase() + String(value).slice(1)
    case 'direction':
      return String(value).charAt(0).toUpperCase() + String(value).slice(1)
    case 'list':
      return Array.isArray(value) ? value.slice(0, 3).join(', ') : String(value)
    default:
      return String(value)
  }
}

function getScoreColor(score: number, color: string): string {
  if (score >= 75) return `bg-${color}-500`
  if (score >= 50) return `bg-${color}-400`
  if (score >= 25) return `bg-${color}-300`
  return 'bg-stone-300'
}

function ScoreRing({ score, color, size = 'md' }: { score: number; color: string; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-10 h-10 text-sm',
    md: 'w-14 h-14 text-lg',
    lg: 'w-20 h-20 text-2xl',
  }
  
  const circumference = 2 * Math.PI * 18
  const strokeDashoffset = circumference - (score / 100) * circumference
  
  const colorMap: Record<string, string> = {
    blue: '#3b82f6',
    emerald: '#10b981',
    amber: '#f59e0b',
    purple: '#8b5cf6',
  }

  return (
    <div className={`relative ${sizeClasses[size]} flex items-center justify-center`}>
      <svg className="absolute w-full h-full -rotate-90" viewBox="0 0 40 40">
        <circle
          cx="20"
          cy="20"
          r="18"
          fill="none"
          stroke="#e5e5e5"
          strokeWidth="3"
        />
        <circle
          cx="20"
          cy="20"
          r="18"
          fill="none"
          stroke={colorMap[color] || '#8b5cf6'}
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <span className="font-bold text-stone-900">{score}</span>
    </div>
  )
}

function PillarSection({
  pillarKey,
  data,
  score,
  quality,
  isExpanded,
  onToggle,
}: {
  pillarKey: 'product' | 'price' | 'place' | 'promotion'
  data: Record<string, unknown>
  score: number
  quality: PillarQuality
  isExpanded: boolean
  onToggle: () => void
}) {
  const config = PILLAR_CONFIG[pillarKey]
  const Icon = config.icon
  
  const bgColor = {
    blue: 'bg-blue-50 border-blue-200',
    emerald: 'bg-emerald-50 border-emerald-200',
    amber: 'bg-amber-50 border-amber-200',
    purple: 'bg-purple-50 border-purple-200',
  }[config.color]
  
  const textColor = {
    blue: 'text-blue-700',
    emerald: 'text-emerald-700',
    amber: 'text-amber-700',
    purple: 'text-purple-700',
  }[config.color]

  return (
    <div className={`rounded-xl border ${bgColor} overflow-hidden`}>
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between hover:bg-white/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <ScoreRing score={score} color={config.color} size="sm" />
          <div className="text-left">
            <div className="flex items-center gap-2">
              <Icon className={textColor} size={16} />
              <span className={`font-semibold ${textColor}`}>{config.label}</span>
            </div>
            <div className="text-xs text-stone-500">{config.title}</div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Quality indicator */}
          <div className="text-right text-xs">
            <div className="text-stone-500">
              {Math.round(quality.completeness * 100)}% data
            </div>
          </div>
          
          {isExpanded ? (
            <ChevronUp className="text-stone-400" size={20} />
          ) : (
            <ChevronDown className="text-stone-400" size={20} />
          )}
        </div>
      </button>
      
      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-white/50">
          <div className="grid grid-cols-2 gap-3">
            {config.fields.map((field) => {
              const value = data[field.key]
              if (value === null || value === undefined) return null
              
              return (
                <div key={field.key} className="bg-white/60 rounded-lg p-3">
                  <div className="text-xs text-stone-500 mb-1">{field.label}</div>
                  <div className="font-medium text-stone-900">
                    {formatValue(value, field.format)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default function FourPsPanel({
  opportunityId,
  showQuality = true,
  defaultExpanded = false,
  className = ''
}: FourPsPanelProps) {
  const [expandedPillars, setExpandedPillars] = useState<Set<string>>(
    defaultExpanded ? new Set(['product', 'price', 'place', 'promotion']) : new Set()
  )

  const { data, isLoading, error } = useQuery({
    queryKey: ['four-ps', opportunityId],
    queryFn: async (): Promise<FourPsData> => {
      const res = await fetch(`/api/v1/opportunities/${opportunityId}/four-ps`)
      if (!res.ok) throw new Error('Failed to fetch 4Ps data')
      return res.json()
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  const togglePillar = (pillar: string) => {
    setExpandedPillars((prev) => {
      const next = new Set(prev)
      if (next.has(pillar)) {
        next.delete(pillar)
      } else {
        next.add(pillar)
      }
      return next
    })
  }

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
        <span className="ml-2 text-stone-500">Loading market intelligence...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-xl p-4 ${className}`}>
        <div className="flex items-center gap-2 text-red-700">
          <AlertTriangle size={16} />
          <span>Failed to load 4 P's data</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header with overall score */}
      <div className="bg-stone-50 rounded-xl p-4 border border-stone-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-stone-900">4 P's Market Intelligence</h3>
            <p className="text-sm text-stone-500">
              {data.city}, {data.state} {data.business_type && `• ${data.business_type}`}
            </p>
          </div>
          <div className="text-center">
            <ScoreRing score={data.overall} color="purple" size="lg" />
            <div className="text-xs text-stone-500 mt-1">Overall</div>
          </div>
        </div>

        {/* Mini score bars */}
        <div className="grid grid-cols-4 gap-3">
          {(['product', 'price', 'place', 'promotion'] as const).map((pillar) => {
            const config = PILLAR_CONFIG[pillar]
            const score = data.scores[pillar]
            
            return (
              <div key={pillar} className="text-center">
                <div className="text-xs font-medium text-stone-500 mb-1">{config.label}</div>
                <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-${config.color}-500 rounded-full transition-all`}
                    style={{ width: `${score}%` }}
                  />
                </div>
                <div className="text-xs font-semibold text-stone-700 mt-1">{score}</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Quality summary (optional) */}
      {showQuality && data.data_quality && (
        <div className="bg-white rounded-xl border border-stone-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Info size={16} className="text-stone-400" />
              <span className="text-sm font-medium text-stone-700">Data Quality</span>
            </div>
            <div className={`text-sm font-semibold ${
              data.data_quality.report_readiness >= 0.7 ? 'text-emerald-600' :
              data.data_quality.report_readiness >= 0.5 ? 'text-amber-600' : 'text-red-600'
            }`}>
              {Math.round(data.data_quality.report_readiness * 100)}% Ready
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-stone-50 rounded p-2">
              <span className="text-stone-500">Completeness:</span>
              <span className="ml-1 font-medium">{Math.round(data.data_quality.completeness * 100)}%</span>
            </div>
            <div className="bg-stone-50 rounded p-2">
              <span className="text-stone-500">Confidence:</span>
              <span className="ml-1 font-medium">{Math.round(data.data_quality.confidence * 100)}%</span>
            </div>
          </div>
          
          {data.data_quality.weakest_pillar && (
            <div className="mt-2 text-xs text-amber-600 flex items-center gap-1">
              <AlertTriangle size={12} />
              <span>Weakest area: {data.data_quality.weakest_pillar.toUpperCase()}</span>
            </div>
          )}
        </div>
      )}

      {/* Pillar sections */}
      <div className="space-y-3">
        {(['product', 'price', 'place', 'promotion'] as const).map((pillar) => (
          <PillarSection
            key={pillar}
            pillarKey={pillar}
            data={data[pillar] as Record<string, unknown>}
            score={data.scores[pillar]}
            quality={data.data_quality.pillar_quality[pillar]}
            isExpanded={expandedPillars.has(pillar)}
            onToggle={() => togglePillar(pillar)}
          />
        ))}
      </div>

      {/* Recommendations */}
      {data.data_quality.recommended_actions.length > 0 && (
        <div className="bg-violet-50 rounded-xl border border-violet-200 p-4">
          <h4 className="text-sm font-medium text-violet-700 mb-2">💡 Recommendations</h4>
          <ul className="space-y-1">
            {data.data_quality.recommended_actions.map((action, i) => (
              <li key={i} className="text-xs text-violet-600 flex items-start gap-2">
                <span>•</span>
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Fetch timestamp */}
      <div className="text-xs text-stone-400 text-center">
        Last updated: {new Date(data.fetched_at).toLocaleString()}
      </div>
    </div>
  )
}
