import { useState } from 'react'
import { Lightbulb, Wand2, CheckCircle, AlertCircle, Loader2, Lock, Sparkles, CreditCard } from 'lucide-react'
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { loadStripe } from '@stripe/stripe-js'
import { useAuthStore } from '../stores/authStore'
import { Link } from 'react-router-dom'

type GeneratedIdea = {
  refined_idea: string
  title: string
  problem_statement: string
  target_audience: string
  unique_value_proposition: string
  category: string
  preview_score: number
  preview_insights: string[]
}

type ValidationResult = {
  opportunity_score: number
  summary: string
  market_size_estimate: string
  competition_level: string
  urgency_level: string
  target_audience: string
  pain_intensity: number
  business_model_suggestions: string[]
  competitive_advantages: string[]
  key_risks: string[]
  next_steps: string[]
  market_trends: string[]
  revenue_potential: string
  time_to_market: string
  validation_confidence: number
}

const VALIDATION_PRICE_CENTS = 999

function PaymentForm({
  clientSecret,
  validationId,
  onSuccess,
  onClose,
}: {
  clientSecret: string
  validationId: number
  onSuccess: (result: ValidationResult) => void
  onClose: () => void
}) {
  const stripe = useStripe()
  const elements = useElements()
  const { token } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit() {
    if (!stripe || !elements) return
    const card = elements.getElement(CardElement)
    if (!card) return

    setError(null)
    setSubmitting(true)

    try {
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card: card as any },
      })

      if (result.error) {
        setError(result.error.message || 'Payment failed')
        setSubmitting(false)
        return
      }

      const pi = result.paymentIntent
      if (!pi || (pi.status !== 'succeeded' && pi.status !== 'processing')) {
        setError(`Payment not completed (status: ${pi?.status || 'unknown'})`)
        setSubmitting(false)
        return
      }

      const runRes = await fetch(`/api/v1/idea-validations/${validationId}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ payment_intent_id: pi.id }),
      })

      if (!runRes.ok) {
        const data = await runRes.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to run validation')
      }

      const validation = await runRes.json()
      if (validation.result) {
        onSuccess(validation.result)
      } else {
        throw new Error('Validation completed but no results returned')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 shadow-xl">
        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">AI Idea Validation</div>
            <div className="text-lg font-semibold text-gray-900">Pay ${(VALIDATION_PRICE_CENTS / 100).toFixed(2)} for Full Analysis</div>
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

          <div className="mt-4 bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
            <strong className="text-gray-900">You'll receive:</strong>
            <ul className="mt-2 space-y-1 list-disc list-inside">
              <li>Comprehensive market analysis</li>
              <li>Competition breakdown</li>
              <li>Business model suggestions</li>
              <li>Risk assessment</li>
              <li>Actionable next steps</li>
            </ul>
          </div>

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
              onClick={handleSubmit}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium disabled:opacity-50 flex items-center gap-2"
              disabled={submitting || !stripe || !elements}
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4" />
                  Pay ${(VALIDATION_PRICE_CENTS / 100).toFixed(2)}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function IdeaEngine() {
  const { token, isAuthenticated } = useAuthStore()

  const [idea, setIdea] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedIdea, setGeneratedIdea] = useState<GeneratedIdea | null>(null)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [isStartingPayment, setIsStartingPayment] = useState(false)

  const [paymentModalOpen, setPaymentModalOpen] = useState(false)
  const [clientSecret, setClientSecret] = useState<string | null>(null)
  const [validationId, setValidationId] = useState<number | null>(null)
  const [stripePromise, setStripePromise] = useState<ReturnType<typeof loadStripe> | null>(null)

  async function handleGenerate() {
    if (!idea.trim()) return

    setIsGenerating(true)
    setGenerateError(null)
    setGeneratedIdea(null)
    setValidationResult(null)

    try {
      const res = await fetch('/api/v1/idea-engine/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea: idea.trim() }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to generate idea')
      }

      const result = await res.json()
      setGeneratedIdea(result)
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setIsGenerating(false)
    }
  }

  async function startPayment() {
    if (!generatedIdea || !token) return

    setIsStartingPayment(true)
    setGenerateError(null)

    try {
      const keyRes = await fetch('/api/v1/idea-engine/stripe-key')
      if (!keyRes.ok) throw new Error('Could not load payment configuration')
      const keyData = await keyRes.json()
      const stripeInstance = loadStripe(keyData.publishable_key)

      const intentRes = await fetch('/api/v1/idea-validations/create-payment-intent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          idea: generatedIdea.refined_idea,
          title: generatedIdea.title,
          category: generatedIdea.category,
          amount_cents: VALIDATION_PRICE_CENTS,
        }),
      })

      if (!intentRes.ok) {
        const data = await intentRes.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to start payment')
      }

      const intentData = await intentRes.json()
      
      setStripePromise(stripeInstance)
      setClientSecret(intentData.client_secret)
      setValidationId(intentData.idea_validation_id)
      setPaymentModalOpen(true)
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Failed to start payment')
    } finally {
      setIsStartingPayment(false)
    }
  }

  function handleValidationSuccess(result: ValidationResult) {
    setValidationResult(result)
    setPaymentModalOpen(false)
    setClientSecret(null)
    setValidationId(null)
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Lightbulb className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">AI Idea Engine</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Validate your business idea with AI-powered analysis. Get instant feedback on 
          market potential, competition, and feasibility.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-8 mb-8">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Describe your business idea
        </label>
        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="Example: A mobile app that connects local farmers directly with restaurants, eliminating middlemen and ensuring fresh produce delivery within 24 hours..."
          rows={6}
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
        <div className="mt-4 flex justify-between items-center">
          <span className="text-sm text-gray-500">
            {idea.length}/2000 characters
          </span>
          <button
            onClick={handleGenerate}
            disabled={!idea.trim() || isGenerating}
            className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Wand2 className="w-5 h-5" />
                Refine Idea (Free)
              </>
            )}
          </button>
        </div>

        {generateError && (
          <div className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            {generateError}
          </div>
        )}
      </div>

      {generatedIdea && !validationResult && (
        <div className="bg-white rounded-2xl border border-gray-200 p-8 mb-8 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">{generatedIdea.title}</h2>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              generatedIdea.preview_score >= 70 ? 'bg-green-50 text-green-700' :
              generatedIdea.preview_score >= 50 ? 'bg-yellow-50 text-yellow-700' :
              'bg-red-50 text-red-700'
            }`}>
              <Sparkles className="w-5 h-5" />
              <span className="font-bold text-lg">{generatedIdea.preview_score} Preview Score</span>
            </div>
          </div>

          <p className="text-gray-700 mb-6">{generatedIdea.refined_idea}</p>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-500 mb-1">Target Audience</div>
              <div className="text-gray-900">{generatedIdea.target_audience}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-500 mb-1">Category</div>
              <div className="text-gray-900">{generatedIdea.category}</div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-medium text-gray-900 mb-3">Preview Insights</h3>
            <ul className="space-y-2">
              {generatedIdea.preview_insights.map((insight, i) => (
                <li key={i} className="flex items-start gap-3 text-gray-600">
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                  {insight}
                </li>
              ))}
            </ul>
          </div>

          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center gap-4 mb-4">
              <Lock className="w-5 h-5 text-gray-400" />
              <span className="text-gray-600">Unlock full market analysis, risk assessment, and actionable insights</span>
            </div>
            {isAuthenticated ? (
              <button
                onClick={startPayment}
                disabled={isStartingPayment}
                className="w-full px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg hover:from-green-600 hover:to-emerald-700 font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isStartingPayment ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Starting payment...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-5 h-5" />
                    Get Full Validation (${(VALIDATION_PRICE_CENTS / 100).toFixed(2)})
                  </>
                )}
              </button>
            ) : (
              <Link
                to={`/login?next=${encodeURIComponent('/idea-engine')}`}
                className="w-full px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium text-center block"
              >
                Sign in to Get Full Validation
              </Link>
            )}
          </div>
        </div>
      )}

      {validationResult && (
        <div className="bg-white rounded-2xl border border-gray-200 p-8 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Full Validation Results</h2>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              validationResult.opportunity_score >= 70 ? 'bg-green-50 text-green-700' :
              validationResult.opportunity_score >= 50 ? 'bg-yellow-50 text-yellow-700' :
              'bg-red-50 text-red-700'
            }`}>
              {validationResult.opportunity_score >= 70 ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <span className="font-bold text-lg">{validationResult.opportunity_score}% Score</span>
            </div>
          </div>

          <p className="text-gray-700 mb-6">{validationResult.summary}</p>

          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-500 mb-1">Market Size</div>
              <div className="text-gray-900 font-medium">{validationResult.market_size_estimate}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-500 mb-1">Competition</div>
              <div className="text-gray-900 font-medium capitalize">{validationResult.competition_level}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-500 mb-1">Revenue Potential</div>
              <div className="text-gray-900 font-medium">{validationResult.revenue_potential}</div>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <h3 className="font-medium text-gray-900 mb-3">Business Model Suggestions</h3>
              <ul className="space-y-2">
                {validationResult.business_model_suggestions.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-600">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-3">Key Risks</h3>
              <ul className="space-y-2">
                {validationResult.key_risks.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-600">
                    <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-3">Next Steps</h3>
              <ul className="space-y-2">
                {validationResult.next_steps.map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-600">
                    <Sparkles className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row gap-4">
              <button className="flex-1 px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium">
                Generate Full Roadmap
              </button>
              <Link to="/discover" className="flex-1 px-6 py-3 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 font-medium text-center">
                Find Similar Opportunities
              </Link>
            </div>
          </div>
        </div>
      )}

      {paymentModalOpen && clientSecret && validationId && stripePromise && (
        <Elements stripe={stripePromise} options={{ clientSecret }}>
          <PaymentForm
            clientSecret={clientSecret}
            validationId={validationId}
            onSuccess={handleValidationSuccess}
            onClose={() => setPaymentModalOpen(false)}
          />
        </Elements>
      )}
    </div>
  )
}
