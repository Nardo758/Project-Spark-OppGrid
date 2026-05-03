import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Code,
  Key,
  Book,
  Zap,
  Shield,
  Globe,
  Copy,
  Check,
  ChevronRight,
  Terminal,
  ExternalLink,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import EnterpriseContactModal from '../components/EnterpriseContactModal'

// ─── Data ─────────────────────────────────────────────────────────────────────

const endpoints = [
  {
    method: 'GET',
    path: '/v1/opportunities',
    description: 'List opportunities with filters (sector, region, score)',
  },
  {
    method: 'GET',
    path: '/v1/opportunities/{id}',
    description: 'Get full details for a specific opportunity',
  },
  {
    method: 'GET',
    path: '/v1/trends',
    description: 'Get aggregated market trend signals',
  },
  {
    method: 'GET',
    path: '/v1/markets',
    description: 'List all tracked market segments with activity scores',
  },
  {
    method: 'GET',
    path: '/v1/markets/{region}',
    description: 'Get regional market breakdown by category',
  },
]

const apiTiers = [
  {
    id: 'starter',
    name: 'Starter',
    price: '$99',
    priceLabel: '/mo',
    summary: '1,000 req/day · 10 RPM',
    popular: false,
    features: [
      'All 5 public endpoints',
      '1,000 requests per day',
      '10 requests per minute',
      '24-hour data freshness',
      'Community support',
    ],
  },
  {
    id: 'professional',
    name: 'Professional',
    price: '$499',
    priceLabel: '/mo',
    summary: '10,000 req/day · 100 RPM',
    popular: true,
    features: [
      'All 5 public endpoints',
      '10,000 requests per day',
      '100 requests per minute',
      '1-hour data freshness',
      'Raw source access',
      'Priority support',
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    priceLabel: '',
    summary: '100,000+ req/day · 1,000 RPM',
    popular: false,
    features: [
      'All 5 public endpoints',
      '100,000+ requests per day',
      '1,000 requests per minute',
      'Real-time data freshness',
      'Raw source access + heatmap',
      'Dedicated SLA & support',
    ],
  },
]

// ─── Component ─────────────────────────────────────────────────────────────────

export default function ApiPortal() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [copied, setCopied] = useState(false)
  const [showEnterpriseModal, setShowEnterpriseModal] = useState(false)

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleTierCta(tierId: string) {
    if (tierId === 'enterprise') {
      setShowEnterpriseModal(true)
      return
    }
    if (isAuthenticated) {
      navigate('/settings/api')
    } else {
      navigate('/signup')
    }
  }

  const exampleCode = `curl -X GET "https://api.oppgrid.com/v1/opportunities" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json"`

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-black text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 rounded-full text-sm mb-6">
              <Code className="w-4 h-4" />
              Developer Platform
            </div>
            <h1 className="text-4xl font-bold mb-4">OppGrid Public API</h1>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
              Programmatic access to opportunities, market trends, and regional intelligence.
              Build integrations in minutes with our RESTful v1 API.
            </p>
          </div>

          <div className="mt-8 flex flex-wrap justify-center gap-4">
            {isAuthenticated ? (
              <>
                <button
                  onClick={() => navigate('/settings/api')}
                  className="px-6 py-3 bg-white text-gray-900 rounded-lg font-semibold hover:bg-gray-100 transition-colors flex items-center gap-2"
                >
                  <Key className="w-5 h-5" />
                  Get API Key
                </button>
                <a
                  href="/v1/docs"
                  className="px-6 py-3 border border-white/30 rounded-lg font-semibold hover:bg-white/10 transition-colors flex items-center gap-2"
                >
                  <Book className="w-5 h-5" />
                  View Docs
                </a>
              </>
            ) : (
              <>
                <Link
                  to="/signup"
                  className="px-6 py-3 bg-white text-gray-900 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
                >
                  Get Started Free
                </Link>
                <a
                  href="#pricing"
                  className="px-6 py-3 border border-white/30 rounded-lg font-semibold hover:bg-white/10 transition-colors"
                >
                  View Pricing
                </a>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Feature cards */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Rate-limited by Plan</h3>
            <p className="text-gray-600">
              10–1,000 requests per minute depending on your API tier. All limits are enforced
              per key for consistent performance.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Secure by Default</h3>
            <p className="text-gray-600">
              API key authentication via <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">X-API-Key</code> header.
              Generate and revoke keys instantly from your settings.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
              <Globe className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Fresh Market Data</h3>
            <p className="text-gray-600">
              Data freshness from 24 hours (Starter) to real-time (Enterprise) — always
              sourced from OppGrid's live intelligence pipeline.
            </p>
          </div>
        </div>

        {/* Quick start */}
        <div className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Quick Start</h2>
          <div className="bg-slate-900 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 bg-slate-800">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-400">bash</span>
              </div>
              <button
                onClick={() => handleCopy(exampleCode)}
                className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="p-4 text-sm text-gray-300 overflow-x-auto">
              <code>{exampleCode}</code>
            </pre>
          </div>
          <p className="mt-3 text-sm text-gray-500">
            Authenticate every request with your API key using the{' '}
            <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">X-API-Key</code> header.{' '}
            {isAuthenticated ? (
              <Link to="/settings/api" className="text-emerald-600 hover:underline">
                Generate a key →
              </Link>
            ) : (
              <Link to="/signup" className="text-emerald-600 hover:underline">
                Sign up to get a key →
              </Link>
            )}
          </p>
        </div>

        {/* Endpoints */}
        <div className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Available Endpoints</h2>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900">
                    Method
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900">
                    Endpoint
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900">
                    Description
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-semibold text-gray-900">
                    Auth
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {endpoints.map((endpoint, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 text-xs font-mono font-bold rounded bg-blue-100 text-blue-700">
                        {endpoint.method}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-gray-900">
                      {endpoint.path}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{endpoint.description}</td>
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-1 text-sm text-gray-500">
                        <Key className="w-3 h-3" />
                        Required
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <a
                href="/v1/docs"
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                View full API documentation (Swagger UI)
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>

        {/* Pricing */}
        <div id="pricing" className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">API Pricing</h2>
          <p className="text-gray-600 text-center mb-10">
            Three simple tiers. All include access to every v1 endpoint.
          </p>

          <div className="grid md:grid-cols-3 gap-6">
            {apiTiers.map((tier) => (
              <div
                key={tier.id}
                className={`bg-white rounded-xl border-2 p-6 transition-all ${
                  tier.popular
                    ? 'border-emerald-500 ring-2 ring-emerald-500/20'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                {tier.popular && (
                  <span className="inline-block px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full mb-4">
                    Most Popular
                  </span>
                )}
                <h3 className="text-xl font-bold text-gray-900">{tier.name}</h3>
                <div className="mt-2 mb-1">
                  <span className="text-3xl font-bold text-gray-900">{tier.price}</span>
                  <span className="text-gray-500 text-sm">{tier.priceLabel}</span>
                </div>
                <p className="text-sm text-gray-500 mb-6">{tier.summary}</p>
                <ul className="space-y-3 mb-6">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm text-gray-600">
                      <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => handleTierCta(tier.id)}
                  className={`w-full py-3 rounded-lg font-medium transition-colors ${
                    tier.popular
                      ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                      : tier.id === 'enterprise'
                        ? 'bg-gray-900 text-white hover:bg-emerald-700'
                        : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  {tier.id === 'enterprise'
                    ? 'Contact Sales'
                    : isAuthenticated
                      ? 'Get API Key'
                      : 'Get Started'}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="bg-gradient-to-br from-slate-900 to-black rounded-2xl p-8 text-white text-center">
          <h2 className="text-2xl font-bold mb-4">Ready to Build?</h2>
          <p className="text-gray-300 mb-6 max-w-xl mx-auto">
            Get your API key in seconds and start integrating OppGrid intelligence into your
            applications.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            {isAuthenticated ? (
              <button
                onClick={() => navigate('/settings/api')}
                className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white rounded-lg font-semibold hover:bg-emerald-600 transition-colors"
              >
                Get Your API Key
                <ChevronRight className="w-5 h-5" />
              </button>
            ) : (
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white rounded-lg font-semibold hover:bg-emerald-600 transition-colors"
              >
                Create Free Account
                <ChevronRight className="w-5 h-5" />
              </Link>
            )}
            <a
              href="/v1/docs"
              className="inline-flex items-center gap-2 px-6 py-3 border border-white/30 rounded-lg font-semibold hover:bg-white/10 transition-colors"
            >
              <Book className="w-5 h-5" />
              Explore the Docs
            </a>
          </div>
        </div>
      </div>

      {showEnterpriseModal && (
        <EnterpriseContactModal
          onClose={() => setShowEnterpriseModal(false)}
          source="api"
        />
      )}
    </div>
  )
}
