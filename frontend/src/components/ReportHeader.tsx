import React from 'react'

interface ReportHeaderProps {
  reportName: string           // e.g., "Validate Idea Analysis"
  subject: string              // e.g., "Mental Health Clinic"
  reportId: string             // e.g., "REPT-2026-04-01-001"
  reportDate: string           // e.g., "April 1, 2026"
  generatedAt: string          // e.g., "7:07 AM PT"
  recommendation: string       // e.g., "HYBRID"
  confidenceScore: number      // 0-100
  riskScore: number            // 0-10
  verdict: 'proceed' | 'proceed_with_caution' | 'do_not_proceed'
}

export default function ReportHeader({
  reportName,
  subject,
  reportId,
  reportDate,
  generatedAt,
  recommendation,
  confidenceScore,
  riskScore,
  verdict,
}: ReportHeaderProps) {
  const getVerdictLabel = () => {
    switch (verdict) {
      case 'proceed':
        return '✓ PROCEED WITH VALIDATION'
      case 'proceed_with_caution':
        return '⚠ PROCEED WITH CAUTION'
      case 'do_not_proceed':
        return '✗ DO NOT PROCEED'
      default:
        return 'ANALYSIS COMPLETE'
    }
  }

  const getVerdictColor = () => {
    switch (verdict) {
      case 'proceed':
        return '#0F6E56' // Green
      case 'proceed_with_caution':
        return '#BA7517' // Orange
      case 'do_not_proceed':
        return '#CC3333' // Red
      default:
        return '#D97757' // Default rust
    }
  }

  const getRiskLabel = () => {
    if (riskScore <= 3) return 'LOW'
    if (riskScore <= 6) return 'MEDIUM'
    return 'HIGH'
  }

  const getRiskColor = () => {
    if (riskScore <= 3) return '#0F6E56' // Green
    if (riskScore <= 6) return '#BA7517' // Orange
    return '#CC3333' // Red
  }

  return (
    <div
      style={{
        border: '2px solid #1C1917',
        borderRadius: '8px',
        padding: '24px',
        background: '#FFFFFF',
        marginBottom: '24px',
        pageBreakAfter: 'avoid',
      }}
    >
      {/* Header Top - OppGrid Branding */}
      <div
        style={{
          textAlign: 'center',
          marginBottom: '20px',
          borderBottom: '1px solid #E5E5E5',
          paddingBottom: '16px',
        }}
      >
        <div
          style={{
            fontSize: '32px',
            fontWeight: 'bold',
            color: '#D97757',
            marginBottom: '8px',
            letterSpacing: '2px',
          }}
        >
          🎯 OPPGRID
        </div>
        <div
          style={{
            fontSize: '14px',
            fontWeight: 600,
            color: '#1C1917',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}
        >
          Consultant Studio Report
        </div>
      </div>

      {/* Metadata Section */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          fontSize: '11px',
          color: '#4B5563',
          margin: '12px 0',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 600, color: '#1C1917', minWidth: '140px' }}>
            REPORT NAME:
          </span>
          <span>{reportName}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 600, color: '#1C1917', minWidth: '140px' }}>
            REPORT ID:
          </span>
          <span>{reportId}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 600, color: '#1C1917', minWidth: '140px' }}>
            SUBJECT:
          </span>
          <span>{subject}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 600, color: '#1C1917', minWidth: '140px' }}>
            DATE:
          </span>
          <span>{reportDate}</span>
        </div>

        <div
          style={{
            gridColumn: '1 / -1',
            display: 'flex',
            justifyContent: 'space-between',
            borderTop: '1px solid #E5E5E5',
            paddingTop: '8px',
            marginTop: '8px',
          }}
        >
          <span style={{ fontWeight: 600, color: '#1C1917' }}>GENERATED AT:</span>
          <span>{generatedAt}</span>
        </div>
      </div>

      {/* Verdict Section */}
      <div
        style={{
          background: '#F5F5F4',
          borderLeft: '4px solid #D97757',
          padding: '16px',
          marginTop: '16px',
          borderRadius: '4px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '20px',
        }}
      >
        <div style={{ fontSize: '11px' }}>
          <div
            style={{
              fontWeight: 600,
              color: '#1C1917',
              marginBottom: '4px',
              display: 'block',
            }}
          >
            RECOMMENDATION:
          </div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757' }}>
            {recommendation}
          </div>
        </div>

        <div style={{ fontSize: '11px' }}>
          <div
            style={{
              fontWeight: 600,
              color: '#1C1917',
              marginBottom: '4px',
              display: 'block',
            }}
          >
            CONFIDENCE SCORE:
          </div>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757' }}>
            {confidenceScore}%
          </div>
        </div>

        <div style={{ fontSize: '11px' }}>
          <div
            style={{
              fontWeight: 600,
              color: '#1C1917',
              marginBottom: '4px',
              display: 'block',
            }}
          >
            RISK LEVEL:
          </div>
          <div
            style={{
              fontSize: '18px',
              fontWeight: 'bold',
              color: getRiskColor(),
            }}
          >
            {getRiskLabel()} ({riskScore.toFixed(1)}/10)
          </div>
        </div>

        {/* Verdict Box - spans both columns */}
        <div
          style={{
            gridColumn: '1 / -1',
            background: getVerdictColor(),
            color: '#FFFFFF',
            padding: '12px',
            borderRadius: '4px',
            textAlign: 'center',
            fontWeight: 600,
            fontSize: '14px',
          }}
        >
          {getVerdictLabel()}
        </div>
      </div>
    </div>
  )
}
