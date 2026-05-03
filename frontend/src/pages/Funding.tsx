import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  DollarSign, Building2, Users, Landmark, Gift, FileText,
  ExternalLink, ChevronRight, Search, Filter, Sparkles,
  GraduationCap, Loader2, BookOpen, CheckCircle, Clock,
  MapPin, Globe
} from 'lucide-react'

const fundingSources = [
  {
    id: 1,
    name: 'SBA Microloans',
    type: 'Government',
    icon: Landmark,
    amount: 'Up to $50,000',
    description: 'Small Business Administration microloans for startups and small businesses.',
    requirements: ['Business plan', '2+ years credit history', 'Collateral preferred'],
    timeline: '2-4 weeks',
    link: 'https://www.sba.gov/funding-programs/loans/microloans'
  },
  {
    id: 2,
    name: 'Angel Investors',
    type: 'Equity',
    icon: Users,
    amount: '$25K - $500K',
    description: 'Connect with angel investors looking for early-stage opportunities.',
    requirements: ['Pitch deck', 'MVP or prototype', 'Market validation'],
    timeline: '1-3 months',
    link: '/network/investor'
  },
  {
    id: 3,
    name: 'SBIR/STTR Grants',
    type: 'Grant',
    icon: Gift,
    amount: 'Up to $1.5M',
    description: 'Federal research grants for technology and innovation startups.',
    requirements: ['US-based company', 'R&D focused', 'Technical proposal'],
    timeline: '3-6 months',
    link: 'https://www.sbir.gov/'
  },
  {
    id: 4,
    name: 'Revenue-Based Financing',
    type: 'Alternative',
    icon: DollarSign,
    amount: '$10K - $5M',
    description: 'Non-dilutive funding based on your monthly recurring revenue.',
    requirements: ['$10K+ MRR', '6+ months history', 'SaaS or subscription model'],
    timeline: '1-2 weeks',
    link: '#'
  },
  {
    id: 5,
    name: 'Bank Business Loans',
    type: 'Debt',
    icon: Building2,
    amount: '$5K - $500K',
    description: 'Traditional bank loans for established businesses with good credit.',
    requirements: ['2+ years in business', 'Good credit score', 'Financial statements'],
    timeline: '2-6 weeks',
    link: '#'
  },
  {
    id: 6,
    name: 'Crowdfunding',
    type: 'Alternative',
    icon: Users,
    amount: 'Varies',
    description: 'Raise funds from the public through platforms like Kickstarter or Wefunder.',
    requirements: ['Compelling story', 'Product/prototype', 'Marketing plan'],
    timeline: '30-60 days campaign',
    link: '#'
  }
]

const fundingTypes = ['All', 'Government', 'Grant', 'Equity', 'Debt', 'Alternative']

interface SBALoanProgram {
  id: number
  name: string
  category: string
  amount: string
  description: string
  uses: string[]
  terms: string
  link: string
}

interface SBACourse {
  id: number
  title: string
  summary: string
  courseCategory: string[]
  url: string
  image?: { url: string; alt: string }
}


export default function Funding() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState('All')
  const [activeTab, setActiveTab] = useState<'overview' | 'programs' | 'courses' | 'lenders'>('overview')

  const { data: loanPrograms = [], isLoading: loadingPrograms } = useQuery({
    queryKey: ['sba-loan-programs'],
    queryFn: async () => {
      const res = await fetch('/api/v1/sba/loan-programs')
      if (!res.ok) throw new Error('Failed to fetch loan programs')
      return res.json()
    },
    enabled: activeTab === 'programs'
  })

  const { data: courses = [], isLoading: loadingCourses } = useQuery({
    queryKey: ['sba-courses'],
    queryFn: async () => {
      const res = await fetch('/api/v1/sba/courses?financing_only=true')
      if (!res.ok) throw new Error('Failed to fetch courses')
      return res.json()
    },
    enabled: activeTab === 'courses'
  })

  const { data: topLenders = [], isLoading: loadingLenders } = useQuery({
    queryKey: ['sba-top-lenders'],
    queryFn: async () => {
      const res = await fetch('/api/v1/sba/top-lenders')
      if (!res.ok) throw new Error('Failed to fetch lenders')
      return res.json()
    },
    enabled: activeTab === 'lenders'
  })

  const filteredSources = fundingSources.filter(source => {
    const matchesSearch = !searchQuery || 
      source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      source.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = selectedType === 'All' || source.type === selectedType
    return matchesSearch && matchesType
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Find Money</h1>
        <p className="text-gray-600">Discover funding options matched to your business stage and needs.</p>
      </div>

      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'overview'
              ? 'border-green-600 text-green-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <DollarSign className="w-4 h-4 inline-block mr-2" />
          Funding Overview
        </button>
        <button
          onClick={() => setActiveTab('programs')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'programs'
              ? 'border-green-600 text-green-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Landmark className="w-4 h-4 inline-block mr-2" />
          SBA Loan Programs
        </button>
        <button
          onClick={() => setActiveTab('courses')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'courses'
              ? 'border-green-600 text-green-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <GraduationCap className="w-4 h-4 inline-block mr-2" />
          Financing Courses
        </button>
        <button
          onClick={() => setActiveTab('lenders')}
          className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'lenders'
              ? 'border-green-600 text-green-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <MapPin className="w-4 h-4 inline-block mr-2" />
          Find Lenders
        </button>
      </div>

      {activeTab === 'overview' && (
        <>
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl p-6 mb-8 border border-green-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-600 rounded-xl flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900 mb-1">AI Funding Advisor</h2>
                <p className="text-sm text-gray-600 mb-3">
                  Get personalized funding recommendations based on your business profile, stage, and goals.
                </p>
                <Link 
                  to="/brain" 
                  className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 text-sm"
                >
                  <Sparkles className="w-4 h-4" />
                  Get AI Recommendations
                </Link>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search funding sources..."
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <div className="flex gap-2 flex-wrap">
                {fundingTypes.map(type => (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      selectedType === type
                        ? 'bg-gray-900 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {filteredSources.map((source) => {
              const IconComponent = source.icon
              return (
                <div key={source.id} className="bg-white rounded-xl border border-gray-200 p-6 hover:border-gray-300 hover:shadow-md transition-all">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center">
                      <IconComponent className="w-6 h-6 text-gray-700" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900">{source.name}</h3>
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                          {source.type}
                        </span>
                      </div>
                      <p className="text-lg font-bold text-green-600">{source.amount}</p>
                    </div>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">{source.description}</p>

                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Requirements</p>
                    <ul className="space-y-1">
                      {source.requirements.map((req, i) => (
                        <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                          <ChevronRight className="w-3 h-3 text-gray-400" />
                          {req}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                    <span className="text-sm text-gray-500">Timeline: {source.timeline}</span>
                    {source.link.startsWith('http') ? (
                      <a
                        href={source.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm font-medium text-green-600 hover:text-green-700"
                      >
                        Learn More
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    ) : (
                      <Link
                        to={source.link}
                        className="inline-flex items-center gap-1 text-sm font-medium text-green-600 hover:text-green-700"
                      >
                        Explore
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 p-8">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">Need Help with Your Application?</h2>
                <p className="text-gray-600">
                  Our AI can help you prepare funding applications, pitch decks, and financial projections.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/build/business-plan"
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700"
              >
                Generate Business Plan
              </Link>
              <Link
                to="/build/reports"
                className="px-4 py-2 border border-gray-200 rounded-lg font-medium hover:bg-gray-50"
              >
                Consultant Studio
              </Link>
              <Link
                to="/build/experts"
                className="px-4 py-2 border border-gray-200 rounded-lg font-medium hover:bg-gray-50"
              >
                Find a Funding Expert
              </Link>
            </div>
          </div>
        </>
      )}

      {activeTab === 'programs' && (
        <>
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 mb-6 border border-blue-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
                <Landmark className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-gray-900 mb-1">SBA Loan Programs</h2>
                <p className="text-sm text-gray-600 mb-3">
                  The Small Business Administration offers several loan programs to help small businesses access capital. These loans are partially guaranteed by the SBA, making them less risky for lenders.
                </p>
                <a
                  href="https://www.sba.gov/funding-programs/loans/lender-match"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 text-sm"
                >
                  <Building2 className="w-4 h-4" />
                  Find an SBA Lender Near You
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>

          {loadingPrograms ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
              <span className="ml-3 text-gray-600">Loading loan programs...</span>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              {loanPrograms.map((program: SBALoanProgram) => (
                <div key={program.id} className="bg-white rounded-xl border border-gray-200 p-6 hover:border-blue-300 hover:shadow-md transition-all">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
                      <DollarSign className="w-6 h-6 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 text-lg">{program.name}</h3>
                      <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full mt-1">
                        {program.category}
                      </span>
                    </div>
                    <p className="text-xl font-bold text-green-600">{program.amount}</p>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">{program.description}</p>

                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Common Uses</p>
                    <div className="flex flex-wrap gap-2">
                      {program.uses.map((use, i) => (
                        <span key={i} className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                          <CheckCircle className="w-3 h-3 text-green-500" />
                          {use}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                    <div className="flex items-center gap-1 text-sm text-gray-500">
                      <Clock className="w-4 h-4" />
                      {program.terms}
                    </div>
                    <a
                      href={program.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
                    >
                      Learn More
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'courses' && (
        <>
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl p-6 mb-6 border border-purple-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center flex-shrink-0">
                <GraduationCap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="font-semibold text-gray-900 mb-1">Free Financing Courses</h2>
                <p className="text-sm text-gray-600">
                  Learn about funding options, loan applications, and financial management through official SBA training courses.
                </p>
              </div>
            </div>
          </div>

          {loadingCourses ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
              <span className="ml-3 text-gray-600">Loading courses...</span>
            </div>
          ) : courses.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
              <GraduationCap className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600">No financing courses available at this time.</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              {courses.map((course: SBACourse) => (
                <div key={course.id} className="bg-white rounded-xl border border-gray-200 p-6 hover:border-purple-300 hover:shadow-md transition-all">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-6 h-6 text-purple-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{course.title}</h3>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {course.courseCategory?.map((cat, i) => (
                          <span key={i} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                            {cat}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <p className="text-sm text-gray-600 mb-4">{course.summary}</p>

                  <a
                    href={`https://www.sba.gov${course.url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm font-medium text-purple-600 hover:text-purple-700"
                  >
                    <GraduationCap className="w-4 h-4" />
                    Start Course
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'lenders' && (
        <>
          <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-2xl p-6 mb-6 border border-teal-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-teal-600 rounded-xl flex items-center justify-center flex-shrink-0">
                <MapPin className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-gray-900 mb-1">Find SBA-Approved Lenders</h2>
                <p className="text-sm text-gray-600 mb-4">
                  Connect with SBA-approved lenders who can help you apply for 7(a), 504, and Microloan programs. Use the SBA's official Lender Match tool to find lenders near you.
                </p>
                <a
                  href="https://www.sba.gov/funding-programs/loans/lender-match"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 transition-colors"
                >
                  <Search className="w-4 h-4" />
                  Find Lenders Near You
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Top SBA Lenders</h3>
            <p className="text-sm text-gray-500">Major national banks and lenders with active SBA lending programs</p>
          </div>

          {loadingLenders ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-teal-600 animate-spin" />
              <span className="ml-3 text-gray-600">Loading lenders...</span>
            </div>
          ) : (
            <>
              <div className="grid md:grid-cols-2 gap-4">
                {topLenders.map((lender: { id: string; name: string; description: string; loan_types: string[]; website: string; national: boolean }) => (
                  <div key={lender.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:border-teal-300 hover:shadow-md transition-all">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Building2 className="w-5 h-5 text-teal-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-gray-900">{lender.name}</h3>
                        {lender.national && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            Nationwide
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-sm text-gray-600 mb-3">{lender.description}</p>

                    <div className="flex flex-wrap gap-1 mb-4">
                      {lender.loan_types.map((type, i) => (
                        <span key={i} className="px-2 py-0.5 bg-teal-100 text-teal-700 text-xs rounded-full">
                          {type}
                        </span>
                      ))}
                    </div>

                    <a
                      href={lender.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm font-medium text-teal-600 hover:text-teal-700"
                    >
                      <Globe className="w-4 h-4" />
                      Visit SBA Loan Page
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                ))}
              </div>

              <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Landmark className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Looking for local lenders?</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      The SBA's Lender Match tool connects you with SBA-approved lenders in your area who are interested in working with businesses like yours.
                    </p>
                    <a
                      href="https://www.sba.gov/funding-programs/loans/lender-match"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 text-sm"
                    >
                      Get Matched with Local Lenders
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
