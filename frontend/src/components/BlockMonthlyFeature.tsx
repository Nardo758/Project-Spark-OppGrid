import { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { MONTHLY_LOCKED_FEATURES } from '../constants/pricing'

type LockedFeature = (typeof MONTHLY_LOCKED_FEATURES)[number]

export default function BlockMonthlyFeature({
  feature,
  children,
}: {
  feature: LockedFeature
  children: ReactNode
}) {
  const tier = useAuthStore((s) => s.user?.tier)
  if (tier === 'monthly' && MONTHLY_LOCKED_FEATURES.includes(feature)) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-stone-900 mb-3">Not included in OppGrid Monthly</h1>
        <p className="text-stone-600 mb-6">
          OppGrid Monthly includes the opportunity feed and 2 reports each billing period.
          This feature is not part of that plan.
        </p>
        <Link to="/pricing" className="text-emerald-700 font-medium">
          View plans
        </Link>
      </div>
    )
  }
  return <>{children}</>
}
