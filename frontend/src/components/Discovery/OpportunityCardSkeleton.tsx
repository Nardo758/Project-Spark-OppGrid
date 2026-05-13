/**
 * OpportunityCardSkeleton
 *
 * Loading skeleton for OpportunityCard (enriched layout).
 * Matches the new header / location / metrics / macro strip regions.
 * Brand-aligned: slate neutrals, emerald score circle.
 */
import React from 'react'

const OpportunityCardSkeleton: React.FC = () => (
  <div className="bg-white rounded-xl border-2 border-slate-200 p-5 animate-pulse">

    {/* Header: tier badge + category + score */}
    <div className="flex items-start justify-between mb-3">
      <div className="flex flex-col gap-1.5 flex-1">
        <div className="flex items-center gap-2">
          <div className="h-5 w-20 bg-emerald-100 rounded-full" />
          <div className="h-4 w-24 bg-slate-200 rounded" />
        </div>
        {/* Location line */}
        <div className="h-3 w-36 bg-slate-100 rounded" />
      </div>
      {/* Feasibility circle */}
      <div className="h-12 w-16 bg-emerald-50 rounded-full ml-4 flex-shrink-0" />
    </div>

    {/* Badge row */}
    <div className="flex items-center gap-2 mb-3">
      <div className="h-5 w-24 bg-slate-100 rounded-full" />
      <div className="h-5 w-20 bg-slate-100 rounded-full" />
      <div className="h-5 w-16 bg-slate-100 rounded-full" />
    </div>

    {/* Title */}
    <div className="h-5 w-3/4 bg-slate-300 rounded mb-2" />

    {/* Description */}
    <div className="space-y-1.5 mb-4">
      <div className="h-3.5 bg-slate-200 rounded w-full" />
      <div className="h-3.5 bg-slate-200 rounded w-5/6" />
    </div>

    {/* Pain × Urgency × Growth row */}
    <div className="grid grid-cols-3 gap-3 mb-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="bg-slate-50 rounded-lg p-3">
          <div className="h-3 w-12 bg-slate-200 rounded mb-2" />
          <div className="h-5 w-10 bg-slate-300 rounded" />
        </div>
      ))}
    </div>

    {/* Macro context strip */}
    <div className="h-7 bg-slate-50 rounded-lg mb-4" />

    {/* Actions row */}
    <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="h-4 w-16 bg-slate-200 rounded" />
        <div className="h-4 w-12 bg-slate-200 rounded" />
      </div>
      <div className="h-4 w-28 bg-slate-200 rounded" />
    </div>
  </div>
)

export { OpportunityCardSkeleton }
export default OpportunityCardSkeleton
