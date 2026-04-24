import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { X, Download, FileText, Lock, Loader2, CheckCircle, Printer, Mail, FileDown } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import EconomicIntelPanel, { EconomicSnapshot } from './EconomicIntelPanel'

type ReportLayer = 'layer1' | 'layer2' | 'layer3'

type GeneratedReport = {
  id: number
  opportunity_id: number
  report_type: string
  content?: string | null
  created_at: string
  economic_snapshot?: EconomicSnapshot | null
}

type ReportViewerProps = {
  opportunityId: number
  opportunityTitle: string
  userTier: string
  isOpen: boolean
  onClose: () => void
  initialLayer?: ReportLayer
  hasUnlockedAccess?: boolean
}

const layerConfig = {
  layer1: {
    title: 'Problem Overview',
    description: 'Executive summary, problem analysis, market snapshot, and validation signals',
    tier: 'Pro',
    price: '$15 one-time or Pro subscription',
    color: 'violet',
  },
  layer2: {
    title: 'Deep Dive Analysis',
    description: 'TAM/SAM/SOM analysis, demographics, competitive landscape, and geographic insights',
    tier: 'Business',
    price: 'Business subscription required',
    color: 'blue',
  },
  layer3: {
    title: 'Execution Package',
    description: 'Full business plan, go-to-market strategy, financial projections, and 90-day roadmap',
    tier: 'Business/Enterprise',
    price: 'Business (5/month) or Enterprise (unlimited)',
    color: 'emerald',
  },
}

export default function ReportViewer({
  opportunityId,
  opportunityTitle,
  userTier,
  isOpen,
  onClose,
  initialLayer = 'layer1',
  hasUnlockedAccess = false
}: ReportViewerProps) {
  const { token } = useAuthStore()
  const [selectedLayer, setSelectedLayer] = useState<ReportLayer>(initialLayer)
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailAddress, setEmailAddress] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailSuccess, setEmailSuccess] = useState(false)

  const tierLevel = (tier: string): number => {
    const levels: Record<string, number> = { free: 0, pro: 1, business: 2, enterprise: 3 }
    return levels[tier.toLowerCase()] ?? 0
  }

  const canAccessLayer = (layer: ReportLayer): boolean => {
    const userLevel = tierLevel(userTier)
    if (layer === 'layer1') return userLevel >= 1 || hasUnlockedAccess
    if (layer === 'layer2') return userLevel >= 2
    if (layer === 'layer3') return userLevel >= 2
    return false
  }

  const generateMutation = useMutation({
    mutationFn: async (layer: ReportLayer) => {
      const res = await fetch(`/api/v1/reports/opportunity/${opportunityId}/${layer}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail?.message || data.detail || 'Failed to generate report')
      }
      const report = data.report
      return {
        id: report.id,
        opportunity_id: opportunityId,
        report_type: layer,
        content: report.content,
        created_at: report.created_at,
        economic_snapshot: report.economic_snapshot ?? null,
      } as GeneratedReport
    },
    onSuccess: (data) => {
      setGeneratedReport(data)
      setError(null)
    },
    onError: (err: Error) => {
      setError(err.message)
      setGeneratedReport(null)
    },
  })

  const existingReportQuery = useQuery({
    queryKey: ['report', opportunityId, selectedLayer],
    enabled: isOpen && canAccessLayer(selectedLayer),
    queryFn: async () => {
      const reportTypeMap: Record<ReportLayer, string> = {
        layer1: 'LAYER_1_OVERVIEW',
        layer2: 'LAYER_2_DEEP_DIVE',
        layer3: 'LAYER_3_EXECUTION',
      }
      const res = await fetch(`/api/v1/reports/?opportunity_id=${opportunityId}&report_type=${reportTypeMap[selectedLayer]}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return null
      const data = await res.json()
      return data.reports?.length > 0 ? data.reports[0] : null
    },
  })

  const handleGenerate = () => {
    setError(null)
    generateMutation.mutate(selectedLayer)
  }

  const handleExportPDF = async () => {
    const report = generatedReport || existingReportQuery.data
    if (!report?.id) return

    setExportingFormat('pdf')
    try {
      const res = await fetch(`/api/v1/reports/${report.id}/export/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `OppGrid - ${opportunityTitle.slice(0, 60)}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError('Failed to export PDF. Please try again.')
    } finally {
      setExportingFormat(null)
    }
  }

  const handleExportDOCX = async () => {
    const report = generatedReport || existingReportQuery.data
    if (!report?.id) return

    setExportingFormat('docx')
    try {
      const res = await fetch(`/api/v1/reports/${report.id}/export/docx`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `OppGrid - ${opportunityTitle.slice(0, 60)}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError('Failed to export DOCX. Please try again.')
    } finally {
      setExportingFormat(null)
    }
  }

  const handlePrint = () => {
    const reportContent = generatedReport?.content || existingReportQuery.data?.content
    if (!reportContent) return

    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>${opportunityTitle} - ${layerConfig[selectedLayer].title}</title>
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            html, body { height: auto !important; overflow: visible !important; }
            body {
              font-family: Helvetica, Arial, sans-serif;
              font-size: 10.5pt;
              line-height: 1.65;
              color: #334155;
              padding: 0.75in 0.85in;
              max-width: 9in;
              margin: 0 auto;
            }
            .accent-bar {
              background-color: #10B981;
              height: 5px;
              margin: -0.75in -0.85in 0 -0.85in;
            }
            .masthead {
              padding: 20px 0 16px 0;
              border-bottom: 1px solid #E2E8F0;
              margin-bottom: 20px;
              line-height: 1;
            }
            .wordmark {
              display: block;
              font-size: 17pt;
              font-weight: bold;
              color: #0F172A;
              letter-spacing: -0.3px;
              margin: 0;
              padding: 0;
              line-height: 1;
            }
            .tagline {
              display: block;
              font-size: 8pt;
              color: #64748B;
              letter-spacing: 1.5px;
              text-transform: uppercase;
              margin: 0;
              padding: 0;
              line-height: 1;
            }
            .report-type-badge {
              font-size: 8.5pt;
              font-weight: bold;
              color: #10B981;
              letter-spacing: 2px;
              text-transform: uppercase;
              margin-bottom: 6px;
            }
            .report-title {
              font-family: Georgia, 'Times New Roman', serif;
              font-size: 22pt;
              font-weight: normal;
              color: #0F172A;
              line-height: 1.2;
              margin-bottom: 4px;
            }
            .meta-row {
              margin-top: 14px;
              padding: 8px 0;
              border-top: 1px solid #F1F5F9;
              border-bottom: 1px solid #F1F5F9;
              margin-bottom: 24px;
              font-size: 9pt;
              color: #64748B;
            }
            h1, h2, h3, h4, h5, h6 { page-break-after: avoid; break-after: avoid; }
            h1 {
              font-family: Georgia, 'Times New Roman', serif;
              font-size: 15pt;
              font-weight: normal;
              color: #0F172A;
              border-bottom: 2.5px solid #10B981;
              padding-bottom: 5px;
              margin-top: 28px;
              margin-bottom: 12px;
            }
            h2 {
              font-size: 12pt;
              font-weight: bold;
              color: #0F172A;
              margin-top: 20px;
              margin-bottom: 8px;
            }
            h3 {
              font-size: 11pt;
              font-weight: bold;
              color: #1E293B;
              margin-top: 16px;
              margin-bottom: 6px;
            }
            p { margin: 6px 0; line-height: 1.65; color: #334155; orphans: 3; widows: 3; }
            ul, ol { margin: 6px 0; padding-left: 22px; page-break-inside: avoid; break-inside: avoid; }
            li { margin-bottom: 3px; color: #334155; }
            strong, b { color: #0F172A; }
            table { width: 100%; border-collapse: collapse; page-break-inside: avoid; margin: 12px 0; font-size: 9.5pt; }
            th { background-color: #0F172A; color: white; font-weight: 500; padding: 7px 10px; text-align: left; border: none; }
            td { padding: 6px 10px; border-bottom: 1px solid #F1F5F9; color: #334155; }
            tr:nth-child(even) td { background-color: #F8FAFC; }
            blockquote {
              border-left: 3px solid #10B981;
              margin: 12px 0;
              padding: 8px 16px;
              background-color: #ECFDF5;
              font-style: italic;
              color: #334155;
            }
            .print-footer {
              margin-top: 40px;
              padding-top: 12px;
              border-top: 1px solid #E2E8F0;
              font-size: 7.5pt;
              color: #94A3B8;
              display: flex;
              justify-content: space-between;
            }
            @media print {
              body { padding: 0; }
              .accent-bar { margin: 0; }
              @page { margin: 0.5in; size: letter; }
            }
          </style>
        </head>
        <body>
          <div class="accent-bar"></div>
          <div class="masthead">
            <span class="wordmark">OppGrid</span>
            <span class="tagline">Opportunity Intelligence</span>
          </div>
          <div class="report-type-badge">${layerConfig[selectedLayer].title}</div>
          <div class="report-title">${opportunityTitle}</div>
          <div class="meta-row">Generated ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} &nbsp;&bull;&nbsp; oppgrid.com</div>
          ${reportContent}
          <div class="print-footer">
            <span>Confidential &mdash; Prepared by OppGrid AI</span>
            <span>oppgrid.com</span>
          </div>
        </body>
        </html>
      `)
      printWindow.document.close()
      printWindow.print()
    }
  }

  const handleSendEmail = async () => {
    const report = generatedReport || existingReportQuery.data
    if (!report || !emailAddress) return

    setEmailSending(true)
    try {
      const res = await fetch('/api/v1/reports/send-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email: emailAddress,
          report_type: layerConfig[selectedLayer].title,
          report_title: opportunityTitle,
          report_id: String(report.id),
          report_content: { html: report.content },
          generated_at: report.created_at || new Date().toISOString(),
        }),
      })
      if (!res.ok) throw new Error('Failed to send email')
      setEmailSuccess(true)
      setTimeout(() => {
        setShowEmailModal(false)
        setEmailSuccess(false)
        setEmailAddress('')
      }, 2000)
    } catch {
      setError('Failed to send email. Please try again.')
      setShowEmailModal(false)
    } finally {
      setEmailSending(false)
    }
  }

  if (!isOpen) return null

  const config = layerConfig[selectedLayer]
  const hasAccess = canAccessLayer(selectedLayer)
  const existingReport = existingReportQuery.data
  const displayReport = generatedReport || existingReport
  const isLoadingExisting = existingReportQuery.isFetching && !generatedReport

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-stone-200">
          <div>
            <h2 className="text-xl font-bold text-stone-900">Generate Report</h2>
            <p className="text-sm text-stone-500">{opportunityTitle}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-stone-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex border-b border-stone-200">
          {(['layer1', 'layer2', 'layer3'] as ReportLayer[]).map((layer) => {
            const cfg = layerConfig[layer]
            const hasLayerAccess = canAccessLayer(layer)
            return (
              <button
                key={layer}
                onClick={() => {
                  setSelectedLayer(layer)
                  setGeneratedReport(null)
                  setError(null)
                }}
                className={`flex-1 py-4 px-6 text-sm font-medium transition-all relative ${
                  selectedLayer === layer
                    ? `text-${cfg.color}-600 border-b-2 border-${cfg.color}-600 bg-${cfg.color}-50`
                    : 'text-stone-600 hover:bg-stone-50'
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  {!hasLayerAccess && <Lock className="w-4 h-4" />}
                  <span>{cfg.title}</span>
                </div>
                <div className="text-xs text-stone-400 mt-1">{cfg.tier}</div>
              </button>
            )
          })}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {!hasAccess ? (
            <div className="text-center py-12">
              <Lock className="w-16 h-16 text-stone-300 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-stone-900 mb-2">Upgrade Required</h3>
              <p className="text-stone-600 mb-4">{config.description}</p>
              <p className="text-sm text-stone-500 mb-6">{config.price}</p>
              <a
                href="/pricing"
                className={`inline-flex items-center gap-2 bg-${config.color}-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-${config.color}-700`}
              >
                Upgrade to {config.tier}
              </a>
            </div>
          ) : isLoadingExisting ? (
            <div className="flex items-center justify-center py-20 gap-3 text-stone-500">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span className="text-sm font-medium">Loading report…</span>
            </div>
          ) : displayReport ? (
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2 text-emerald-600">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">Report Ready</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleExportPDF}
                    disabled={exportingFormat === 'pdf'}
                    className="flex items-center gap-2 bg-stone-900 text-white px-4 py-2 rounded-lg font-medium hover:bg-stone-800 disabled:opacity-50 text-sm"
                  >
                    {exportingFormat === 'pdf' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    PDF
                  </button>
                  <button
                    onClick={handleExportDOCX}
                    disabled={exportingFormat === 'docx'}
                    className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
                  >
                    {exportingFormat === 'docx' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileDown className="w-4 h-4" />
                    )}
                    Word
                  </button>
                  <button
                    onClick={handlePrint}
                    className="flex items-center gap-2 border border-stone-300 text-stone-700 px-4 py-2 rounded-lg font-medium hover:bg-stone-50 text-sm"
                  >
                    <Printer className="w-4 h-4" />
                    Print
                  </button>
                  <button
                    onClick={() => setShowEmailModal(true)}
                    className="flex items-center gap-2 border border-stone-300 text-stone-700 px-4 py-2 rounded-lg font-medium hover:bg-stone-50 text-sm"
                  >
                    <Mail className="w-4 h-4" />
                    Email
                  </button>
                </div>
              </div>
              <div
                className="prose prose-stone max-w-none bg-stone-50 rounded-xl p-8 border border-stone-200"
                dangerouslySetInnerHTML={{ __html: displayReport.content ?? '' }}
              />
              {displayReport.economic_snapshot && (
                <EconomicIntelPanel snapshot={displayReport.economic_snapshot} />
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-stone-300 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-stone-900 mb-2">{config.title}</h3>
              <p className="text-stone-600 mb-6 max-w-md mx-auto">{config.description}</p>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 max-w-md mx-auto">
                  <p className="text-red-700 text-sm">{error}</p>
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
                className={`inline-flex items-center gap-2 bg-${config.color}-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-${config.color}-700 disabled:opacity-50`}
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <FileText className="w-5 h-5" />
                    Generate {config.title}
                  </>
                )}
              </button>
            </div>
          )}

          {error && displayReport && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>

      {showEmailModal && (
        <div className="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-stone-900 mb-4">Email Report</h3>
            {emailSuccess ? (
              <div className="text-center py-6">
                <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                <p className="text-stone-700 font-medium">Report sent successfully!</p>
              </div>
            ) : (
              <>
                <p className="text-sm text-stone-500 mb-4">
                  Send a branded copy of this report to any email address.
                </p>
                <input
                  type="email"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  placeholder="recipient@example.com"
                  className="w-full border border-stone-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 mb-4"
                />
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => { setShowEmailModal(false); setEmailAddress('') }}
                    className="px-4 py-2 text-sm text-stone-600 hover:bg-stone-100 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSendEmail}
                    disabled={!emailAddress || emailSending}
                    className="flex items-center gap-2 bg-violet-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-violet-700 disabled:opacity-50"
                  >
                    {emailSending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Mail className="w-4 h-4" />
                    )}
                    Send
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
