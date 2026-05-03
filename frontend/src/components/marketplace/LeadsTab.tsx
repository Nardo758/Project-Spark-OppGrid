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
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface MarketplaceLead {
  id: number
  category: string
  company: string | null
  location: string | null
  quality_score: number
  price: number
  contact_count: number
  last_active: string | null
  verified: boolean
  is_purchased: boolean
}

interface MarketplaceResponse {
  items: MarketplaceLead[]
  total: number
  categories: { id: string; name: string; count: number }[]
}

const industries = ['All Industries', 'Healthcare', 'E-commerce', 'FinTech', 'SaaS', 'Manufacturing', 'Services']

export default function LeadsTab() {
  const { isAuthenticated, token } = useAuthStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIndustry, setSelectedIndustry] = useState('All Industries')
  const [leads, setLeads] = useState<MarketplaceLead[]>([])
  const [totalLeads, setTotalLeads] = useState(0)
  const [categories, setCategories] = useState<{ id: string; name: string; count: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [purchasing, setPurchasing] = useState<number | null>(null)
  const [sortBy, setSortBy] = useState('recent')

  useEffect(() => {
    let cancelled = false

    async function fetchLeads() {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        if (searchQuery) params.append('search', searchQuery)
        if (selectedIndustry !== 'All Industries') params.append('category', selectedIndustry.toLowerCase())
        params.append('sort_by', sortBy)

        const headers: Record<string, string> = {}
        if (token) headers['Authorization'] = `Bearer ${token}`

        const response = await fetch(`/api/v1/marketplace/leads/browse?${params}`, { headers })
        if (!response.ok) return
        const data: MarketplaceResponse = await response.json()
        if (cancelled) return
        setLeads(data.items)
        setTotalLeads(data.total)
        setCategories(data.categories)
      } catch (error) {
        console.error('Failed to fetch leads:', error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchLeads()
    return () => {
      cancelled = true
    }
  }, [searchQuery, selectedIndustry, sortBy, token])

  const handlePurchase = async (leadId: number) => {
    if (!isAuthenticated) return

    setPurchasing(leadId)
    try {
      const response = await fetch('/api/v1/marketplace/leads/purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ lead_id: leadId }),
      })

      if (response.ok) {
        setLeads((prev) =>
          prev.map((lead) => (lead.id === leadId ? { ...lead, is_purchased: true } : lead)),
        )
      }
    } catch (error) {
      console.error('Failed to purchase lead:', error)
    } finally {
      setPurchasing(null)
    }
  }

  const getQualityLabel = (score: number) => {
    if (score >= 80) return 'Excellent'
    if (score >= 60) return 'Good'
    return 'Standard'
  }

  return (
    <div>
      {/* Compact stats strip */}
      <div className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-gray-600">
        <span><span className="font-semibold text-gray-900">{totalLeads || 0}</span> active leads</span>
        <span><span className="font-semibold text-gray-900">{categories.length}</span> categories</span>
        <span><span className="font-semibold text-gray-900">92%</span> response rate</span>
        <span><span className="font-semibold text-gray-900">90-day</span> access</span>
      </div>

      {/* Compact filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search leads by keyword, industry, or company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
          />
        </div>
        <select
          value={selectedIndustry}
          onChange={(e) => setSelectedIndustry(e.target.value)}
          className="text-sm px-3 py-2 border border-gray-200 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
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
              {loading ? 'Loading...' : `Showing ${leads.length} of ${totalLeads} leads`}
            </p>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700"
            >
              <option value="recent">Newest First</option>
              <option value="quality">Quality Score</option>
              <option value="price">Price</option>
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : leads.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No leads found</h3>
              <p className="text-gray-600">
                {searchQuery || selectedIndustry !== 'All Industries'
                  ? 'Try adjusting your filters or search query'
                  : 'New leads will appear here as they become available'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {leads.map((lead) => (
                <div
                  key={lead.id}
                  className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-mono text-gray-400">LD-{lead.id}</span>
                        {lead.verified && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Verified
                          </span>
                        )}
                        {lead.quality_score >= 80 && (
                          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">
                            Premium
                          </span>
                        )}
                        {lead.is_purchased && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                            Purchased
                          </span>
                        )}
                      </div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {lead.company || `Business Opportunity in ${lead.category}`}
                      </h3>

                      <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
                        <span className="flex items-center gap-1">
                          <Building2 className="w-4 h-4" />
                          {lead.category || 'General'}
                        </span>
                        {lead.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {lead.location}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <TrendingUp className="w-4 h-4" />
                          {lead.contact_count} contact{lead.contact_count !== 1 ? 's' : ''}
                        </span>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                          <span className="font-medium">{lead.quality_score}</span>
                          <span className="text-gray-400 text-sm">{getQualityLabel(lead.quality_score)}</span>
                        </div>
                        {lead.last_active && (
                          <div className="text-gray-400 text-sm">
                            Active {new Date(lead.last_active).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="text-right ml-6">
                      <div className="text-2xl font-bold text-gray-900">${lead.price}</div>
                      <div className="text-sm text-gray-500 mb-3">one-time</div>

                      {lead.is_purchased ? (
                        <button
                          disabled
                          className="w-full px-4 py-2 bg-green-100 text-green-700 rounded-lg flex items-center justify-center gap-2"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Purchased
                        </button>
                      ) : isAuthenticated ? (
                        <button
                          onClick={() => handlePurchase(lead.id)}
                          disabled={purchasing === lead.id}
                          className="w-full px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                          {purchasing === lead.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <ShoppingCart className="w-4 h-4" />
                          )}
                          {purchasing === lead.id ? 'Processing...' : 'Purchase Lead'}
                        </button>
                      ) : (
                        <Link
                          to="/signup"
                          className="w-full px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors flex items-center justify-center gap-2"
                        >
                          <Lock className="w-4 h-4" />
                          Sign Up to Buy
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
              Get notified when new leads match your criteria.
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
                          ? 'bg-black text-white'
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
                <p className="text-gray-300">Browse anonymized leads with key metrics</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                  2
                </div>
                <p className="text-gray-300">Purchase to unlock full contact &amp; financials</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                  3
                </div>
                <p className="text-gray-300">Connect directly with the opportunity</p>
              </div>
            </div>
            <Link
              to="/leads/how-it-works"
              className="mt-4 inline-flex items-center gap-1 text-sm text-white/80 hover:text-white"
            >
              Learn more <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
