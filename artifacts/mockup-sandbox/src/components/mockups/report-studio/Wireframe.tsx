import { useState } from "react";
import { Lightbulb, Search, MapPin, Copy, Sparkles, FileText, ChevronRight, ChevronDown, CheckCircle, Clock, Download, Printer, X, Star, Zap, Gift, ArrowRight, BarChart3, Shield, TrendingUp, AlertTriangle, Target, Presentation, Briefcase, PieChart, LineChart, FileSpreadsheet, Lock, ShoppingCart, Megaphone, ClipboardList, Mail, Palette, Globe, Calendar, Rocket, Users, DollarSign, BookOpen, MousePointer, Layout, Layers } from "lucide-react";

function ModeTab({ icon: Icon, label, active }: { icon: any; label: string; active?: boolean }) {
  return (
    <button className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
      active ? 'bg-white text-gray-900 shadow-sm border border-gray-200' : 'text-gray-500 hover:text-gray-700'
    }`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const r = 28, circ = 2 * Math.PI * r, offset = circ * (1 - score / 100);
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="68" height="68" viewBox="0 0 68 68">
        <circle cx="34" cy="34" r={r} fill="none" stroke="#f0f0f0" strokeWidth="5" />
        <circle cx="34" cy="34" r={r} fill="none" stroke={color} strokeWidth="5" strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" transform="rotate(-90 34 34)" />
        <text x="34" y="36" textAnchor="middle" dominantBaseline="middle" fill={color} fontSize="14" fontWeight="700">{score}</text>
      </svg>
      <span className="text-[10px] text-gray-500 font-medium">{label}</span>
    </div>
  );
}

function FourPsBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-medium text-gray-600 w-16 text-right">{label}</span>
      <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-[10px] font-semibold w-7" style={{ color }}>{score}%</span>
    </div>
  );
}

type ReportItem = {
  slug: string;
  title: string;
  description: string;
  price: string;
  consultantPrice: string;
  icon: any;
  accentColor: string;
  sections: string[];
  deliveryTime: string;
};

const REPORT_CATEGORIES: { id: string; label: string; icon: any; color: string; reports: ReportItem[] }[] = [
  {
    id: 'strategy', label: 'Strategy & Analysis', icon: Target, color: '#185FA5',
    reports: [
      { slug: 'market_analysis', title: 'Market Analysis', description: 'TAM/SAM/SOM with competitive landscape and growth trends.', price: '$99', consultantPrice: '$2,000 - $8,000', icon: PieChart, accentColor: '#185FA5', sections: ['Market Size', 'Growth Trends', 'Customer Segments', 'Competitive Landscape', 'Entry Strategy', 'Revenue Projections'], deliveryTime: '2-3 hrs' },
      { slug: 'business_plan', title: 'Business Plan', description: 'Comprehensive strategy document with financial projections.', price: '$149', consultantPrice: '$3,000 - $15,000', icon: FileSpreadsheet, accentColor: '#0F6E56', sections: ['Executive Summary', 'Company Description', 'Market Analysis', 'Organization', 'Marketing Strategy', 'Financial Projections'], deliveryTime: '4-6 hrs' },
      { slug: 'financial_model', title: 'Financial Model', description: '5-year projections, unit economics, and sensitivity analysis.', price: '$129', consultantPrice: '$2,500 - $10,000', icon: LineChart, accentColor: '#BA7517', sections: ['Revenue Model', 'Cost Structure', 'Unit Economics', 'Cash Flow', '5-Year P&L', 'Sensitivity Analysis'], deliveryTime: '3-5 hrs' },
      { slug: 'strategic_assessment', title: 'Strategic Assessment', description: 'SWOT analysis and competitive positioning.', price: '$89', consultantPrice: '$1,500 - $5,000', icon: Briefcase, accentColor: '#185FA5', sections: ['SWOT Analysis', 'Competitive Positioning', 'Value Proposition', 'Strategic Options', 'Recommendations'], deliveryTime: '2-3 hrs' },
      { slug: 'pestle_analysis', title: 'PESTLE Analysis', description: 'Political, Economic, Social, Tech, Legal, Environmental factors.', price: '$99', consultantPrice: '$1,500 - $5,000', icon: Shield, accentColor: '#0F6E56', sections: ['Political', 'Economic', 'Social', 'Technological', 'Legal', 'Environmental'], deliveryTime: '2-3 hrs' },
      { slug: 'competitive_analysis', title: 'Competitive Analysis', description: 'Deep competitor benchmarking with strategic recommendations.', price: '$149', consultantPrice: '$2,000 - $6,000', icon: BarChart3, accentColor: '#993556', sections: ['Competitor Profiles', 'Feature Matrix', 'Pricing Comparison', 'Market Positioning'], deliveryTime: '3-4 hrs' },
      { slug: 'pricing_strategy', title: 'Pricing Strategy', description: 'Optimal pricing model based on market and competitor data.', price: '$139', consultantPrice: '$1,500 - $5,000', icon: DollarSign, accentColor: '#BA7517', sections: ['Market Pricing', 'Value-Based Pricing', 'Competitor Pricing', 'Recommended Model'], deliveryTime: '2-4 hrs' },
    ]
  },
  {
    id: 'marketing', label: 'Marketing & Growth', icon: Megaphone, color: '#D97757',
    reports: [
      { slug: 'ad_creatives', title: 'Ad Creatives', description: 'Platform-optimized ad copy and creative concepts.', price: '$79', consultantPrice: '$500 - $2,000', icon: Sparkles, accentColor: '#D97757', sections: ['Ad Copy Variants', 'Visual Concepts', 'Platform Targeting', 'A/B Test Ideas'], deliveryTime: '1-2 hrs' },
      { slug: 'brand_package', title: 'Brand Package', description: 'Brand identity including mission, voice, visual guidelines.', price: '$149', consultantPrice: '$3,000 - $10,000', icon: Palette, accentColor: '#993556', sections: ['Brand Mission', 'Voice & Tone', 'Visual Identity', 'Brand Guidelines'], deliveryTime: '2-4 hrs' },
      { slug: 'landing_page', title: 'Landing Page', description: 'Conversion-optimized landing page copy and structure.', price: '$99', consultantPrice: '$1,000 - $3,000', icon: Layout, accentColor: '#185FA5', sections: ['Hero Section', 'Value Props', 'Social Proof', 'CTA Strategy'], deliveryTime: '2-3 hrs' },
      { slug: 'content_calendar', title: 'Content Calendar', description: '30-day content strategy across all channels.', price: '$129', consultantPrice: '$1,500 - $4,000', icon: Calendar, accentColor: '#0F6E56', sections: ['Content Pillars', 'Platform Strategy', '30-Day Calendar', 'Content Templates'], deliveryTime: '2-3 hrs' },
      { slug: 'email_funnel_system', title: 'Email Funnel System', description: 'Complete automated email sequence for lead nurturing.', price: '$179', consultantPrice: '$2,000 - $5,000', icon: Mail, accentColor: '#BA7517', sections: ['Welcome Sequence', 'Nurture Flow', 'Sales Emails', 'Re-engagement'], deliveryTime: '3-4 hrs' },
      { slug: 'email_sequence', title: 'Email Sequence', description: 'Targeted email campaign for a specific objective.', price: '$79', consultantPrice: '$500 - $1,500', icon: Mail, accentColor: '#D97757', sections: ['Subject Lines', 'Email Copy', 'Send Schedule', 'Segmentation'], deliveryTime: '1-2 hrs' },
      { slug: 'lead_magnet', title: 'Lead Magnet', description: 'High-value lead capture asset concept and outline.', price: '$89', consultantPrice: '$500 - $2,000', icon: Gift, accentColor: '#993556', sections: ['Magnet Concept', 'Content Outline', 'Landing Page Copy', 'Distribution Plan'], deliveryTime: '2-3 hrs' },
      { slug: 'sales_funnel', title: 'Sales Funnel', description: 'End-to-end customer acquisition funnel design.', price: '$149', consultantPrice: '$2,000 - $5,000', icon: Layers, accentColor: '#185FA5', sections: ['Awareness Stage', 'Consideration Stage', 'Decision Stage', 'Retention Strategy'], deliveryTime: '3-4 hrs' },
      { slug: 'seo_content', title: 'SEO Content', description: 'SEO-optimized content strategy with keyword targeting.', price: '$129', consultantPrice: '$1,500 - $4,000', icon: Globe, accentColor: '#0F6E56', sections: ['Keyword Research', 'Content Briefs', 'On-Page SEO', 'Link Strategy'], deliveryTime: '2-3 hrs' },
    ]
  },
  {
    id: 'product', label: 'Product & Launch', icon: Rocket, color: '#0F6E56',
    reports: [
      { slug: 'pitch_deck', title: 'Pitch Deck', description: 'Investor-ready presentation content and structure.', price: '$79', consultantPrice: '$2,000 - $5,000', icon: Presentation, accentColor: '#BA7517', sections: ['Problem', 'Solution', 'Market Size', 'Business Model', 'Traction', 'Team', 'Financials', 'Ask'], deliveryTime: '2-3 hrs' },
      { slug: 'feature_specs', title: 'Feature Specs', description: 'Detailed feature specifications with user stories.', price: '$149', consultantPrice: '$2,000 - $6,000', icon: ClipboardList, accentColor: '#0F6E56', sections: ['Feature List', 'User Stories', 'Acceptance Criteria', 'Priority Matrix'], deliveryTime: '3-4 hrs' },
      { slug: 'mvp_roadmap', title: 'MVP Roadmap', description: 'Phased product development plan with milestones.', price: '$179', consultantPrice: '$3,000 - $8,000', icon: Rocket, accentColor: '#185FA5', sections: ['MVP Scope', 'Phase 1-3 Plan', 'Tech Stack', 'Timeline & Milestones'], deliveryTime: '3-5 hrs' },
      { slug: 'product_requirements_doc', title: 'Product Requirements Doc', description: 'Complete PRD with technical and business requirements.', price: '$169', consultantPrice: '$3,000 - $8,000', icon: BookOpen, accentColor: '#993556', sections: ['Objectives', 'Requirements', 'User Flows', 'Technical Specs', 'Success Metrics'], deliveryTime: '4-6 hrs' },
      { slug: 'gtm_strategy', title: 'GTM Strategy', description: 'Go-to-market strategy with channel and positioning plan.', price: '$189', consultantPrice: '$3,000 - $8,000', icon: Rocket, accentColor: '#D97757', sections: ['Market Positioning', 'Channel Strategy', 'Launch Plan', 'Growth Levers'], deliveryTime: '3-5 hrs' },
      { slug: 'gtm_launch_calendar', title: 'GTM Launch Calendar', description: 'Day-by-day launch execution plan with tasks and owners.', price: '$159', consultantPrice: '$2,000 - $5,000', icon: Calendar, accentColor: '#BA7517', sections: ['Pre-Launch Tasks', 'Launch Day Plan', 'Week 1-4 Actions', 'KPI Tracking'], deliveryTime: '2-3 hrs' },
      { slug: 'kpi_dashboard', title: 'KPI Dashboard', description: 'Key performance indicators and tracking framework.', price: '$119', consultantPrice: '$1,500 - $4,000', icon: BarChart3, accentColor: '#0F6E56', sections: ['North Star Metric', 'Leading Indicators', 'Dashboard Layout', 'Review Cadence'], deliveryTime: '2-3 hrs' },
    ]
  },
  {
    id: 'research', label: 'Research', icon: Search, color: '#993556',
    reports: [
      { slug: 'user_personas', title: 'User Personas', description: 'Data-driven customer personas with behavior insights.', price: '$99', consultantPrice: '$1,000 - $3,000', icon: Users, accentColor: '#993556', sections: ['Demographics', 'Pain Points', 'Behaviors', 'Buying Triggers'], deliveryTime: '2-3 hrs' },
      { slug: 'customer_interview_guide', title: 'Customer Interview Guide', description: 'Structured interview script for customer discovery.', price: '$89', consultantPrice: '$500 - $2,000', icon: Users, accentColor: '#185FA5', sections: ['Research Questions', 'Interview Script', 'Analysis Framework', 'Insight Template'], deliveryTime: '2-3 hrs' },
      { slug: 'tweet_landing_page', title: 'Tweet Landing Page', description: 'Viral tweet thread + micro landing page content.', price: '$49', consultantPrice: '$300 - $800', icon: MousePointer, accentColor: '#D97757', sections: ['Tweet Thread', 'Hook Variants', 'Landing Copy', 'CTA Options'], deliveryTime: '0.5-1 hr' },
      { slug: 'feasibility_study', title: 'Feasibility Study', description: 'Quick viability check with market validation data.', price: '$25', consultantPrice: '$1,500 - $15,000', icon: Target, accentColor: '#0F6E56', sections: ['Executive Summary', 'Market Opportunity', 'Technical Feasibility', 'Financial Viability', 'Risk Assessment'], deliveryTime: '1-2 hrs' },
    ]
  },
];

function ReportListRow({ report, expanded, onToggle }: { report: ReportItem; expanded: boolean; onToggle: () => void }) {
  const Icon = report.icon;
  return (
    <div className={`transition-all ${expanded ? 'bg-white rounded-xl shadow-sm border border-gray-200' : ''}`}>
      <button onClick={onToggle} className={`w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${expanded ? 'bg-gray-50 rounded-b-none' : 'hover:bg-gray-50'}`}>
        <div className="w-7 h-7 rounded-md flex items-center justify-center shrink-0" style={{ background: `${report.accentColor}12` }}>
          <Icon className="w-3.5 h-3.5" style={{ color: report.accentColor }} />
        </div>
        <span className="flex-1 text-sm font-medium text-gray-900 truncate">{report.title}</span>
        <span className="text-xs text-gray-400 hidden sm:inline">{report.deliveryTime}</span>
        <span className="text-sm font-semibold min-w-[50px] text-right" style={{ color: report.accentColor }}>{report.price}</span>
        <span className="text-[10px] text-gray-400 line-through min-w-[80px] text-right hidden sm:inline">{report.consultantPrice}</span>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform shrink-0 ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        <div className="px-4 pb-4 pt-3">
          <p className="text-xs text-gray-600 mb-3">{report.description}</p>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {report.sections.map((s, i) => (
              <span key={i} className="px-2 py-0.5 rounded text-[9px] font-medium bg-gray-100 text-gray-600">{s}</span>
            ))}
          </div>
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 text-[10px] text-gray-400">
                <Clock className="w-3 h-3" /> Delivery: {report.deliveryTime}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-gray-400">
                <span>Consultant: {report.consultantPrice}</span>
              </div>
            </div>
            <button className="px-4 py-1.5 rounded-lg text-white text-xs font-medium flex items-center gap-1.5 transition-all hover:opacity-90" style={{ background: report.accentColor }}>
              <ShoppingCart className="w-3 h-3" /> Purchase
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ReportModalPreview() {
  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 w-full overflow-hidden">
      <div className="bg-gradient-to-r from-emerald-600 to-teal-600 p-5 text-white flex items-center justify-between">
        <div>
          <p className="text-[10px] text-emerald-200 font-medium">FEASIBILITY STUDY</p>
          <h3 className="text-lg font-bold mt-0.5">Organic Meal Prep Subscription</h3>
          <p className="text-xs text-emerald-100 mt-1">Generated Apr 1, 2026 · AI Confidence: 87%</p>
        </div>
        <button className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30 transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="p-5 space-y-4 max-h-[400px] overflow-y-auto">
        {['Executive Summary', 'Market Opportunity', 'Technical Feasibility', 'Financial Viability', 'Risk Assessment', 'Recommendation'].map((section, i) => (
          <div key={i}>
            <h4 className="text-sm font-semibold text-gray-900 mb-1.5">{section}</h4>
            <div className="h-2.5 bg-gray-100 rounded w-full mb-1" />
            <div className="h-2.5 bg-gray-100 rounded w-11/12 mb-1" />
            <div className="h-2.5 bg-gray-100 rounded w-9/12" />
          </div>
        ))}
      </div>
      <div className="border-t border-gray-200 p-4 flex items-center justify-between bg-gray-50">
        <div className="flex gap-2">
          <button className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-700 flex items-center gap-1.5 hover:bg-gray-50">
            <Download className="w-3 h-3" /> PDF
          </button>
          <button className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-700 flex items-center gap-1.5 hover:bg-gray-50">
            <Download className="w-3 h-3" /> Word
          </button>
          <button className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-700 flex items-center gap-1.5 hover:bg-gray-50">
            <Printer className="w-3 h-3" /> Print
          </button>
        </div>
        <button className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700">
          Close
        </button>
      </div>
    </div>
  );
}

export function Wireframe() {
  const [expandedReport, setExpandedReport] = useState<string | null>('market_analysis');
  const [expandedCategory, setExpandedCategory] = useState<string | null>('strategy');

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-6 rounded-full bg-gradient-to-b from-[#D97757] to-[#BA7517]" />
          <h1 className="text-xl font-bold text-gray-900">Report Studio</h1>
          <span className="text-xs text-gray-400 ml-1">Design Wireframe — New Layout</span>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex gap-1 p-1 bg-gray-100 rounded-lg mb-4">
            <ModeTab icon={Lightbulb} label="Validate Idea" active />
            <ModeTab icon={Search} label="Search Ideas" />
            <ModeTab icon={MapPin} label="Identify Location" />
            <ModeTab icon={Copy} label="Clone Success" />
          </div>
          <textarea className="w-full border border-gray-200 rounded-lg p-3 text-sm text-gray-700 bg-gray-50 resize-none" rows={3} defaultValue="Organic meal prep subscription service targeting busy professionals in Austin, TX" />
          <button className="mt-3 w-full py-2.5 bg-[#D97757] hover:bg-[#c4684b] text-white rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition-colors">
            <Sparkles className="w-4 h-4" /> Analyze & Generate Reports
          </button>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-5 rounded-full bg-[#0F6E56]" />
            <h2 className="text-lg font-semibold text-gray-900">Analysis Results</h2>
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium border border-emerald-200">Hybrid Business</span>
          </div>

          <div className="flex justify-center gap-6 mb-5">
            <ScoreRing score={87} label="Overall" color="#0F6E56" />
            <ScoreRing score={82} label="Market Fit" color="#185FA5" />
            <ScoreRing score={91} label="Demand" color="#D97757" />
            <ScoreRing score={78} label="Feasibility" color="#BA7517" />
          </div>

          <div className="space-y-2 mb-5">
            <FourPsBar label="Product" score={88} color="#0F6E56" />
            <FourPsBar label="Price" score={75} color="#185FA5" />
            <FourPsBar label="Place" score={82} color="#D97757" />
            <FourPsBar label="Promotion" score={69} color="#BA7517" />
          </div>

          <div className="grid grid-cols-3 gap-2 mb-5">
            {[
              { label: 'Market Size', value: '$4.2B', color: '#185FA5' },
              { label: 'Growth Rate', value: '12% CAGR', color: '#0F6E56' },
              { label: 'Avg Revenue', value: '$850K/yr', color: '#BA7517' },
            ].map((m, i) => (
              <div key={i} className="p-3 rounded-lg border border-gray-100 bg-gray-50 text-center">
                <p className="text-[10px] text-gray-400 mb-0.5">{m.label}</p>
                <p className="text-sm font-bold" style={{ color: m.color }}>{m.value}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
                <CheckCircle className="w-3 h-3 text-emerald-500" /> Key Advantages
              </h4>
              <ul className="space-y-1.5">
                {['High demand in urban areas', 'Low startup barriers', 'Strong repeat revenue'].map((a, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-gray-600">
                    <CheckCircle className="w-3 h-3 text-emerald-400 mt-0.5 shrink-0" /> {a}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-500" /> Key Risks
              </h4>
              <ul className="space-y-1.5">
                {['Competitive market', 'Supply chain complexity', 'Customer churn risk'].map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-gray-600">
                    <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" /> {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1.5 h-5 rounded-full bg-[#D97757]" />
              <h3 className="text-base font-semibold text-gray-900">Just Generated</h3>
              <span className="text-[10px] text-gray-400">Free with your analysis</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { title: 'Idea Validation', icon: Lightbulb, color: '#185FA5', desc: 'Business viability analysis with scoring' },
                { title: 'Feasibility Study', icon: FileText, color: '#0F6E56', desc: 'Market opportunity and risk assessment' },
              ].map((card, i) => (
                <button key={i} className="p-4 bg-white border-2 border-gray-100 rounded-xl hover:border-gray-300 hover:shadow-md transition-all text-left group">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${card.color}12` }}>
                      <card.icon className="w-4 h-4" style={{ color: card.color }} />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-gray-900">{card.title}</span>
                      <span className="text-[9px] ml-2 px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 font-medium">FREE</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-500">{card.desc}</p>
                  <div className="flex items-center gap-1 mt-2 text-[10px] font-medium group-hover:text-gray-700 transition-colors" style={{ color: card.color }}>
                    View Report <ChevronRight className="w-3 h-3" />
                  </div>
                </button>
              ))}
            </div>
          </div>

          <p className="text-[10px] text-gray-400 text-center mt-3">Powered by DeepSeek + Claude AI · 4P's data from 6 live sources</p>

          <div className="mt-8">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-5 rounded-full" style={{ background: '#BA7517' }} />
                <h2 className="text-lg font-semibold text-gray-900">Go Deeper</h2>
                <span className="ml-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-500">27 reports</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-amber-50 text-amber-700 border border-amber-200">Save up to 30% with bundles</span>
            </div>
            <p className="text-xs text-gray-500 mb-4">Purchase additional reports tailored to your business context. Each uses your analysis data for personalized insights.</p>

            <div className="space-y-1">
              {REPORT_CATEGORIES.map(cat => {
                const CatIcon = cat.icon;
                const isExpanded = expandedCategory === cat.id;
                return (
                  <div key={cat.id} className={`rounded-xl transition-all ${isExpanded ? 'bg-white border border-gray-200 shadow-sm' : ''}`}>
                    <button
                      onClick={() => setExpandedCategory(isExpanded ? null : cat.id)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all ${isExpanded ? 'bg-gray-50 rounded-b-none border-b border-gray-100' : 'hover:bg-white hover:shadow-sm'}`}
                    >
                      <div className="w-7 h-7 rounded-md flex items-center justify-center" style={{ background: `${cat.color}12` }}>
                        <CatIcon className="w-3.5 h-3.5" style={{ color: cat.color }} />
                      </div>
                      <span className="text-sm font-semibold text-gray-800 flex-1 text-left">{cat.label}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: `${cat.color}10`, color: cat.color }}>{cat.reports.length} reports</span>
                      <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>
                    {isExpanded && (
                      <div className="px-2 pb-2 pt-1">
                        <div className="divide-y divide-gray-50">
                          {cat.reports.map(r => (
                            <ReportListRow
                              key={r.slug}
                              report={r}
                              expanded={expandedReport === r.slug}
                              onToggle={() => setExpandedReport(expandedReport === r.slug ? null : r.slug)}
                            />
                          ))}
                        </div>
                        {cat.id === 'strategy' && (
                          <div className="mt-2 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 flex items-center justify-between">
                            <div>
                              <p className="text-[11px] font-semibold text-gray-900">Strategic Analysis Bundle</p>
                              <p className="text-[9px] text-gray-500">Market Analysis + PESTLE + Strategic Assessment</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-blue-700">$229</span>
                              <span className="text-[9px] text-gray-400 line-through">$287</span>
                              <button className="px-3 py-1 rounded-lg text-white text-[10px] font-medium bg-blue-600">Bundle</button>
                            </div>
                          </div>
                        )}
                        {cat.id === 'marketing' && (
                          <div className="mt-2 p-3 bg-gradient-to-r from-orange-50 to-amber-50 rounded-lg border border-orange-200 flex items-center justify-between">
                            <div>
                              <p className="text-[11px] font-semibold text-gray-900">Marketing Bundle — 5 reports</p>
                              <p className="text-[9px] text-gray-500">Calendar + Email Funnel + Lead Magnet + Funnel + Personas</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-orange-700">$599</span>
                              <span className="text-[9px] text-gray-400 line-through">$815</span>
                              <button className="px-3 py-1 rounded-lg text-white text-[10px] font-medium bg-orange-600">Bundle</button>
                            </div>
                          </div>
                        )}
                        {cat.id === 'product' && (
                          <div className="mt-2 p-3 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-lg border border-emerald-200 flex items-center justify-between">
                            <div>
                              <p className="text-[11px] font-semibold text-gray-900">Launch Bundle — 4 reports</p>
                              <p className="text-[9px] text-gray-500">GTM Strategy + Calendar + MVP Roadmap + KPI Dashboard</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-emerald-700">$499</span>
                              <span className="text-[9px] text-gray-400 line-through">$646</span>
                              <button className="px-3 py-1 rounded-lg text-white text-[10px] font-medium bg-emerald-600">Bundle</button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-4 p-4 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl border border-violet-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-900">Complete Starter Bundle — 10 reports</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">Brand + Landing Page + Ads + Email + Personas + MVP + GTM + KPI + Competitive + Pricing</p>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-violet-700">$1,299</span>
                    <span className="text-sm text-gray-400 line-through">$1,856</span>
                  </div>
                  <button className="mt-1 px-4 py-1.5 rounded-lg text-white text-xs font-medium bg-violet-600 hover:bg-violet-700 transition-colors">
                    Get Bundle
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 p-5 bg-gray-50 rounded-xl border border-dashed border-gray-300 text-center">
            <Lock className="w-5 h-5 text-gray-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-700">Sign in to save & access your reports anytime</p>
            <p className="text-[10px] text-gray-400 mt-1 mb-3">Your current analysis results will be preserved after sign-in.</p>
            <button className="px-5 py-2 rounded-lg text-white text-sm font-medium bg-gray-900 hover:bg-gray-800 transition-colors">
              Sign In / Create Account
            </button>
          </div>

          <div className="mt-6 border-t border-dashed border-gray-300 pt-6">
            <p className="text-[10px] text-gray-400 text-center italic mb-2">Below shows what signed-in users see instead of the sign-in prompt:</p>
            <div className="opacity-60">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-5 rounded-full bg-gray-400" />
                  <h2 className="text-lg font-semibold text-gray-900">Report History</h2>
                  <span className="text-xs text-gray-400">All your past reports</span>
                </div>
              </div>
              <div className="space-y-2">
                {[
                  { title: 'Idea Validation: Coffee Shop Downtown', date: 'Mar 28, 2026', confidence: 78, icon: Lightbulb, color: '#185FA5' },
                  { title: 'Feasibility Study: Coffee Shop Downtown', date: 'Mar 28, 2026', confidence: 82, icon: FileText, color: '#0F6E56' },
                  { title: 'Idea Validation: Pet Grooming Mobile', date: 'Mar 15, 2026', confidence: 91, icon: Lightbulb, color: '#185FA5' },
                ].map((report, i) => (
                  <button key={i} className="w-full text-left">
                    <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-100">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${report.color}10` }}>
                          <report.icon className="w-4 h-4" style={{ color: report.color }} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{report.title}</p>
                          <p className="text-[10px] text-gray-400">{report.date} · Confidence: {report.confidence}%</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-300" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-dashed border-gray-300 pt-8 mt-8">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-5 rounded-full bg-gray-400" />
            <h2 className="text-lg font-bold text-gray-900">Report Viewer (Modal)</h2>
            <span className="text-xs text-gray-400">Opens when any report card is clicked</span>
          </div>
          <p className="text-[10px] text-gray-400 mb-4">Shown inline here for wireframe purposes — in the app this is a modal overlay.</p>
          <ReportModalPreview />
        </div>
      </div>
    </div>
  );
}
