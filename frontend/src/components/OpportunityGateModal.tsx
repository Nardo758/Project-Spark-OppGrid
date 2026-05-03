import { useState } from 'react'
import { X, Mail, Lock, Sparkles, FileText, Target, TrendingUp, ArrowRight, User, Globe, BarChart3, DollarSign } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

type Opportunity = {
  id: number
  title: string
  description?: string
  category?: string
  score?: number
}

type ReportOption = {
  id: string
  name: string
  price: number
  description: string
  icon: React.ComponentType<{ className?: string }>
  recommended?: boolean
}

const allReports: ReportOption[] = [
  { id: 'feasibility', name: 'Feasibility Study', price: 0, description: 'Quick viability check', icon: Target, recommended: true },
  { id: 'market-analysis', name: 'Market Analysis', price: 99, description: 'Industry & competitor insights', icon: TrendingUp },
  { id: 'strategic-assessment', name: 'Strategic Assessment', price: 89, description: 'SWOT & strategic positioning', icon: BarChart3 },
  { id: 'pestle', name: 'PESTLE Analysis', price: 79, description: 'External factors analysis', icon: Globe },
  { id: 'business-plan', name: 'Business Plan', price: 149, description: 'Comprehensive strategy', icon: FileText },
  { id: 'financials', name: 'Financial Model', price: 129, description: 'Revenue & cost projections', icon: DollarSign },
  { id: 'pitch-deck', name: 'Pitch Deck', price: 79, description: 'Investor presentation', icon: BarChart3 },
]

type Props = {
  isOpen: boolean
  onClose: () => void
  opportunity: Opportunity | null
  onPurchaseReport: (reportType: string, opportunity: Opportunity, guestEmail?: string) => void
}

export default function OpportunityGateModal({ isOpen, onClose, opportunity, onPurchaseReport }: Props) {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [emailSubmitted, setEmailSubmitted] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  if (!isOpen || !opportunity) return null

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('Please enter your email')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email')
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      await fetch('/api/leads/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          source: 'opportunity_gate',
          opportunity_id: opportunity.id,
          opportunity_title: opportunity.title,
        }),
      })
      setEmailSubmitted(true)
    } catch {
      setEmailSubmitted(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleViewDetails = () => {
    onClose()
    navigate(`/opportunity/${opportunity.id}`)
  }

  const handleReportPurchase = (reportId: string, capturedEmail?: string) => {
    onPurchaseReport(reportId, opportunity, capturedEmail)
    onClose()
  }

  const handleLogin = () => {
    onClose()
    navigate('/login', { state: { returnTo: `/opportunity/${opportunity.id}` } })
  }

  const handleSignup = () => {
    onClose()
    navigate('/signup', { state: { returnTo: `/opportunity/${opportunity.id}` } })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-5 h-5" />
            <span className="text-sm font-medium text-purple-200">Opportunity Intelligence</span>
          </div>
          <h2 className="text-xl font-bold">{opportunity.title}</h2>
          <div className="flex items-center gap-3 mt-2">
            {opportunity.category && (
              <span className="px-2 py-0.5 bg-white/20 rounded text-xs">{opportunity.category}</span>
            )}
            {opportunity.score && (
              <span className="px-2 py-0.5 bg-emerald-500/80 rounded text-xs font-medium">
                Score: {opportunity.score}
              </span>
            )}
          </div>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {isAuthenticated ? (
            <div className="space-y-4">
              <p className="text-gray-600 text-sm">
                Get detailed intelligence on this opportunity with AI-powered reports:
              </p>
              <div className="space-y-2">
                {allReports.map((report: ReportOption) => (
                  <button
                    key={report.id}
                    onClick={() => handleReportPurchase(report.id)}
                    className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-purple-50 border border-gray-200 hover:border-purple-300 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                        <report.icon className="w-5 h-5 text-purple-600" />
                      </div>
                      <div className="text-left">
                        <div className="font-medium text-gray-900">{report.name}</div>
                        <div className="text-xs text-gray-500">{report.description}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {report.price === 0 ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-bold">FREE</span>
                      ) : (
                        <span className="font-bold text-purple-600">${report.price}</span>
                      )}
                      <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-purple-600 transition-colors" />
                    </div>
                  </button>
                ))}
              </div>
              <div className="pt-4 border-t border-gray-100">
                <button
                  onClick={handleViewDetails}
                  className="w-full py-2 text-gray-600 hover:text-purple-600 text-sm font-medium transition-colors"
                >
                  Just view opportunity details →
                </button>
              </div>
            </div>
          ) : emailSubmitted ? (
            <div className="space-y-4">
              <div className="text-center py-4">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Mail className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">You're on the list!</h3>
                <p className="text-gray-600 text-sm">
                  Now get AI-powered reports for this opportunity:
                </p>
              </div>
              <div className="space-y-2">
                {allReports.map((report: ReportOption) => (
                  <button
                    key={report.id}
                    onClick={() => handleReportPurchase(report.id, email)}
                    className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-purple-50 border border-gray-200 hover:border-purple-300 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                        <report.icon className="w-5 h-5 text-purple-600" />
                      </div>
                      <div className="text-left">
                        <div className="font-medium text-gray-900">{report.name}</div>
                        <div className="text-xs text-gray-500">{report.description}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {report.price === 0 ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-bold">FREE</span>
                      ) : (
                        <span className="font-bold text-purple-600">${report.price}</span>
                      )}
                      <ArrowRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </button>
                ))}
              </div>
              <button
                onClick={handleViewDetails}
                className="w-full py-2 text-gray-600 hover:text-purple-600 text-sm font-medium transition-colors"
              >
                Just view opportunity details →
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <Lock className="w-8 h-8 text-gray-400 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Unlock This Opportunity</h3>
                <p className="text-gray-600 text-sm">
                  Enter your email to view details and get AI-powered reports
                </p>
              </div>

              <form onSubmit={handleEmailSubmit} className="space-y-3">
                <div>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter your email"
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                  </div>
                  {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 bg-purple-600 text-white font-medium rounded-xl hover:bg-purple-700 transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? 'Please wait...' : 'Continue with Email'}
                </button>
              </form>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">or</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={handleLogin}
                  className="flex items-center justify-center gap-2 py-2.5 border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700"
                >
                  <User className="w-4 h-4" />
                  Log In
                </button>
                <button
                  onClick={handleSignup}
                  className="flex items-center justify-center gap-2 py-2.5 bg-gray-900 text-white rounded-xl hover:bg-emerald-700 transition-colors text-sm font-medium"
                >
                  <Sparkles className="w-4 h-4" />
                  Sign Up Free
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
