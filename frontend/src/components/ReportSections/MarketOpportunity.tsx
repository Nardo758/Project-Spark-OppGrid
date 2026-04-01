import React from 'react'

interface MarketOpportunityProps {
  market_intelligence?: Record<string, any>
  viability_report?: Record<string, any>
}

export default function MarketOpportunity({ market_intelligence, viability_report }: MarketOpportunityProps) {
  const marketSize = market_intelligence?.market_size || viability_report?.market_size || 'N/A'
  const growth = market_intelligence?.growth_trend || viability_report?.growth || 'N/A'
  const saturation = market_intelligence?.saturation || 'MEDIUM'
  const population = market_intelligence?.population
  const medianIncome = market_intelligence?.median_income
  const competitors = market_intelligence?.competitor_count || 0

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        📊 MARKET OPPORTUNITY
      </h2>

      {/* Market Size */}
      <div style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '4px' }}>Market Size</div>
        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#D97757' }}>
          {typeof marketSize === 'string' ? marketSize : `$${marketSize}B - $${marketSize}B`}
        </div>
        <div style={{ fontSize: '10px', color: '#8B8B8B', marginTop: '4px' }}>
          Growth: {growth}
        </div>
      </div>

      {/* Demographics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {population && (
          <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px' }}>
            <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Population</div>
            <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#1C1917', marginTop: '4px' }}>
              {(population / 1000000).toFixed(1)}M
            </div>
          </div>
        )}
        {medianIncome && (
          <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px' }}>
            <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Median Income</div>
            <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#1C1917', marginTop: '4px' }}>
              ${(medianIncome / 1000).toFixed(0)}K
            </div>
          </div>
        )}
        <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Saturation</div>
          <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#BA7517', marginTop: '4px' }}>
            {saturation}
          </div>
        </div>
        <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Competitors</div>
          <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#BA7517', marginTop: '4px' }}>
            {competitors}+
          </div>
        </div>
      </div>

      {/* Description */}
      <p style={{ fontSize: '11px', lineHeight: '1.6', color: '#4B5563', margin: '12px 0 0 0' }}>
        The market demonstrates significant growth potential with clear demand signals. Competition exists but opportunity remains for differentiated positioning.
      </p>
    </div>
  )
}
