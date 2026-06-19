import { useState } from 'react'
import { FileText, Download, Share2, Clock, CheckCircle, Loader2, AlertCircle, Search } from 'lucide-react'
import { useReports, Report, REPORT_INFO, ReportType } from './useReports'

interface ReportLibraryProps {
  filterBySource?: 'validate' | 'search' | 'location' | 'clone'
  compact?: boolean
}

export function ReportLibrary({ filterBySource, compact = false }: ReportLibraryProps) {
  const { reports, isLoading, downloadReport, shareReport } = useReports()
  const [searchQuery, setSearchQuery] = useState('')
  const [shareEmail, setShareEmail] = useState('')
  const [sharingReportId, setSharingReportId] = useState<string | null>(null)

  const filteredReports = reports.filter((report) => {
    if (filterBySource && report.source_feature !== filterBySource) return false
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        report.title.toLowerCase().includes(query) ||
        REPORT_INFO[report.type as ReportType]?.name.toLowerCase().includes(query)
      )
    }
    return true
  })

  const handleShare = async (reportId: string) => {
    if (!shareEmail) return
    try {
      await shareReport(reportId, shareEmail)
      setShareEmail('')
      setSharingReportId(null)
    } catch (error) {
      console.error('Failed to share report:', error)
    }
  }

  const getStatusIcon = (status: Report['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'generating':
        return <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
      </div>
    )
  }

  if (compact) {
    return (
      <div className="space-y-2">
        {filteredReports.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-4">No reports generated yet</p>
        ) : (
          filteredReports.slice(0, 5).map((report) => (
            <div
              key={report.id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(report.status)}
                <div>
                  <p className="font-medium text-sm text-gray-900">{report.title}</p>
                  <p className="text-xs text-gray-500">
                    {REPORT_INFO[report.type as ReportType]?.name}
                  </p>
                </div>
              </div>
              {report.status === 'completed' && (
                <button
                  onClick={() => downloadReport(report.id)}
                  className="p-2 text-gray-400 hover:text-purple-600"
                >
                  <Download className="w-4 h-4" />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search reports..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      {filteredReports.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No reports found</p>
          <p className="text-sm text-gray-400">Generate your first report to see it here</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredReports.map((report) => (
            <div
              key={report.id}
              className="bg-white border border-gray-200 rounded-xl p-4 hover:border-purple-300 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  {getStatusIcon(report.status)}
                  <div>
                    <h4 className="font-semibold text-gray-900">{report.title}</h4>
                    <p className="text-sm text-gray-500">
                      {REPORT_INFO[report.type as ReportType]?.name}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(report.created_at).toLocaleDateString()}
                </span>
              </div>

              {report.status === 'completed' && (
                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-100">
                  <button
                    onClick={() => downloadReport(report.id)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                  {sharingReportId === report.id ? (
                    <div className="flex items-center gap-2 flex-1">
                      <input
                        type="email"
                        placeholder="Email address"
                        value={shareEmail}
                        onChange={(e) => setShareEmail(e.target.value)}
                        className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                      <button
                        onClick={() => handleShare(report.id)}
                        className="px-3 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                      >
                        Send
                      </button>
                      <button
                        onClick={() => setSharingReportId(null)}
                        className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setSharingReportId(report.id)}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg"
                    >
                      <Share2 className="w-4 h-4" />
                      Share
                    </button>
                  )}
                </div>
              )}

              {report.status === 'generating' && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-2 text-sm text-purple-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating report...
                  </div>
                </div>
              )}

              {report.status === 'failed' && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-sm text-red-600">Report generation failed. Please try again.</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
