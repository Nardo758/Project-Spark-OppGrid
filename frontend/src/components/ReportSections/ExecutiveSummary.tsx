import React from 'react'

interface ExecutiveSummaryProps {
  verdict_summary?: string
  verdict_detail?: string
  recommendation?: string
  confidence_score?: number
  viability_report?: Record<string, any>
}

export default function ExecutiveSummary({
  verdict_summary,
  verdict_detail,
  recommendation,
  confidence_score,
  viability_report,
}: ExecutiveSummaryProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        EXECUTIVE SUMMARY
      </h2>

      {/* Main Verdict */}
      <div style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px' }}>
        <p style={{ fontSize: '11px', lineHeight: '1.6', color: '#4B5563', margin: 0 }}>
          {verdict_summary ||
            viability_report?.summary ||
            `This ${recommendation} business model shows ${confidence_score}% confidence potential. The market opportunity is significant with manageable risks. Proceed with validation phase to confirm market demand and competitive positioning.`}
        </p>
      </div>

      {/* Supporting Detail */}
      {verdict_detail && (
        <p style={{ fontSize: '11px', lineHeight: '1.6', color: '#4B5563', margin: '8px 0 0 0' }}>
          {verdict_detail}
        </p>
      )}

      {/* Key Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginTop: '12px' }}>
        <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Recommendation</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#D97757', marginTop: '4px' }}>
            {recommendation?.toUpperCase()}
          </div>
        </div>
        <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Confidence</div>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#0F6E56', marginTop: '4px' }}>
            {confidence_score}%
          </div>
        </div>
        <div style={{ background: '#F5F5F4', padding: '8px', borderRadius: '4px', textAlign: 'center' }}>
          <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Verdict</div>
          <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#0F6E56', marginTop: '4px' }}>
            PROCEED
          </div>
        </div>
      </div>
    </div>
  )
}
