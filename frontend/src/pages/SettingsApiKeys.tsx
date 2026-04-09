import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
  X,
  Loader2,
  ChevronLeft,
  Shield,
  Clock,
  Activity,
  Eye,
  EyeOff,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

// ─── Types ───────────────────────────────────────────────────────────────────

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  environment: 'production' | 'sandbox'
  tier: string
  scopes: string[]
  rate_limit_rpm: number
  daily_limit: number
  is_active: boolean
  last_used_at: string | null
  expires_at: string | null
  created_at: string | null
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function subscriptionToApiTier(tier?: string): string {
  if (!tier) return 'starter'
  const t = tier.toLowerCase()
  if (['team', 'business', 'enterprise'].includes(t)) return 'enterprise'
  if (['starter', 'growth', 'pro'].includes(t)) return 'professional'
  return 'starter'
}

function apiTierLabel(tier: string): string {
  const map: Record<string, string> = {
    starter: 'Starter',
    professional: 'Professional',
    enterprise: 'Enterprise',
  }
  return map[tier] ?? tier
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatNumber(n: number): string {
  return n.toLocaleString()
}

// ─── Create Modal ─────────────────────────────────────────────────────────────

interface CreateModalProps {
  onClose: () => void
  onCreated: (plaintext: string, key: ApiKey) => void
  token: string
  defaultTier: string
}

function CreateModal({ onClose, onCreated, token, defaultTier }: CreateModalProps) {
  const [name, setName] = useState('')
  const [environment, setEnvironment] = useState<'production' | 'sandbox'>('production')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Key name is required')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/v1/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          environment,
          tier: defaultTier,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create API key')
      }
      onCreated(data.plaintext_key, data.key)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Create API Key</h3>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Key Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My Production App"
              maxLength={100}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Environment</label>
            <div className="grid grid-cols-2 gap-3">
              {(['production', 'sandbox'] as const).map((env) => (
                <button
                  key={env}
                  type="button"
                  onClick={() => setEnvironment(env)}
                  className={`px-4 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${
                    environment === env
                      ? env === 'production'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                        : 'border-slate-500 bg-slate-50 text-slate-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {env === 'production' ? '🔴 Production' : '🧪 Sandbox'}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-gray-500">
              {environment === 'production'
                ? 'Prefix: og_live_… — Use for live traffic'
                : 'Prefix: og_test_… — Safe for testing'}
            </p>
          </div>

          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-600">
              <span className="font-medium">API Tier:</span> {apiTierLabel(defaultTier)} — assigned
              based on your subscription plan.
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating…
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Key
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── One-time Key Banner ──────────────────────────────────────────────────────

interface KeyRevealBannerProps {
  plaintext: string
  keyName: string
  onDismiss: () => void
}

function KeyRevealBanner({ plaintext, keyName, onDismiss }: KeyRevealBannerProps) {
  const [copied, setCopied] = useState(false)
  const [shown, setShown] = useState(true)

  function handleCopy() {
    navigator.clipboard.writeText(plaintext).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mb-6 border-2 border-emerald-400 rounded-xl bg-emerald-50 p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
            <Key className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <p className="font-semibold text-emerald-900 text-sm">API key created: {keyName}</p>
            <p className="text-xs text-emerald-700">
              Copy this key now — it won't be shown again.
            </p>
          </div>
        </div>
        <button onClick={onDismiss} className="p-1 hover:bg-emerald-100 rounded-lg transition-colors">
          <X className="w-4 h-4 text-emerald-700" />
        </button>
      </div>

      <div className="flex items-center gap-2 bg-white border border-emerald-200 rounded-lg px-3 py-2">
        <code className="flex-1 text-sm font-mono text-gray-800 break-all select-all">
          {shown ? plaintext : '•'.repeat(Math.min(plaintext.length, 48))}
        </code>
        <button
          onClick={() => setShown(!shown)}
          className="p-1.5 hover:bg-gray-100 rounded-md transition-colors flex-shrink-0"
          title={shown ? 'Hide key' : 'Reveal key'}
        >
          {shown ? (
            <EyeOff className="w-4 h-4 text-gray-500" />
          ) : (
            <Eye className="w-4 h-4 text-gray-500" />
          )}
        </button>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-md text-xs font-medium hover:bg-emerald-700 transition-colors flex-shrink-0"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      <div className="mt-3 flex items-start gap-1.5 text-xs text-amber-700">
        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        <span>
          Store this key securely (e.g. in an environment variable). Once you close this notice,
          you won't be able to retrieve the plaintext key again.
        </span>
      </div>
    </div>
  )
}

// ─── Revoke Confirmation ──────────────────────────────────────────────────────

interface RevokeConfirmProps {
  keyName: string
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
  error?: string | null
}

function RevokeConfirm({ keyName, onConfirm, onCancel, loading, error }: RevokeConfirmProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Revoke API Key?</h3>
            <p className="text-sm text-gray-600 mt-0.5">
              <span className="font-medium">"{keyName}"</span> will stop working immediately.
              This cannot be undone.
            </p>
          </div>
        </div>
        {error && (
          <div className="mb-4 flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Revoking…
              </>
            ) : (
              'Yes, revoke it'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Key Row ──────────────────────────────────────────────────────────────────

interface KeyRowProps {
  apiKey: ApiKey
  onRevoke: (id: string) => void
}

function KeyRow({ apiKey, onRevoke }: KeyRowProps) {
  return (
    <div className="p-4 border border-gray-200 rounded-xl hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-medium text-gray-900 text-sm">{apiKey.name}</span>
            <span
              className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                apiKey.environment === 'production'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {apiKey.environment === 'production' ? '🔴 Production' : '🧪 Sandbox'}
            </span>
            <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
              {apiTierLabel(apiKey.tier)}
            </span>
          </div>
          <code className="text-xs font-mono text-gray-500">{apiKey.key_prefix}••••••••</code>

          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Rate Limit</p>
              <p className="text-xs font-medium text-gray-700">
                {formatNumber(apiKey.rate_limit_rpm)} RPM
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Daily Limit</p>
              <p className="text-xs font-medium text-gray-700">
                {formatNumber(apiKey.daily_limit)} reqs/day
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Created</p>
              <p className="text-xs font-medium text-gray-700">{formatDate(apiKey.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Last Used</p>
              <p className="text-xs font-medium text-gray-700">
                {apiKey.last_used_at ? formatDate(apiKey.last_used_at) : 'Never'}
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={() => onRevoke(apiKey.id)}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Revoke
        </button>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SettingsApiKeys() {
  const navigate = useNavigate()
  const { user, token, isAuthenticated } = useAuthStore()

  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [newKeyPlaintext, setNewKeyPlaintext] = useState<string | null>(null)
  const [newKeyName, setNewKeyName] = useState<string>('')

  const [revokeTarget, setRevokeTarget] = useState<{ id: string; name: string } | null>(null)
  const [revoking, setRevoking] = useState(false)
  const [revokeError, setRevokeError] = useState<string | null>(null)

  const apiTier = subscriptionToApiTier(user?.tier)

  const tierLimits: Record<string, { rpm: number; daily: number }> = {
    starter:      { rpm: 10,    daily: 1_000 },
    professional: { rpm: 100,   daily: 10_000 },
    enterprise:   { rpm: 1_000, daily: 100_000 },
  }
  const currentLimits = tierLimits[apiTier] ?? tierLimits.starter

  const fetchKeys = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/v1/api-keys', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to load API keys')
      const data = await res.json()
      setKeys(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load API keys')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    fetchKeys()
  }, [isAuthenticated, fetchKeys, navigate])

  function handleCreated(plaintext: string, key: ApiKey) {
    setShowCreate(false)
    setNewKeyPlaintext(plaintext)
    setNewKeyName(key.name)
    setKeys((prev) => [key, ...prev])
  }

  async function handleRevoke() {
    if (!revokeTarget || !token) return
    setRevoking(true)
    setRevokeError(null)
    try {
      const res = await fetch(`/api/v1/api-keys/${revokeTarget.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to revoke key')
      }
      setKeys((prev) => prev.filter((k) => k.id !== revokeTarget.id))
      setRevokeTarget(null)
    } catch (err) {
      setRevokeError(err instanceof Error ? err.message : 'Failed to revoke key')
    } finally {
      setRevoking(false)
    }
  }

  const tierColorMap: Record<string, string> = {
    free: 'text-gray-600 bg-gray-100',
    starter: 'text-blue-700 bg-blue-100',
    growth: 'text-purple-700 bg-purple-100',
    pro: 'text-indigo-700 bg-indigo-100',
    team: 'text-orange-700 bg-orange-100',
    business: 'text-emerald-700 bg-emerald-100',
    enterprise: 'text-slate-700 bg-slate-100',
  }
  const subTierColor = tierColorMap[user?.tier ?? 'free'] ?? 'text-gray-600 bg-gray-100'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link
            to="/settings"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Account Settings
          </Link>
        </div>

        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
              <Key className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">API Keys</h1>
              <p className="text-sm text-gray-500">Manage your OppGrid API credentials</p>
            </div>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            disabled={keys.length >= 10}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={keys.length >= 10 ? 'Maximum 10 active keys' : undefined}
          >
            <Plus className="w-4 h-4" />
            Create API Key
          </button>
        </div>

        {/* Tier info cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className="w-9 h-9 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-slate-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-0.5">Subscription</p>
              <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${subTierColor}`}>
                {user?.tier ? user.tier.charAt(0).toUpperCase() + user.tier.slice(1) : 'Free'}
              </span>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <Activity className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-0.5">API Tier</p>
              <p className="text-sm font-semibold text-gray-900">{apiTierLabel(apiTier)}</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <Clock className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-0.5">Rate Limits</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(currentLimits.rpm)} RPM · {formatNumber(currentLimits.daily)}/day
              </p>
            </div>
          </div>
        </div>

        {/* One-time key reveal banner */}
        {newKeyPlaintext && (
          <KeyRevealBanner
            plaintext={newKeyPlaintext}
            keyName={newKeyName}
            onDismiss={() => setNewKeyPlaintext(null)}
          />
        )}

        {/* Keys list */}
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
            <h2 className="font-semibold text-gray-900 text-sm">
              Active Keys{' '}
              <span className="ml-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                {keys.length}/10
              </span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : error ? (
            <div className="flex items-center gap-3 p-6 text-red-700">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div>
                <p className="font-medium text-sm">{error}</p>
                <button
                  onClick={fetchKeys}
                  className="text-sm text-red-600 underline hover:no-underline mt-1"
                >
                  Try again
                </button>
              </div>
            </div>
          ) : keys.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
                <Key className="w-7 h-7 text-gray-400" />
              </div>
              <p className="font-medium text-gray-900 mb-1">No API keys yet</p>
              <p className="text-sm text-gray-500 mb-4 max-w-xs">
                Create an API key to start building integrations with the OppGrid API.
              </p>
              <button
                onClick={() => setShowCreate(true)}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Create your first key
              </button>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {keys.map((k) => (
                <KeyRow
                  key={k.id}
                  apiKey={k}
                  onRevoke={(id) => setRevokeTarget({ id, name: k.name })}
                />
              ))}
            </div>
          )}
        </div>

        {/* Help note */}
        <div className="mt-4 flex items-start gap-2 text-xs text-gray-500">
          <Shield className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-gray-400" />
          <p>
            API keys grant programmatic access to your OppGrid account. Treat them like passwords —
            never share them or commit them to source control. Revoke any key you suspect has been
            compromised immediately.{' '}
            <a href="/developer" className="text-emerald-600 hover:underline">
              View API documentation →
            </a>
          </p>
        </div>
      </div>

      {showCreate && token && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
          token={token}
          defaultTier={apiTier}
        />
      )}

      {revokeTarget && (
        <RevokeConfirm
          keyName={revokeTarget.name}
          onConfirm={handleRevoke}
          onCancel={() => { setRevokeTarget(null); setRevokeError(null) }}
          loading={revoking}
          error={revokeError}
        />
      )}
    </div>
  )
}
