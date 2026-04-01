import { useState } from 'react'
import { useAuthStore } from '../stores/authStore'

interface StudioReportCheckoutRequest {
  report_type: string
  success_url: string
  cancel_url: string
  email?: string
  report_context?: Record<string, any>
}

interface CheckoutResponse {
  session_id: string
  url: string
}

export function useStudioReportCheckout() {
  const { token } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const startCheckout = async (
    reportType: string,
    reportContext?: Record<string, any>,
    guestEmail?: string
  ) => {
    setLoading(true)
    setError(null)

    try {
      const baseUrl = window.location.origin
      const returnPath = window.location.pathname
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent(returnPath)}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent(returnPath)}`

      const payload: StudioReportCheckoutRequest = {
        report_type: reportType,
        success_url: successUrl,
        cancel_url: cancelUrl,
        ...(reportContext && { report_context: reportContext }),
        ...(guestEmail && { email: guestEmail }),
      }

      const res = await fetch('/api/v1/report-pricing/studio-report-checkout', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(payload),
      })

      const data = (await res.json()) as CheckoutResponse

      if (!res.ok) {
        throw new Error((data as any)?.detail || 'Failed to start checkout')
      }

      if (!data.url) {
        throw new Error('No checkout URL returned from server')
      }

      // Redirect to Stripe checkout
      window.location.href = data.url
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Checkout failed'
      setError(message)
      console.error('Checkout error:', e)
      throw e
    } finally {
      setLoading(false)
    }
  }

  return {
    startCheckout,
    loading,
    error,
  }
}
