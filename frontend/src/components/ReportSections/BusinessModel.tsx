import React from 'react'

interface BusinessModelProps {
  recommendation?: string
  advantages?: string[]
  risks?: string[]
  viability_report?: Record<string, any>
}

export default function BusinessModel({ recommendation, advantages = [], risks = [], viability_report }: BusinessModelProps) {
  const successFactors = viability_report?.strengths || advantages.slice(0, 4) || [
    'Licensed/credentialed professionals',
    'Strong brand positioning',
    'Efficient operations',
    'Customer retention focus',
  ]

  const pitfalls = viability_report?.weaknesses || risks.slice(0, 4) || [
    'Regulatory compliance complexity',
    'High customer acquisition cost',
    'Talent retention challenges',
    'Market saturation risk',
  ]

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        💼 BUSINESS MODEL
      </h2>

      {/* Recommendation */}
      <div style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '4px' }}>
          RECOMMENDED: {recommendation?.toUpperCase()}
        </div>
        <p style={{ fontSize: '10px', lineHeight: '1.5', color: '#4B5563', margin: '4px 0 0 0' }}>
          This model balances {recommendation?.toLowerCase()} characteristics to maximize market reach while maintaining customer trust and operational efficiency.
        </p>
      </div>

      {/* Success Factors */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '8px' }}>✓ KEY SUCCESS FACTORS:</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {successFactors.map((factor, i) => (
            <div key={i} style={{ background: '#DCFCE7', borderRadius: '4px', padding: '8px', fontSize: '10px', color: '#15803D' }}>
              ✓ {factor}
            </div>
          ))}
        </div>
      </div>

      {/* Pitfalls */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '8px' }}>⚠ PITFALLS TO AVOID:</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          {pitfalls.map((pitfall, i) => (
            <div key={i} style={{ background: '#FEE2E2', borderRadius: '4px', padding: '8px', fontSize: '10px', color: '#991B1B' }}>
              ✗ {pitfall}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
