import { useEffect, useState } from 'react'
import { Check, Loader2, FileText, Sparkles } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { LAUNCH_OFFERS } from '../constants/pricing'

type MySubscriptionResponse = {
  tier?: string | null
  status?: string | null
  is_active?: boolean | null
  period_end?: string | null
}

export default function Pricing() {
  const { token, isAuthenticated } = useAuthStore()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [billingLoading, setBillingLoading] = useState<'monthly' | 'report' | 'portal' | null>(null)
  const [billingError, setBillingError] = useState<string | null>(null)
  const [billingSuccess, setBillingSuccess] = useState<string | null>(null)
  const [subscriptionInfo, setSubscriptionInfo] = useState<null | {
    tier: string
    status: string
    is_active: boolean
    period_end: string | null
  }>(null)

  async function fetchMySubscription() {
    if (!token) throw new Error('Not authenticated')
    const res = await fetch('/api/v1/subscriptions/my-subscription', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data?.detail || 'Failed to load subscription status')
    setSubscriptionInfo({
      tier: String(data?.tier || ''),
      status: String(data?.status || ''),
      is_active: Boolean(data?.is_active),
      period_end: data?.period_end ? String(data.period_end) : null,
    })
    return data as MySubscriptionResponse
  }

  useEffect(() => {
    if (!isAuthenticated || !token) return
    fetchMySubscription().catch(() => {})
  }, [isAuthenticated, token])

  async function startMonthly() {
    if (!token) {
      navigate('/signup?plan=monthly')
      return
    }
    setBillingError(null)
    setBillingSuccess(null)
    setBillingLoading('monthly')
    try {
      const baseUrl = window.location.origin
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent('/pricing')}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent('/pricing')}`
      const res = await fetch('/api/v1/subscriptions/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          tier: 'monthly',
          success_url: successUrl,
          cancel_url: cancelUrl,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || data?.message || 'Unable to start checkout')
      }
      if (!data?.url) throw new Error('No checkout URL returned')
      window.location.href = data.url
    } catch (e) {
      setBillingError(e instanceof Error ? e.message : 'Unable to start subscription')
    } finally {
      setBillingLoading(null)
    }
  }

  async function startDeepClone() {
    if (!token) {
      navigate(`/login?next=${encodeURIComponent('/pricing')}`)
      return
    }
    setBillingError(null)
    setBillingLoading('report')
    try {
      const res = await fetch('/api/v1/subscriptions/deep-clone-checkout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || 'Unable to start checkout')
      }
      if (data?.has_access) {
        setBillingSuccess(data?.message || 'You already have access to this report.')
        return
      }
      if (!data?.checkout_url) throw new Error('No checkout URL returned')
      window.location.href = data.checkout_url
    } catch (e) {
      setBillingError(e instanceof Error ? e.message : 'Unable to start checkout')
    } finally {
      setBillingLoading(null)
    }
  }

  async function openBillingPortal() {
    if (!token) {
      navigate(`/login?next=${encodeURIComponent('/pricing')}`)
      return
    }
    setBillingError(null)
    setBillingLoading('portal')
    try {
      const res = await fetch('/api/v1/subscriptions/portal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ return_url: window.location.href }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || 'Unable to open billing portal')
      if (!data?.url) throw new Error('Portal URL missing')
      window.location.href = String(data.url)
    } catch (e) {
      setBillingError(e instanceof Error ? e.message : 'Unable to open billing portal')
    } finally {
      setBillingLoading(null)
    }
  }

  const onMonthly = subscriptionInfo?.is_active && subscriptionInfo.tier.toUpperCase() === 'MONTHLY'

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50/50 via-white to-emerald-50/30">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-100 text-emerald-700 rounded-full text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            Two ways to get a report
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">OppGrid pricing</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Buy one Deep Clone report for {LAUNCH_OFFERS.deepClone.priceLabel}, or subscribe to{' '}
            {LAUNCH_OFFERS.monthly.name} for {LAUNCH_OFFERS.monthly.priceLabel}.
          </p>
        </div>

        {searchParams.get('deep_clone_success') === 'true' && (
          <div className="mb-8 bg-green-50 border border-green-200 text-green-800 rounded-xl px-4 py-3 text-sm">
            Deep Clone checkout completed. Your {LAUNCH_OFFERS.deepClone.priceLabel} report is ready to run.
          </div>
        )}
        {billingError && (
          <div className="mb-8 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            {billingError}
          </div>
        )}
        {billingSuccess && (
          <div className="mb-8 bg-green-50 border border-green-200 text-green-800 rounded-xl px-4 py-3 text-sm">
            {billingSuccess}
          </div>
        )}
        {isAuthenticated && subscriptionInfo?.is_active && (
          <div className="mb-8 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <span className="font-medium">You have an active subscription.</span>
              {subscriptionInfo.period_end && (
                <span className="text-gray-500">
                  {' '}
                  Access runs through {new Date(subscriptionInfo.period_end).toLocaleDateString()}.
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={openBillingPortal}
              disabled={billingLoading === 'portal'}
              className="px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium"
            >
              {billingLoading === 'portal' ? 'Opening…' : 'Manage billing'}
            </button>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-gray-200 p-8 flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-stone-100 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-stone-700" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{LAUNCH_OFFERS.deepClone.name}</h2>
                <p className="text-sm text-gray-500">Single report</p>
              </div>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-gray-900">{LAUNCH_OFFERS.deepClone.priceLabel}</span>
              <span className="text-gray-500"> one time</span>
            </div>
            <ul className="space-y-3 mb-8 text-sm text-gray-700">
              <li className="flex gap-2"><Check className="w-4 h-4 text-emerald-600 mt-0.5" /> One Deep Clone report</li>
              <li className="flex gap-2"><Check className="w-4 h-4 text-emerald-600 mt-0.5" /> No subscription</li>
            </ul>
            <button
              type="button"
              onClick={startDeepClone}
              disabled={billingLoading !== null}
              className="mt-auto w-full py-3 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {billingLoading === 'report' && <Loader2 className="w-4 h-4 animate-spin" />}
              Buy report for {LAUNCH_OFFERS.deepClone.priceLabel}
            </button>
          </div>

          <div className="bg-white rounded-2xl border-2 border-emerald-500 p-8 flex flex-col shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-emerald-700" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{LAUNCH_OFFERS.monthly.name}</h2>
                <p className="text-sm text-gray-500">Subscription</p>
              </div>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-gray-900">{LAUNCH_OFFERS.monthly.priceLabel}</span>
            </div>
            <ul className="space-y-3 mb-8 text-sm text-gray-700">
              <li className="flex gap-2"><Check className="w-4 h-4 text-emerald-600 mt-0.5" /> 2 reports each billing period</li>
              <li className="flex gap-2"><Check className="w-4 h-4 text-emerald-600 mt-0.5" /> Opportunity feed</li>
              <li className="flex gap-2"><Check className="w-4 h-4 text-emerald-600 mt-0.5" /> Unused reports do not roll over</li>
              <li className="flex gap-2"><Check className="w-4 h-4 text-emerald-600 mt-0.5" /> Cancel and keep access through the paid period</li>
            </ul>
            <button
              type="button"
              onClick={startMonthly}
              disabled={billingLoading !== null || onMonthly}
              className="mt-auto w-full py-3 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {billingLoading === 'monthly' && <Loader2 className="w-4 h-4 animate-spin" />}
              {onMonthly ? 'Current plan' : `Subscribe for ${LAUNCH_OFFERS.monthly.priceLabel}`}
            </button>
          </div>
        </div>

        <p className="text-center text-sm text-gray-500 mt-10">
          Need another report after the two included ones? Buy a single Deep Clone for {LAUNCH_OFFERS.deepClone.priceLabel}.{' '}
          <Link to="/discover" className="text-emerald-700 font-medium">Browse the feed</Link>
        </p>
      </div>
    </div>
  )
}
