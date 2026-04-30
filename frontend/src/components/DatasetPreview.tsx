import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X, Download, TrendingUp, Database, AlertCircle } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

interface PreviewData {
  metadata: {
    record_count: number
    data_freshness: string
    vertical?: string
    city?: string
  }
  rows: Record<string, any>[]
  columns: string[]
}

interface DatasetPreviewProps {
  datasetId: string
  datasetName: string
  onClose: () => void
  onCheckout: () => void
}

export default function DatasetPreview({
  datasetId,
  datasetName,
  onClose,
  onCheckout,
}: DatasetPreviewProps) {
  const { token } = useAuthStore()

  const { data: preview, isLoading, error } = useQuery({
    queryKey: ['dataset-preview', datasetId],
    queryFn: async (): Promise<PreviewData> => {
      const res = await fetch(`/api/v1/datasets/${datasetId}/preview`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!res.ok) throw new Error('Failed to load preview')
      return res.json()
    },
  })

  const formatFreshness = (freshness: string) => {
    const now = new Date()
    const dataDate = new Date(freshness)
    const diffMs = now.getTime() - dataDate.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 30) return `${diffDays}d ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`
    return `${Math.floor(diffDays / 365)}y ago`
  }

  const formatRecordCount = (count: number) => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M records`
    }
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K records`
    }
    return `${count} records`
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-gray-900 rounded-lg shadow-2xl max-w-4xl w-full my-8 border border-gray-700">
        {/* Header */}
        <div className="border-b border-gray-700 p-6 flex items-center justify-between bg-gradient-to-r from-gray-800 to-gray-900">
          <div>
            <h2 className="text-2xl font-bold text-white">{datasetName}</h2>
            <p className="text-gray-400 text-sm mt-1">Preview - First 5 Rows</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Metadata Section */}
          {preview && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Database className="w-4 h-4" />
                Dataset Information
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">Total Records</p>
                  <p className="text-lg font-bold text-white mt-1">
                    {formatRecordCount(preview.metadata.record_count)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase font-semibold">Last Updated</p>
                  <p className="text-lg font-bold text-white mt-1">
                    {formatFreshness(preview.metadata.data_freshness)}
                  </p>
                </div>
                {preview.metadata.vertical && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase font-semibold">Vertical</p>
                    <p className="text-lg font-bold text-white mt-1">{preview.metadata.vertical}</p>
                  </div>
                )}
                {preview.metadata.city && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase font-semibold">City</p>
                    <p className="text-lg font-bold text-white mt-1">{preview.metadata.city}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <div className="inline-block">
                <div className="w-8 h-8 border-4 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
              </div>
              <p className="text-gray-400 mt-4">Loading preview...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 flex gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-red-300">Preview Unavailable</h4>
                <p className="text-red-200 text-sm mt-1">Unable to load preview data. This is common for large datasets.</p>
              </div>
            </div>
          )}

          {/* Table Section */}
          {preview && preview.rows.length > 0 && !error && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
              <h3 className="text-sm font-semibold text-white p-4 border-b border-gray-700 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Sample Data ({Math.min(5, preview.rows.length)} rows)
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      {preview.columns.slice(0, 8).map((col, i) => (
                        <th
                          key={i}
                          className="px-4 py-3 text-left text-xs font-semibold text-gray-300 bg-gray-900"
                        >
                          {col}
                        </th>
                      ))}
                      {preview.columns.length > 8 && (
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">
                          +{preview.columns.length - 8} more
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.slice(0, 5).map((row, rowIndex) => (
                      <tr
                        key={rowIndex}
                        className={rowIndex % 2 === 0 ? 'bg-gray-800' : 'bg-gray-800/50'}
                      >
                        {preview.columns.slice(0, 8).map((col, colIndex) => (
                          <td
                            key={colIndex}
                            className="px-4 py-3 text-gray-300 truncate max-w-xs"
                            title={String(row[col])}
                          >
                            {row[col] !== null && row[col] !== undefined
                              ? String(row[col]).substring(0, 50)
                              : '—'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="bg-gray-900 px-4 py-3 text-xs text-gray-400 border-t border-gray-700">
                Showing {Math.min(5, preview.rows.length)} of {preview.metadata.record_count} total records
              </div>
            </div>
          )}

          {/* Empty State */}
          {preview && preview.rows.length === 0 && !error && (
            <div className="text-center py-12 bg-gray-800 border border-gray-700 rounded-lg">
              <p className="text-gray-400">No preview data available</p>
            </div>
          )}
        </div>

        {/* Footer with CTA */}
        <div className="border-t border-gray-700 p-6 bg-gradient-to-r from-gray-800 to-gray-900 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 transition-colors"
          >
            Close
          </button>
          <button
            onClick={onCheckout}
            className="flex-1 px-4 py-2 rounded-lg font-medium text-white bg-blue-600 hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download Full Dataset
          </button>
        </div>
      </div>
    </div>
  )
}
