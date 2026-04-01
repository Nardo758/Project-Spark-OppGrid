import React from 'react'

interface FinancialViabilityProps {
  viability_report?: Record<string, any>
}

export default function FinancialViability({ viability_report }: FinancialViabilityProps) {
  const startupCostLow = viability_report?.startup_cost_low || 25000
  const startupCostHigh = viability_report?.startup_cost_high || 75000
  const timeToProfit = viability_report?.time_to_profitability || '12-18'
  const revenueRange = viability_report?.revenue_potential || 'Medium-High'
  const marginRange = viability_report?.margin_potential || '35-50%'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        💰 FINANCIAL VIABILITY
      </h2>

      {/* Startup Capital */}
      <div style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '4px' }}>STARTUP CAPITAL REQUIRED</div>
        <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#D97757' }}>
          ${(startupCostLow / 1000).toFixed(0)}K - ${(startupCostHigh / 1000).toFixed(0)}K
        </div>
        <div style={{ fontSize: '10px', color: '#8B8B8B', marginTop: '4px' }}>Low to moderate capital requirement</div>
      </div>

      {/* Key Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div style={{ background: '#F5F5F4', padding: '12px', borderRadius: '4px' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B', marginBottom: '4px' }}>Time to Profitability</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#D97757' }}>{timeToProfit} months</div>
          <div style={{ fontSize: '9px', color: '#8B8B8B', marginTop: '4px' }}>With steady ramp</div>
        </div>
        <div style={{ background: '#F5F5F4', padding: '12px', borderRadius: '4px' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B', marginBottom: '4px' }}>Breakeven Volume</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#0F6E56' }}>15-20 clients</div>
          <div style={{ fontSize: '9px', color: '#8B8B8B', marginTop: '4px' }}>Active, paying</div>
        </div>

        <div style={{ background: '#F5F5F4', padding: '12px', borderRadius: '4px' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B', marginBottom: '4px' }}>Revenue Potential</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#0F6E56' }}>{revenueRange}</div>
          <div style={{ fontSize: '9px', color: '#8B8B8B', marginTop: '4px' }}>With scale</div>
        </div>
        <div style={{ background: '#F5F5F4', padding: '12px', borderRadius: '4px' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B', marginBottom: '4px' }}>Margin Potential</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#0F6E56' }}>{marginRange}</div>
          <div style={{ fontSize: '9px', color: '#8B8B8B', marginTop: '4px' }}>Healthy for services</div>
        </div>
      </div>

      {/* Funding Options */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '8px' }}>FUNDING OPTIONS:</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {[
            { source: 'Founder Capital', time: 'Immediate' },
            { source: 'Small Business Loan', time: '6-8 weeks' },
            { source: 'Friends & Family', time: '4-12 weeks' },
            { source: 'Angel/VC', time: '3-6 months' },
          ].map((option, i) => (
            <div key={i} style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px', fontSize: '10px' }}>
              <div style={{ fontWeight: 600, color: '#1C1917' }}>{option.source}</div>
              <div style={{ color: '#8B8B8B', fontSize: '9px', marginTop: '2px' }}>{option.time}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
