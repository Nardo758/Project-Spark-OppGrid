import { useState } from 'react'
import { Download, Printer, Mail, Loader2, X, CheckCircle } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface GeneratedReportViewerProps {
  report: {
    id: number
    title: string
    content: string
    report_type?: string
    confidence_score?: number
    created_at?: string
  }
}

export default function GeneratedReportViewer({ report }: GeneratedReportViewerProps) {
  const { token } = useAuthStore()
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailAddress, setEmailAddress] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailSuccess, setEmailSuccess] = useState(false)

  const headers = (): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['Authorization'] = `Bearer ${token}`
    return h
  }

  const handleExport = async (format: 'pdf' | 'docx') => {
    setExportingFormat(format)
    try {
      const res = await fetch(`/api/v1/reports/${report.id}/export/${format}`, { headers: headers() })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `OppGrid - ${report.title.slice(0, 60)}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Export failed:', e)
    } finally {
      setExportingFormat(null)
    }
  }

  const handlePrint = () => {
    const w = window.open('', '_blank')
    if (!w) return
    const reportType = report.report_type || 'Report'
    const generatedDate = report.created_at
      ? new Date(report.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
      : new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    w.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${report.title}</title>
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
          .wordmark { display: block; font-size: 17pt; font-weight: bold; color: #0F172A; letter-spacing: -0.3px; margin: 0; padding: 0; line-height: 1; }
          .tagline { display: block; font-size: 8pt; color: #64748B; letter-spacing: 1.5px; text-transform: uppercase; margin: 0; padding: 0; line-height: 1; }
          .report-type-badge {
            font-size: 8.5pt; font-weight: bold; color: #10B981;
            letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px;
          }
          .report-title {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 22pt; font-weight: normal; color: #0F172A; line-height: 1.2; margin-bottom: 4px;
          }
          .meta-row {
            margin-top: 14px; padding: 8px 0;
            border-top: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9;
            margin-bottom: 24px; font-size: 9pt; color: #64748B;
          }
          h1, h2, h3, h4, h5, h6 { page-break-after: avoid; break-after: avoid; }
          h1 {
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 15pt; font-weight: normal; color: #0F172A;
            border-bottom: 2.5px solid #10B981; padding-bottom: 5px;
            margin-top: 28px; margin-bottom: 12px;
          }
          h2 { font-size: 12pt; font-weight: bold; color: #0F172A; margin-top: 20px; margin-bottom: 8px; }
          h3 { font-size: 11pt; font-weight: bold; color: #1E293B; margin-top: 16px; margin-bottom: 6px; }
          p { margin: 6px 0; line-height: 1.65; color: #334155; orphans: 3; widows: 3; }
          ul, ol { margin: 6px 0; padding-left: 22px; page-break-inside: avoid; break-inside: avoid; }
          li { margin-bottom: 3px; color: #334155; }
          strong, b { color: #0F172A; }
          table { width: 100%; border-collapse: collapse; page-break-inside: avoid; margin: 12px 0; font-size: 9.5pt; }
          th { background-color: #0F172A; color: white; font-weight: 500; padding: 7px 10px; text-align: left; border: none; }
          td { padding: 6px 10px; border-bottom: 1px solid #F1F5F9; color: #334155; }
          tr:nth-child(even) td { background-color: #F8FAFC; }
          blockquote {
            border-left: 3px solid #10B981; margin: 12px 0; padding: 8px 16px;
            background-color: #ECFDF5; font-style: italic; color: #334155;
          }
          .print-footer {
            margin-top: 40px; padding-top: 12px; border-top: 1px solid #E2E8F0;
            font-size: 7.5pt; color: #94A3B8;
            display: flex; justify-content: space-between;
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
        <div class="report-type-badge">${reportType}</div>
        <div class="report-title">${report.title}</div>
        <div class="meta-row">Generated ${generatedDate} &nbsp;&bull;&nbsp; oppgrid.com</div>
        ${report.content}
        <div class="print-footer">
          <span>Confidential &mdash; Prepared by OppGrid AI</span>
          <span>oppgrid.com</span>
        </div>
      </body>
      </html>
    `)
    w.document.close()
    w.print()
  }

  const handleSendEmail = async () => {
    if (!emailAddress) return
    setEmailSending(true)
    try {
      const res = await fetch('/api/v1/reports/send-email', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ report_id: report.id, email: emailAddress }),
      })
      if (res.ok) {
        setEmailSuccess(true)
        setTimeout(() => { setShowEmailModal(false); setEmailSuccess(false) }, 2000)
      }
    } catch (e) {
      console.error('Email failed:', e)
    } finally {
      setEmailSending(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-amber-500 px-6 py-4">
        <h3 className="text-white font-bold text-lg">{report.title}</h3>
        {report.confidence_score && (
          <span className="text-white/80 text-sm">Confidence: {report.confidence_score}%</span>
        )}
      </div>

      {/* Content */}
      <div
        className="prose prose-sm max-w-none p-6 text-gray-700"
        dangerouslySetInnerHTML={{ __html: report.content }}
      />

      {/* Export bar */}
      <div className="border-t border-gray-200 px-6 py-4 flex flex-wrap items-center gap-3 bg-gray-50">
        <button
          onClick={() => handleExport('pdf')}
          disabled={exportingFormat === 'pdf'}
          className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm font-medium disabled:opacity-50"
        >
          {exportingFormat === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          PDF
        </button>
        <button
          onClick={() => handleExport('docx')}
          disabled={exportingFormat === 'docx'}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium disabled:opacity-50"
        >
          {exportingFormat === 'docx' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Word
        </button>
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-white text-sm font-medium"
        >
          <Printer className="w-4 h-4" />
          Print
        </button>
        <button
          onClick={() => setShowEmailModal(true)}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-white text-sm font-medium"
        >
          <Mail className="w-4 h-4" />
          Email
        </button>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 text-xs text-gray-400 flex items-center justify-between">
        <span>Generated by OppGrid Intelligence Platform</span>
        {report.created_at && <span>{new Date(report.created_at).toLocaleDateString()}</span>}
      </div>

      {/* Email modal */}
      {showEmailModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold text-gray-900">Email Report</h4>
              <button onClick={() => setShowEmailModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            {emailSuccess ? (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span>Report sent!</span>
              </div>
            ) : (
              <>
                <input
                  type="email"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  placeholder="recipient@example.com"
                  className="w-full p-3 border border-gray-200 rounded-lg mb-4 focus:ring-2 focus:ring-amber-500"
                />
                <button
                  onClick={handleSendEmail}
                  disabled={!emailAddress || emailSending}
                  className="w-full px-4 py-3 bg-amber-500 text-white rounded-lg hover:bg-amber-600 font-medium disabled:opacity-50"
                >
                  {emailSending ? 'Sending...' : 'Send Report'}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
