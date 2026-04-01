import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { FileText, Loader2, CheckCircle, Lock, ChevronDown, Sparkles, Download } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

interface ReportSelectionPanelProps {
  ideaDescription?: string
  consultantResult?: Record<string, any> | null
  className?: string
}

type StudioReport = {
  type: string
  name: string
  description: string
  price_cents: number
  included_in: string[]
}

export default function ReportSelectionPanel({
  ideaDescription,
  consultantResult,
  className = '',
}: ReportSelectionPanelProps) {
  const { token } = useAuthStore()
  const [selectedReport, setSelectedReport] = useState<string>('')
  const [generatedReport, setGeneratedReport] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  // Fetch available studio reports
  const { data: studioData } = useQuery<{ reports: StudioReport[] }>({
    queryKey: ['studio-reports-panel'],
    queryFn: async () => {
      const res = await fetch('/api/v1/report-pricing/public')
      if (!res.ok) throw new Error('Failed to fetch reports')
      return res.json()
    },
  })

  const reports = studioData?.reports || []

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedReport) throw new Error('Select a report type')
      setError(null)

      const context = ideaDescription || consultantResult?.idea_description || ''
      const res = await fetch('/api/v1/report-pricing/generate-free-report', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          report_type: selectedReport,
          idea_description: context,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        let detail = 'Failed to generate report'
        try { detail = JSON.parse(text).detail || detail } catch { detail = text || detail }
        throw new Error(detail)
      }
      return res.json()
    },
    onSuccess: (data) => setGeneratedReport(data),
    onError: (err: Error) => setError(err.message),
  })

  const selected = reports.find((r) => r.type === selectedReport)
  const price = selected ? `$${(selected.price_cents / 100).toFixed(0)}` : null

  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-amber-500" />
        <h3 className="font-semibold text-gray-900">Generate Report</h3>
      </div>

      {/* Report selector */}
      <div className="relative mb-4">
        <select
          value={selectedReport}
          onChange={(e) => {
            setSelectedReport(e.target.value)
            setGeneratedReport(null)
          }}
          className="w-full p-3 border border-gray-200 rounded-lg appearance-none bg-white pr-10 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 text-sm"
        >
          <option value="">Choose a report type...</option>
          {reports.map((r) => (
            <option key={r.type} value={r.type}>
              {r.name} — ${(r.price_cents / 100).toFixed(0)}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-3.5 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>

      {/* Selected report info */}
      {selected && (
        <div className="bg-gray-50 rounded-lg p-3 mb-4 text-sm">
          <p className="text-gray-700">{selected.description}</p>
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-gray-500">
              {selected.included_in?.length ? `Free with ${selected.included_in.join(', ')}` : 'One-time purchase'}
            </span>
            <span className="font-semibold text-gray-900">{price}</span>
          </div>
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={() => generateMutation.mutate()}
        disabled={!selectedReport || generateMutation.isPending || !ideaDescription}
        className="w-full px-4 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
      >
        {generateMutation.isPending ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <FileText className="w-5 h-5" />
            Generate Report
          </>
        )}
      </button>

      {!ideaDescription && (
        <p className="text-xs text-gray-400 mt-2 text-center">
          Run an analysis first to generate a report.
        </p>
      )}

      {/* Error */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Generated report preview */}
      {generatedReport && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-sm font-medium text-green-700">Report generated!</span>
          </div>
          {generatedReport.content && (
            <div
              className="prose prose-sm max-w-none text-gray-700 max-h-64 overflow-y-auto border border-gray-100 rounded-lg p-3"
              dangerouslySetInnerHTML={{ __html: generatedReport.content }}
            />
          )}
          {generatedReport.id && (
            <div className="flex gap-2 mt-3">
              <button
                onClick={async () => {
                  const res = await fetch(`/api/v1/reports/${generatedReport.id}/export/pdf`, { headers: headers() })
                  if (!res.ok) return
                  const blob = await res.blob()
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `OppGrid-Report.pdf`
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                PDF
              </button>
              <button
                onClick={async () => {
                  const res = await fetch(`/api/v1/reports/${generatedReport.id}/export/docx`, { headers: headers() })
                  if (!res.ok) return
                  const blob = await res.blob()
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `OppGrid-Report.docx`
                  document.body.appendChild(a)
                  a.click()
                  document.body.removeChild(a)
                  URL.revokeObjectURL(url)
                }}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                Word
              </button>
            </div>
          )}
        </div>
      )}

      {/* Trust signals */}
      <div className="mt-4 pt-3 border-t border-gray-100 space-y-2">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Lock className="w-3 h-3" />
          <span>Secure checkout via Stripe</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <FileText className="w-3 h-3" />
          <span>PDF + Word export included</span>
        </div>
      </div>
    </div>
  )
}
