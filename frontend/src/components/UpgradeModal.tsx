import { useState } from 'react'
import { X, Zap, Lock, TrendingUp, FileText, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { LAUNCH_OFFERS } from '../constants/pricing'

interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  feature?: string
  context?: 'opportunity' | 'report' | 'analysis' | 'general'
  returnUrl?: string
}

const contextMessages = {
  opportunity: {
    title: 'Unlock Full Opportunity Access',
    description: 'Get complete market data, competitor analysis, and actionable insights for this opportunity.',
    icon: TrendingUp,
  },
  report: {
    title: 'Unlock AI-Generated Reports',
    description: 'Access detailed business reports including marketing plans, financial projections, and go-to-market strategies.',
    icon: FileText,
  },
  analysis: {
    title: 'Unlock Advanced Analysis',
    description: 'Get in-depth market research, demographic data, and location intelligence for your business idea.',
    icon: Zap,
  },
  general: {
    title: 'Upgrade Your Plan',
    description: 'Unlock premium features to accelerate your business journey.',
    icon: Lock,
  },
}

const benefits = [
  { icon: TrendingUp, text: 'Opportunity feed' },
  { icon: FileText, text: '2 reports each billing period' },
  { icon: Zap, text: 'Extra reports are the single Deep Clone purchase' },
]

export default function UpgradeModal({ isOpen, onClose, feature, context = 'general', returnUrl }: UpgradeModalProps) {
  const navigate = useNavigate()
  const { isAuthenticated, token } = useAuthStore()
  const [selectedPlan] = useState<string>('monthly')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  if (!isOpen) return null

  const contextInfo = contextMessages[context]
  const ContextIcon = contextInfo.icon

  async function handleCheckout() {
    if (!isAuthenticated) {
      onClose()
      navigate('/signup?plan=monthly')
      return
    }

    // Validate token is available
    if (!token) {
      setError('Please log in again to continue')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const baseUrl = window.location.origin
      const returnPath = returnUrl || (window.location.pathname + window.location.search + window.location.hash)
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent(returnPath)}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent(returnPath)}`
      const res = await fetch('/api/v1/subscriptions/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          tier: selectedPlan,
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
        // Redirect to Stripe Checkout
        window.location.href = data.url
      } else {
        throw new Error('No checkout URL returned')
      }
    } catch (e) {
      console.error('Checkout error:', e)
      setError(e instanceof Error ? e.message : 'Unable to start checkout')
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-white/20 rounded-lg">
              <ContextIcon className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold">{contextInfo.title}</h2>
          </div>
          <p className="text-white/90 text-sm">
            {contextInfo.description}
          </p>
          {feature && (
            <p className="mt-2 text-sm text-white/70">
              Feature: {feature}
            </p>
          )}
        </div>

        <div className="p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">What you'll get:</h3>
          <div className="space-y-2 mb-6">
            {benefits.map((benefit, i) => (
              <div key={i} className="flex items-center gap-3 text-sm text-gray-700">
                <benefit.icon className="w-4 h-4 text-purple-600 shrink-0" />
                <span>{benefit.text}</span>
              </div>
            ))}
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="mb-4 p-4 rounded-xl border-2 border-purple-600 bg-purple-50">
            <div className="font-semibold text-gray-900">{LAUNCH_OFFERS.monthly.name}</div>
            <div className="text-sm text-gray-600">{LAUNCH_OFFERS.monthly.priceLabel}</div>
            <div className="text-xs text-gray-500 mt-1">2 reports per billing period, plus the feed</div>
            <p className="text-xs text-gray-500 mt-2">
              A single Deep Clone report is {LAUNCH_OFFERS.deepClone.priceLabel}.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Maybe later
            </button>
            <button
              onClick={handleCheckout}
              disabled={!selectedPlan || isLoading}
              className="flex-1 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg text-sm font-semibold hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              Checkout
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function useUpgradeModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [context, setContext] = useState<UpgradeModalProps['context']>('general')
  const [feature, setFeature] = useState<string | undefined>()

  function openUpgradeModal(ctx?: UpgradeModalProps['context'], feat?: string) {
    setContext(ctx || 'general')
    setFeature(feat)
    setIsOpen(true)
  }

  function closeUpgradeModal() {
    setIsOpen(false)
  }

  return {
    isOpen,
    context,
    feature,
    openUpgradeModal,
    closeUpgradeModal,
  }
}
