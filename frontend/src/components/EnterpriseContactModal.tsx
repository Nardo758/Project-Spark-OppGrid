import { useState } from 'react'
import { X, Building2, Send, Loader2, CheckCircle2 } from 'lucide-react'

type Props = {
  onClose: () => void
  source?: string
}

export default function EnterpriseContactModal({ onClose, source = 'pricing' }: Props) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    teamSize: '',
    message: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      const res = await fetch('/api/v1/contact/enterprise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, source }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to submit. Please try again.')
      }

      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
        <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 shadow-xl p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Thank You!</h3>
          <p className="text-gray-600 mb-6">
            We've received your request. Our enterprise team will reach out within 24 hours.
          </p>
          <button
            onClick={onClose}
            className="px-6 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium"
          >
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-gray-200 shadow-xl">
        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-lg font-semibold text-gray-900">Contact Enterprise Sales</div>
              <div className="text-sm text-gray-500">Get unlimited access and priority support</div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Work Email</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="john@company.com"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
              <input
                type="text"
                required
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Acme Inc"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Team Size</label>
              <select
                value={formData.teamSize}
                onChange={(e) => setFormData({ ...formData, teamSize: e.target.value })}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Select size</option>
                <option value="1-10">1-10</option>
                <option value="11-50">11-50</option>
                <option value="51-200">51-200</option>
                <option value="201-500">201-500</option>
                <option value="500+">500+</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">What are you looking for?</label>
            <textarea
              rows={3}
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Tell us about your needs (optional)"
            />
          </div>

          {error && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
            <strong className="text-gray-900">Enterprise includes:</strong>
            <ul className="mt-2 space-y-1 list-disc list-inside">
              <li>Earliest access to HOT opportunities (0-7 days)</li>
              <li>Unlimited Deep Dive analyses</li>
              <li>Unlimited Execution Packages</li>
              <li>Dedicated account manager</li>
              <li>Custom API access</li>
            </ul>
          </div>

          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium text-gray-700"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium disabled:opacity-50 flex items-center gap-2"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Request Demo
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
