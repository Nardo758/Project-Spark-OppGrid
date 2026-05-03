import { useMemo, useState } from 'react'
import { Elements, CardElement, useElements, useStripe } from '@stripe/react-stripe-js'
import { loadStripe } from '@stripe/stripe-js'

type Props = {
  publishableKey: string
  clientSecret: string
  amountLabel: string
  contextLabel?: string
  title?: string
  confirmLabel?: string
  footnote?: string
  onClose: () => void
  onConfirmed: (paymentIntentId: string) => Promise<void>
}

type InnerProps = Omit<Props, 'publishableKey'>

function PayPerUnlockInner({
  clientSecret,
  amountLabel,
  contextLabel,
  title,
  confirmLabel,
  footnote,
  onClose,
  onConfirmed,
}: InnerProps) {
  const stripe = useStripe()
  const elements = useElements()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit() {
    setError(null)
    if (!stripe || !elements) return
    const card = elements.getElement(CardElement)
    if (!card) return

    try {
      setSubmitting(true)
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card: card as any },
      })

      if (result.error) {
        setError(result.error.message || 'Payment failed.')
        return
      }

      const pi = result.paymentIntent
      const ok = pi && (pi.status === 'succeeded' || pi.status === 'processing')
      if (!ok) {
        setError(`Payment not completed (status: ${pi?.status || 'unknown'}).`)
        return
      }

      await onConfirmed(pi.id)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 shadow-xl">
        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">{contextLabel || 'Pay‑per‑unlock'}</div>
            <div className="text-lg font-semibold text-gray-900">{title || `Unlock for ${amountLabel}`}</div>
          </div>
          <button onClick={onClose} className="px-3 py-2 text-gray-600 hover:text-gray-900">
            ✕
          </button>
        </div>

        <div className="p-5">
          <div className="text-sm text-gray-600 mb-3">Enter your card details:</div>
          <div className="border border-gray-200 rounded-lg p-3">
            <CardElement options={{ hidePostalCode: true }} />
          </div>

          {error && (
            <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="mt-5 flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={submit}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium disabled:opacity-50"
              disabled={submitting || !stripe || !elements}
            >
              {submitting ? 'Processing…' : confirmLabel || `Pay ${amountLabel}`}
            </button>
          </div>

          <div className="mt-4 text-xs text-gray-500">
            {footnote || 'Your access will be granted after payment confirmation.'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function PayPerUnlockModal(props: Props) {
  const stripePromise = useMemo(() => loadStripe(props.publishableKey), [props.publishableKey])
  const options = useMemo(() => ({ clientSecret: props.clientSecret }), [props.clientSecret])

  return (
    <Elements stripe={stripePromise} options={options}>
      <PayPerUnlockInner
        clientSecret={props.clientSecret}
        amountLabel={props.amountLabel}
        contextLabel={props.contextLabel}
        title={props.title}
        confirmLabel={props.confirmLabel}
        footnote={props.footnote}
        onClose={props.onClose}
        onConfirmed={props.onConfirmed}
      />
    </Elements>
  )
}

