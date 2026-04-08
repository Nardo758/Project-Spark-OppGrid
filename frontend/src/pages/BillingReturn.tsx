import { useEffect } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { CheckCircle, XCircle, Loader2, Mail, ArrowLeft } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

export default function BillingReturn() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const bootstrap = useAuthStore((s) => s.bootstrap)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const status = searchParams.get('status')
  const returnTo = searchParams.get('return_to')
  const email = searchParams.get('email')

  useEffect(() => {
    if (status === 'success' && isAuthenticated) {
      bootstrap()
    }
  }, [status, isAuthenticated, bootstrap])

  useEffect(() => {
    if (status === 'canceled') {
      const timer = setTimeout(() => {
        navigate(returnTo || '/')
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [status, returnTo, navigate])

  if (status === 'success') {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h1>
          <p className="text-gray-600 mb-6">
            Your report is being generated and will be ready within a few minutes.
          </p>

          {email ? (
            <div className="bg-[#0F6E56]/5 border border-[#0F6E56]/20 rounded-2xl p-5 mb-6 text-left">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-9 h-9 rounded-full bg-[#0F6E56]/10 flex items-center justify-center flex-shrink-0">
                  <Mail className="w-4 h-4 text-[#0F6E56]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Check your inbox</p>
                  <p className="text-xs text-gray-500">Sending to <span className="font-medium text-gray-700">{email}</span></p>
                </div>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                Your report will arrive by email with a direct link to view the full content — no account needed.
                Delivery typically takes 2–5 minutes.
              </p>
            </div>
          ) : (
            <div className="bg-[#0F6E56]/5 border border-[#0F6E56]/20 rounded-2xl p-5 mb-6 text-left">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-[#0F6E56]/10 flex items-center justify-center flex-shrink-0">
                  <Mail className="w-4 h-4 text-[#0F6E56]" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Your report is on its way</p>
                  <p className="text-xs text-gray-500">Check your account email — delivery takes 2–5 minutes.</p>
                </div>
              </div>
            </div>
          )}

          <Link
            to={returnTo || '/'}
            className="inline-flex items-center gap-2 text-sm font-medium text-[#0F6E56] hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Studio
          </Link>
        </div>
      </div>
    )
  }

  if (status === 'canceled') {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <XCircle className="w-8 h-8 text-amber-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Canceled</h1>
          <p className="text-gray-600 mb-6">No charges were made. Redirecting you back...</p>
          <Link
            to={returnTo || '/'}
            className="inline-flex items-center gap-2 text-sm font-medium text-gray-600 hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Go back now
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Processing your payment...</p>
      </div>
    </div>
  )
}
