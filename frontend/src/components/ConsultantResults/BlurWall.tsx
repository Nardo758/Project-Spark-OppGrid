import { Lock } from 'lucide-react'

interface BlurWallProps {
  children: React.ReactNode
  title?: string
  description?: string
  ctaText?: string
  price?: string
  onUnlock?: () => void
}

export default function BlurWall({
  children,
  title = 'Unlock Full Analysis',
  description = 'Get detailed financial projections, competitive benchmarks, and actionable next steps.',
  ctaText = 'Get Full Report',
  price = '$25',
  onUnlock,
}: BlurWallProps) {
  return (
    <div className="relative rounded-xl overflow-hidden">
      {/* Blurred content — real values NOT rendered as readable text */}
      <div
        className="pointer-events-none select-none"
        style={{ filter: 'blur(6px)', WebkitFilter: 'blur(6px)' }}
        aria-hidden="true"
      >
        {children}
      </div>

      {/* CTA overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-sm">
        <div className="bg-white border border-gray-200 shadow-lg rounded-xl p-6 max-w-sm text-center">
          <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-6 h-6 text-amber-600" />
          </div>
          <h4 className="text-lg font-bold text-gray-900 mb-2">{title}</h4>
          <p className="text-sm text-gray-600 mb-4">{description}</p>
          <button
            onClick={onUnlock}
            className="w-full px-6 py-3 bg-amber-500 text-white font-semibold rounded-lg hover:bg-amber-600 transition-colors"
          >
            {ctaText} — {price}
          </button>
          <p className="text-xs text-gray-400 mt-2">One-time purchase. Instant access.</p>
        </div>
      </div>
    </div>
  )
}
