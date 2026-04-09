import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  Loader2,
  CheckCircle,
  Sparkles,
  BarChart3,
  Target,
  Users,
  Mail,
  Search as SearchIcon,
  Calendar,
  DollarSign,
  Megaphone,
  ClipboardList,
  Download,
  Lightbulb,
  MapPin,
  Copy,
  Globe,
  Briefcase,
  PieChart,
  LineChart,
  Presentation,
  FileSpreadsheet,
  Shield,
  Lock,
  Clock,
  Gift,
  ChevronDown,
  ChevronRight,
  ShoppingCart,
  AlertTriangle,
  X,
  Printer,
  Rocket,
  Palette,
  Layout,
  Layers,
  BookOpen,
  MousePointer,
  LogIn,
} from 'lucide-react'
import DOMPurify from 'dompurify'
import { FourPsHorizontalBar, ScoreRing, OppRow } from './ConsultantResults/ResultCards'
import { useAuthStore } from '../stores/authStore'

type InputMode = 'validate' | 'search' | 'location' | 'clone'

type ReportItem = {
  slug: string
  title: string
  description: string
  price: string
  priceCents: number
  consultantPrice: string
  icon: any
  accentColor: string
  sections: string[]
  deliveryTime: string
  isStudio: boolean
}

type ReportCategory = {
  id: string
  label: string
  icon: any
  color: string
  reports: ReportItem[]
}

type GeneratedReport = {
  id: number
  report_type: string
  status: string
  title?: string
  summary?: string
  content?: string
  confidence_score?: number
  created_at: string
  completed_at?: string
}

const INPUT_MODES = [
  { id: 'validate' as InputMode, label: 'Validate Idea', icon: Lightbulb, description: 'Describe your business idea and get an Online/Physical/Hybrid recommendation with viability analysis.' },
  { id: 'search' as InputMode, label: 'Search Ideas', icon: SearchIcon, description: 'Browse validated opportunities by keyword or category.' },
  { id: 'location' as InputMode, label: 'Identify Location', icon: MapPin, description: 'Enter a city + business type for market analysis.' },
  { id: 'clone' as InputMode, label: 'Clone Success', icon: Copy, description: 'Analyze a successful business and find similar markets.' },
]

const REPORT_CATEGORIES: ReportCategory[] = [
  {
    id: 'strategy', label: 'Strategy & Analysis', icon: Target, color: '#185FA5',
    reports: [
      { slug: 'market_analysis', title: 'Market Analysis', description: 'TAM/SAM/SOM with competitive landscape and growth trends.', price: '$99', priceCents: 9900, consultantPrice: '$2,000 - $8,000', icon: PieChart, accentColor: '#185FA5', sections: ['Market Size', 'Growth Trends', 'Customer Segments', 'Competitive Landscape', 'Entry Strategy', 'Revenue Projections'], deliveryTime: '2-3 hrs', isStudio: true },
      { slug: 'business_plan', title: 'Business Plan', description: 'Comprehensive strategy document with financial projections.', price: '$149', priceCents: 14900, consultantPrice: '$3,000 - $15,000', icon: FileSpreadsheet, accentColor: '#0F6E56', sections: ['Executive Summary', 'Company Description', 'Market Analysis', 'Organization', 'Marketing Strategy', 'Financial Projections'], deliveryTime: '4-6 hrs', isStudio: true },
      { slug: 'financial_model', title: 'Financial Model', description: '5-year projections, unit economics, and sensitivity analysis.', price: '$129', priceCents: 12900, consultantPrice: '$2,500 - $10,000', icon: LineChart, accentColor: '#BA7517', sections: ['Revenue Model', 'Cost Structure', 'Unit Economics', 'Cash Flow', '5-Year P&L', 'Sensitivity Analysis'], deliveryTime: '3-5 hrs', isStudio: true },
      { slug: 'strategic_assessment', title: 'Strategic Assessment', description: 'SWOT analysis and competitive positioning.', price: '$89', priceCents: 8900, consultantPrice: '$1,500 - $5,000', icon: Briefcase, accentColor: '#185FA5', sections: ['SWOT Analysis', 'Competitive Positioning', 'Value Proposition', 'Strategic Options', 'Recommendations'], deliveryTime: '2-3 hrs', isStudio: true },
      { slug: 'pestle_analysis', title: 'PESTLE Analysis', description: 'Political, Economic, Social, Tech, Legal, Environmental factors.', price: '$99', priceCents: 9900, consultantPrice: '$1,500 - $5,000', icon: Shield, accentColor: '#0F6E56', sections: ['Political', 'Economic', 'Social', 'Technological', 'Legal', 'Environmental'], deliveryTime: '2-3 hrs', isStudio: true },
      { slug: 'competitive_analysis', title: 'Competitive Analysis', description: 'Deep competitor benchmarking with strategic recommendations.', price: '$149', priceCents: 14900, consultantPrice: '$2,000 - $6,000', icon: BarChart3, accentColor: '#D97757', sections: ['Competitor Profiles', 'Feature Matrix', 'Pricing Comparison', 'Market Positioning'], deliveryTime: '3-4 hrs', isStudio: false },
      { slug: 'pricing_strategy', title: 'Pricing Strategy', description: 'Optimal pricing model based on market and competitor data.', price: '$139', priceCents: 13900, consultantPrice: '$1,500 - $5,000', icon: DollarSign, accentColor: '#BA7517', sections: ['Market Pricing', 'Value-Based Pricing', 'Competitor Pricing', 'Recommended Model'], deliveryTime: '2-4 hrs', isStudio: false },
    ]
  },
  {
    id: 'marketing', label: 'Marketing & Growth', icon: Megaphone, color: '#D97757',
    reports: [
      { slug: 'ad_creatives', title: 'Ad Creatives', description: 'Platform-optimized ad copy and creative concepts.', price: '$79', priceCents: 7900, consultantPrice: '$500 - $2,000', icon: Sparkles, accentColor: '#D97757', sections: ['Ad Copy Variants', 'Visual Concepts', 'Platform Targeting', 'A/B Test Ideas'], deliveryTime: '1-2 hrs', isStudio: false },
      { slug: 'brand_package', title: 'Brand Package', description: 'Brand identity including mission, voice, visual guidelines.', price: '$149', priceCents: 14900, consultantPrice: '$3,000 - $10,000', icon: Palette, accentColor: '#D97757', sections: ['Brand Mission', 'Voice & Tone', 'Visual Identity', 'Brand Guidelines'], deliveryTime: '2-4 hrs', isStudio: false },
      { slug: 'landing_page', title: 'Landing Page', description: 'Conversion-optimized landing page copy and structure.', price: '$99', priceCents: 9900, consultantPrice: '$1,000 - $3,000', icon: Layout, accentColor: '#185FA5', sections: ['Hero Section', 'Value Props', 'Social Proof', 'CTA Strategy'], deliveryTime: '2-3 hrs', isStudio: false },
      { slug: 'content_calendar', title: 'Content Calendar', description: '30-day content strategy across all channels.', price: '$129', priceCents: 12900, consultantPrice: '$1,500 - $4,000', icon: Calendar, accentColor: '#0F6E56', sections: ['Content Pillars', 'Platform Strategy', '30-Day Calendar', 'Content Templates'], deliveryTime: '2-3 hrs', isStudio: false },
      { slug: 'email_funnel', title: 'Email Funnel System', description: 'Complete automated email sequence for lead nurturing.', price: '$179', priceCents: 17900, consultantPrice: '$2,000 - $5,000', icon: Mail, accentColor: '#BA7517', sections: ['Welcome Sequence', 'Nurture Flow', 'Sales Emails', 'Re-engagement'], deliveryTime: '3-4 hrs', isStudio: false },
      { slug: 'email_sequence', title: 'Email Sequence', description: 'Targeted email campaign for a specific objective.', price: '$79', priceCents: 7900, consultantPrice: '$500 - $1,500', icon: Mail, accentColor: '#D97757', sections: ['Subject Lines', 'Email Copy', 'Send Schedule', 'Segmentation'], deliveryTime: '1-2 hrs', isStudio: false },
      { slug: 'lead_magnet', title: 'Lead Magnet', description: 'High-value lead capture asset concept and outline.', price: '$89', priceCents: 8900, consultantPrice: '$500 - $2,000', icon: Gift, accentColor: '#D97757', sections: ['Magnet Concept', 'Content Outline', 'Landing Page Copy', 'Distribution Plan'], deliveryTime: '2-3 hrs', isStudio: false },
      { slug: 'sales_funnel', title: 'Sales Funnel', description: 'End-to-end customer acquisition funnel design.', price: '$149', priceCents: 14900, consultantPrice: '$2,000 - $5,000', icon: Layers, accentColor: '#185FA5', sections: ['Awareness Stage', 'Consideration Stage', 'Decision Stage', 'Retention Strategy'], deliveryTime: '3-4 hrs', isStudio: false },
      { slug: 'seo_content', title: 'SEO Content', description: 'SEO-optimized content strategy with keyword targeting.', price: '$129', priceCents: 12900, consultantPrice: '$1,500 - $4,000', icon: Globe, accentColor: '#0F6E56', sections: ['Keyword Research', 'Content Briefs', 'On-Page SEO', 'Link Strategy'], deliveryTime: '2-3 hrs', isStudio: false },
    ]
  },
  {
    id: 'product', label: 'Product & Launch', icon: Rocket, color: '#0F6E56',
    reports: [
      { slug: 'pitch_deck', title: 'Pitch Deck', description: 'Investor-ready presentation content and structure.', price: '$79', priceCents: 7900, consultantPrice: '$2,000 - $5,000', icon: Presentation, accentColor: '#BA7517', sections: ['Problem', 'Solution', 'Market Size', 'Business Model', 'Traction', 'Team', 'Financials', 'Ask'], deliveryTime: '2-3 hrs', isStudio: true },
      { slug: 'feature_specs', title: 'Feature Specs', description: 'Detailed feature specifications with user stories.', price: '$149', priceCents: 14900, consultantPrice: '$2,000 - $6,000', icon: ClipboardList, accentColor: '#0F6E56', sections: ['Feature List', 'User Stories', 'Acceptance Criteria', 'Priority Matrix'], deliveryTime: '3-4 hrs', isStudio: false },
      { slug: 'mvp_roadmap', title: 'MVP Roadmap', description: 'Phased product development plan with milestones.', price: '$179', priceCents: 17900, consultantPrice: '$3,000 - $8,000', icon: Rocket, accentColor: '#185FA5', sections: ['MVP Scope', 'Phase 1-3 Plan', 'Tech Stack', 'Timeline & Milestones'], deliveryTime: '3-5 hrs', isStudio: false },
      { slug: 'prd', title: 'Product Requirements Doc', description: 'Complete PRD with technical and business requirements.', price: '$169', priceCents: 16900, consultantPrice: '$3,000 - $8,000', icon: BookOpen, accentColor: '#D97757', sections: ['Objectives', 'Requirements', 'User Flows', 'Technical Specs', 'Success Metrics'], deliveryTime: '4-6 hrs', isStudio: false },
      { slug: 'gtm_strategy', title: 'GTM Strategy', description: 'Go-to-market strategy with channel and positioning plan.', price: '$189', priceCents: 18900, consultantPrice: '$3,000 - $8,000', icon: Rocket, accentColor: '#D97757', sections: ['Market Positioning', 'Channel Strategy', 'Launch Plan', 'Growth Levers'], deliveryTime: '3-5 hrs', isStudio: false },
      { slug: 'gtm_calendar', title: 'GTM Launch Calendar', description: 'Day-by-day launch execution plan with tasks and owners.', price: '$159', priceCents: 15900, consultantPrice: '$2,000 - $5,000', icon: Calendar, accentColor: '#BA7517', sections: ['Pre-Launch Tasks', 'Launch Day Plan', 'Week 1-4 Actions', 'KPI Tracking'], deliveryTime: '2-3 hrs', isStudio: false },
      { slug: 'kpi_dashboard', title: 'KPI Dashboard', description: 'Key performance indicators and tracking framework.', price: '$119', priceCents: 11900, consultantPrice: '$1,500 - $4,000', icon: BarChart3, accentColor: '#0F6E56', sections: ['North Star Metric', 'Leading Indicators', 'Dashboard Layout', 'Review Cadence'], deliveryTime: '2-3 hrs', isStudio: false },
    ]
  },
  {
    id: 'research', label: 'Research', icon: SearchIcon, color: '#D97757',
    reports: [
      { slug: 'user_personas', title: 'User Personas', description: 'Data-driven customer personas with behavior insights.', price: '$99', priceCents: 9900, consultantPrice: '$1,000 - $3,000', icon: Users, accentColor: '#D97757', sections: ['Demographics', 'Pain Points', 'Behaviors', 'Buying Triggers'], deliveryTime: '2-3 hrs', isStudio: false },
      { slug: 'customer_interview', title: 'Customer Interview Guide', description: 'Structured interview script for customer discovery.', price: '$89', priceCents: 8900, consultantPrice: '$500 - $2,000', icon: Users, accentColor: '#185FA5', sections: ['Research Questions', 'Interview Script', 'Analysis Framework', 'Insight Template'], deliveryTime: '2-3 hrs', isStudio: false },
      { slug: 'tweet_landing', title: 'Tweet Landing Page', description: 'Viral tweet thread + micro landing page content.', price: '$49', priceCents: 4900, consultantPrice: '$300 - $800', icon: MousePointer, accentColor: '#D97757', sections: ['Tweet Thread', 'Hook Variants', 'Landing Copy', 'CTA Options'], deliveryTime: '0.5-1 hr', isStudio: false },
      { slug: 'feasibility_study', title: 'Feasibility Study', description: 'Quick viability check with market validation data.', price: '$25', priceCents: 2500, consultantPrice: '$1,500 - $15,000', icon: Target, accentColor: '#0F6E56', sections: ['Executive Summary', 'Market Opportunity', 'Technical Feasibility', 'Financial Viability', 'Risk Assessment'], deliveryTime: '1-2 hrs', isStudio: true },
    ]
  },
]

const TOTAL_REPORTS = REPORT_CATEGORIES.reduce((sum, cat) => sum + cat.reports.length, 0)

interface ReportLibraryProps {
  opportunityId?: number
  customContext?: string
}

export default function ReportLibrary({
  opportunityId,
  customContext,
}: ReportLibraryProps) {
  const { isAuthenticated, token } = useAuthStore()

  const [inputMode, setInputMode] = useState<InputMode>('validate')
  const [ideaDescription, setIdeaDescription] = useState(customContext || '')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchCategory, setSearchCategory] = useState('')
  const [locationCity, setLocationCity] = useState('')
  const [locationBusiness, setLocationBusiness] = useState('')
  const [cloneBusinessName, setCloneBusinessName] = useState('')
  const [cloneBusinessAddress, setCloneBusinessAddress] = useState('')
  const [cloneTargetCity, setCloneTargetCity] = useState('')

  const [consultantResult, setConsultantResult] = useState<any>(null)
  const [consultantLoading, setConsultantLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [expandedReport, setExpandedReport] = useState<string | null>(null)

  const [viewingReport, setViewingReport] = useState<GeneratedReport | null>(null)
  const [generatingFree, setGeneratingFree] = useState<string | null>(null)
  const [freeReports, setFreeReports] = useState<Record<string, GeneratedReport>>({})
  const [generateError, setGenerateError] = useState<string | null>(null)

  const [purchaseLoading, setPurchaseLoading] = useState(false)
  const [generatingReport, setGeneratingReport] = useState<string | null>(null)
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [sidebarReport, setSidebarReport] = useState('business_plan')
  const [sidebarEmail, setSidebarEmail] = useState('')
  const [sidebarEmailError, setSidebarEmailError] = useState<string | null>(null)

  const [guestEmail, setGuestEmail] = useState('')
  const [guestEmailError, setGuestEmailError] = useState<string | null>(null)

  const [checkoutState, setCheckoutState] = useState<any>(null)
  const [checkoutStateLoading, setCheckoutStateLoading] = useState(false)
  const [sidebarCheckoutState, setSidebarCheckoutState] = useState<any>(null)

  const isGuest = !isAuthenticated

  const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const isValidGuestEmail = isGuest && EMAIL_REGEX.test(guestEmail.trim())
  const isValidSidebarEmail = isGuest && EMAIL_REGEX.test(sidebarEmail.trim())

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const { data: reportHistory } = useQuery<GeneratedReport[]>({
    queryKey: ['my-reports', token],
    queryFn: async () => {
      if (!token) return []
      const res = await fetch('/api/v1/reports/my-reports', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return []
      return res.json()
    },
    enabled: isAuthenticated,
  })

  const canAnalyze = () => {
    switch (inputMode) {
      case 'validate': return ideaDescription.trim().length > 10
      case 'search': return !!(searchQuery.trim() || searchCategory)
      case 'location': return !!(locationCity.trim() && locationBusiness.trim())
      case 'clone': return !!(cloneBusinessName.trim() && cloneBusinessAddress.trim())
      default: return false
    }
  }

  const runConsultantAnalysis = async () => {
    setConsultantLoading(true)
    setConsultantResult(null)
    setAnalysisError(null)
    setFreeReports({})

    try {
      let endpoint = ''
      let body: any = {}

      switch (inputMode) {
        case 'validate':
          endpoint = '/api/v1/consultant/validate-idea'
          body = { idea_description: ideaDescription, business_context: {} }
          break
        case 'search':
          endpoint = '/api/v1/consultant/search-ideas'
          body = { query: searchQuery || undefined, category: searchCategory || undefined }
          break
        case 'location':
          endpoint = '/api/v1/consultant/identify-location'
          body = { city: locationCity, business_description: locationBusiness }
          break
        case 'clone':
          endpoint = '/api/v1/consultant/clone-success'
          body = {
            business_name: cloneBusinessName,
            business_address: cloneBusinessAddress,
            target_city: cloneTargetCity || undefined,
            radius_miles: 3,
          }
          break
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Analysis failed (${res.status})`)
      }
      const result = await res.json()
      setConsultantResult(result)

      if (inputMode === 'validate' && result.success) {
        generateFreeReports(result)
      }
    } catch (e) {
      setAnalysisError(e instanceof Error ? e.message : 'Analysis failed. Please try again.')
    } finally {
      setConsultantLoading(false)
    }
  }

  const generateFreeReports = async (analysisResult: any) => {
    const analysisContext = `Idea: ${ideaDescription}\n\nAnalysis: ${JSON.stringify(analysisResult, null, 2)}`
    const reportTypes = ['feasibility_study']

    for (const reportType of reportTypes) {
      setGeneratingFree(reportType)
      try {
        const res = await fetch('/api/v1/report-pricing/generate-free-report', {
          method: 'POST',
          headers: headers(),
          body: JSON.stringify({
            report_type: reportType,
            idea_description: ideaDescription,
            analysis_context: analysisContext,
            opportunity_id: opportunityId,
          }),
        })
        if (res.ok) {
          const report = await res.json()
          setFreeReports(prev => ({ ...prev, [reportType]: report }))
        }
      } catch {
      }
    }
    setGeneratingFree(null)
  }

  const fetchCheckoutState = async (reportType: string, setter: (s: any) => void) => {
    setCheckoutStateLoading(true)
    try {
      const h: Record<string, string> = {}
      if (token) h['Authorization'] = `Bearer ${token}`
      const res = await fetch(`/api/v1/report-pricing/checkout-state?report_type=${encodeURIComponent(reportType)}`, { headers: h })
      if (res.ok) setter(await res.json())
    } catch {
    } finally {
      setCheckoutStateLoading(false)
    }
  }

  useEffect(() => {
    if (consultantResult?.intel_cta?.report_type) {
      const ctaSlugMap: Record<string, string> = {
        'Feasibility Study': 'feasibility_study',
        'Business Plan': 'business_plan',
        'Deep Clone Analysis': 'competitive_analysis',
        'Subscription': 'market_analysis',
      }
      const slug = ctaSlugMap[consultantResult.intel_cta.report_type] || 'market_analysis'
      fetchCheckoutState(slug, setCheckoutState)
    }
  }, [consultantResult?.intel_cta?.report_type, token])

  useEffect(() => {
    fetchCheckoutState(sidebarReport, setSidebarCheckoutState)
  }, [sidebarReport, token])

  const handleSubscriberGenerate = async (reportType: string) => {
    setGeneratingReport(reportType)
    setGenerateError(null)
    try {
      const analysisContext = getContextForMode()
      const res = await fetch('/api/v1/report-pricing/generate-free-report', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          report_type: reportType,
          idea_description: ideaDescription || analysisContext,
          analysis_context: analysisContext,
          opportunity_id: opportunityId,
        }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || 'Generation failed')
      }
      const report = await res.json()
      setViewingReport(report)
      fetchCheckoutState(reportType, setCheckoutState)
      fetchCheckoutState(sidebarReport, setSidebarCheckoutState)
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      setGeneratingReport(null)
    }
  }

  const handleReportAction = async (report: ReportItem) => {
    if (sidebarCheckoutState?.state === 'subscriber_has_credits') {
      await handleSubscriberGenerate(report.slug)
      return
    }
    setSidebarEmailError(null)
    setPurchaseLoading(true)
    setGenerateError(null)
    try {
      if (isAuthenticated) {
        const accessRes = await fetch(`/api/v1/reports/check-access?template_slug=${encodeURIComponent(report.slug)}`, {
          method: 'POST',
          headers: headers(),
        })
        if (accessRes.ok) {
          const accessData = await accessRes.json()
          if (accessData.has_access) {
            await handleGenerateReport(report)
            return
          }
        }
      }
      const baseUrl = window.location.origin
      const returnPath = window.location.pathname
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent(returnPath)}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent(returnPath)}`

      const checkoutBody: Record<string, any> = {
        report_type: report.slug,
        success_url: successUrl,
        cancel_url: cancelUrl,
      }
      if (isGuest || sidebarEmail.trim()) {
        checkoutBody.email = sidebarEmail.trim()
      }
      checkoutBody.report_context = { idea_description: ideaDescription }

      const res = await fetch('/api/v1/report-pricing/studio-report-checkout', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(checkoutBody),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start checkout')
      if (data.url) window.location.href = data.url
      else throw new Error('No checkout URL returned')
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Checkout failed')
    } finally {
      setPurchaseLoading(false)
    }
  }

  const handleCtaCheckout = async (report: ReportItem) => {
    if (checkoutState?.state === 'subscriber_has_credits') {
      await handleSubscriberGenerate(report.slug)
      return
    }
    setPurchaseLoading(true)
    setGenerateError(null)
    try {
      const baseUrl = window.location.origin
      const returnPath = window.location.pathname
      const email = isAuthenticated ? '' : guestEmail.trim()
      const successUrl = `${baseUrl}/billing/return?status=success&return_to=${encodeURIComponent(returnPath)}${email ? `&email=${encodeURIComponent(email)}` : ''}`
      const cancelUrl = `${baseUrl}/billing/return?status=canceled&return_to=${encodeURIComponent(returnPath)}`
      const body: Record<string, any> = {
        report_type: report.slug,
        success_url: successUrl,
        cancel_url: cancelUrl,
        report_context: { idea_description: ideaDescription },
      }
      if (email) body.email = email
      const res = await fetch('/api/v1/report-pricing/studio-report-checkout', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start checkout')
      if (data.url) window.location.href = data.url
      else throw new Error('No checkout URL returned')
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Checkout failed')
    } finally {
      setPurchaseLoading(false)
    }
  }

  const getContextForMode = () => {
    switch (inputMode) {
      case 'validate':
        return consultantResult
          ? `Idea: ${ideaDescription}\n\nAnalysis: ${JSON.stringify(consultantResult, null, 2)}`
          : ideaDescription
      case 'search':
        return consultantResult
          ? `Search: ${searchQuery} (${searchCategory})\n\nResults: ${JSON.stringify(consultantResult, null, 2)}`
          : `Search query: ${searchQuery}, Category: ${searchCategory}`
      case 'location':
        return consultantResult
          ? `Location: ${locationBusiness} in ${locationCity}\n\nAnalysis: ${JSON.stringify(consultantResult, null, 2)}`
          : `${locationBusiness} in ${locationCity}`
      case 'clone':
        return consultantResult
          ? `Clone: ${cloneBusinessName}\n\nAnalysis: ${JSON.stringify(consultantResult, null, 2)}`
          : `Clone ${cloneBusinessName} at ${cloneBusinessAddress}`
      default:
        return ''
    }
  }

  const handleGenerateReport = async (report: ReportItem) => {
    setGeneratingReport(report.slug)
    setGenerateError(null)
    try {
      const context = getContextForMode()
      const res = await fetch('/api/v1/reports/generate', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          template_slug: report.slug,
          custom_context: context,
          opportunity_id: opportunityId,
        }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'Report generation failed')
      }
      const generated = await res.json()
      setViewingReport(generated)
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Report generation failed')
    } finally {
      setGeneratingReport(null)
      setPurchaseLoading(false)
    }
  }

  const handleExport = async (format: string) => {
    if (!viewingReport) return
    setExportingFormat(format)
    try {
      const exportHeaders: Record<string, string> = {}
      if (token) exportHeaders['Authorization'] = `Bearer ${token}`
      const res = await fetch(`/api/v1/reports/${viewingReport.id}/export/${format}`, {
        headers: exportHeaders,
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${viewingReport.id}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setGenerateError('Export failed. Please try again.')
    } finally {
      setExportingFormat(null)
    }
  }

  const allReports = REPORT_CATEGORIES.flatMap(cat => cat.reports)
  const selectedSidebarReport = allReports.find(r => r.slug === sidebarReport)

  const sidebarCard = (
    <div className="lg:sticky lg:top-8">
      <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#0F6E56]" />
          <h3 className="text-sm font-bold text-gray-900">Generate Report</h3>
        </div>

        <div>
          <label className="text-[11px] font-medium text-gray-500 mb-1.5 block">Report Type</label>
          <select
            value={sidebarReport}
            onChange={(e) => setSidebarReport(e.target.value)}
            className="w-full p-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56] transition-all"
          >
            {REPORT_CATEGORIES.map(cat => (
              <optgroup key={cat.id} label={cat.label}>
                {cat.reports.map(r => (
                  <option key={r.slug} value={r.slug}>{r.title} — {r.price}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {/* ── Subscriber with credits ── */}
        {sidebarCheckoutState?.state === 'subscriber_has_credits' ? (
          <>
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0F6E56]/10 w-fit">
              <CheckCircle className="w-3.5 h-3.5 text-[#0F6E56]" />
              <span className="text-[11px] font-semibold text-[#0F6E56]">
                {sidebarCheckoutState.reports_remaining === -1
                  ? 'Unlimited reports'
                  : `${sidebarCheckoutState.reports_remaining} of ${sidebarCheckoutState.reports_total} reports remaining`}
              </span>
            </div>
            <div className="bg-gray-50 rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-gray-500">Report value</span>
                <span className="line-through text-gray-300">${(sidebarCheckoutState.base_price_cents / 100).toFixed(0)}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-gray-700 font-semibold">Your price</span>
                <span className="text-[#0F6E56] font-bold">$0 (included)</span>
              </div>
              {selectedSidebarReport && (
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-gray-400">Delivery time</span>
                  <span className="text-gray-500 font-medium">{selectedSidebarReport.deliveryTime}</span>
                </div>
              )}
            </div>
            {generateError && <p className="text-[10px] text-red-600">{generateError}</p>}
            <button
              onClick={() => {
                const report = allReports.find(r => r.slug === sidebarReport)
                if (report) handleSubscriberGenerate(report.slug)
              }}
              disabled={purchaseLoading || !!generatingReport}
              className="w-full py-3 text-white rounded-xl text-sm font-semibold transition-all hover:shadow-md active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
              style={{ background: 'linear-gradient(135deg, #0F6E56, #185FA5)' }}
            >
              {generatingReport ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : <><FileText className="w-4 h-4" /> Generate report (use 1 credit)</>}
            </button>
          </>
        ) : sidebarCheckoutState?.state === 'free_tier' || sidebarCheckoutState?.state === 'subscriber_no_credits' ? (
          <>
            {sidebarCheckoutState.upsell_message && (
              <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                <p className="text-[11px] text-amber-700">{sidebarCheckoutState.upsell_message}</p>
              </div>
            )}
            <div className="bg-gray-50 rounded-xl p-3.5 space-y-2">
              {sidebarCheckoutState.discount_pct > 0 && (
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-500">Base price</span>
                  <span className="line-through text-gray-300">${(sidebarCheckoutState.base_price_cents / 100).toFixed(0)}</span>
                </div>
              )}
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-gray-700 font-semibold">
                  {sidebarCheckoutState.discount_pct > 0 ? `Your price (${sidebarCheckoutState.discount_pct}% off)` : 'Price'}
                </span>
                <span className="text-gray-900 font-bold">${(sidebarCheckoutState.final_price_cents / 100).toFixed(0)}</span>
              </div>
            </div>
            {generateError && <p className="text-[10px] text-red-600">{generateError}</p>}
            <button
              onClick={() => {
                const report = allReports.find(r => r.slug === sidebarReport)
                if (report) handleReportAction(report)
              }}
              disabled={purchaseLoading || !!generatingReport}
              className="w-full py-3 text-white rounded-xl text-sm font-semibold transition-all hover:shadow-md active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
              style={{ background: 'linear-gradient(135deg, #0F6E56, #185FA5)' }}
            >
              {purchaseLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Redirecting...</> : <><ShoppingCart className="w-4 h-4" /> {sidebarCheckoutState.primary_cta}</>}
            </button>
            <Link to="/billing" className="block text-center text-[11px] text-[#185FA5] hover:underline">
              Subscribe & save 20%+ →
            </Link>
          </>
        ) : (
          <>
            {selectedSidebarReport && (
              <div className="bg-gray-50 rounded-xl p-3.5 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-700 font-semibold">OppGrid Price</span>
                  <span className="text-[#0F6E56] font-bold text-base">{selectedSidebarReport.price}</span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-gray-400">Consultant equivalent</span>
                  <span className="text-gray-400 line-through">{selectedSidebarReport.consultantPrice}</span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-gray-400">Delivery time</span>
                  <span className="text-gray-500 font-medium">{selectedSidebarReport.deliveryTime}</span>
                </div>
              </div>
            )}
            {isGuest && (
              <div>
                <label className="text-[11px] font-medium text-gray-500 mb-1.5 block">
                  Email for delivery <span className="text-red-400 font-normal">(required)</span>
                </label>
                <input
                  type="email"
                  value={sidebarEmail}
                  onChange={(e) => { setSidebarEmail(e.target.value); setSidebarEmailError(null) }}
                  placeholder="your@email.com"
                  className="w-full p-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56] transition-all placeholder:text-gray-400"
                />
                <p className="text-[10px] text-gray-400 mt-1">Reports are also available in your dashboard</p>
                {sidebarEmailError && <p className="text-[10px] text-red-500 mt-1 font-medium">{sidebarEmailError}</p>}
              </div>
            )}
            {generateError && <p className="text-[10px] text-red-600">{generateError}</p>}
            <button
              onClick={() => {
                const report = allReports.find(r => r.slug === sidebarReport)
                if (report) handleReportAction(report)
              }}
              disabled={purchaseLoading || !!generatingReport || (isGuest && !isValidSidebarEmail)}
              className="w-full py-3 text-white rounded-xl text-sm font-semibold transition-all hover:shadow-md active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
              style={{ background: 'linear-gradient(135deg, #0F6E56, #185FA5)' }}
            >
              {purchaseLoading || generatingReport ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</> : <><ShoppingCart className="w-4 h-4" /> Get Report</>}
            </button>
          </>
        )}

        <div className="border-t border-gray-100 pt-3 space-y-2 text-[11px] text-gray-500">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-3.5 h-3.5 text-[#0F6E56] shrink-0" />
            <span>AI-powered analysis in minutes</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-3.5 h-3.5 text-[#0F6E56] shrink-0" />
            <span>Export to PDF, Word, or print</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-3.5 h-3.5 text-[#0F6E56] shrink-0" />
            <span>Available in your dashboard</span>
          </div>
        </div>

      </div>
    </div>
  )

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 items-start">
      <div className="bg-white rounded-2xl border border-gray-200 p-5 sm:p-6 shadow-sm">
        <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-5">
          {INPUT_MODES.map((mode) => {
            const Icon = mode.icon
            return (
              <button
                key={mode.id}
                onClick={() => {
                  setInputMode(mode.id)
                  setConsultantResult(null)
                  setFreeReports({})
                  setAnalysisError(null)
                }}
                aria-label={mode.label}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-3 rounded-xl text-xs font-medium transition-all ${
                  inputMode === mode.id
                    ? 'bg-white text-gray-900 shadow-sm border border-gray-200'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{mode.label}</span>
              </button>
            )
          })}
        </div>

        {inputMode === 'validate' && (
          <textarea
            value={ideaDescription}
            onChange={(e) => setIdeaDescription(e.target.value)}
            placeholder="Describe your business idea in detail — the more context you provide, the better your analysis will be..."
            className="w-full border border-gray-200 rounded-xl p-4 text-sm text-gray-700 bg-gray-50/50 resize-none focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56] transition-all placeholder:text-gray-400"
            rows={4}
          />
        )}

        {inputMode === 'search' && (
          <div className="space-y-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search keyword (e.g., coffee, fitness, SaaS...)"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            />
            <select
              value={searchCategory}
              onChange={(e) => setSearchCategory(e.target.value)}
              className="w-full p-3 border border-gray-200 rounded-lg bg-gray-50 text-sm focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            >
              <option value="">All Categories</option>
              <option value="work_productivity">Work & Productivity</option>
              <option value="money_finance">Money & Finance</option>
              <option value="health_wellness">Health & Wellness</option>
              <option value="technology">Technology</option>
            </select>
          </div>
        )}

        {inputMode === 'location' && (
          <div className="space-y-3">
            <input
              type="text"
              value={locationCity}
              onChange={(e) => setLocationCity(e.target.value)}
              placeholder="City (e.g., Miami, Florida)"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            />
            <input
              type="text"
              value={locationBusiness}
              onChange={(e) => setLocationBusiness(e.target.value)}
              placeholder="Business type (e.g., Coffee shop)"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            />
          </div>
        )}

        {inputMode === 'clone' && (
          <div className="space-y-3">
            <input
              type="text"
              value={cloneBusinessName}
              onChange={(e) => setCloneBusinessName(e.target.value)}
              placeholder="Business name (e.g., Sweetgreen)"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            />
            <input
              type="text"
              value={cloneBusinessAddress}
              onChange={(e) => setCloneBusinessAddress(e.target.value)}
              placeholder="Business address"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            />
            <input
              type="text"
              value={cloneTargetCity}
              onChange={(e) => setCloneTargetCity(e.target.value)}
              placeholder="Target city (optional)"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
            />
          </div>
        )}

        {analysisError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{analysisError}</p>
          </div>
        )}

        <button
          onClick={runConsultantAnalysis}
          disabled={!canAnalyze() || consultantLoading}
          className="mt-4 w-full py-3 bg-[#0F6E56] hover:bg-[#0a5a44] text-white rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md active:scale-[0.98]"
        >
          {consultantLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Analyze & Generate Reports
            </>
          )}
        </button>
      </div>
      {sidebarCard}
      </div>

      {consultantLoading && !consultantResult && (
        <div className="bg-white rounded-2xl border border-gray-100 p-5 sm:p-6 shadow-sm mt-4">
          <div className="animate-pulse space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-2 h-5 bg-gray-200 rounded-full" />
              <div className="h-4 bg-gray-200 rounded w-32" />
            </div>
            <div className="rounded-xl p-4 bg-gray-50 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-gray-200 rounded-full" />
                <div className="h-3 bg-gray-200 rounded w-24" />
                <div className="ml-auto h-5 bg-gray-200 rounded w-20" />
              </div>
              <div className="h-3 bg-gray-200 rounded w-full" />
              <div className="h-3 bg-gray-200 rounded w-4/5" />
              <div className="h-3 bg-gray-200 rounded w-2/3" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[0,1,2].map(i => (
                <div key={i} className="bg-gray-50 rounded-xl p-3 text-center space-y-2">
                  <div className="h-2 bg-gray-200 rounded w-3/4 mx-auto" />
                  <div className="h-5 bg-gray-200 rounded w-1/2 mx-auto" />
                  <div className="h-2 bg-gray-200 rounded w-2/3 mx-auto" />
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-gray-200 rounded w-full" />
              <div className="h-3 bg-gray-200 rounded w-4/5" />
            </div>
            <p className="text-xs text-gray-400 text-center pt-1">AI analysis in progress — typically 15–30 seconds</p>
          </div>
        </div>
      )}

      {consultantResult && consultantResult.success && (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 sm:p-6 shadow-sm animate-slide-up" style={{ borderLeft: '3px solid #0F6E56' }}>
          <div className="flex items-center gap-2 mb-5">
            <div className="w-1.5 h-5 rounded-full bg-[#0F6E56]" />
            <h2 className="text-lg font-bold text-gray-900">Analysis Results</h2>
            {inputMode === 'validate' && consultantResult.recommendation && (
              <span className="ml-auto text-[10px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                {consultantResult.recommendation.charAt(0).toUpperCase() + consultantResult.recommendation.slice(1)} Business
              </span>
            )}
            <button onClick={() => setConsultantResult(null)} className="text-gray-400 hover:text-gray-600 ml-2 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* ── INTELLIGENCE CARD ─────────────────────────────── */}
          {consultantResult.intel_verdict && (
            <div className="mb-5">
              {/* Verdict box */}
              <div className="rounded-r-xl mb-4 p-3.5" style={{
                background: 'linear-gradient(135deg,#f8faf9 0%,#e8f4f0 100%)',
                borderLeft: '4px solid #0F6E56',
              }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-base">{consultantResult.intel_verdict.icon}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[#0F6E56]">
                    {consultantResult.intel_verdict.label}
                  </span>
                  <span className="ml-auto text-[10px] font-medium px-2 py-0.5 rounded"
                    style={{
                      background: consultantResult.intel_verdict.signal === 'green' ? '#E1F5EE'
                        : consultantResult.intel_verdict.signal === 'yellow' ? '#FAEEDA' : '#FCEBEB',
                      color: consultantResult.intel_verdict.signal === 'green' ? '#0F6E56'
                        : consultantResult.intel_verdict.signal === 'yellow' ? '#854F0B' : '#A32D2D',
                    }}>
                    {consultantResult.intel_verdict.signal_text}
                  </span>
                </div>
                {consultantResult.intel_verdict.summary && (
                  <p className="text-[13px] text-gray-700 leading-relaxed m-0">
                    {consultantResult.intel_verdict.summary
                      .replace(/<strong>/g, '\u200B__BOLD__')
                      .replace(/<\/strong>/g, '__END__\u200B')
                      .split('\u200B')
                      .map((part: string, idx: number) => {
                        if (part.startsWith('__BOLD__') && part.endsWith('__END__')) {
                          return <strong key={idx} className="text-[#0F6E56] font-semibold">{part.slice(8, -7)}</strong>
                        }
                        if (part.startsWith('__BOLD__')) {
                          return <strong key={idx} className="text-[#0F6E56] font-semibold">{part.slice(8)}</strong>
                        }
                        const text = part.replace(/__END__/g, '').replace(/<[^>]+>/g, '')
                        return text ? <span key={idx}>{text}</span> : null
                      })
                    }
                  </p>
                )}
              </div>

              {/* Metric cards */}
              {consultantResult.intel_metrics && consultantResult.intel_metrics.length > 0 && (
                <div className={`grid gap-3 mb-4`} style={{
                  gridTemplateColumns: `repeat(${Math.min(consultantResult.intel_metrics.length, 4)}, 1fr)`
                }}>
                  {consultantResult.intel_metrics.map((m: any, i: number) => (
                    <div key={i} className="bg-gray-50 rounded-xl p-3 text-center">
                      <div className="text-[10px] text-gray-400 uppercase tracking-wide mb-1">{m.label}</div>
                      <div className={`text-[17px] font-semibold ${
                        m.color === 'success' ? 'text-[#0F6E56]'
                        : m.color === 'warning' ? 'text-amber-600'
                        : m.color === 'danger' ? 'text-red-600'
                        : 'text-gray-900'
                      }`}>{String(m.value)}</div>
                      {m.subtext && <div className="text-[10px] text-gray-400 mt-0.5">{m.subtext}</div>}
                    </div>
                  ))}
                </div>
              )}

              {/* Insights (validate + clone) */}
              {consultantResult.intel_insights && consultantResult.intel_insights.length > 0 && (
                <div className="space-y-2 mb-4">
                  {consultantResult.intel_insights.map((ins: any, i: number) => (
                    <div key={i} className="flex items-start gap-3 pt-2 border-t border-gray-100">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] flex-shrink-0 ${
                        ins.type === 'positive' ? 'bg-emerald-50 text-emerald-700'
                        : ins.type === 'caution' ? 'bg-amber-50 text-amber-700'
                        : 'bg-blue-50 text-blue-700'
                      }`}>
                        {ins.type === 'positive' ? '✓' : ins.type === 'caution' ? '!' : '→'}
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-400 block mb-0.5">{ins.label}</span>
                        <span className="text-[12px] text-gray-700 leading-snug">{ins.text}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Competitor tags (validate mode) */}
              {inputMode === 'validate' && consultantResult.intel_verdict && consultantResult.key_competitors && consultantResult.key_competitors.length > 0 && (
                <div className="mb-4">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">Known competitors</div>
                  <div className="flex flex-wrap gap-1.5">
                    {consultantResult.key_competitors.map((comp: string, i: number) => (
                      <span key={i} className="text-[11px] px-2 py-1 rounded-full bg-gray-100 text-gray-600 font-medium border border-gray-200">{comp}</span>
                    ))}
                  </div>
                </div>
              )}
              {/* Competitor placeholder when no data (validate mode) */}
              {inputMode === 'validate' && consultantResult.intel_verdict && (!consultantResult.key_competitors || consultantResult.key_competitors.length === 0) && (
                <div className="mb-4">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">Known competitors</div>
                  <div className="flex flex-wrap gap-1.5">
                    <span className="text-[11px] px-2 py-1 rounded-full bg-gray-50 text-gray-400 font-medium border border-gray-100 italic">No established competitors identified — early market</span>
                  </div>
                </div>
              )}

              {/* Top signals (search mode) */}
              {consultantResult.intel_top_signals && consultantResult.intel_top_signals.length > 0 && (
                <div className="mb-4">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">Top signals this week</div>
                  <div className="space-y-2">
                    {consultantResult.intel_top_signals.map((sig: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg">
                        <div>
                          <div className="text-[12px] font-medium text-gray-800">{sig.name || sig.title}</div>
                          {(sig.tam_label || sig.tam) && <div className="text-[10px] text-gray-400">TAM: {sig.tam_label || sig.tam}</div>}
                        </div>
                        <div className="text-right">
                          <div className="text-[11px] font-semibold text-[#0F6E56]">↑{sig.velocity_pct}%</div>
                          <div className="text-[10px] text-gray-400">{sig.member_count ?? sig.mention_count ?? 0} signals</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Micro-markets (location mode) */}
              {consultantResult.intel_micro_markets && consultantResult.intel_micro_markets.length > 0 && (
                <div className="mb-4">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">Recommended micro-markets</div>
                  <div className="space-y-2">
                    {consultantResult.intel_micro_markets.map((mm: any, i: number) => (
                      <div key={i} className="flex items-center gap-3 p-2.5 bg-gray-50 rounded-lg">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0 ${
                          mm.score_label === 'high' ? 'bg-emerald-50 text-[#0F6E56]'
                          : mm.score_label === 'medium' ? 'bg-amber-50 text-amber-700'
                          : 'bg-red-50 text-red-700'
                        }`}>{mm.score}</div>
                        <div>
                          <div className="text-[12px] font-medium text-gray-800">{mm.name}</div>
                          <div className="text-[10px] text-gray-500">{mm.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Why it works (clone mode) */}
              {consultantResult.intel_why_it_works && consultantResult.intel_why_it_works.length > 0 && (
                <div className="mb-4">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">Why this model works</div>
                  <div className="space-y-1.5">
                    {consultantResult.intel_why_it_works.map((bullet: string, i: number) => (
                      <div key={i} className="flex items-start gap-2 text-[12px] text-gray-700">
                        <span className="text-[#0F6E56] mt-0.5 flex-shrink-0">•</span>
                        <span>{bullet}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Demographics (location mode) */}
              {consultantResult.intel_demographics && (
                <div className="grid grid-cols-2 gap-2 mb-4 text-[11px] text-gray-500">
                  {consultantResult.intel_demographics.median_income && (
                    <div>💰 Median income: <strong className="text-gray-700">${consultantResult.intel_demographics.median_income.toLocaleString()}</strong></div>
                  )}
                  {consultantResult.intel_demographics.age_25_44_pct && (
                    <div>👥 25–44 demographic: <strong className="text-gray-700">{consultantResult.intel_demographics.age_25_44_pct}%</strong></div>
                  )}
                  {consultantResult.intel_demographics.pop_growth && (
                    <div>📈 Pop. growth: <strong className="text-gray-700">+{consultantResult.intel_demographics.pop_growth}%</strong></div>
                  )}
                </div>
              )}

              {/* Source tags */}
              {consultantResult.intel_tags && consultantResult.intel_tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {consultantResult.intel_tags.map((tag: string, i: number) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-gray-100 text-gray-400">{tag}</span>
                  ))}
                </div>
              )}

              {/* CTA — 3-state checkout panel */}
              {consultantResult.intel_cta && (() => {
                const ctaSlugMap: Record<string, string> = {
                  'Feasibility Study': 'feasibility_study',
                  'Business Plan': 'business_plan',
                  'Deep Clone Analysis': 'competitive_analysis',
                  'Subscription': 'market_analysis',
                }
                const ctaSlug = ctaSlugMap[consultantResult.intel_cta.report_type] || 'market_analysis'
                const ctaReport = allReports.find(r => r.slug === ctaSlug)
                const cs = checkoutState
                const selectedOpt = cs?.report_options?.find((o: any) => o.report_type === ctaSlug) || null

                return (
                  <div className="pt-3 border-t border-gray-100 space-y-3">

                    {/* ── STATE: SUBSCRIBER WITH CREDITS ── */}
                    {cs?.state === 'subscriber_has_credits' && (
                      <>
                        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0F6E56]/10 w-fit">
                          <CheckCircle className="w-3.5 h-3.5 text-[#0F6E56]" />
                          <span className="text-[11px] font-semibold text-[#0F6E56]">
                            {cs.reports_remaining === -1
                              ? 'Unlimited reports'
                              : `${cs.reports_remaining} of ${cs.reports_total} reports remaining this month`}
                          </span>
                        </div>
                        <div className="space-y-1 text-[11px]">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-500">Report value</span>
                            <span className="line-through text-gray-300">${(cs.base_price_cents / 100).toFixed(0)}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-gray-700 font-medium">Your price</span>
                            <span className="text-[#0F6E56] font-bold">$0 (included)</span>
                          </div>
                        </div>
                        {generateError && <p className="text-[10px] text-red-600">{generateError}</p>}
                        <button
                          onClick={() => ctaReport && handleSubscriberGenerate(ctaReport.slug)}
                          disabled={purchaseLoading || !!generatingReport}
                          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-white text-[12px] font-semibold disabled:opacity-50 transition-all hover:shadow-md"
                          style={{ background: 'linear-gradient(135deg, #0F6E56, #185FA5)' }}
                        >
                          {generatingReport ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><FileText className="w-3.5 h-3.5" /> Generate report (use 1 credit)</>}
                        </button>
                      </>
                    )}

                    {/* ── STATE: GUEST ── */}
                    {(!cs || cs.state === 'guest') && (
                      <>
                        <div>
                          <p className="text-[11px] text-gray-500 mb-1.5">Enter your email to receive the report:</p>
                          <input
                            type="email"
                            placeholder="you@example.com"
                            value={guestEmail}
                            onChange={e => { setGuestEmail(e.target.value); setGuestEmailError(null) }}
                            className="w-full text-[12px] px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0F6E56]/30 focus:border-[#0F6E56]"
                          />
                          {guestEmailError && <p className="text-[10px] text-red-500 mt-1">{guestEmailError}</p>}
                        </div>
                        {generateError && <p className="text-[10px] text-red-600">{generateError}</p>}
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] text-gray-500">{consultantResult.intel_cta.text}</span>
                          <button
                            onClick={() => { if (ctaReport) handleCtaCheckout(ctaReport) }}
                            disabled={purchaseLoading || !ctaReport || !isValidGuestEmail}
                            className="flex-shrink-0 text-[11px] font-semibold px-3 py-1.5 rounded-lg text-white disabled:opacity-40 transition-all"
                            style={{ background: '#0F6E56' }}
                          >
                            {purchaseLoading ? 'Redirecting...' : `Get ${consultantResult.intel_cta.report_type} → $${consultantResult.intel_cta.price}`}
                          </button>
                        </div>
                        <Link to="/register" className="block text-center text-[10px] text-[#185FA5] hover:underline">
                          Create free account (save 20%)
                        </Link>
                      </>
                    )}

                    {/* ── STATE: FREE TIER or NO CREDITS (auth user needs to pay) ── */}
                    {cs && (cs.state === 'free_tier' || cs.state === 'subscriber_no_credits') && (
                      <>
                        {cs.upsell_message && (
                          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                            <p className="text-[11px] text-amber-700">{cs.upsell_message}</p>
                          </div>
                        )}
                        <div className="space-y-1 text-[11px]">
                          {cs.discount_pct > 0 && (
                            <div className="flex items-center justify-between">
                              <span className="text-gray-500">Base price</span>
                              <span className="line-through text-gray-300">${(cs.base_price_cents / 100).toFixed(0)}</span>
                            </div>
                          )}
                          <div className="flex items-center justify-between">
                            <span className="text-gray-700 font-medium">
                              {cs.discount_pct > 0 ? `Your price (${cs.discount_pct}% off)` : 'Price'}
                            </span>
                            <span className="text-gray-900 font-bold">${(cs.final_price_cents / 100).toFixed(0)}</span>
                          </div>
                        </div>
                        {generateError && <p className="text-[10px] text-red-600">{generateError}</p>}
                        <button
                          onClick={() => { if (ctaReport) handleCtaCheckout(ctaReport) }}
                          disabled={purchaseLoading || !ctaReport}
                          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-white text-[12px] font-semibold disabled:opacity-50 transition-all hover:shadow-md"
                          style={{ background: 'linear-gradient(135deg, #0F6E56, #185FA5)' }}
                        >
                          {purchaseLoading ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Redirecting...</> : <><ShoppingCart className="w-3.5 h-3.5" /> {cs.primary_cta}</>}
                        </button>
                        <Link to="/billing" className="block text-center text-[10px] text-[#185FA5] hover:underline">
                          Subscribe & save 20%+ →
                        </Link>
                      </>
                    )}

                  </div>
                )
              })()}
            </div>
          )}
          {/* ── END INTELLIGENCE CARD ─────────────────────────────── */}

          {inputMode === 'validate' && !consultantResult.intel_verdict && (
            <>
              <div className="flex flex-wrap justify-center gap-4 sm:gap-6 mb-5">
                <ScoreRing
                  score={consultantResult.confidence_score || Math.round(((consultantResult.online_score || 0) + (consultantResult.physical_score || 0)) / 2)}
                  label="Overall"
                  color="#0F6E56"
                />
                <ScoreRing score={consultantResult.online_score || 0} label="Online" color="#185FA5" />
                <ScoreRing score={consultantResult.physical_score || 0} label="Physical" color="#D97757" />
                {consultantResult.four_ps_scores && (
                  <ScoreRing
                    score={Math.round(
                      ((consultantResult.four_ps_scores.product || 0) +
                        (consultantResult.four_ps_scores.price || 0) +
                        (consultantResult.four_ps_scores.place || 0) +
                        (consultantResult.four_ps_scores.promotion || 0)) / 4
                    )}
                    label="4P's Avg"
                    color="#BA7517"
                  />
                )}
              </div>

              {consultantResult.four_ps_scores && (
                <div className="space-y-2.5 mb-6 bg-gray-50/50 rounded-xl p-4">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">4P's Analysis</h4>
                  <FourPsHorizontalBar label="Product" score={consultantResult.four_ps_scores.product || 0} color="#0F6E56" />
                  <FourPsHorizontalBar label="Price" score={consultantResult.four_ps_scores.price || 0} color="#185FA5" />
                  <FourPsHorizontalBar label="Place" score={consultantResult.four_ps_scores.place || 0} color="#D97757" />
                  <FourPsHorizontalBar label="Promotion" score={consultantResult.four_ps_scores.promotion || 0} color="#BA7517" />
                </div>
              )}

              {consultantResult.viability_report && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
                  {(consultantResult.viability_report.tam || consultantResult.viability_report.market_size) && (
                    <div className="p-3 rounded-xl border border-gray-100 bg-gray-50 text-center" style={{ borderTop: '2px solid #185FA5' }}>
                      <p className="text-[10px] text-gray-500 mb-1 font-medium">Market Size</p>
                      <p className="text-sm font-bold text-[#185FA5]">
                        {consultantResult.viability_report.tam || consultantResult.viability_report.market_size}
                      </p>
                    </div>
                  )}
                  {(consultantResult.market_intelligence?.growth_trend || consultantResult.viability_report.growth) && (
                    <div className="p-3 rounded-xl border border-gray-100 bg-gray-50 text-center" style={{ borderTop: '2px solid #0F6E56' }}>
                      <p className="text-[10px] text-gray-500 mb-1 font-medium">Growth</p>
                      <p className="text-sm font-bold text-[#0F6E56]">
                        {consultantResult.market_intelligence?.growth_trend || consultantResult.viability_report.growth}
                      </p>
                    </div>
                  )}
                  {(consultantResult.market_intelligence?.competition_level || consultantResult.viability_report.competition) && (
                    <div className="p-3 rounded-xl border border-gray-100 bg-gray-50 text-center" style={{ borderTop: '2px solid #BA7517' }}>
                      <p className="text-[10px] text-gray-500 mb-1 font-medium">Competition</p>
                      <p className="text-sm font-bold text-[#BA7517]">
                        {consultantResult.market_intelligence?.competition_level || consultantResult.viability_report.competition}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                <div className="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100">
                  <h4 className="text-xs font-semibold text-emerald-800 mb-3 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> Key Advantages
                  </h4>
                  <ul className="space-y-2">
                    {(consultantResult.advantages || consultantResult.viability_report?.strengths || []).slice(0, 4).map((a: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-700 leading-relaxed">
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                        {typeof a === 'string' ? a : JSON.stringify(a)}
                      </li>
                    ))}
                    {!(consultantResult.advantages || consultantResult.viability_report?.strengths || []).length && (
                      <li className="text-xs text-gray-400">Details available in full report</li>
                    )}
                  </ul>
                </div>
                <div className="bg-amber-50/50 rounded-xl p-4 border border-amber-100">
                  <h4 className="text-xs font-semibold text-amber-800 mb-3 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> Key Risks
                  </h4>
                  <ul className="space-y-2">
                    {(consultantResult.risks || consultantResult.viability_report?.weaknesses || []).slice(0, 4).map((r: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-700 leading-relaxed">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                        {typeof r === 'string' ? r : JSON.stringify(r)}
                      </li>
                    ))}
                    {!(consultantResult.risks || consultantResult.viability_report?.weaknesses || []).length && (
                      <li className="text-xs text-gray-400">Risk analysis available in full report</li>
                    )}
                  </ul>
                </div>
              </div>
            </>
          )}

          {inputMode === 'search' && !consultantResult.intel_verdict && (
            <div className="space-y-3">
              {consultantResult.ai_synthesis && (
                <div className="rounded-lg p-3 mb-3 border-l-3 bg-amber-50" style={{ borderLeft: '3px solid #D97757' }}>
                  <p className="text-sm text-gray-700 leading-relaxed">{consultantResult.ai_synthesis}</p>
                </div>
              )}
              <p className="text-sm text-gray-500">Found {consultantResult.total_count || 0} opportunities</p>
              {consultantResult.opportunities?.slice(0, 5).map((opp: any) => (
                <OppRow key={opp.id} title={opp.title} category={opp.category} score={opp.score} to={`/opportunity/${opp.id}`} />
              ))}
            </div>
          )}

          {inputMode === 'search' && consultantResult.intel_verdict && consultantResult.total_count > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-[11px] text-gray-400 mb-2">Top matching opportunities ({consultantResult.total_count})</p>
              {consultantResult.opportunities?.slice(0, 3).map((opp: any) => (
                <OppRow key={opp.id} title={opp.title} category={opp.category} score={opp.score} to={`/opportunity/${opp.id}`} />
              ))}
            </div>
          )}

          {inputMode === 'location' && !consultantResult.intel_verdict && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {consultantResult.inferred_category && (
                  <div className="p-3 rounded-xl border border-gray-100 bg-gray-50 text-center" style={{ borderTop: '2px solid #0F6E56' }}>
                    <p className="text-[10px] text-gray-500 mb-1 font-medium">Category</p>
                    <p className="text-sm font-bold text-[#0F6E56]">{consultantResult.inferred_category}</p>
                  </div>
                )}
                <div className="p-3 rounded-xl border border-gray-100 bg-gray-50 text-center" style={{ borderTop: '2px solid #BA7517' }}>
                  <p className="text-[10px] text-gray-500 mb-1 font-medium">Competitors</p>
                  <p className="text-sm font-bold text-[#BA7517]">{consultantResult.geo_analysis?.competitors?.length || 0}</p>
                </div>
                {consultantResult.geo_analysis?.market_density && (
                  <div className="p-3 rounded-xl border border-gray-100 bg-gray-50 text-center" style={{ borderTop: '2px solid #185FA5' }}>
                    <p className="text-[10px] text-gray-500 mb-1 font-medium">Density</p>
                    <p className="text-sm font-bold text-[#185FA5]">{consultantResult.geo_analysis.market_density}</p>
                  </div>
                )}
              </div>
              {consultantResult.four_ps_scores && (
                <div className="space-y-2">
                  <FourPsHorizontalBar label="Product" score={consultantResult.four_ps_scores.product || 0} color="#0F6E56" />
                  <FourPsHorizontalBar label="Price" score={consultantResult.four_ps_scores.price || 0} color="#185FA5" />
                  <FourPsHorizontalBar label="Place" score={consultantResult.four_ps_scores.place || 0} color="#D97757" />
                  <FourPsHorizontalBar label="Promotion" score={consultantResult.four_ps_scores.promotion || 0} color="#BA7517" />
                </div>
              )}
              {consultantResult.site_recommendations?.slice(0, 3).map((site: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium" style={{
                    background: (site.priority === 'High' || idx < 2) ? '#E1F5EE' : '#FFF7ED',
                    color: (site.priority === 'High' || idx < 2) ? '#085041' : '#BA7517',
                  }}>{site.priority || (idx < 2 ? 'High' : 'Medium')}</span>
                  <div>
                    <div className="text-sm font-medium text-gray-900">{site.name || site.area || `Site ${idx + 1}`}</div>
                    {site.reason && <div className="text-xs text-gray-500">{site.reason}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {inputMode === 'clone' && !consultantResult.intel_verdict && (
            <div className="space-y-3">
              {consultantResult.source_business && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Source business</p>
                  <p className="font-medium text-gray-900">{consultantResult.source_business.name}</p>
                  {consultantResult.source_business.category && (
                    <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">
                      {consultantResult.source_business.category}
                    </span>
                  )}
                </div>
              )}
              <p className="text-sm text-gray-500">Found {consultantResult.matching_locations?.length || 0} matching locations</p>
              {consultantResult.matching_locations?.slice(0, 3).map((loc: any, idx: number) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg flex justify-between items-center">
                  <div>
                    <div className="font-medium text-gray-900 text-sm">{loc.name}</div>
                    <div className="text-xs text-gray-500">{loc.city}, {loc.state}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-[#0F6E56]">{loc.similarity_score}%</div>
                    <div className="text-[10px] text-gray-400">Match</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {inputMode === 'clone' && consultantResult.intel_verdict && consultantResult.matching_locations?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-[11px] text-gray-400 mb-2">Best matching locations ({consultantResult.matching_locations.length} found)</p>
              {consultantResult.matching_locations.slice(0, 3).map((loc: any, idx: number) => (
                <div key={idx} className="p-3 mb-2 bg-gray-50 rounded-lg flex justify-between items-center">
                  <div>
                    <div className="font-medium text-gray-900 text-sm">{loc.name}</div>
                    <div className="text-xs text-gray-500">{loc.city}, {loc.state}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-[#0F6E56]">{loc.similarity_score}%</div>
                    <div className="text-[10px] text-gray-400">Match</div>
                  </div>
                </div>
              ))}
            </div>
          )}


        </div>
      )}

      {(consultantResult?.success || !consultantResult) && (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 sm:p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-5 rounded-full bg-[#0F6E56]" />
              <h2 className="text-lg font-bold text-gray-900">Go Deeper</h2>
              <span className="ml-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-500">{TOTAL_REPORTS} reports</span>
            </div>
            <span className="text-[10px] px-2.5 py-1 rounded-full font-semibold bg-amber-50 text-amber-700 border border-amber-200 hidden sm:inline">Save up to 30% with bundles</span>
          </div>
          <p className="text-xs text-gray-500 mb-5">Purchase additional reports tailored to your business context. Each uses your analysis data for personalized insights.</p>

          {generateError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{generateError}</p>
              <button onClick={() => setGenerateError(null)} className="text-xs text-red-500 mt-1 hover:underline">Dismiss</button>
            </div>
          )}

          <div className="space-y-1">
            {REPORT_CATEGORIES.map((cat) => {
              const CatIcon = cat.icon
              const isCatExpanded = expandedCategory === cat.id
              return (
                <div key={cat.id} className={`rounded-xl transition-all ${isCatExpanded ? 'bg-white border border-gray-200 shadow-sm' : ''}`}>
                  <button
                    onClick={() => setExpandedCategory(isCatExpanded ? null : cat.id)}
                    className={`w-full text-left flex items-center gap-2.5 px-3 py-3 rounded-xl transition-all ${
                      isCatExpanded ? 'bg-gray-50 rounded-b-none border-b border-gray-100' : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${cat.color}12` }}>
                      <CatIcon className="w-3.5 h-3.5" style={{ color: cat.color }} />
                    </div>
                    <span className="flex-1 text-sm font-semibold text-gray-900">{cat.label}</span>
                    <span className="text-[10px] text-gray-400">{cat.reports.length} reports</span>
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isCatExpanded ? 'rotate-180' : ''}`} />
                  </button>

                  {isCatExpanded && (
                    <div className="px-2 pb-2 space-y-0.5">
                      {cat.reports.map((report) => {
                        const Icon = report.icon
                        const isExpanded = expandedReport === report.slug
                        return (
                          <div key={report.slug} className={`transition-all ${isExpanded ? 'bg-white rounded-xl shadow-sm border border-gray-200' : ''}`}>
                            <button
                              onClick={() => setExpandedReport(isExpanded ? null : report.slug)}
                              className={`w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                                isExpanded ? 'bg-gray-50 rounded-b-none' : 'hover:bg-gray-50'
                              }`}
                            >
                              <div className="w-7 h-7 rounded-md flex items-center justify-center shrink-0" style={{ background: `${report.accentColor}12` }}>
                                <Icon className="w-3.5 h-3.5" style={{ color: report.accentColor }} />
                              </div>
                              <span className="flex-1 text-sm font-medium text-gray-900 truncate">{report.title}</span>
                              <span className="text-xs text-gray-400 hidden sm:inline">{report.deliveryTime}</span>
                              <span className="text-sm font-semibold min-w-[50px] text-right" style={{ color: report.accentColor }}>{report.price}</span>
                              <span className="text-[10px] text-gray-400 line-through min-w-[80px] text-right hidden sm:inline">{report.consultantPrice}</span>
                              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`} />
                            </button>
                            {isExpanded && (
                              <div className="px-4 pb-4 pt-3">
                                <p className="text-xs text-gray-600 mb-3">{report.description}</p>
                                <div className="flex flex-wrap gap-1.5 mb-4">
                                  {report.sections.map((s, i) => (
                                    <span key={i} className="px-2.5 py-1 rounded-lg text-[10px] font-medium bg-gray-50 text-gray-500 border border-gray-100">{s}</span>
                                  ))}
                                </div>
                                <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                                  <div className="flex items-center gap-4">
                                    <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
                                      <Clock className="w-3.5 h-3.5" /> {report.deliveryTime}
                                    </div>
                                    <div className="flex items-center gap-1 text-[10px] text-gray-400 line-through">
                                      {report.consultantPrice}
                                    </div>
                                  </div>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleReportAction(report)
                                    }}
                                    disabled={purchaseLoading || generatingReport === report.slug}
                                    className="px-5 py-2 rounded-xl text-white text-xs font-semibold flex items-center gap-1.5 transition-all hover:shadow-md active:scale-[0.98] disabled:opacity-50"
                                    style={{ background: report.accentColor }}
                                  >
                                    {purchaseLoading || generatingReport === report.slug ? (
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    ) : (
                                      <ShoppingCart className="w-3.5 h-3.5" />
                                    )}
                                    {generatingReport === report.slug ? 'Generating...' : 'Get Report'}
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {isGuest ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 sm:p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1.5 h-5 rounded-full bg-gray-400" />
            <h2 className="text-lg font-bold text-gray-900">Report History</h2>
          </div>
          <div className="text-center py-8">
            <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-700 mb-1">Sign in to save and access your reports</p>
            <p className="text-xs text-gray-400 mb-5">Your analysis data is preserved after sign-in</p>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-medium hover:bg-gray-800 transition-all hover:shadow-md active:scale-[0.98]"
            >
              <LogIn className="w-4 h-4" />
              Sign In
            </Link>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 p-5 sm:p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-5 rounded-full bg-[#185FA5]" />
            <h2 className="text-lg font-bold text-gray-900">Report History</h2>
            <span className="ml-auto text-[10px] text-gray-400">{reportHistory?.length || 0} reports</span>
          </div>
          {reportHistory && reportHistory.length > 0 ? (
            <div className="space-y-2">
              {reportHistory.slice(0, 10).map((report) => (
                <button
                  key={report.id}
                  onClick={() => setViewingReport(report)}
                  className="w-full text-left flex items-center gap-3 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-all group"
                >
                  <div className="w-8 h-8 rounded-lg bg-[#185FA5]/10 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-[#185FA5]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{report.title || report.report_type}</p>
                    <p className="text-[10px] text-gray-400">
                      {new Date(report.created_at).toLocaleDateString()} · {report.status}
                    </p>
                  </div>
                  {report.confidence_score && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#0F6E56]/10 text-[#0F6E56] font-semibold">{report.confidence_score}%</span>
                  )}
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors shrink-0" />
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
                <FileText className="w-5 h-5 text-gray-300" />
              </div>
              <p className="text-sm text-gray-400">No reports yet. Run an analysis to get started.</p>
            </div>
          )}
        </div>
      )}

      {viewingReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 animate-fade-in print-container" onClick={() => setViewingReport(null)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col animate-slide-up print-root" onClick={(e) => e.stopPropagation()}>
            <div className="bg-gradient-to-r from-[#0F6E56] to-[#185FA5] p-5 sm:p-6 text-white flex items-start justify-between shrink-0 report-header">
              <div>
                <p className="text-[10px] text-white/60 font-semibold uppercase tracking-wider">
                  {viewingReport.report_type?.replace(/_/g, ' ')}
                </p>
                <h3 className="text-lg font-bold mt-1">
                  {viewingReport.title || viewingReport.report_type?.replace(/_/g, ' ')}
                </h3>
                <div className="flex items-center gap-3 mt-2">
                  <p className="text-xs text-white/70">
                    Generated {viewingReport.created_at && !isNaN(new Date(viewingReport.created_at).getTime()) ? new Date(viewingReport.created_at).toLocaleDateString() : 'Today'}
                  </p>
                  {viewingReport.confidence_score && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/20 text-white font-medium">
                      AI Confidence: {viewingReport.confidence_score}%
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setViewingReport(null)}
                aria-label="Close report viewer"
                className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30 transition-colors shrink-0 ml-4"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="border-b border-gray-200 px-5 sm:px-6 py-3 flex items-center justify-between bg-gray-50/80 backdrop-blur-sm shrink-0 sticky top-0 z-10">
              <div className="flex gap-2">
                {viewingReport.id > 0 && (
                  <>
                    <button
                      onClick={() => handleExport('pdf')}
                      disabled={!!exportingFormat}
                      className="px-3.5 py-2 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-700 flex items-center gap-1.5 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 transition-all"
                    >
                      {exportingFormat === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} PDF
                    </button>
                    <button
                      onClick={() => handleExport('docx')}
                      disabled={!!exportingFormat}
                      className="px-3.5 py-2 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-700 flex items-center gap-1.5 hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 transition-all"
                    >
                      {exportingFormat === 'docx' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} Word
                    </button>
                    <button
                      onClick={() => window.print()}
                      className="px-3.5 py-2 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-700 flex items-center gap-1.5 hover:bg-gray-50 hover:border-gray-300 transition-all"
                    >
                      <Printer className="w-3.5 h-3.5" /> Print
                    </button>
                  </>
                )}
              </div>
              <button
                onClick={() => setViewingReport(null)}
                className="px-5 py-2 bg-[#0F6E56] text-white rounded-xl text-xs font-semibold hover:bg-[#0a5a46] transition-all"
              >
                Close
              </button>
            </div>

            <div className="p-5 sm:p-6 overflow-y-auto flex-1">
              {viewingReport.summary && (
                <div className="mb-5 p-4 bg-[#0F6E56]/5 rounded-xl border border-[#0F6E56]/15">
                  <h4 className="text-sm font-bold text-gray-900 mb-1">Summary</h4>
                  <p className="text-sm text-gray-700 leading-relaxed">{viewingReport.summary}</p>
                </div>
              )}

              {viewingReport.content && (
                <div className="prose prose-sm max-w-none">
                  {(() => {
                    try {
                      const parsed = JSON.parse(viewingReport.content)
                      if (parsed.viability_report || parsed.recommendation) {
                        return (
                          <div className="space-y-4">
                            {parsed.verdict_summary && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-1">Recommendation</h4>
                                <p className="text-sm text-gray-700">{parsed.verdict_summary}</p>
                                {parsed.verdict_detail && <p className="text-xs text-gray-500 mt-1">{parsed.verdict_detail}</p>}
                              </div>
                            )}
                            {parsed.viability_report?.summary && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-1">Analysis</h4>
                                <p className="text-sm text-gray-700">{parsed.viability_report.summary}</p>
                              </div>
                            )}
                            {parsed.advantages && parsed.advantages.length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-1">Advantages</h4>
                                <ul className="list-disc pl-5 space-y-1">
                                  {parsed.advantages.map((a: string, i: number) => (
                                    <li key={i} className="text-sm text-gray-700">{a}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {parsed.risks && parsed.risks.length > 0 && (
                              <div>
                                <h4 className="text-sm font-semibold text-gray-900 mb-1">Risks</h4>
                                <ul className="list-disc pl-5 space-y-1">
                                  {parsed.risks.map((r: string, i: number) => (
                                    <li key={i} className="text-sm text-gray-700">{r}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )
                      }
                      return <pre className="text-xs text-gray-600 whitespace-pre-wrap">{JSON.stringify(parsed, null, 2)}</pre>
                    } catch {
                      const content = viewingReport.content!
                      if (content.trim().startsWith('<') && content.includes('</')) {
                        return <div className="text-sm text-gray-700 report-html-content" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }} />
                      }
                      const sections = content.split(/\n(?=#{1,3}\s)/)
                      if (sections.length > 1) {
                        return sections.map((section, i) => {
                          const lines = section.trim().split('\n')
                          const heading = lines[0].replace(/^#+\s*/, '')
                          const body = lines.slice(1).join('\n').trim()
                          return (
                            <div key={i} className="mb-4">
                              <h4 className="text-sm font-semibold text-gray-900 mb-1.5">{heading}</h4>
                              <p className="text-sm text-gray-700 whitespace-pre-wrap">{body}</p>
                            </div>
                          )
                        })
                      }
                      return <p className="text-sm text-gray-700 whitespace-pre-wrap">{content}</p>
                    }
                  })()}
                </div>
              )}

              {!viewingReport.content && !viewingReport.summary && (
                <div className="text-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Report content is being generated...</p>
                </div>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  )
}
