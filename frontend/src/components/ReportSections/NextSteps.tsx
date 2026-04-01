import React from 'react'

interface NextStepsProps {
  viability_report?: Record<string, any>
}

export default function NextSteps({ viability_report }: NextStepsProps) {
  const phases = [
    {
      phase: 1,
      name: 'Market Validation',
      weeks: '1-4',
      objective: 'Confirm customer problem and willingness to pay',
      tasks: [
        'Conduct 20-30 customer interviews',
        'Validate pricing expectations',
        'Identify competitive advantages',
      ],
      criteria: '70%+ say "I would pay for this"',
    },
    {
      phase: 2,
      name: 'Competitive Analysis',
      weeks: '2-5',
      objective: 'Understand competitive landscape',
      tasks: [
        'Deep dive on 5-8 competitors',
        'Document pricing & positioning',
        'Identify market gaps',
      ],
      criteria: 'Clear differentiation strategy',
    },
    {
      phase: 3,
      name: 'MVP Design',
      weeks: '4-8',
      objective: 'Define minimum viable product',
      tasks: [
        'Service packages & pricing',
        'Tech stack & delivery method',
        'Build landing page',
      ],
      criteria: '1-page MVP specification',
    },
    {
      phase: 4,
      name: 'Pilot Testing',
      weeks: '8-16',
      objective: 'Validate with real paying customers',
      tasks: [
        'Recruit 5-10 beta customers',
        'Run 4-6 weeks, gather feedback',
        'Measure satisfaction & retention',
      ],
      criteria: '80%+ would recommend',
    },
  ]

  const quickWins = [
    'Research state licensing requirements (2 hours)',
    'Brainstorm recruitment strategy (1 hour)',
    'List 10 potential partners (1 hour)',
    'Evaluate 5 platforms/tools (2 hours)',
  ]

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#D97757', borderBottom: '2px solid #E5E5E5', paddingBottom: '8px' }}>
        🎯 NEXT STEPS - VALIDATION ROADMAP
      </h2>

      {/* Phases */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
        {phases.map((phase) => (
          <div key={phase.phase} style={{ background: '#F5F5F4', borderLeft: '4px solid #D97757', padding: '12px', borderRadius: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917' }}>
                PHASE {phase.phase}: {phase.name.toUpperCase()}
              </div>
              <div style={{ fontSize: '10px', color: '#8B8B8B' }}>Weeks {phase.weeks}</div>
            </div>
            <p style={{ fontSize: '10px', color: '#4B5563', margin: '4px 0 6px 0' }}>{phase.objective}</p>
            <ul style={{ fontSize: '9px', color: '#4B5563', margin: '4px 0', paddingLeft: '16px' }}>
              {phase.tasks.map((task, i) => (
                <li key={i} style={{ margin: '2px 0' }}>
                  {task}
                </li>
              ))}
            </ul>
            <div style={{ fontSize: '9px', color: '#8B8B8B', marginTop: '4px' }}>✓ {phase.criteria}</div>
          </div>
        ))}
      </div>

      {/* Quick Wins */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '8px' }}>⚡ QUICK WINS (Do Today):</div>
        <ul style={{ fontSize: '10px', color: '#4B5563', margin: '0', paddingLeft: '16px' }}>
          {quickWins.map((win, i) => (
            <li key={i} style={{ margin: '4px 0' }}>
              {win}
            </li>
          ))}
        </ul>
      </div>

      {/* Timeline */}
      <div style={{ background: '#F5F5F4', padding: '12px', borderRadius: '4px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#1C1917', marginBottom: '8px' }}>TIMELINE:</div>
        <div style={{ fontSize: '10px', color: '#4B5563', lineHeight: '1.6' }}>
          <div>Week 1-4: Market validation + Legal review (parallel)</div>
          <div>Week 5-8: Competitive analysis + MVP design</div>
          <div>Week 9-16: Pilot with beta customers</div>
          <div style={{ fontWeight: 600, marginTop: '4px' }}>Month 5: Go/no-go decision</div>
        </div>
      </div>
    </div>
  )
}
