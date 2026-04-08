import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import ReportLibrary from '../../components/ReportLibrary'

function parseOptionalPositiveInt(raw: string | null): number | undefined {
  if (!raw) return undefined
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return undefined
  return Math.floor(parsed)
}

export default function ReportStudio() {
  const [searchParams] = useSearchParams()

  const opportunityId = useMemo(() => {
    return (
      parseOptionalPositiveInt(searchParams.get('opp')) ??
      parseOptionalPositiveInt(searchParams.get('opportunityId'))
    )
  }, [searchParams])

  return (
    <div className="min-h-screen bg-gray-50 py-6 sm:py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto mb-6 sm:mb-8">
        <div className="flex items-center gap-2.5 mb-1.5">
          <div className="w-2 h-7 rounded-full bg-gradient-to-b from-[#0F6E56] to-[#185FA5]" />
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Report Studio</h1>
        </div>
        <p className="text-sm text-gray-500 ml-[18px]">
          AI-powered business reports using your analysis data
        </p>
      </div>
      <ReportLibrary opportunityId={opportunityId} />
    </div>
  )
}
