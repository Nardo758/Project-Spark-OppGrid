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

const SOURCE_META: Record<string, { label: string; color: string; emoji: string }> = {
  reddit:        { label: 'Reddit',       color: 'bg-orange-500',  emoji: '🔴' },
  google_maps:   { label: 'Google Maps',  color: 'bg-blue-500',    emoji: '🗺️' },
  yelp:          { label: 'Yelp',         color: 'bg-red-600',     emoji: '★' },
  nextdoor:      { label: 'Nextdoor',     color: 'bg-emerald-600', emoji: '🏘️' },
  twitter:       { label: 'Twitter/X',    color: 'bg-slate-900',   emoji: '𝕏' },
  greatschools:  { label: 'GreatSchools', color: 'bg-indigo-500',  emoji: '🎓' },
  craigslist:    { label: 'Craigslist',   color: 'bg-purple-600',  emoji: 'C' },
  macro_anomaly: { label: 'Economic',     color: 'bg-amber-500',   emoji: '📈' },
  facebook:      { label: 'Facebook',     color: 'bg-blue-600',    emoji: 'F' },
  linkedin:      { label: 'LinkedIn',     color: 'bg-blue-700',    emoji: 'in' },
}

export default function SourceMixIndicator({ contributingSources, maxDisplay = 5 }: Props) {
  const { displayed, overflow, total } = useMemo(() => {
    if (!contributingSources) return { displayed: [], overflow: 0, total: 0 }
    const entries = Object.entries(contributingSources)
      .filter(([k]) => k !== 'total_sources' && k !== 'total_signals')
      .filter(([, v]) => (v ?? 0) > 0)
      .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
    return {
      displayed: entries.slice(0, maxDisplay),
      overflow: Math.max(0, entries.length - maxDisplay),
      total: contributingSources.total_sources ?? entries.length,
    }
  }, [contributingSources, maxDisplay])

  if (total === 0) return null

  return (
    <div className="flex items-center gap-1.5" title={`${total} source${total === 1 ? '' : 's'}`}>
      <div className="flex -space-x-1">
        {displayed.map(([source, count]) => {
          const meta = SOURCE_META[source]
          if (!meta) return null
          return (
            <span
              key={source}
              className={`inline-flex items-center justify-center w-5 h-5 rounded-full
                text-[10px] text-white font-bold ring-2 ring-white ${meta.color}`}
              title={`${meta.label}: ${count} signal${count === 1 ? '' : 's'}`}
            >
              {meta.emoji}
            </span>
          )
        })}
        {overflow > 0 && (
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full
            text-[10px] bg-slate-200 text-slate-700 font-bold ring-2 ring-white">
            +{overflow}
          </span>
        )}
      </div>
      <span className="text-xs text-slate-600 font-medium">
        {total} source{total === 1 ? '' : 's'}
      </span>
    </div>
  )
}
