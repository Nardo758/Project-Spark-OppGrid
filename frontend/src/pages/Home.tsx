import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  ArrowRight, 
  Search, 
  TrendingUp, 
  FileText,
  Sparkles,
  BarChart3,
  Target,
  Users,
  Play
} from 'lucide-react'

interface PlatformStats {
  validated_ideas: number
  total_market_opportunity: string
  global_markets: number
  validated_opportunities?: number
  reports_generated?: number
}

interface FeaturedOpportunity {
  id: number
  title: string
  description: string
  score: number
  market_size: string
  submissions: number
  growth: number
}

export default function Home() {
  const [stats, setStats] = useState<PlatformStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [featuredOpp, setFeaturedOpp] = useState<FeaturedOpportunity | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const statsRes = await fetch('/api/v1/opportunities/stats/platform')
        if (statsRes.ok) {
          const statsData = await statsRes.json()
          setStats(statsData)
        }
        
        setFeaturedOpp({
          id: 1,
          title: "Finding mental health therapists who accept insurance is difficult",
          description: "612 validations at 5/5 severity reveal massive gap in mental health provider discovery and booking",
          score: 87,
          market_size: "$2B-$8B",
          submissions: 612,
          growth: 32
        })
      } catch (err) {
        console.error('Failed to fetch landing page data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="bg-white">
      {/* Hero Section - Transform Market Signals */}
      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-50/50 via-white to-emerald-50/30">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(16,185,129,0.08),transparent_50%)] pointer-events-none" />
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
          
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            {/* Left Column - Main Content */}
            <div>
              {/* Badge - Clickable */}
              <Link 
                to="/discover"
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-100 text-emerald-700 rounded-full text-sm font-medium mb-6 hover:bg-emerald-200 transition-colors"
              >
                <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                {loading ? '...' : `${stats?.validated_ideas ?? 323}+ Validated Opportunities`}
              </Link>

              {/* Headline */}
              <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 tracking-tight leading-tight mb-6">
                Transform Market Signals<br />
                into{' '}
                <span className="text-emerald-500">Business<br />Opportunities</span>
              </h1>

              {/* Subtitle */}
              <p className="text-lg text-gray-600 mb-8 max-w-lg">
                Discover validated market opportunities backed by real consumer insights. From AI-powered validation to expert execution playbooks—everything you need to build what people actually want.
              </p>

              {/* CTA Buttons Row */}
              <div className="flex flex-wrap sm:flex-nowrap gap-2.5 mb-12">
                {/* Validate Your Idea */}
                <Link
                  to="/build/reports"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-md hover:bg-emerald-700 transition-colors whitespace-nowrap"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Validate Your Idea
                </Link>

                {/* Identify a Location */}
                <Link
                  to="/build/reports"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-md hover:bg-emerald-700 transition-colors whitespace-nowrap"
                >
                  <Target className="w-3.5 h-3.5" />
                  Identify a Location
                </Link>

                {/* Watch Demo */}
                <Link
                  to="/about"
                  className="inline-flex items-center gap-1.5 px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-100 transition-colors whitespace-nowrap"
                >
                  <Play className="w-3.5 h-3.5" />
                  Watch Demo
                </Link>
              </div>

              {/* Stats Row */}
              <div className="flex gap-10 -mt-4">
                <div>
                  <div className="text-2xl font-bold text-emerald-500">
                    {loading ? '...' : stats?.validated_ideas ?? 323}
                  </div>
                  <div className="text-xs text-gray-500">Validated Ideas</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900">
                    {loading ? '...' : stats?.total_market_opportunity ?? '$3.9T+'}
                  </div>
                  <div className="text-xs text-gray-500">Market Opportunity</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900">
                    {loading ? '...' : stats?.global_markets ?? 18}
                  </div>
                  <div className="text-xs text-gray-500">Global Markets</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-emerald-500">
                    {loading ? '...' : stats?.reports_generated ?? 50}
                  </div>
                  <div className="text-xs text-gray-500">Reports Generated</div>
                </div>
              </div>
            </div>

            {/* Right Column - Featured Opportunity Card */}
            <div className="relative">
              {/* Users want this badge - positioned above card */}
              <div className="flex items-center justify-end gap-2 text-sm text-gray-500 mb-3">
                <Users className="w-4 h-4" />
                <span>{featuredOpp?.submissions || 612} users want this</span>
              </div>

              <Link 
                to={`/opportunity/${featuredOpp?.id || 1}`}
                className="block bg-white rounded-2xl border border-gray-200 shadow-lg p-6 hover:shadow-xl hover:border-emerald-200 transition-all group"
              >
                {/* Card Header */}
                <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                  UNLOCK THIS WEEK'S TOP OPPORTUNITY
                </div>

                {/* Title and Score */}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <h3 className="text-xl font-semibold text-gray-900 leading-snug group-hover:text-emerald-600 transition-colors">
                    {featuredOpp?.title || "Finding mental health therapists who accept insurance is difficult"}
                  </h3>
                  <div className="flex-shrink-0 w-14 h-14 bg-emerald-50 border-2 border-emerald-200 rounded-xl flex items-center justify-center">
                    <span className="text-xl font-bold text-emerald-600">{featuredOpp?.score || 87}</span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-gray-600 text-sm mb-6">
                  {featuredOpp?.description || "612 validations at 5/5 severity reveal massive gap in mental health provider discovery and booking"}
                </p>

                {/* Metrics Grid */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-400 uppercase mb-1">Market Size</div>
                    <div className="text-lg font-semibold text-gray-900">{featuredOpp?.market_size || "$2B-$8B"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 uppercase mb-1">Submissions</div>
                    <div className="text-lg font-semibold text-gray-900">{featuredOpp?.submissions || 612}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 uppercase mb-1">Growth</div>
                    <div className="text-lg font-semibold text-emerald-500">+{featuredOpp?.growth || 32}%</div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-gray-100 rounded-full h-2 mb-4">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '75%' }}></div>
                </div>

                {/* Growth indicator */}
                <div className="flex items-center gap-2 text-emerald-500 text-sm mb-6">
                  <TrendingUp className="w-4 h-4" />
                  <span>+{featuredOpp?.growth || 32}% monthly growth</span>
                </div>

                {/* See More */}
                <div className="inline-flex items-center gap-2 text-emerald-600 group-hover:text-emerald-700 font-medium">
                  See More Opportunities
                  <ArrowRight className="w-4 h-4" />
                </div>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Featured: Consultant Report Studio */}
      <section className="py-16 bg-gradient-to-r from-slate-900 to-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 text-purple-300 rounded-full text-sm font-medium mb-4">
                <Sparkles className="w-4 h-4" />
                Featured Tool
              </div>
              <h2 className="text-3xl font-bold text-white mb-4">
                Consultant Report Studio
              </h2>
              <p className="text-lg text-gray-300 mb-6">
                Get investor-ready analysis in minutes. Generate comprehensive feasibility studies, 
                market analyses, and strategic assessments powered by AI.
              </p>
              <div className="flex flex-wrap gap-3 mb-8">
                {['Feasibility Study', 'Market Analysis', 'SWOT', 'PESTLE', 'Pitch Deck'].map((item) => (
                  <span key={item} className="px-3 py-1.5 bg-white/10 text-white text-sm rounded-lg">
                    {item}
                  </span>
                ))}
              </div>
              <div className="flex gap-4">
                <Link
                  to="/build/reports"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <FileText className="w-5 h-5" />
                  See Examples
                </Link>
                <Link
                  to="/build/reports/sample"
                  className="inline-flex items-center gap-2 px-6 py-3 border border-white/30 text-white font-medium rounded-lg hover:bg-white/10 transition-colors"
                >
                  Try Free Sample
                </Link>
              </div>
            </div>
            <div className="hidden lg:block">
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-purple-500 rounded-xl flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-white font-medium">Sample Report</div>
                    <div className="text-gray-400 text-sm">Market Analysis</div>
                  </div>
                </div>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between text-gray-300">
                    <span>Market Size (TAM)</span>
                    <span className="text-white font-medium">$8.2B</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Growth Rate</span>
                    <span className="text-emerald-400 font-medium">+24% YoY</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Competition Level</span>
                    <span className="text-amber-400 font-medium">Medium</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Confidence Score</span>
                    <span className="text-white font-medium">87%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">How It Works</h2>
            <p className="mt-4 text-lg text-gray-600">From discovery to execution in three steps</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="relative">
              <div className="absolute -top-3 -left-3 w-10 h-10 bg-black text-white rounded-full flex items-center justify-center font-bold">1</div>
              <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 pt-10">
                <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center mb-4">
                  <Search className="w-6 h-6 text-emerald-600" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg mb-3">Discover or Ideate</h3>
                <p className="text-gray-600">
                  Browse AI-curated opportunities or validate your own idea with our intelligent analysis engine.
                </p>
              </div>
            </div>
            <div className="relative">
              <div className="absolute -top-3 -left-3 w-10 h-10 bg-black text-white rounded-full flex items-center justify-center font-bold">2</div>
              <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 pt-10">
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
                  <Target className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg mb-3">Validate & Plan</h3>
                <p className="text-gray-600">
                  Get AI-powered market analysis, feasibility studies, and strategic recommendations.
                </p>
              </div>
            </div>
            <div className="relative">
              <div className="absolute -top-3 -left-3 w-10 h-10 bg-black text-white rounded-full flex items-center justify-center font-bold">3</div>
              <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 pt-10">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 text-lg mb-3">Build & Launch</h3>
                <p className="text-gray-600">
                  Generate business plans, pitch decks, and connect with experts to bring your idea to life.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 bg-gradient-to-r from-purple-600 to-indigo-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to Build What's Next?</h2>
          <p className="text-purple-100 text-lg mb-8">
            Join thousands of entrepreneurs discovering and validating opportunities every day.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/signup"
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-medium text-purple-600 bg-white hover:bg-gray-100 rounded-lg gap-2"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/pricing?from=home&plan=builder"
              className="inline-flex items-center justify-center px-6 py-3 text-sm font-medium text-white border border-white/60 hover:bg-white/10 rounded-lg gap-2"
            >
              View paid plans
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
                <span className="text-gray-900 font-bold text-sm">OG</span>
              </div>
              <div className="flex flex-col">
                <span className="font-semibold text-xl leading-tight">OppGrid</span>
                <span className="text-[9px] text-gray-400 leading-tight">The Opportunity Intelligence Platform</span>
              </div>
            </div>
            <div className="flex gap-6 text-sm text-gray-400 mb-4 md:mb-0">
              <Link to="/about" className="hover:text-white">About</Link>
              <Link to="/pricing" className="hover:text-white">Pricing</Link>
              <Link to="/blog" className="hover:text-white">Blog</Link>
              <Link to="/contact" className="hover:text-white">Contact</Link>
              <Link to="/terms" className="hover:text-white">Terms</Link>
              <Link to="/privacy" className="hover:text-white">Privacy</Link>
            </div>
            <p className="text-gray-500 text-sm">
              © 2024 OppGrid. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
