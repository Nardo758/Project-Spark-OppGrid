import { Link } from 'react-router-dom'

export function FourPsBar({ product, price, place, promotion }: { product: number; price: number; place: number; promotion: number }) {
  const bars = [
    { label: 'Product', score: product, color: '#0F6E56' },
    { label: 'Price', score: price, color: '#185FA5' },
    { label: 'Place', score: place, color: '#D97757' },
    { label: 'Promotion', score: promotion, color: '#BA7517' },
  ]
  return (
    <div className="flex items-center gap-1.5">
      {bars.map(b => (
        <div key={b.label} title={`${b.label}: ${b.score}/100`} className="flex flex-col items-center gap-0.5">
          <div className="w-5 h-16 rounded-sm relative overflow-hidden" style={{ background: '#e5e5e5' }}>
            <div className="absolute bottom-0 w-full rounded-sm" style={{ height: `${b.score}%`, background: b.color }} />
          </div>
          <span className="text-[9px] text-gray-400">{b.label[0]}</span>
        </div>
      ))}
    </div>
  )
}

export function FourPsHorizontalBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium text-gray-600 w-20 text-right">{label}</span>
      <div className="flex-1 h-3.5 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs font-bold w-10" style={{ color }}>{score}%</span>
    </div>
  )
}

export function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const r = 28, circ = 2 * Math.PI * r, offset = circ * (1 - score / 100)
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="68" height="68" viewBox="0 0 68 68">
        <circle cx="34" cy="34" r={r} fill="none" stroke="#f0f0f0" strokeWidth="5" />
        <circle cx="34" cy="34" r={r} fill="none" stroke={color} strokeWidth="5" strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" transform="rotate(-90 34 34)" />
        <text x="34" y="36" textAnchor="middle" dominantBaseline="middle" fill={color} fontSize="14" fontWeight="700">{score}</text>
      </svg>
      <span className="text-[10px] text-gray-500 font-medium">{label}</span>
    </div>
  )
}

export function BlurGate({ children, title, priceLabel, subtitle, onPurchase, loading }: {
  children: React.ReactNode
  title: string
  priceLabel: string
  subtitle: string
  onPurchase?: () => void
  loading?: boolean
}) {
  return (
    <div className="relative rounded-2xl overflow-hidden border border-gray-200">
      <div className="blur-[8px] pointer-events-none opacity-40 select-none">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.85), rgba(250,248,245,0.9))', backdropFilter: 'blur(4px)' }}>
        <div className="bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 text-center max-w-sm shadow-lg">
          <div className="w-12 h-12 rounded-2xl bg-[#D97757]/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-[#D97757]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
          </div>
          <p className="font-bold text-gray-900 text-base mb-1">{title}</p>
          <p className="text-xs text-gray-500 mb-5 leading-relaxed">{subtitle}</p>
          <button
            onClick={onPurchase}
            disabled={loading}
            className="w-full px-6 py-3 rounded-xl text-white text-sm font-semibold disabled:opacity-50 transition-all hover:shadow-md active:scale-[0.98]"
            style={{ background: 'linear-gradient(135deg, #D97757, #BA7517)' }}
          >
            {loading ? 'Processing...' : priceLabel}
          </button>
          <div className="flex items-center justify-center gap-4 mt-4 text-[10px] text-gray-400">
            <span>Consultants charge <span className="line-through font-medium">$1,500+</span></span>
            <span className="text-[#0F6E56] font-semibold">Save 90%+</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ScoreCard({ label, value, color, suffix = '%' }: { label: string; value: number; color: string; suffix?: string }) {
  const pct = suffix === '%' ? value : value * 10
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-medium text-gray-900">{value}{suffix}</div>
      <div className="mt-2 h-1 bg-gray-200 rounded-full">
        <div className="h-1 rounded-full" style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
      </div>
    </div>
  )
}

export function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="border border-gray-100 rounded-lg p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-medium mt-0.5" style={{ color: color || '#1C1917' }}>{value}</div>
    </div>
  )
}

export function OppRow({ title, category, score, to }: { title: string; category?: string; score?: number | string; to?: string }) {
  const content = (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
      <div>
        <div className="text-sm font-medium text-gray-900">{title}</div>
        {category && <div className="text-xs text-gray-500">{category}</div>}
      </div>
      {score != null && (
        <div className="text-right">
          <div className="text-sm font-medium" style={{ color: '#D97757' }}>{score}</div>
          <div className="text-[10px] text-gray-400">score</div>
        </div>
      )}
    </div>
  )
  if (to) return <Link to={to}>{content}</Link>
  return content
}
