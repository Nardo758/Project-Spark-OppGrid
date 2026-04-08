import { useEffect, useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { Loader2, FileText, AlertCircle, ChevronLeft } from 'lucide-react'

interface ReportData {
  id: number
  title: string
  report_type: string
  status: string
  content: string
  confidence_score?: number
  created_at?: string
  completed_at?: string
}

export default function PublicReportViewer() {
  const { reportId } = useParams<{ reportId: string }>()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!reportId || !token) {
      setError('Invalid report link.')
      setLoading(false)
      return
    }
    fetch(`/api/v1/reports/public/${reportId}?token=${encodeURIComponent(token)}`)
      .then(async res => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || 'Could not load report.')
        }
        return res.json()
      })
      .then(data => setReport(data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [reportId, token])

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-[#0F6E56] animate-spin mx-auto mb-3" />
          <p className="text-gray-600 text-sm">Loading your report...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-7 h-7 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Report Unavailable</h1>
          <p className="text-gray-600 text-sm mb-6">{error}</p>
          <Link to="/" className="text-sm text-[#0F6E56] font-medium hover:underline">
            ← Go to OppGrid
          </Link>
        </div>
      </div>
    )
  }

  if (!report) return null

  const reportName = report.report_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) ?? 'Report'
  const date = report.completed_at || report.created_at
  const formattedDate = date ? new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'Recently'

  const renderContent = (content: string) => {
    if (!content) return <p className="text-gray-500 italic">Report content is still generating. Check back shortly.</p>
    return content.split('\n').map((line, i) => {
      if (line.startsWith('## ')) return <h2 key={i} className="text-xl font-bold text-gray-900 mt-8 mb-3">{line.slice(3)}</h2>
      if (line.startsWith('### ')) return <h3 key={i} className="text-base font-semibold text-gray-800 mt-5 mb-2">{line.slice(4)}</h3>
      if (line.startsWith('# ')) return <h1 key={i} className="text-2xl font-bold text-gray-900 mt-6 mb-4">{line.slice(2)}</h1>
      if (line.startsWith('- ') || line.startsWith('• ')) return <li key={i} className="text-gray-700 text-sm leading-relaxed ml-4">{line.slice(2)}</li>
      if (line.startsWith('**') && line.endsWith('**')) return <p key={i} className="font-semibold text-gray-900 text-sm">{line.slice(2, -2)}</p>
      if (line.trim() === '') return <div key={i} className="h-3" />
      return <p key={i} className="text-gray-700 text-sm leading-relaxed">{line}</p>
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <Link to="/" className="text-[#0F6E56] hover:text-[#0a5c47] transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div className="w-8 h-8 rounded-lg bg-[#0F6E56]/10 flex items-center justify-center">
            <FileText className="w-4 h-4 text-[#0F6E56]" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-gray-900 truncate">{report.title || reportName}</h1>
            <p className="text-[11px] text-gray-400">Generated {formattedDate}</p>
          </div>
          {report.confidence_score && (
            <div className="flex-shrink-0 text-right">
              <span className="text-xs font-semibold text-[#0F6E56]">{report.confidence_score}%</span>
              <p className="text-[10px] text-gray-400">Confidence</p>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 sm:p-8">
          {renderContent(report.content)}
        </div>

        <div className="mt-8 text-center">
          <p className="text-xs text-gray-400 mb-3">Want deeper intelligence for your business idea?</p>
          <Link
            to="/consultant-studio"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
            style={{ background: '#0F6E56' }}
          >
            Run another analysis →
          </Link>
        </div>
      </div>
    </div>
  )
}
