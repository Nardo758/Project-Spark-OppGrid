import { useState } from 'react'
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Loader2, Check, Crown } from 'lucide-react'
import PayPerUnlockModal from '../components/PayPerUnlockModal'
import { PLAN_DISPLAY, type Tier } from '../constants/pricing'

const planDetails: Record<string, { name: string; price: string; color: string; tier: Tier }> = {
  starter: { name: 'Starter', price: '$20/mo', color: 'blue', tier: 'starter' },
  growth: { name: 'Growth', price: '$50/mo', color: 'blue', tier: 'growth' },
  pro: { name: 'Pro', price: '$99/mo', color: 'purple', tier: 'pro' },
  builder: PLAN_DISPLAY.builder,
  team: { name: 'Team', price: '$250/mo', color: 'emerald', tier: 'team' },
  business: { name: 'Business', price: '$750/mo', color: 'emerald', tier: 'business' },
  scaler: PLAN_DISPLAY.scaler,
  enterprise: { name: 'Enterprise', price: 'Custom', color: 'amber', tier: 'enterprise' },
}

export default function Signup() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const selectedPlan = searchParams.get('plan')
  const planInfo = selectedPlan ? planDetails[selectedPlan.toLowerCase()] : null
  
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [error, setError] = useState('')
  const [showNextSteps, setShowNextSteps] = useState(false)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  
  const [paymentModalOpen, setPaymentModalOpen] = useState(false)
  const [publishableKey, setPublishableKey] = useState<string | null>(null)
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [paymentCancelled, setPaymentCancelled] = useState(false)
  const [signupComplete, setSignupComplete] = useState(false)
  
  const { signup, isLoading, startReplitAuth, startGoogleAuth, startLinkedInAuth } = useAuthStore()
  const navigate = useNavigate()

  async function startCheckout(tier: string, authToken: string) {
    setCheckoutLoading(true)
    setError('')
    try {
      const keyRes = await fetch('/api/v1/subscriptions/stripe-key')
      const keyData = await keyRes.json().catch(() => ({}))
      if (!keyRes.ok) throw new Error(keyData?.detail || 'Payment system not configured')
      
      if (!keyData?.publishable_key || typeof keyData.publishable_key !== 'string') {
        throw new Error('Invalid Stripe configuration')
      }

      const res = await fetch('/api/v1/subscriptions/subscription-intent', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          Authorization: `Bearer ${authToken}` 
        },
        body: JSON.stringify({ tier }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail || 'Unable to start subscription')
      
      if (data?.status === 'active') {
        navigate('/dashboard')
        return
      }
      
      if (!data?.client_secret || typeof data.client_secret !== 'string') {
        throw new Error('Missing payment information')
      }

      setPublishableKey(keyData.publishable_key)
      setClientSecret(data.client_secret)
      setPaymentModalOpen(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to start checkout')
    } finally {
      setCheckoutLoading(false)
    }
  }

  async function handlePaymentConfirmed(_paymentIntentId: string) {
    navigate('/dashboard')
  }

  function handlePaymentModalClose() {
    setPaymentModalOpen(false)
    setPaymentCancelled(true)
  }

  async function retryCheckout() {
    if (!planInfo) return
    const authToken = useAuthStore.getState().token
    if (authToken) {
      setPaymentCancelled(false)
      await startCheckout(planInfo.tier, authToken)
    } else {
      navigate(`/login?next=${encodeURIComponent(`/dashboard?checkout=${planInfo.tier}`)}`)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (!acceptedTerms) {
      setError('You must accept the Terms of Service and Privacy Policy to continue.')
      return
    }
    
    try {
      await signup(email, password, name)
      setSignupComplete(true)
      
      if (selectedPlan && planInfo && planInfo.tier !== 'enterprise') {
        const authToken = useAuthStore.getState().token
        if (authToken) {
          await startCheckout(planInfo.tier, authToken)
        } else {
          navigate(`/dashboard?checkout=${planInfo.tier}`)
        }
      } else if (selectedPlan && planInfo?.tier === 'enterprise') {
        navigate('/pricing?plan=enterprise&contact=true')
      } else {
        const from = (location.state as { from?: string } | null)?.from
        if (from) {
          navigate(from)
        } else {
          setShowNextSteps(true)
        }
      }
    } catch {
      setError('Failed to create account. Please try again.')
    }
  }

  const colorClasses = {
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', iconBg: 'bg-blue-100', iconText: 'text-blue-600' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-200', iconBg: 'bg-purple-100', iconText: 'text-purple-600' },
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200', iconBg: 'bg-emerald-100', iconText: 'text-emerald-600' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', iconBg: 'bg-amber-100', iconText: 'text-amber-600' },
  }

  const planColors = planInfo ? colorClasses[planInfo.color as keyof typeof colorClasses] : null

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {planInfo && planColors && (
          <div className={`mb-6 p-4 rounded-xl border-2 ${planColors.bg} ${planColors.border}`}>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${planColors.iconBg}`}>
                <Crown className={`w-5 h-5 ${planColors.iconText}`} />
              </div>
              <div>
                <p className="font-semibold text-gray-900">
                  You're signing up for {planInfo.name}
                </p>
                <p className="text-sm text-gray-600">
                  {planInfo.price} - You'll complete checkout after registration
                </p>
              </div>
            </div>
          </div>
        )}
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Create your account</h1>
          <p className="text-gray-600">
            {planInfo ? `Complete registration to activate your ${planInfo.name} plan` : 'Start building your startup today'}
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                Full name
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="John Doe"
              />
            </div>
            
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="••••••••"
              />
              <p className="mt-1 text-xs text-gray-500">Must be at least 8 characters</p>
            </div>

            <div className="flex items-start gap-3">
              <button
                type="button"
                onClick={() => setAcceptedTerms(!acceptedTerms)}
                className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                  acceptedTerms 
                    ? 'bg-purple-600 border-purple-600' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                {acceptedTerms && <Check className="w-3 h-3 text-white" />}
              </button>
              <label 
                onClick={() => setAcceptedTerms(!acceptedTerms)}
                className="text-sm text-gray-600 cursor-pointer select-none"
              >
                I agree to the{' '}
                <Link 
                  to="/terms" 
                  target="_blank"
                  className="text-purple-600 hover:text-purple-700 font-medium"
                  onClick={(e) => e.stopPropagation()}
                >
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link 
                  to="/privacy" 
                  target="_blank"
                  className="text-purple-600 hover:text-purple-700 font-medium"
                  onClick={(e) => e.stopPropagation()}
                >
                  Privacy Policy
                </Link>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading || checkoutLoading || showNextSteps || paymentModalOpen}
              className="w-full py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating account...
                </>
              ) : checkoutLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Preparing checkout...
                </>
              ) : (
                'Create account'
              )}
            </button>
          </form>

          {showNextSteps && !signupComplete && (
            <div className="mt-8 border-t border-gray-100 pt-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Next, choose how you want to start
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                You now have a free Explorer account. You can keep browsing for free or upgrade to unlock more data.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => navigate('/dashboard')}
                  className="w-full py-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-800"
                >
                  Continue with free Explorer plan
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/pricing?from=signup&plan=builder')}
                  className="w-full py-3 bg-gray-900 text-white rounded-lg hover:bg-emerald-700 text-sm font-medium"
                >
                  View paid plans & upgrade
                </button>
              </div>
            </div>
          )}

          {paymentCancelled && signupComplete && planInfo && (
            <div className="mt-8 border-t border-gray-100 pt-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Complete your {planInfo.name} subscription
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                Your account is ready! Complete payment to activate your {planInfo.name} plan, or continue with the free tier.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => navigate('/dashboard')}
                  className="w-full py-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-800"
                >
                  Continue with free plan
                </button>
                <button
                  type="button"
                  onClick={retryCheckout}
                  disabled={checkoutLoading}
                  className="w-full py-3 bg-gray-900 text-white rounded-lg hover:bg-emerald-700 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {checkoutLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    `Subscribe to ${planInfo.name}`
                  )}
                </button>
              </div>
            </div>
          )}

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">Or continue with</span>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-3">
              <button 
                type="button"
                onClick={() => startGoogleAuth(selectedPlan ? `/dashboard?checkout=${selectedPlan}` : '/dashboard')}
                className="w-full py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-700"
              >
                Google
              </button>
              <button 
                type="button"
                onClick={() => startReplitAuth(selectedPlan ? `/dashboard?checkout=${selectedPlan}` : '/dashboard')}
                className="w-full py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-700"
              >
                Replit
              </button>
              <button 
                type="button"
                onClick={() => startLinkedInAuth(selectedPlan ? `/dashboard?checkout=${selectedPlan}` : '/dashboard')}
                className="w-full py-2.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-700"
              >
                LinkedIn
              </button>
            </div>
          </div>
        </div>

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium">
            Sign in
          </Link>
        </p>
      </div>

      {paymentModalOpen && publishableKey && clientSecret && planInfo && (
        <PayPerUnlockModal
          publishableKey={publishableKey}
          clientSecret={clientSecret}
          amountLabel={planInfo.price}
          contextLabel="Subscription"
          title={`Subscribe to ${planInfo.name} for ${planInfo.price}`}
          confirmLabel="Subscribe"
          footnote="Your plan activates immediately after payment."
          onClose={handlePaymentModalClose}
          onConfirmed={handlePaymentConfirmed}
        />
      )}
    </div>
  )
}
