import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { TIER_CONFIG, type Tier } from '../constants/pricing'

export interface InlinePaymentState {
  isLoading: boolean
  error: string | null
  paymentModalOpen: boolean
  publishableKey: string | null
  clientSecret: string | null
  selectedTier: Tier | null
  priceLabel: string | null
}

export interface UseInlinePaymentReturn {
  state: InlinePaymentState
  startCheckout: (tier: Tier) => Promise<void>
  closePaymentModal: () => void
  handlePaymentConfirmed: (paymentIntentId: string) => Promise<void>
  clearError: () => void
}

export function useInlinePayment(onSuccess?: () => void, returnTo?: string): UseInlinePaymentReturn {
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  
  const [state, setState] = useState<InlinePaymentState>({
    isLoading: false,
    error: null,
    paymentModalOpen: false,
    publishableKey: null,
    clientSecret: null,
    selectedTier: null,
    priceLabel: null,
  })

  const startCheckout = useCallback(async (tier: Tier) => {
    if (tier !== 'monthly') {
      setState((s) => ({
        ...s,
        isLoading: false,
        error: 'That plan is not available. Subscribe to OppGrid Monthly for $39/mo.',
      }))
      return
    }
    if (!token) {
      const returnPath = returnTo || window.location.pathname + window.location.search
      navigate(`/signup?plan=${tier}&next=${encodeURIComponent(returnPath)}`)
      return
    }

    setState(s => ({ ...s, isLoading: true, error: null, selectedTier: tier }))
    
    try {
      const keyRes = await fetch('/api/v1/subscriptions/stripe-key')
      const keyData = await keyRes.json().catch(() => ({}))
      if (!keyRes.ok) {
        throw new Error(keyData?.detail || 'Payment system not configured')
      }
      
      if (!keyData?.publishable_key || typeof keyData.publishable_key !== 'string') {
        throw new Error('Invalid Stripe configuration')
      }

      const res = await fetch('/api/v1/subscriptions/subscription-intent', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({ tier }),
      })
      const data = await res.json().catch(() => ({}))
      
      if (!res.ok) {
        throw new Error(data?.detail || 'Unable to start subscription')
      }
      
      // Handle success cases where no payment is needed (active, trialing, or subscription created)
      if (data?.status === 'active' || data?.status === 'trialing') {
        setState(s => ({ ...s, isLoading: false }))
        if (onSuccess) {
          onSuccess()
        } else {
          navigate(returnTo || '/dashboard?subscription=success')
        }
        return
      }
      
      // Fallback: If we have a subscription ID but no client_secret, 
      // the subscription may have been created with a trial or already paid
      if (data?.stripe_subscription_id && !data?.client_secret) {
        console.log('Subscription created without payment required:', {
          stripeSubId: data.stripe_subscription_id,
          status: data?.status,
        })
        setState(s => ({ ...s, isLoading: false }))
        if (onSuccess) {
          onSuccess()
        } else {
          navigate(returnTo || '/dashboard?subscription=success')
        }
        return
      }
      
      if (!data?.client_secret || typeof data.client_secret !== 'string') {
        // Log more detail for debugging
        console.error('Subscription intent response missing client_secret:', {
          hasClientSecret: !!data?.client_secret,
          status: data?.status,
          stripeSubId: data?.stripe_subscription_id,
        })
        throw new Error('Payment setup incomplete. Please try again or contact support.')
      }

      const tierConfig = TIER_CONFIG[tier]
      setState(s => ({
        ...s,
        isLoading: false,
        publishableKey: keyData.publishable_key,
        clientSecret: data.client_secret,
        paymentModalOpen: true,
        priceLabel: tierConfig?.priceLabel || `$${tierConfig?.price}/mo`,
      }))
    } catch (e) {
      setState(s => ({
        ...s,
        isLoading: false,
        error: e instanceof Error ? e.message : 'Unable to start checkout',
      }))
    }
  }, [token, navigate, onSuccess, returnTo])

  const closePaymentModal = useCallback(() => {
    setState(s => ({
      ...s,
      paymentModalOpen: false,
      clientSecret: null,
    }))
  }, [])

  const handlePaymentConfirmed = useCallback(async (_paymentIntentId: string) => {
    setState(s => ({ ...s, paymentModalOpen: false }))
    if (onSuccess) {
      onSuccess()
    } else {
      navigate(returnTo || '/dashboard')
    }
  }, [navigate, onSuccess, returnTo])

  const clearError = useCallback(() => {
    setState(s => ({ ...s, error: null }))
  }, [])

  return {
    state,
    startCheckout,
    closePaymentModal,
    handlePaymentConfirmed,
    clearError,
  }
}
