import { useState } from 'react'
import { FileText, Download, Loader2, Printer } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface ActionBarProps {
  onSaveReport?: () => void
  onExportPdf?: () => void
  onPrint?: () => void
  isSaving?: boolean
  reportSaved?: boolean
}

export default function ActionBar({ onSaveReport, onExportPdf, onPrint, isSaving, reportSaved }: ActionBarProps) {
  const { token } = useAuthStore()
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    if (!onExportPdf) return
    setExporting(true)
    try {
      await onExportPdf()
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="flex flex-wrap gap-3">
      {token && onSaveReport && (
        <button
          onClick={onSaveReport}
          disabled={isSaving || reportSaved}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 font-medium disabled:opacity-50 transition-colors"
        >
          {isSaving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileText className="w-4 h-4" />
          )}
          {reportSaved ? 'Saved' : isSaving ? 'Saving...' : 'Save Report'}
        </button>
      )}
      {onExportPdf && (
        <button
          onClick={handleExport}
          disabled={exporting}
          className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50 transition-colors"
        >
          {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          {exporting ? 'Exporting...' : 'Export PDF'}
        </button>
      )}
      {onPrint && (
        <button
          onClick={onPrint}
          className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium transition-colors"
        >
          <Printer className="w-4 h-4" />
          Print
        </button>
      )}
    </div>
  )
}
