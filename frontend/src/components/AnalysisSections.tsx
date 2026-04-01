import React from 'react'
import {
  BarChart3, TrendingUp, Zap, AlertTriangle, Target, Compass,
  CheckCircle, AlertCircle, ChevronDown, ChevronUp
} from 'lucide-react'

interface AnalysisSection {
  title: string
  content: any
  icon?: React.ComponentType<{ className?: string }>
}

interface CollapsibleSectionProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  children: React.ReactNode
  defaultOpen?: boolean
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  icon: Icon,
  color,
  children,
  defaultOpen = true
}) => {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors`}
        style={{ borderBottom: isOpen ? `2px solid ${color}` : 'none' }}
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5" style={{ color }} />
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>
      {isOpen && (
        <div className="px-6 py-6 space-y-4">
          {children}
        </div>
      )}
    </div>
  )
}

// Market Opportunity Section
export const MarketOpportunitySection: React.FC<{ data: any }> = ({ data }) => (
  <CollapsibleSection title={data.title} icon={TrendingUp} color="#3b82f6" defaultOpen>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-blue-50 rounded-lg p-4">
        <p className="text-xs text-blue-600 font-semibold">Market Size (TAM)</p>
        <p className="text-xl font-bold text-blue-900">{data.market_size}</p>
      </div>
      <div className="bg-green-50 rounded-lg p-4">
        <p className="text-xs text-green-600 font-semibold">Growth Trend</p>
        <p className="text-xl font-bold text-green-900">{data.growth_trend}</p>
      </div>
    </div>
    <div>
      <h4 className="font-semibold text-gray-900 mb-3">Market Insights</h4>
      <ul className="space-y-2">
        {data.market_insights?.map((insight: string, i: number) => (
          <li key={i} className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 mt-1 shrink-0" />
            <span className="text-sm text-gray-700">{insight}</span>
          </li>
        ))}
      </ul>
    </div>
    <div className="mt-4 p-3 bg-blue-100 rounded-lg">
      <p className="text-sm text-blue-900">
        <strong>Opportunity Score:</strong> {data.opportunity_score}/10
      </p>
    </div>
  </CollapsibleSection>
)

// Business Model Section
export const BusinessModelSection: React.FC<{ data: any }> = ({ data }) => (
  <CollapsibleSection title={data.title} icon={Zap} color="#8b5cf6" defaultOpen>
    <div>
      <h4 className="font-semibold text-gray-900 mb-2">Recommendation</h4>
      <p className="text-sm text-gray-700 mb-4">{data.recommendation_reason}</p>
    </div>

    <div className="grid md:grid-cols-3 gap-4 mb-6">
      <div className="border border-green-200 bg-green-50 rounded-lg p-4">
        <h5 className="text-xs font-semibold text-green-900 mb-2">✓ Pros</h5>
        <ul className="space-y-1">
          {data.pros?.slice(0, 3).map((pro: string, i: number) => (
            <li key={i} className="text-xs text-green-800">• {pro}</li>
          ))}
        </ul>
      </div>
      <div className="border border-red-200 bg-red-50 rounded-lg p-4">
        <h5 className="text-xs font-semibold text-red-900 mb-2">✗ Cons</h5>
        <ul className="space-y-1">
          {data.cons?.slice(0, 3).map((con: string, i: number) => (
            <li key={i} className="text-xs text-red-800">• {con}</li>
          ))}
        </ul>
      </div>
      <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
        <h5 className="text-xs font-semibold text-blue-900 mb-2">📊 Key Metrics</h5>
        <div className="space-y-1 text-xs text-blue-800">
          <p><strong>Startup:</strong> {data.startup_cost}</p>
          <p><strong>Timeline:</strong> {data.time_to_market}</p>
          <p><strong>Scale:</strong> {data.scalability}</p>
        </div>
      </div>
    </div>

    <div>
      <h4 className="font-semibold text-gray-900 mb-2">Key Success Factors</h4>
      <ul className="space-y-2">
        {data.key_success_factors?.map((factor: string, i: number) => (
          <li key={i} className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 mt-1 shrink-0" />
            <span className="text-sm text-gray-700">{factor}</span>
          </li>
        ))}
      </ul>
    </div>
  </CollapsibleSection>
)

// Financial Viability Section
export const FinancialViabilitySection: React.FC<{ data: any }> = ({ data }) => (
  <CollapsibleSection title={data.title} icon={BarChart3} color="#10b981" defaultOpen>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div>
        <p className="text-xs text-gray-500 font-semibold">Startup Cost</p>
        <p className="text-2xl font-bold text-gray-900">{data.startup_cost_range}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 font-semibold">Time to Profitability</p>
        <p className="text-2xl font-bold text-gray-900">{data.time_to_profitability}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 font-semibold">Revenue Potential</p>
        <p className="text-2xl font-bold text-gray-900">{data.annual_revenue_potential}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 font-semibold">Gross Margin</p>
        <p className="text-2xl font-bold text-gray-900">{data.gross_margin_expectation}</p>
      </div>
    </div>

    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
      <h4 className="font-semibold text-yellow-900 mb-3">Financial Milestones</h4>
      <ul className="space-y-2">
        {data.financial_milestones?.map((milestone: string, i: number) => (
          <li key={i} className="text-sm text-yellow-800">
            <strong>M{i + 3}:</strong> {milestone.replace(/Month \d+: /, '')}
          </li>
        ))}
      </ul>
    </div>

    <div>
      <h4 className="font-semibold text-gray-900 mb-3">Unit Economics</h4>
      <div className="space-y-2 text-sm">
        {Object.entries(data.unit_economics || {}).map(([key, value]) => (
          <div key={key} className="flex justify-between p-2 bg-gray-50 rounded">
            <span className="text-gray-600">{key.replace(/_/g, ' ').toUpperCase()}</span>
            <span className="font-semibold text-gray-900">{String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  </CollapsibleSection>
)

// Risk Assessment Section
export const RiskAssessmentSection: React.FC<{ data: any }> = ({ data }) => (
  <CollapsibleSection title={data.title} icon={AlertTriangle} color="#ef4444" defaultOpen>
    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
      <p className="text-lg font-bold text-red-900">{data.overall_risk_score}</p>
      <p className="text-sm text-red-800 mt-1">This is a manageable level of risk with proper mitigation strategies</p>
    </div>

    <div className="space-y-4">
      {Object.entries(data).map(([key, riskData]: [string, any]) => {
        if (!riskData.level || !riskData.factors) return null
        return (
          <div key={key} className="border-l-4 border-orange-300 bg-orange-50 p-4 rounded">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-orange-600" />
              <h4 className="font-semibold text-orange-900">{key.replace(/_/g, ' ').toUpperCase()}</h4>
              <span className="text-xs font-bold text-orange-700">{riskData.level}</span>
            </div>
            <ul className="space-y-1 mb-3">
              {riskData.factors?.slice(0, 2).map((factor: string, i: number) => (
                <li key={i} className="text-xs text-orange-800">• {factor}</li>
              ))}
            </ul>
            <p className="text-xs text-orange-700"><strong>Mitigation:</strong> {riskData.mitigation?.[0]}</p>
          </div>
        )
      })}
    </div>
  </CollapsibleSection>
)

// Next Steps Section
export const NextStepsSection: React.FC<{ data: any }> = ({ data }) => (
  <CollapsibleSection title={data.title} icon={Target} color="#f59e0b" defaultOpen>
    <div className="mb-6">
      <h4 className="font-semibold text-gray-900 mb-3">Immediate Actions (Next 2-4 Weeks)</h4>
      <div className="space-y-3">
        {data.immediate_actions?.map((action: any, i: number) => (
          <div key={i} className="border-l-4 border-blue-400 bg-blue-50 p-4 rounded">
            <div className="flex items-start justify-between mb-2">
              <h5 className="font-semibold text-gray-900">
                {action.step}. {action.title}
              </h5>
              <span className="text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-1 rounded">
                {action.timeline}
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-2">{action.description}</p>
            <p className="text-xs text-gray-600">
              <strong>Effort:</strong> {action.effort}
            </p>
          </div>
        ))}
      </div>
    </div>

    <div className="grid md:grid-cols-3 gap-4">
      <div className="bg-green-50 rounded-lg p-4 border border-green-200">
        <h5 className="font-semibold text-green-900 mb-2">30-Day Focus</h5>
        <ul className="text-xs text-green-800 space-y-1">
          {data['30_day_focus']?.slice(0, 3).map((item: string, i: number) => (
            <li key={i}>✓ {item}</li>
          ))}
        </ul>
      </div>
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h5 className="font-semibold text-blue-900 mb-2">90-Day Goals</h5>
        <ul className="text-xs text-blue-800 space-y-1">
          {data['90_day_goals']?.slice(0, 3).map((item: string, i: number) => (
            <li key={i}>→ {item}</li>
          ))}
        </ul>
      </div>
      <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
        <h5 className="font-semibold text-purple-900 mb-2">6-Month Goals</h5>
        <ul className="text-xs text-purple-800 space-y-1">
          {data['6_month_milestones']?.slice(0, 3).map((item: string, i: number) => (
            <li key={i}>🚀 {item}</li>
          ))}
        </ul>
      </div>
    </div>
  </CollapsibleSection>
)

// Competitive Landscape Section
export const CompetitiveSection: React.FC<{ data: any }> = ({ data }) => (
  <CollapsibleSection title={data.title} icon={Compass} color="#6366f1">
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-red-50 rounded-lg p-4 border border-red-200">
        <p className="text-xs text-red-600 font-semibold">Direct Competitors</p>
        <p className="text-3xl font-bold text-red-900">{data.direct_competitors}</p>
      </div>
      <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
        <p className="text-xs text-orange-600 font-semibold">Indirect Competitors</p>
        <p className="text-3xl font-bold text-orange-900">{data.indirect_competitors}</p>
      </div>
    </div>

    <div>
      <h4 className="font-semibold text-gray-900 mb-3">Differentiation Opportunities</h4>
      <ul className="space-y-2">
        {data.differentiation_strategy?.map((strategy: string, i: number) => (
          <li key={i} className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-blue-600 mt-1 shrink-0" />
            <span className="text-sm text-gray-700">{strategy}</span>
          </li>
        ))}
      </ul>
    </div>

    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
      <h5 className="font-semibold text-gray-900 mb-3">Competitive Advantage Checklist</h5>
      <div className="space-y-2 text-sm">
        {Object.entries(data.competitive_advantage_checklist || {}).map(([key, status]) => (
          <div key={key} className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-gray-400" />
            <span className="text-gray-700 flex-1">{key.replace(/_/g, ' ').toUpperCase()}</span>
            <span className="text-xs font-semibold text-gray-600">{String(status)}</span>
          </div>
        ))}
      </div>
    </div>
  </CollapsibleSection>
)

export default {
  CollapsibleSection,
  MarketOpportunitySection,
  BusinessModelSection,
  FinancialViabilitySection,
  RiskAssessmentSection,
  NextStepsSection,
  CompetitiveSection,
}
