import React from 'react'

interface RiskAssessmentProps {
  viability_report?: Record<string, any>
}

export default function RiskAssessment({ viability_report }: RiskAssessmentProps) {
  const risks = [
    {
      type: 'MARKET RISK',
      level: 'MEDIUM',
      likelihood: '25%',
      description: 'Market adoption plateau or economic downturn',
      mitigation: 'Diversify offerings, build corporate partnerships',
    },
    {
      type: 'EXECUTION RISK',
      level: 'LOW',
      likelihood: '15%',
      description: 'Operational challenges or talent recruitment',
      mitigation: 'Competitive compensation, remote flexibility, strong processes',
    },
    {
      type: 'COMPETITION RISK',
      level: 'MEDIUM',
      likelihood: '50%',
      description: 'Well-funded competitors entering market',
      mitigation: 'Local focus, niche positioning, community integration',
    },
    {
      type: 'REGULATORY RISK',
      level: 'MEDIUM-HIGH',
      likelihood: '50%',
      description: 'Licensing/compliance requirements evolving',
      mitigation: 'Early legal review, multi-state licensing strategy',
    },
  ]

  const getRiskColor = (level: string) => {
    if (level.includes('LOW')) return { bg: '#DCFCE7', border: '#0F6E56', text: '#15803D' }
    if (level.includes('MEDIUM')) return { bg: '#FEF3C7', border: '#BA7517', text: '#92400E' }
    return { bg: '#FEE2E2', border: '#CC3333', text: '#991B1B' }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        ⚠️ RISK ASSESSMENT
      </h2>

      {/* Risk Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
        {risks.map((risk, i) => {
          const color = getRiskColor(risk.level)
          return (
            <div key={i} style={{ background: color.bg, borderLeft: `4px solid ${color.border}`, padding: '12px', borderRadius: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: color.text }}>{risk.type}</div>
                <div style={{ fontSize: '10px', fontWeight: 600, color: color.text }}>
                  {risk.level} ({risk.likelihood})
                </div>
              </div>
              <p style={{ fontSize: '10px', color: color.text, margin: '0 0 6px 0' }}>{risk.description}</p>
              <div style={{ fontSize: '9px', color: color.text, opacity: 0.8 }}>
                Mitigation: {risk.mitigation}
              </div>
            </div>
          )
        })}
      </div>

      {/* Overall Risk Score */}
      <div style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px', marginTop: '12px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '4px' }}>OVERALL RISK SCORE</div>
        <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#BA7517', marginBottom: '4px' }}>6.2 / 10 (Moderate Risk)</div>
        <p style={{ fontSize: '10px', color: '#8B8B8B', margin: 0 }}>
          Manageable with proper planning, legal review, and market validation
        </p>
      </div>
    </div>
  )
}
