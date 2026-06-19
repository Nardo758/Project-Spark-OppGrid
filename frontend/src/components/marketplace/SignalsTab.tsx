import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Search,
  Filter,
  MapPin,
  Building2,
  TrendingUp,
  Star,
  Lock,
  ShoppingCart,
  Bell,
  ChevronRight,
  Loader2,
  CheckCircle,
  Zap,
  Radio,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface MarketplaceSignal {
  id: number
  title: string
  category: string
  subcategory: string | null
  location: string | null
  quality_score: number
  price: number
  source_platform: string | null
  confidence_tier: string | null
  ai_summary: string | null
  ai_urgency_level: string | null
  market_size: string | null
  verified: boolean
  is_purchased: boolean
  created_at: string | null
}

interface MarketplaceResponse {
  items: MarketplaceSignal[]
  total: number
  categories: { id: string; name: string; count: number }[]
}

const industries = ['All Industries', 'Healthcare', 'E-commerce', 'FinTech', 'SaaS', 'Manufacturing', 'Services']

export default function SignalsTab() {
  const { isAuthenticated, token } = useAuthStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIndustry, setSelectedIndustry] = useState('All Industries')
  const [signals, setSignals] = useState<MarketplaceSignal[]>([])
  const [totalSignals, setTotalSignals] = useState(0)
  const [categories, setCategories] = useState<{ id: string; name: string; count: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [purchasing, setPurchasing] = useState<number | null>(null)
  const [sortBy, setSortBy] = useState('quality')

  useEffect(() => {
    let cancelled = false

    async function fetchSignals() {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        if (searchQuery) params.append('search', searchQuery)
        if (selectedIndustry !== 'All Industries') params.append('category', selectedIndustry.toLowerCase())
        params.append('sort_by', sortBy)

        const headers: Record<string, string> = {}
        if (token) headers['Authorization'] = `Bearer ${token}`

        const response = await fetch(`/api/v1/marketplace/signals/browse?${params}`, { headers })
        if (!response.ok) return
        const data: MarketplaceResponse = await response.json()
        if (cancelled) return
        setSignals(data.items)
        setTotalSignals(data.total)
        setCategories(data.categories)
      } catch (error) {
        console.error('Failed to fetch signals:', error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchSignals()
    return () => {
      cancelled = true
    }
  }, [searchQuery, selectedIndustry, sortBy, token])

  const handlePurchase = async (signalId: number) => {
    if (!isAuthenticated || !token) return

    setPurchasing(signalId)
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      if (token) headers['Authorization'] = `Bearer ${token}`

      const response = await fetch('/api/v1/marketplace/signals/purchase', {
        method: 'POST',
        headers,
        body: JSON.stringify({ signal_id: signalId }),
      })

      if (response.ok) {
        setSignals((prev) =>
          prev.map((sig) => (sig.id === signalId ? { ...sig, is_purchased: true } : sig)),
        )
      }
    } catch (error) {
      console.error('Failed to purchase signal:', error)
    } finally {
      setPurchasing(null)
    }
  }

  const getQualityLabel = (score: number) => {
    if (score >= 80) return 'Excellent'
    if (score >= 60) return 'Good'
    return 'Standard'
  }

  const getConfidenceBadge = (tier: string | null) => {
    if (!tier) return null
    const colors: Record<string, string> = {
      goldmine: 'bg-amber-100 text-amber-700',
      validated: 'bg-blue-100 text-blue-700',
      weak_signal: 'bg-gray-100 text-gray-600',
      noise: 'bg-red-100 text-red-700',
    }
    return colors[tier] || 'bg-gray-100 text-gray-600'
  }

  const getUrgencyBadge = (level: string | null) => {
    if (!level) return null
    const colors: Record<string, string> = {
      critical: 'bg-red-100 text-red-700',
      high: 'bg-orange-100 text-orange-700',
      medium: 'bg-yellow-100 text-yellow-700',
      low: 'bg-green-100 text-green-700',
    }
    return colors[level] || 'bg-gray-100 text-gray-600'
  }

  return (
    <div>
      {/* Compact stats strip */}
      <div className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-gray-600">
        <span><span className="font-semibold text-gray-900">{totalSignals || 0}</span> active signals</span>
        <span><span className="font-semibold text-gray-900">{categories.length}</span> categories</span>
        <span><span className="font-semibold text-gray-900">AI-Powered</span> scoring</span>
        <span><span className="font-semibold text-gray-900">Real-time</span> pipeline</span>
      </div>

      {/* Compact filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search market signals by keyword, industry, or location..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>
        <select
          value={selectedIndustry}
          onChange={(e) => setSelectedIndustry(e.target.value)}
          className="text-sm px-3 py-2 border border-gray-200 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
        >
          {industries.map((ind) => (
            <option key={ind} value={ind}>
              {ind}
            </option>
          ))}
        </select>
        <button className="text-sm px-3 py-2 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg flex items-center gap-2 transition-colors text-gray-700">
          <Filter className="w-4 h-4" />
          More
        </button>
      </div>

      <div className="flex gap-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500">
              {loading ? 'Loading...' : `Showing ${signals.length} of ${totalSignals} signals`}
            </p>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700"
            >
              <option value="quality">Quality Score</option>
              <option value="recent">Newest First</option>
              <option value="price">Price</option>
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : signals.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <Radio className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No signals found</h3>
              <p className="text-gray-600">
                {searchQuery || selectedIndustry !== 'All Industries'
                  ? 'Try adjusting your filters or search query'
                  : 'Market signals will appear here as the pipeline discovers real opportunities'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {signals.map((sig) => (
                <div
                  key={sig.id}
                  className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className="text-xs font-mono text-gray-400">SIG-{sig.id}</span>
                        {sig.verified && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Verified
                          </span>
                        )}
                        {sig.confidence_tier && (
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full capitalize ${getConfidenceBadge(sig.confidence_tier)}`}>
                            {sig.confidence_tier.replace('_', ' ')}
                          </span>
                        )}
                        {sig.ai_urgency_level && (
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full capitalize ${getUrgencyBadge(sig.ai_urgency_level)}`}>
                            <Zap className="w-3 h-3 inline mr-0.5" />
                            {sig.ai_urgency_level}
                          </span>
                        )}
                        {sig.is_purchased && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                            Unlocked
                          </span>
                        )}
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {sig.title}
                      </h3>

                      {sig.ai_summary && (
                        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                          {sig.ai_summary}
                        </p>
                      )}

                      <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
                        <span className="flex items-center gap-1">
                          <Building2 className="w-4 h-4" />
                          {sig.category || 'General'}
                          {sig.subcategory && ` / ${sig.subcategory}`}
                        </span>
                        {sig.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {sig.location}
                          </span>
                        )}
                        {sig.source_platform && (
                          <span className="flex items-center gap-1">
                            <TrendingUp className="w-4 h-4" />
                            Source: {sig.source_platform}
                          </span>
                        )}
                        {sig.market_size && (
                          <span className="flex items-center gap-1 text-emerald-600">
                            <Star className="w-4 h-4" />
                            {sig.market_size}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                          <span className="font-medium">{sig.quality_score}</span>
                          <span className="text-gray-400 text-sm">{getQualityLabel(sig.quality_score)}</span>
                        </div>
                        {sig.created_at && (
                          <div className="text-gray-400 text-sm">
                            Discovered {new Date(sig.created_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="text-right ml-6">
                      <div className="text-2xl font-bold text-gray-900">${sig.price}</div>
                      <div className="text-sm text-gray-500 mb-3">unlock</div>

                      {sig.is_purchased ? (
                        <button
                          disabled
                          className="w-full px-4 py-2 bg-green-100 text-green-700 rounded-lg flex items-center justify-center gap-2"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Unlocked
                        </button>
                      ) : isAuthenticated ? (
                        <button
                          onClick={() => handlePurchase(sig.id)}
                          disabled={purchasing === sig.id}
                          className="w-full px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          {purchasing === sig.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <ShoppingCart className="w-4 h-4" />
                          )}
                          {purchasing === sig.id ? 'Processing...' : 'Unlock Signal'}
                        </button>
                      ) : (
                        <Link
                          to="/signup"
                          className="w-full px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2"
                        >
                          <Lock className="w-4 h-4" />
                          Sign Up to Unlock
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="hidden lg:block w-80 flex-shrink-0">
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 sticky top-36">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Save This Search
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              Get notified when new market signals match your criteria.
            </p>
            {isAuthenticated ? (
              <button className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium">
                Create Alert
              </button>
            ) : (
              <Link
                to="/signup"
                className="block w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium text-center"
              >
                Sign Up for Alerts
              </Link>
            )}
          </div>

          {categories.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">Categories</h3>
              <div className="space-y-2">
                {categories
                  .filter((c) => c.count > 0)
                  .map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => setSelectedIndustry(cat.name)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                        selectedIndustry === cat.name
                          ? 'bg-emerald-600 text-white'
                          : 'hover:bg-gray-100'
                      }`}
                    >
                      <span>{cat.name}</span>
                      <span className={selectedIndustry === cat.name ? 'text-white/70' : 'text-gray-400'}>
                        {cat.count}
                      </span>
                    </button>
                  ))}
              </div>
            </div>
          )}

          <div className="bg-gradient-to-br from-gray-900 to-black rounded-xl p-6 text-white">
            <h3 className="font-semibold mb-2">How It Works</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                  1
                </div>
                <p className="text-gray-300">AI scans real market data from Reddit, Yelp, Twitter & more</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                  2
                </div>
                <p className="text-gray-300">Signals are scored, summarized, and classified by confidence</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                  3
                </div>
                <p className="text-gray-300">Unlock full details to access source data + AI analysis</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
