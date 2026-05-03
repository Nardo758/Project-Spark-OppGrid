import { Link } from 'react-router-dom'
import { BarChart3, FileText, ShieldCheck, Users, Wand2 } from 'lucide-react'
import SimplePage from '../components/SimplePage'

const categories = [
  { label: 'Market Research', icon: BarChart3 },
  { label: 'Feasibility Studies', icon: FileText },
  { label: 'Financial Models', icon: FileText },
  { label: 'Expert Consultations', icon: Users },
  { label: 'AI Tools', icon: Wand2 },
]

export default function Services() {
  return (
    <SimplePage
      title="Services"
      subtitle="Buy one-off reports, tools, and expert help — no subscription required."
      actions={
        <>
          <Link to="/discover" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
            Browse opportunities
          </Link>
          <Link to="/signup" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">
            Create account
          </Link>
        </>
      }
    >
      <div className="grid md:grid-cols-3 gap-4">
        {categories.map((c) => (
          <div key={c.label} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center gap-2 text-gray-900 font-semibold">
              <c.icon className="w-5 h-5" />
              {c.label}
            </div>
            <p className="mt-2 text-sm text-gray-600">Browse templates, instant AI deliverables, and expert-reviewed options.</p>
          </div>
        ))}
      </div>

      <div className="mt-8 grid lg:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <div className="text-sm text-gray-500">Top service</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">Feasibility study</div>
          <p className="mt-2 text-sm text-gray-600">AI-generated report with a clear go/no-go recommendation.</p>
          <div className="mt-4 flex items-center gap-2 text-sm">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="text-gray-700">Instant delivery</span>
          </div>
          <div className="mt-5 flex gap-2">
            <Link to="/idea-engine" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
              Generate now
            </Link>
            <Link to="/pricing" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">
              Compare plans
            </Link>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <div className="text-sm text-gray-500">Popular</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">Market research deep dive</div>
          <p className="mt-2 text-sm text-gray-600">Industry overview + competitor landscape + growth signals.</p>
          <div className="mt-4 text-sm text-gray-700">From <span className="font-semibold">$299</span></div>
          <div className="mt-5 flex gap-2">
            <Link to="/signup" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
              Buy a report
            </Link>
            <Link to="/discover" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">
              Find an opportunity
            </Link>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <div className="text-sm text-gray-500">Expert help</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">Book a strategy session</div>
          <p className="mt-2 text-sm text-gray-600">Talk to an operator, marketer, or engineer to unblock next steps.</p>
          <div className="mt-4 text-sm text-gray-700">From <span className="font-semibold">$99</span></div>
          <div className="mt-5 flex gap-2">
            <Link to="/network" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
              View network
            </Link>
            <Link to="/contact" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">
              Contact
            </Link>
          </div>
        </div>
      </div>
    </SimplePage>
  )
}

