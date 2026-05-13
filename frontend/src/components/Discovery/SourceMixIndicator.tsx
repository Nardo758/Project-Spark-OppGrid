import { useMemo } from 'react'

interface ContributingSources {
  total_sources?: number
  total_signals?: number
  [key: string]: number | undefined
}

interface Props {
  contributingSources?: ContributingSources | null
  maxDisplay?: number
}

const SOURCE_META: Record<string, { label: string; bg: string; abbr: string }> = {
  reddit:        { label: 'Reddit',       bg: 'bg-orange-500',  abbr: 'R' },
  google_maps:   { label: 'Google Maps',  bg: 'bg-blue-500',    abbr: 'G' },
  yelp:          { label: 'Yelp',         bg: 'bg-red-500',     abbr: 'Y' },
  nextdoor:      { label: 'Nextdoor',     bg: 'bg-green-600',   abbr: 'N' },
  twitter:       { label: 'Twitter/X',    bg: 'bg-sky-500',     abbr: 'X' },
  facebook:      { label: 'Facebook',     bg: 'bg-blue-600',    abbr: 'F' },
  macro_anomaly: { label: 'Macro Data',   bg: 'bg-purple-500',  abbr: 'M' },
  craigslist:    { label: 'Craigslist',   bg: 'bg-violet-500',  abbr: 'C' },
  linkedin:      { label: 'LinkedIn',     bg: 'bg-blue-700',    abbr: 'L' },
  greatschools:  { label: 'GreatSchools', bg: 'bg-teal-500',    abbr: 'S' },
}

export default function SourceMixIndicator({ contributingSources, maxDisplay = 6 }: Props) {
  const sources = useMemo(() => {
    if (!contributingSources) return []
    return Object.entries(contributingSources)
      .filter(([key]) => !['total_sources', 'total_signals'].includes(key))
      .filter(([, count]) => typeof count === 'number' && count > 0)
      .sort(([, a], [, b]) => (b as number) - (a as number))
  }, [contributingSources])

  if (!sources.length) return null

  const displayed   = sources.slice(0, maxDisplay)
  const overflow    = sources.length - maxDisplay
  const totalSignals = contributingSources?.total_signals
    ?? sources.reduce((sum, [, c]) => sum + (c as number), 0)
  const totalSources = contributingSources?.total_sources ?? sources.length

  return (
    <div
      className="flex items-center gap-1"
      title={`${totalSources} source${totalSources !== 1 ? 's' : ''} · ${totalSignals} signal${totalSignals !== 1 ? 's' : ''}`}
    >
      {displayed.map(([key]) => {
        const meta = SOURCE_META[key] ?? { label: key, bg: 'bg-slate-400', abbr: '?' }
        return (
          <span
            key={key}
            className={`w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold text-white ${meta.bg} flex-shrink-0`}
            title={`${meta.label}: ${contributingSources?.[key]} signals`}
          >
            {meta.abbr}
          </span>
        )
      })}
      {overflow > 0 && (
        <span className="text-xs text-slate-500 font-medium">+{overflow}</span>
      )}
      <span className="text-xs text-slate-400 ml-0.5">
        {totalSources} src
      </span>
    </div>
  )
}
