import { useEffect, useMemo, useState } from 'react'
import { 
  Check, 
  X,
  Loader2, 
  Zap, 
  TrendingUp, 
  FileText,
  BarChart3,
  Target,
  Lightbulb,
  Globe,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Users,
  Database
} from 'lucide-react'
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import EnterpriseContactModal from '../components/EnterpriseContactModal'

type MySubscriptionResponse = {
  tier?: string | null
  status?: string | null
  is_active?: boolean | null
  period_end?: string | null
}

const individualTiers = [
  {
    id: 'starter',
    name: 'Starter',
    price: 20,
    priceLabel: '$20/mo',
    description: 'Start exploring opportunities',
    tier: 'starter',
    slots: 1,
    seats: 1,
    reportDiscount: 0,
    extraSlotPrice: 50,
    features: [
      { text: '1 opportunity slot/month', included: true },
      { text: 'Full platform access', included: true },
      { text: 'AI execution reports (full price)', included: true },
      { text: 'Additional slots: $50 each', included: true },
      { text: 'Report discounts', included: false },
      { text: 'Commercial use', included: false },
    ],
    cta: 'Get Started',
    popular: false,
    gradient: 'from-gray-500 to-gray-600',
  },
  {
    id: 'growth',
    name: 'Growth',
    price: 50,
    priceLabel: '$50/mo',
    description: 'Explore more opportunities',
    tier: 'growth',
    slots: 3,
    seats: 1,
    reportDiscount: 10,
    extraSlotPrice: 35,
    features: [
      { text: '3 opportunity slots/month', included: true },
      { text: 'Full platform access', included: true },
      { text: '10% off all reports', included: true },
      { text: 'Additional slots: $35 each', included: true },
      { text: 'Priority support', included: true },
      { text: 'Commercial use', included: false },
    ],
    cta: 'Start Growing',
    popular: true,
    gradient: 'from-emerald-500 to-teal-600',
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 99,
    priceLabel: '$99/mo',
    description: 'Maximum individual power',
    tier: 'pro',
    slots: 5,
    seats: 1,
    reportDiscount: 15,
    extraSlotPrice: 25,
    features: [
      { text: '5 opportunity slots/month', included: true },
      { text: 'Full platform access', included: true },
      { text: '15% off all reports', included: true },
      { text: 'Additional slots: $25 each', included: true },
      { text: 'Priority support', included: true },
      { text: 'Commercial use', included: true },
    ],
    cta: 'Go Pro',
    popular: false,
    gradient: 'from-emerald-600 to-teal-700',
  },
]

const businessTiers = [
  {
    id: 'team',
    name: 'Team',
    price: 250,
    priceLabel: '$250/mo',
    description: 'For small teams and consultants',
    tier: 'team',
    slots: 5,
    seats: 3,
    reportDiscount: 0,
    extraSlotPrice: 30,
    whiteLabel: true,
    features: [
      { text: '5 opportunity slots/month', included: true },
      { text: '3 team seats', included: true },
      { text: 'White-label reports', included: true },
      { text: 'Full commercial use', included: true },
      { text: 'Additional slots: $30 each', included: true },
      { text: 'Team collaboration', included: true },
    ],
    cta: 'Start Team',
    popular: false,
    gradient: 'from-blue-500 to-cyan-600',
  },
  {
    id: 'business',
    name: 'Business',
    price: 750,
    priceLabel: '$750/mo',
    description: 'Scale your consulting practice',
    tier: 'business',
    slots: 15,
    seats: 10,
    reportDiscount: 20,
    extraSlotPrice: 25,
    whiteLabel: true,
    features: [
      { text: '15 opportunity slots/month', included: true },
      { text: '10 team seats', included: true },
      { text: 'White-label + 20% off reports', included: true },
      { text: 'API access', included: true },
      { text: 'Additional slots: $25 each', included: true },
      { text: 'Priority support', included: true },
    ],
    cta: 'Scale Up',
    popular: true,
    gradient: 'from-emerald-600 to-teal-700',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 2500,
    priceLabel: '$2,500+/mo',
    description: 'Unlimited power for agencies',
    tier: 'enterprise',
    slots: 30,
    seats: -1,
    reportDiscount: 50,
    extraSlotPrice: 20,
    whiteLabel: true,
    features: [
      { text: '30 opportunity slots/month', included: true },
      { text: 'Unlimited team seats', included: true },
      { text: 'White-label + 50% off reports', included: true },
      { text: 'Full API access', included: true },
      { text: 'Additional slots: $20 each', included: true },
      { text: 'Dedicated account manager', included: true },
    ],
    cta: 'Contact Sales',
    popular: false,
    gradient: 'from-amber-500 to-orange-600',
  },
]

const subscriptionTiers = [...individualTiers, ...businessTiers]

const layerDetails = [
  {
    layer: 'Layer 1',
    name: 'Problem Overview',
    access: 'All paid tiers (uses 1 slot)',
    features: [
      'Problem statement and consumer pain points',
      'Basic market size estimate',
      'Competition level (Low/Medium/High)',
      'Top 3 geographic markets',
      'Source count and validation score',
    ],
  },
  {
    layer: 'Layer 2',
    name: 'Deep Dive Analysis',
    access: 'Growth+ tiers (included with slot)',
    features: [
      'Complete source compilation (all discussions)',
      'TAM/SAM/SOM detailed estimates',
      'Competitive landscape analysis',
      'All geographic markets',
      'Customer acquisition channel recommendations',
      'Pricing strategy insights',
    ],
  },
  {
    layer: 'Layer 3',
    name: 'Execution Package',
    access: 'Via AI reports (tier discounts apply)',
    features: [
      '90-day execution playbook',
      'MVP feature recommendations',
      'Go-to-market timeline',
      'Launch checklist',
      'Initial team structure recommendations',
    ],
  },
]

const reports = [
  { id: 'feasibility', name: 'Feasibility Study', price: 25, priceLabel: '$25', description: 'Quick viability check', consultantPrice: '$1,500-$15,000', icon: Target },
  { id: 'pitch-deck', name: 'Pitch Deck Assistant', price: 79, priceLabel: '$79', description: 'Investor presentation outline', consultantPrice: '$2,000-$5,000', icon: Sparkles },
  { id: 'strategic-assessment', name: 'Strategic Assessment', price: 89, priceLabel: '$89', description: 'SWOT + strategic positioning', consultantPrice: '$2,000-$8,000', icon: Lightbulb },
  { id: 'market-analysis', name: 'Market Analysis', price: 99, priceLabel: '$99', description: 'TAM/SAM/SOM + competitive landscape', consultantPrice: '$5,000-$50,000', icon: TrendingUp },
  { id: 'pestle', name: 'PESTLE Analysis', price: 99, priceLabel: '$99', description: 'Macro-environmental factors affecting your opportunity', consultantPrice: '$5,000-$25,000', icon: Globe },
  { id: 'financials', name: 'Financial Model', price: 129, priceLabel: '$129', description: '5-year projections & unit economics', consultantPrice: '$3,000-$10,000', icon: BarChart3 },
  { id: 'business-plan', name: 'Business Plan', price: 149, priceLabel: '$149', description: 'Comprehensive strategy document', consultantPrice: '$2,000-$5,000', icon: FileText },
]

const bundles = [
  {
    id: 'marketing',
    name: 'Marketing Bundle',
    price: 599,
    priceLabel: '$599',
    businessPrice: 999,
    savings: 146,
    description: 'Complete marketing foundation for launch',
    includes: ['Content Calendar ($129)', 'Email Funnel System ($179)', 'Lead Magnet ($89)', 'Sales Funnel ($149)', 'User Personas ($99)'],
    totalValue: 645,
    consultantValue: '$8,000-$15,000',
    popular: true,
  },
  {
    id: 'launch',
    name: 'Launch Bundle',
    price: 899,
    priceLabel: '$899',
    businessPrice: 1499,
    savings: 228,
    description: 'Coordinated product launch with tracking',
    includes: ['GTM Strategy ($189)', 'GTM Launch Calendar ($159)', 'MVP Roadmap ($179)', 'KPI Dashboard ($119)'],
    totalValue: 646,
    consultantValue: '$12,000-$25,000',
    popular: false,
  },
  {
    id: 'complete-starter',
    name: 'Complete Starter Bundle',
    price: 1299,
    priceLabel: '$1,299',
    businessPrice: 2299,
    savings: 400,
    description: 'Everything you need to launch from zero to one',
    includes: ['Brand Package ($149)', 'Landing Page ($99)', 'Ad Creatives ($79)', 'Email Sequence ($79)', 'User Personas ($99)', 'MVP Roadmap ($179)', 'GTM Strategy ($189)', 'KPI Dashboard ($119)', 'Competitive Analysis ($149)', 'Pricing Strategy ($139)'],
    totalValue: 1280,
    consultantValue: '$25,000-$50,000',
    popular: false,
    featured: true,
  },
]

const faqs = [
  {
    question: "What are opportunity slots?",
    answer: "Slots give you exclusive access to claim opportunities. Each tier includes a monthly slot allowance. Only 3-10 people can claim each opportunity, ensuring real exclusivity. You can purchase additional slots anytime.",
  },
  {
    question: "What's the difference between Individual and Business tracks?",
    answer: "Individual track ($20-$99/mo) is for solo entrepreneurs exploring opportunities. Business track ($250-$2,500+/mo) adds team seats, white-label reports for client deliverables, commercial use rights, and API access.",
  },
  {
    question: "How do report discounts work?",
    answer: "Higher tiers get report discounts: Growth 10% off, Pro 15% off, Business 20% off, Enterprise 50% off. Business track tiers also get white-label rights to rebrand reports for clients.",
  },
  {
    question: "Can I upgrade my plan anytime?",
    answer: "Yes! You can upgrade at any time and we'll prorate your billing. Your slot allowance updates immediately, and any unused purchased slots carry over.",
  },
  {
    question: "What's included in the Complete Starter Bundle?",
    answer: "The Complete Starter Bundle ($1,299 individual / $2,299 business) includes 10 essential reports: Brand Package, Landing Page, Ad Creatives, Email Sequence, User Personas, MVP Roadmap, GTM Strategy, KPI Dashboard, Competitive Analysis, and Pricing Strategy. Save $400+ vs buying separately.",
  },
]

export default function Pricing() {
  const { token, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const autoCheckout = searchParams.get('checkout')
  const [autoCheckoutTriggered, setAutoCheckoutTriggered] = useState(false)

  const queryParams = new URLSearchParams(location.search)
  const planFromQuery = queryParams.get('plan')
  const fromQuery = queryParams.get('from')
  const [signupAutoStartTriggered, setSignupAutoStartTriggered] = useState(false)

  type TierType = 'starter' | 'growth' | 'pro' | 'team' | 'business' | 'enterprise'
  const [billingLoading, setBillingLoading] = useState<TierType | 'portal' | null>(null)
  const [billingError, setBillingError] = useState<string | null>(null)
  const [billingSuccess, setBillingSuccess] = useState<string | null>(null)
  const [billingSyncing, setBillingSyncing] = useState(false)
  const [subscriptionInfo, setSubscriptionInfo] = useState<null | {
    tier: string
    status: string
    is_active: boolean
    period_end: string | null
  }>(null)

  const [enterpriseModalOpen, setEnterpriseModalOpen] = useState(false)
  const [subPendingTier, setSubPendingTier] = useState<TierType | null>(null)
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null)

  async function startSubscription(tier: TierType) {
    if (!token) {
      navigate(`/login?next=${encodeURIComponent('/pricing')}`)
      return
    }
    setBillingError(null)
    setBillingSuccess(null)
    setBillingLoading(tier)
    try {
      const baseUrl = window.location.origin
      const returnPath = '/pricing'
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent(returnPath)}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent(returnPath)}`
      const res = await fetch('/api/v1/subscriptions/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ 
          tier,
          success_url: successUrl,
          cancel_url: cancelUrl,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const errorMessage = data?.detail || data?.message || `Error ${res.status}: Unable to start checkout`
        throw new Error(errorMessage)
      }
      
      if (data?.url) {
        window.location.href = data.url
      } else {
        throw new Error('No checkout URL returned')
      }
    } catch (e) {
      console.error('Subscription checkout error:', e)
      setBillingError(e instanceof Error ? e.message : 'Unable to start subscription')
    } finally {
      setBillingLoading(null)
    }
  }

  const expectedTierLabel = useMemo(() => {
    return subPendingTier || null
  }, [subPendingTier])

  async function fetchMySubscription() {
    if (!token) throw new Error('Not authenticated')
    const res = await fetch('/api/v1/subscriptions/my-subscription', { headers: { Authorization: `Bearer ${token}` } })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data?.detail || 'Failed to load subscription status')
    setSubscriptionInfo({
      tier: String(data?.tier || ''),
      status: String(data?.status || ''),
      is_active: Boolean(data?.is_active),
      period_end: (data?.period_end ? String(data.period_end) : null) as string | null,
    })
    return data as MySubscriptionResponse
  }

  async function openBillingPortal() {
    if (!token) {
      navigate(`/login?next=${encodeURIComponent('/pricing')}`)
      return
    }
    setBillingError(null)
    setBillingSuccess(null)
    setBillingLoading('portal')
    try {
      const returnUrl = window.location.href
      const res = await fetch('/api/v1/subscriptions/portal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ return_url: returnUrl }),
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

  useEffect(() => {
    if (!isAuthenticated || !token) return
    fetchMySubscription().catch(() => {})
  }, [isAuthenticated, token])

  useEffect(() => {
    if (!autoCheckout || autoCheckoutTriggered || !isAuthenticated || !token) return
    const tier = autoCheckout.toLowerCase() as TierType
    const validTiers: TierType[] = ['starter', 'growth', 'pro', 'team', 'business', 'enterprise']
    if (validTiers.includes(tier) && tier !== 'enterprise') {
      setAutoCheckoutTriggered(true)
      const newParams = new URLSearchParams(searchParams)
      newParams.delete('checkout')
      setSearchParams(newParams, { replace: true })
      startSubscription(tier)
    }
  }, [autoCheckout, autoCheckoutTriggered, isAuthenticated, token, searchParams, setSearchParams])

  useEffect(() => {
    if (!isAuthenticated || !token) return
    if (fromQuery !== 'signup') return
    if (signupAutoStartTriggered) return
    if (billingLoading) return
    if (subscriptionInfo?.is_active) return

    setSignupAutoStartTriggered(true)
    const newParams = new URLSearchParams(searchParams)
    newParams.delete('from')
    newParams.delete('plan')
    setSearchParams(newParams, { replace: true })

    const plan: TierType = planFromQuery === 'scaler' ? 'business' : 'pro'
    startSubscription(plan)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromQuery, planFromQuery, isAuthenticated, token, signupAutoStartTriggered, billingLoading, subscriptionInfo?.is_active])

  useEffect(() => {
    if (!billingSyncing) return
    if (!token) return

    let cancelled = false
    const startedAt = Date.now()
    const timeoutMs = 60_000
    const intervalMs = 3_000

    async function tick() {
      try {
        const res = await fetch('/api/v1/subscriptions/my-subscription', { headers: { Authorization: `Bearer ${token}` } })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data?.detail || 'Failed to load subscription status')
        if (cancelled) return
        setSubscriptionInfo({
          tier: String(data?.tier || ''),
          status: String(data?.status || ''),
          is_active: Boolean(data?.is_active),
          period_end: (data?.period_end ? String(data.period_end) : null) as string | null,
        })

        if (isExpectedTierActive(data, expectedTierLabel)) {
          setBillingSuccess('Your plan is active.')
          setBillingSyncing(false)
          setSubPendingTier(null)
        } else if (Date.now() - startedAt > timeoutMs) {
          setBillingSuccess('Payment confirmed. Plan sync is taking longer than usual — please refresh in a moment.')
          setBillingSyncing(false)
        }
      } catch (e) {
        if (cancelled) return
        if (Date.now() - startedAt > timeoutMs) {
          setBillingError(e instanceof Error ? e.message : 'Failed to sync subscription status')
          setBillingSyncing(false)
        }
      }
    }

    const id = window.setInterval(tick, intervalMs)
    tick()
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [billingSyncing, token, expectedTierLabel])

  const hasActiveSubscription = subscriptionInfo && 
    subscriptionInfo.is_active && 
    subscriptionInfo.tier && 
    subscriptionInfo.tier.toLowerCase() !== 'free'

  const handleTierClick = (tier: typeof subscriptionTiers[0]) => {
    const tierName = tier.tier as TierType
    if (tierName === 'enterprise') {
      setEnterpriseModalOpen(true)
    } else {
      if (!isAuthenticated) {
        navigate(`/login?next=${encodeURIComponent(`/pricing?checkout=${tierName}`)}`)
      } else if (hasActiveSubscription) {
        setBillingError(`You already have an active ${subscriptionInfo?.tier} subscription. Use "Manage Billing" to change your plan.`)
      } else {
        startSubscription(tierName)
      }
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50/50 via-white to-emerald-50/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-100 text-emerald-700 rounded-full text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            Professional Business Intelligence. AI Speed.
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Discover. Claim. Execute.
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-6">
            Start at <span className="font-semibold text-emerald-600">$20/month</span>{' '}
            - 10x more accessible than competitors. Pay to play, not to browse.
          </p>
          <p className="text-lg text-gray-500">
            Exclusive opportunity slots. AI execution reports. Real business intelligence.
          </p>
        </div>

        {billingError && (
          <div className="mb-10 max-w-3xl mx-auto bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            {billingError}
          </div>
        )}
        {billingSuccess && (
          <div className="mb-10 max-w-3xl mx-auto bg-green-50 border border-green-200 text-green-800 rounded-xl px-4 py-3 text-sm">
            {billingSuccess}
          </div>
        )}
        {subscriptionInfo && (
          <div className="mb-10 max-w-3xl mx-auto bg-white border border-gray-200 text-gray-700 rounded-xl px-4 py-3 text-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <span className="font-medium">Current plan:</span>{' '}
                <span className="font-semibold">{subscriptionInfo.tier || '—'}</span>{' '}
                <span className="text-gray-500">({subscriptionInfo.status || '—'})</span>
                {subscriptionInfo.period_end && (
                  <span className="text-gray-500"> • Renews/ends {new Date(subscriptionInfo.period_end).toLocaleDateString()}</span>
                )}
              </div>
              {isAuthenticated && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => fetchMySubscription().catch((e) => setBillingError(e instanceof Error ? e.message : 'Failed to refresh'))}
                    className="px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium"
                    disabled={billingSyncing}
                  >
                    Refresh
                  </button>
                  <button
                    type="button"
                    onClick={openBillingPortal}
                    disabled={billingLoading !== null}
                    className="px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50"
                  >
                    {billingLoading === 'portal' ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Manage Billing'}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="mb-20">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Individual Track</h2>
            <p className="text-gray-600">For solo entrepreneurs and side hustlers</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            {individualTiers.map((tier) => (
              <div
                key={tier.id}
                className={`relative bg-white rounded-2xl border-2 ${
                  tier.popular ? 'border-emerald-500 shadow-xl' : 'border-gray-200'
                } overflow-hidden`}
              >
                {tier.popular && (
                  <div className="absolute top-0 left-0 right-0 bg-emerald-500 text-white text-center text-sm py-1 font-medium">
                    Most Popular
                  </div>
                )}
                <div className={`bg-gradient-to-r ${tier.gradient} p-6 text-white ${tier.popular ? 'mt-7' : ''}`}>
                  <h3 className="text-xl font-bold">{tier.name}</h3>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{tier.priceLabel}</span>
                  </div>
                  <p className="text-white/80 text-sm mt-2">{tier.description}</p>
                </div>
                <div className="p-6">
                  <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase tracking-wider">Monthly Slots</div>
                    <div className="font-medium text-gray-900 flex items-center gap-2">
                      <Database className="w-4 h-4 text-gray-400" />
                      {tier.slots} {tier.slots === 1 ? 'opportunity' : 'opportunities'}
                    </div>
                  </div>
                  <ul className="space-y-3 mb-6">
                    {tier.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2">
                        {feature.included ? (
                          <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <X className="w-5 h-5 text-gray-300 flex-shrink-0 mt-0.5" />
                        )}
                        <span className={feature.included ? 'text-gray-700 text-sm' : 'text-gray-400 text-sm'}>
                          {feature.text}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => handleTierClick(tier)}
                    disabled={billingLoading !== null}
                    className={`block w-full py-3 rounded-lg text-center font-medium transition-colors disabled:opacity-50 ${
                      tier.popular
                        ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {billingLoading === tier.tier ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing...
                      </span>
                    ) : (
                      tier.cta
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Business Track</h2>
            <p className="text-gray-600">For teams, consultants, and agencies</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {businessTiers.map((tier) => (
              <div
                key={tier.id}
                className={`relative bg-white rounded-2xl border-2 ${
                  tier.popular ? 'border-emerald-500 shadow-xl' : 'border-gray-200'
                } overflow-hidden`}
              >
                {tier.popular && (
                  <div className="absolute top-0 left-0 right-0 bg-emerald-500 text-white text-center text-sm py-1 font-medium">
                    Most Popular
                  </div>
                )}
                <div className={`bg-gradient-to-r ${tier.gradient} p-6 text-white ${tier.popular ? 'mt-7' : ''}`}>
                  <h3 className="text-xl font-bold">{tier.name}</h3>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{tier.priceLabel}</span>
                  </div>
                  <p className="text-white/80 text-sm mt-2">{tier.description}</p>
                </div>
                <div className="p-6">
                  <div className="mb-4 grid grid-cols-2 gap-2">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase tracking-wider">Slots/Mo</div>
                      <div className="font-medium text-gray-900 flex items-center gap-1">
                        <Database className="w-4 h-4 text-gray-400" />
                        {tier.slots}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase tracking-wider">Team Seats</div>
                      <div className="font-medium text-gray-900 flex items-center gap-1">
                        <Users className="w-4 h-4 text-gray-400" />
                        {tier.seats === -1 ? 'Unlimited' : tier.seats}
                      </div>
                    </div>
                  </div>
                  <ul className="space-y-3 mb-6">
                    {tier.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2">
                        {feature.included ? (
                          <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <X className="w-5 h-5 text-gray-300 flex-shrink-0 mt-0.5" />
                        )}
                        <span className={feature.included ? 'text-gray-700 text-sm' : 'text-gray-400 text-sm'}>
                          {feature.text}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => handleTierClick(tier)}
                    disabled={billingLoading !== null}
                    className={`block w-full py-3 rounded-lg text-center font-medium transition-colors disabled:opacity-50 ${
                      tier.popular
                        ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {billingLoading === tier.tier ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing...
                      </span>
                    ) : (
                      tier.cta
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">What's in Each Layer?</h2>
            <p className="text-gray-600">Progressive intelligence that deepens as you commit</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {layerDetails.map((layer, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    i === 0 ? 'bg-blue-100 text-blue-600' :
                    i === 1 ? 'bg-amber-100 text-amber-600' :
                    'bg-emerald-100 text-emerald-600'
                  }`}>
                    {i === 0 ? <Lightbulb className="w-5 h-5" /> :
                     i === 1 ? <TrendingUp className="w-5 h-5" /> :
                     <Zap className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">{layer.layer}</div>
                    <div className="font-semibold text-gray-900">{layer.name}</div>
                  </div>
                </div>
                <div className="text-xs text-emerald-600 font-medium mb-4 p-2 bg-emerald-50 rounded-lg">
                  {layer.access}
                </div>
                <ul className="space-y-2">
                  {layer.features.map((feature, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-gray-600">
                      <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Execution Reports</h2>
            <p className="text-gray-600">Transform opportunities into investor-ready documentation</p>
          </div>

          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-2xl border border-emerald-200 p-8 mb-8">
            <div className="flex flex-col md:flex-row md:items-center gap-6">
              <div className="w-16 h-16 bg-emerald-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <Target className="w-8 h-8 text-emerald-600" />
              </div>
              <div className="flex-1">
                <div className="text-sm text-emerald-600 font-medium">BEST VALUE - START HERE</div>
                <h3 className="text-2xl font-bold text-gray-900">Feasibility Study</h3>
                <p className="text-gray-600">Quick viability check - prove our quality before you invest in the full suite</p>
              </div>
              <div className="text-right">
                <div className="text-4xl font-bold text-emerald-600">$25</div>
                <div className="text-sm text-gray-500 line-through">$1,500-$15,000 from consultants</div>
                <div className="text-xs text-emerald-500 font-medium">Save 98%+</div>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {reports.filter(r => r.id !== 'feasibility').map((report) => (
              <div key={report.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-300 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                      <report.icon className="w-5 h-5 text-emerald-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-900">{report.name}</h4>
                      <p className="text-xs text-gray-500">{report.description}</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold text-emerald-600">{report.priceLabel}</span>
                  <span className="text-xs text-gray-400 line-through">{report.consultantPrice}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Save with Bundles</h2>
            <p className="text-gray-600">Get everything you need at a significant discount</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {bundles.map((bundle) => (
              <div key={bundle.id} className="bg-white rounded-xl border-2 border-gray-200 hover:border-emerald-300 transition-colors overflow-hidden">
                <div className="p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-1">{bundle.name}</h3>
                  <p className="text-sm text-gray-500 mb-4">{bundle.description}</p>
                  <div className="flex items-baseline gap-2 mb-4">
                    <span className="text-3xl font-bold text-emerald-600">
                      {bundle.priceLabel || `$${bundle.price}`}
                    </span>
                    {bundle.savings > 0 && (
                      <span className="text-sm text-green-600 font-medium">Save ${bundle.savings}</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mb-4">
                    <span className="line-through">{bundle.consultantValue}</span> from consultants
                  </div>
                  <ul className="space-y-2 mb-6">
                    {bundle.includes.map((item, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                        <Check className="w-4 h-4 text-green-500" />
                        {item}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => {
                      if (!isAuthenticated) {
                        navigate(`/login?next=${encodeURIComponent('/discover?bundle=' + bundle.id)}`)
                      } else {
                        navigate(`/discover?bundle=${bundle.id}`)
                      }
                    }}
                    className="block w-full py-3 bg-emerald-600 text-white rounded-lg text-center font-medium hover:bg-emerald-700 transition-colors"
                  >
                    Get {bundle.name}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Additional Services</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                  <Database className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">API Access</h3>
                  <p className="text-sm text-gray-500">Integrate OppGrid into your systems</p>
                </div>
              </div>
              <ul className="space-y-2 mb-4">
                <li className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Opportunity data endpoint</span>
                  <span className="font-medium">$0.10/call</span>
                </li>
                <li className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Report generation API</span>
                  <span className="font-medium">$0.50/report</span>
                </li>
                <li className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Bulk data export</span>
                  <span className="font-medium">$99/month</span>
                </li>
              </ul>
              <Link to="/api" className="text-emerald-600 hover:text-emerald-700 text-sm font-medium">
                View API Documentation →
              </Link>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
                  <Users className="w-6 h-6 text-amber-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Leads Marketplace</h3>
                  <p className="text-sm text-gray-500">Connect with verified business leads</p>
                </div>
              </div>
              <ul className="space-y-2 mb-4">
                <li className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Verified business leads</span>
                  <span className="font-medium">$5-$25/lead</span>
                </li>
                <li className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Investor connections</span>
                  <span className="font-medium">$50-$100/intro</span>
                </li>
                <li className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Expert consultations</span>
                  <span className="font-medium">$150-$500/hour</span>
                </li>
              </ul>
              <Link to="/leads" className="text-emerald-600 hover:text-emerald-700 text-sm font-medium">
                Browse Leads →
              </Link>
            </div>
          </div>
        </div>

        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Frequently Asked Questions</h2>
          </div>
          <div className="max-w-3xl mx-auto space-y-4">
            {faqs.map((faq, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setExpandedFaq(expandedFaq === i ? null : i)}
                  className="w-full p-6 text-left flex items-center justify-between"
                >
                  <span className="font-medium text-gray-900">{faq.question}</span>
                  {expandedFaq === i ? (
                    <ChevronUp className="w-5 h-5 text-gray-500" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-500" />
                  )}
                </button>
                {expandedFaq === i && (
                  <div className="px-6 pb-6 text-gray-600">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-8 md:p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-white/80 mb-8 max-w-2xl mx-auto">
            Browse opportunities and get your first Feasibility Study for just $25. No subscription required.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/opportunities"
              className="px-8 py-3 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors"
            >
              Browse Opportunities
            </Link>
            <Link
              to="/build"
              className="px-8 py-3 bg-white/10 text-white rounded-lg font-medium hover:bg-white/20 transition-colors border border-white/20"
            >
              See Sample Reports
            </Link>
          </div>
        </div>
      </div>


      {enterpriseModalOpen && (
        <EnterpriseContactModal
          source="pricing"
          onClose={() => setEnterpriseModalOpen(false)}
        />
      )}
    </div>
  )
}

function isExpectedTierActive(raw: unknown, expectedTier: string | null) {
  const obj = (raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}) as Record<string, unknown>
  const tier = String(obj.tier ?? '').toLowerCase()
  const isActive = Boolean(obj.is_active)
  if (!expectedTier) return isActive
  return isActive && tier === expectedTier
}
