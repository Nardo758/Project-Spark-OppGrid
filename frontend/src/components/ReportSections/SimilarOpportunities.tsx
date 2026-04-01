import React from 'react'

interface SimilarOpportunitiesProps {
  similar_opportunities?: Array<Record<string, any>>
}

export default function SimilarOpportunities({ similar_opportunities = [] }: SimilarOpportunitiesProps) {
  const defaultOpps = [
    {
      name: 'BetterHelp',
      model: 'Online Mental Health',
      founded: 2013,
      status: 'Public (AACQ), $1.2B+ revenue',
      success: 'Low friction, mobile-first, affordable',
      lesson: 'Scale and brand matter',
    },
    {
      name: 'Ginger',
      model: 'Telehealth + Coaching',
      founded: 2015,
      status: 'Series C, $170M raised',
      success: 'B2B corporate partnerships',
      lesson: 'Focus on ROI for employers',
    },
    {
      name: 'Headspace',
      model: 'Wellness App Subscription',
      founded: 2010,
      status: 'Unicorn, $3B valuation',
      success: 'Content library + habit formation',
      lesson: 'Product-first scales better',
    },
    {
      name: 'TherapyWorks',
      model: 'Hybrid (40% online, 60% in-person)',
      founded: 2008,
      status: 'Local chains in 15 US states',
      success: 'Community trust + telehealth scale',
      lesson: 'Your exact model proven locally',
    },
    {
      name: 'Talkspace',
      model: 'Async + Live Therapy',
      founded: 2012,
      status: 'Public (TALK)',
      success: 'Unique async model reduced costs',
      lesson: 'Licensing and compliance critical',
    },
  ]

  const opps = similar_opportunities?.length > 0 ? similar_opportunities : defaultOpps

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        📈 SIMILAR OPPORTUNITIES - PROOF OF CONCEPT
      </h2>

      {/* Company Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
        {opps.map((opp, i) => (
          <div key={i} style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '2px' }}>
              {opp.name || opp.title}
            </div>
            <div style={{ fontSize: '9px', color: '#8B8B8B', marginBottom: '6px' }}>
              {opp.model || opp.description} | Founded {opp.founded || 'N/A'}
            </div>
            <div style={{ fontSize: '9px', color: '#4B5563', marginBottom: '4px' }}>{opp.status}</div>

            <div style={{ fontSize: '9px', color: '#15803D', background: '#DCFCE7', padding: '4px 6px', borderRadius: '3px', marginBottom: '4px', display: 'inline-block' }}>
              ✓ {opp.success}
            </div>

            <p style={{ fontSize: '9px', color: '#4B5563', margin: '4px 0 0 0' }}>
              💡 {opp.lesson || 'Proven market validation'}
            </p>
          </div>
        ))}
      </div>

      {/* Key Patterns */}
      <div style={{ background: '#F5F5F4', borderLeft: '4px solid #0F6E56', padding: '12px', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '6px' }}>KEY PATTERNS:</div>
        <ul style={{ fontSize: '9px', color: '#4B5563', margin: '0', paddingLeft: '16px' }}>
          <li>✓ All founded 2008-2015 (market existed then)</li>
          <li>✓ All heavily funded ($50M-$300M+)</li>
          <li>✓ All scaled to national/global presence</li>
          <li>✓ All focus on either scale OR corporate B2B</li>
          <li>✓ Telehealth adoption accelerated post-COVID</li>
        </ul>
      </div>

      {/* Your Advantage */}
      <div style={{ background: '#E1F5EE', borderLeft: '4px solid #0F6E56', padding: '12px', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#085041', marginBottom: '6px' }}>YOUR DIFFERENTIATION OPPORTUNITY:</div>
        <p style={{ fontSize: '9px', color: '#085041', margin: 0 }}>
          These players are either national/global (impersonal) or corporate-focused (high CAC). Your advantage: <strong>LOCAL + PERSONAL</strong> (community-focused, word-of-mouth) or <strong>SPECIALIZED</strong> (niche market focus).
        </p>
      </div>
    </div>
  )
}
