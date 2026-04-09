import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { 
  User, 
  Bell, 
  CreditCard, 
  Shield, 
  Users, 
  Briefcase,
  HandCoins,
  Handshake,
  Building2,
  ChevronRight,
  Loader2,
  ExternalLink,
  Calendar,
  Zap,
  Smartphone,
  Copy,
  Check,
  AlertTriangle,
  RefreshCw,
  X,
  Bot,
  Key,
  Eye,
  EyeOff,
  BarChart2,
  TrendingUp,
  DollarSign,
  Cpu
} from 'lucide-react'

type SubscriptionInfo = {
  tier: string | null
  status: string | null
  is_active: boolean
  period_end: string | null
  views_remaining: number | null
}

type TwoFactorStatus = {
  enabled: boolean
  backup_codes_count: number
}

type TwoFactorSetup = {
  secret: string
  qr_code: string
}

type AIPreferences = {
  provider: string
  mode: 'replit' | 'byok'
  model: string
  has_openai_key: boolean
  has_claude_key: boolean
  openai_key_validated_at: string | null
  claude_key_validated_at: string | null
}

type AvailableModel = {
  model_id: string
  display_name: string
  provider: string
  description: string | null
  is_default: boolean
}

type AvailableModelsResponse = {
  models: AvailableModel[]
  user_tier: string
  default_model: string | null
}

type ModelUsage = {
  model: string
  requests: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  markup_percent: number
}

type TokenUsageData = {
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_estimated_cost_usd: number
  period_days: number
  since: string
  by_model: ModelUsage[]
  stripe_billing_enabled: boolean
}

type NetworkRole = 'expert' | 'partner' | 'investor' | 'lender'

interface NetworkRoleConfig {
  id: NetworkRole
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  benefits: string[]
}

const networkRoles: NetworkRoleConfig[] = [
  {
    id: 'expert',
    title: 'Expert/Consultant',
    description: 'Offer your expertise to entrepreneurs and startups',
    icon: Briefcase,
    benefits: [
      'Get matched with relevant opportunities',
      'Set your own rates and availability',
      'Build your professional reputation',
      'Earn from consulting engagements'
    ]
  },
  {
    id: 'partner',
    title: 'Find Partners',
    description: 'Connect with potential co-founders and business partners',
    icon: Handshake,
    benefits: [
      'Browse validated opportunities',
      'Connect with like-minded entrepreneurs',
      'Form strategic partnerships',
      'Access exclusive networking events'
    ]
  },
  {
    id: 'investor',
    title: 'Investor',
    description: 'Discover and invest in vetted opportunities',
    icon: HandCoins,
    benefits: [
      'Access pre-validated deals',
      'AI-powered opportunity matching',
      'Due diligence reports included',
      'Direct founder connections'
    ]
  },
  {
    id: 'lender',
    title: 'Lender',
    description: 'Provide funding to qualified startups and businesses',
    icon: Building2,
    benefits: [
      'Vetted borrower profiles',
      'Risk assessment reports',
      'Flexible lending options',
      'Platform-secured transactions'
    ]
  }
]

export default function Settings() {
  const { user, token } = useAuthStore()
  const [activeTab, setActiveTab] = useState('profile')
  const [subscriptionInfo, setSubscriptionInfo] = useState<SubscriptionInfo | null>(null)
  const [loadingSubscription, setLoadingSubscription] = useState(false)
  const [loadingPortal, setLoadingPortal] = useState(false)
  const [tokenUsage, setTokenUsage] = useState<TokenUsageData | null>(null)
  const [loadingUsage, setLoadingUsage] = useState(false)
  const [usagePeriod, setUsagePeriod] = useState(30)

  const [twoFactorStatus, setTwoFactorStatus] = useState<TwoFactorStatus | null>(null)
  const [loading2FA, setLoading2FA] = useState(false)
  const [show2FASetup, setShow2FASetup] = useState(false)
  const [setupData, setSetupData] = useState<TwoFactorSetup | null>(null)
  const [otpCode, setOtpCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [showBackupCodes, setShowBackupCodes] = useState(false)
  const [disablePassword, setDisablePassword] = useState('')
  const [showDisable2FA, setShowDisable2FA] = useState(false)
  const [twoFactorError, setTwoFactorError] = useState('')
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  const [aiPreferences, setAIPreferences] = useState<AIPreferences | null>(null)
  const [loadingAI, setLoadingAI] = useState(false)
  const [savingAI, setSavingAI] = useState(false)
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [openaiKey, setOpenaiKey] = useState('')
  const [claudeKey, setClaudeKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [showClaudeKey, setShowClaudeKey] = useState(false)
  const [aiError, setAIError] = useState('')
  const [aiSuccess, setAISuccess] = useState('')

  useEffect(() => {
    if (activeTab === 'billing' && token) {
      fetchSubscriptionInfo()
      fetchTokenUsage(usagePeriod)
    }
    if (activeTab === 'security' && token) {
      fetch2FAStatus()
    }
    if (activeTab === 'ai' && token) {
      fetchAIPreferences()
      fetchAvailableModels()
    }
  }, [activeTab, token])

  useEffect(() => {
    if (activeTab === 'billing' && token) {
      fetchTokenUsage(usagePeriod)
    }
  }, [usagePeriod])

  async function fetchSubscriptionInfo() {
    if (!token) return
    setLoadingSubscription(true)
    try {
      const res = await fetch('/api/v1/subscriptions/my-subscription', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSubscriptionInfo(data)
      }
    } catch (err) {
      console.error('Failed to fetch subscription:', err)
    } finally {
      setLoadingSubscription(false)
    }
  }

  async function fetchTokenUsage(days: number) {
    if (!token) return
    setLoadingUsage(true)
    try {
      const res = await fetch(`/api/v1/billing/usage?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setTokenUsage(data)
      }
    } catch (err) {
      console.error('Failed to fetch token usage:', err)
    } finally {
      setLoadingUsage(false)
    }
  }

  async function openBillingPortal() {
    if (!token) return
    setLoadingPortal(true)
    try {
      const res = await fetch('/api/v1/subscriptions/portal', {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ return_url: window.location.href })
      })
      if (res.ok) {
        const data = await res.json()
        if (data.url) {
          window.location.href = data.url
        }
      }
    } catch (err) {
      console.error('Failed to open billing portal:', err)
    } finally {
      setLoadingPortal(false)
    }
  }

  function formatTierName(tier: string | null | undefined): string {
    if (!tier) return 'Free'
    const tierMap: Record<string, string> = {
      'explorer': 'Explorer (Free)',
      'free': 'Explorer (Free)',
      'pro': 'Builder',
      'builder': 'Builder',
      'business': 'Scaler',
      'scaler': 'Scaler',
      'enterprise': 'Enterprise'
    }
    return tierMap[tier.toLowerCase()] || tier.charAt(0).toUpperCase() + tier.slice(1)
  }

  async function fetch2FAStatus() {
    if (!token) return
    setLoading2FA(true)
    try {
      const res = await fetch('/api/v1/2fa/status', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setTwoFactorStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch 2FA status:', err)
    } finally {
      setLoading2FA(false)
    }
  }

  async function initiate2FASetup() {
    if (!token) return
    setLoading2FA(true)
    setTwoFactorError('')
    try {
      const res = await fetch('/api/v1/2fa/setup', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSetupData(data)
        setShow2FASetup(true)
      } else {
        const error = await res.json()
        setTwoFactorError(error.detail || 'Failed to initiate 2FA setup')
      }
    } catch (err) {
      console.error('Failed to setup 2FA:', err)
      setTwoFactorError('An error occurred. Please try again.')
    } finally {
      setLoading2FA(false)
    }
  }

  async function enable2FA() {
    if (!token || !otpCode) return
    setLoading2FA(true)
    setTwoFactorError('')
    try {
      const res = await fetch('/api/v1/2fa/enable', {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ otp_code: otpCode })
      })
      if (res.ok) {
        const data = await res.json()
        setBackupCodes(data.backup_codes)
        setShowBackupCodes(true)
        setShow2FASetup(false)
        setOtpCode('')
        setSetupData(null)
        fetch2FAStatus()
      } else {
        const error = await res.json()
        setTwoFactorError(error.detail || 'Invalid verification code')
      }
    } catch (err) {
      console.error('Failed to enable 2FA:', err)
      setTwoFactorError('An error occurred. Please try again.')
    } finally {
      setLoading2FA(false)
    }
  }

  async function disable2FA() {
    if (!token || !disablePassword) return
    setLoading2FA(true)
    setTwoFactorError('')
    try {
      const res = await fetch('/api/v1/2fa/disable', {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ password: disablePassword })
      })
      if (res.ok) {
        setShowDisable2FA(false)
        setDisablePassword('')
        fetch2FAStatus()
      } else {
        const error = await res.json()
        setTwoFactorError(error.detail || 'Incorrect password')
      }
    } catch (err) {
      console.error('Failed to disable 2FA:', err)
      setTwoFactorError('An error occurred. Please try again.')
    } finally {
      setLoading2FA(false)
    }
  }

  async function regenerateBackupCodes() {
    if (!token) return
    setLoading2FA(true)
    try {
      const res = await fetch('/api/v1/2fa/regenerate-backup-codes', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setBackupCodes(data.backup_codes)
        setShowBackupCodes(true)
        fetch2FAStatus()
      }
    } catch (err) {
      console.error('Failed to regenerate backup codes:', err)
    } finally {
      setLoading2FA(false)
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
    setCopiedCode(text)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  function copyAllBackupCodes() {
    const allCodes = backupCodes.join('\n')
    navigator.clipboard.writeText(allCodes)
    setCopiedCode('all')
    setTimeout(() => setCopiedCode(null), 2000)
  }

  async function fetchAIPreferences() {
    if (!token) return
    setLoadingAI(true)
    setAIError('')
    try {
      const res = await fetch('/api/v1/ai-preferences', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setAIPreferences(data)
      }
    } catch (err) {
      console.error('Failed to fetch AI preferences:', err)
    } finally {
      setLoadingAI(false)
    }
  }

  async function fetchAvailableModels() {
    if (!token) return
    setLoadingModels(true)
    try {
      const res = await fetch('/api/v1/ai/models', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data: AvailableModelsResponse = await res.json()
        setAvailableModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to fetch available models:', err)
    } finally {
      setLoadingModels(false)
    }
  }

  async function saveAIPreferences(updates: Partial<AIPreferences & { openai_api_key?: string }>) {
    if (!token) return
    setSavingAI(true)
    setAIError('')
    setAISuccess('')
    try {
      const res = await fetch('/api/v1/ai-preferences', {
        method: 'PUT',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      })
      if (res.ok) {
        const data = await res.json()
        setAIPreferences(data)
        setAISuccess('AI preferences saved successfully')
        setOpenaiKey('')
        setTimeout(() => setAISuccess(''), 3000)
      } else {
        const error = await res.json()
        setAIError(error.detail || 'Failed to save preferences')
      }
    } catch (err) {
      console.error('Failed to save AI preferences:', err)
      setAIError('An error occurred. Please try again.')
    } finally {
      setSavingAI(false)
    }
  }

  async function validateAndSaveOpenAIKey() {
    if (!token || !openaiKey.trim()) return
    setSavingAI(true)
    setAIError('')
    setAISuccess('')
    try {
      const res = await fetch('/api/v1/ai-preferences/openai-key', {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: openaiKey.trim() })
      })
      const data = await res.json()
      if (!res.ok) {
        setAIError(data.detail || 'Invalid OpenAI API key')
        setSavingAI(false)
        return
      }
      setAISuccess(data.message || 'OpenAI API key validated and saved successfully')
      setOpenaiKey('')
      fetchAIPreferences()
      setTimeout(() => setAISuccess(''), 3000)
    } catch (err) {
      console.error('Failed to validate OpenAI key:', err)
      setAIError('An error occurred. Please try again.')
    } finally {
      setSavingAI(false)
    }
  }

  async function deleteOpenAIKey() {
    if (!token) return
    setSavingAI(true)
    setAIError('')
    try {
      const res = await fetch('/api/v1/ai-preferences/openai-key', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setAISuccess('OpenAI API key removed')
        fetchAIPreferences()
        setTimeout(() => setAISuccess(''), 3000)
      } else {
        const error = await res.json()
        setAIError(error.detail || 'Failed to remove key')
      }
    } catch (err) {
      console.error('Failed to delete OpenAI key:', err)
      setAIError('An error occurred. Please try again.')
    } finally {
      setSavingAI(false)
    }
  }

  async function validateAndSaveClaudeKey() {
    if (!token || !claudeKey.trim()) return
    setSavingAI(true)
    setAIError('')
    setAISuccess('')
    try {
      const res = await fetch('/api/v1/ai-preferences/claude-key', {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: claudeKey.trim() })
      })
      const data = await res.json()
      if (!res.ok) {
        setAIError(data.detail || 'Invalid Claude API key')
        setSavingAI(false)
        return
      }
      setAISuccess(data.message || 'Claude API key validated and saved successfully')
      setClaudeKey('')
      fetchAIPreferences()
      setTimeout(() => setAISuccess(''), 3000)
    } catch (err) {
      console.error('Failed to validate Claude key:', err)
      setAIError('An error occurred. Please try again.')
    } finally {
      setSavingAI(false)
    }
  }

  async function deleteClaudeKey() {
    if (!token) return
    setSavingAI(true)
    setAIError('')
    try {
      const res = await fetch('/api/v1/ai-preferences/claude-key', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setAISuccess('Claude API key removed')
        fetchAIPreferences()
        setTimeout(() => setAISuccess(''), 3000)
      } else {
        const error = await res.json()
        setAIError(error.detail || 'Failed to remove key')
      }
    } catch (err) {
      console.error('Failed to delete Claude key:', err)
      setAIError('An error occurred. Please try again.')
    } finally {
      setSavingAI(false)
    }
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'ai', label: 'AI Settings', icon: Bot },
    { id: 'network', label: 'Join Our Network', icon: Users },
    { id: 'api-keys', label: 'API Keys', icon: Key, href: '/settings/api' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Account Settings</h1>
        
        <div className="flex flex-col md:flex-row gap-6">
          {/* Sidebar */}
          <div className="w-full md:w-64 bg-white rounded-xl border border-gray-200 p-4">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const cls = `w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`
                if ('href' in tab && tab.href) {
                  return (
                    <Link key={tab.id} to={tab.href} className={cls}>
                      <tab.icon className="w-5 h-5" />
                      {tab.label}
                    </Link>
                  )
                }
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cls}
                  >
                    <tab.icon className="w-5 h-5" />
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>
          
          {/* Content */}
          <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6">
            {activeTab === 'profile' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile Information</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <input 
                      type="text" 
                      defaultValue={user?.name || ''} 
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input 
                      type="email" 
                      defaultValue={user?.email || ''} 
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
                    />
                  </div>
                  <button className="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors">
                    Save Changes
                  </button>
                </div>
              </div>
            )}
            
            {activeTab === 'notifications' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Notification Preferences</h2>
                <div className="space-y-4">
                  {['New opportunities matching your interests', 'Weekly digest emails', 'Partner connection requests', 'Platform updates and news'].map((item) => (
                    <label key={item} className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                      <span className="text-sm text-gray-700">{item}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            
            {activeTab === 'billing' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Billing & Subscription</h2>
                
                {loadingSubscription ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="p-5 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl border border-gray-200">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 bg-white rounded-lg border border-gray-200">
                            <Zap className="w-5 h-5 text-purple-600" />
                          </div>
                          <div>
                            <p className="font-semibold text-gray-900 text-lg">
                              {formatTierName(subscriptionInfo?.tier || user?.tier)}
                            </p>
                            <p className="text-sm text-gray-500">
                              {subscriptionInfo?.is_active ? (
                                <span className="text-green-600 font-medium">Active</span>
                              ) : (
                                <span className="text-gray-500">Free tier</span>
                              )}
                            </p>
                          </div>
                        </div>
                        <Link 
                          to="/pricing" 
                          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
                        >
                          Upgrade Plan
                        </Link>
                      </div>

                      {subscriptionInfo?.period_end && subscriptionInfo?.is_active && (
                        <div className="mt-4 pt-4 border-t border-gray-200 flex items-center gap-2 text-sm text-gray-600">
                          <Calendar className="w-4 h-4" />
                          <span>
                            Renews on {new Date(subscriptionInfo.period_end).toLocaleDateString('en-US', { 
                              month: 'long', 
                              day: 'numeric', 
                              year: 'numeric' 
                            })}
                          </span>
                        </div>
                      )}

                      {subscriptionInfo?.views_remaining !== null && subscriptionInfo?.views_remaining !== undefined && (
                        <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
                          <span className="font-medium">{subscriptionInfo.views_remaining}</span>
                          <span>opportunity views remaining this month</span>
                        </div>
                      )}
                    </div>

                    {subscriptionInfo?.is_active && (
                      <div className="p-4 bg-white rounded-lg border border-gray-200">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900">Manage Billing</p>
                            <p className="text-sm text-gray-500 mt-1">Update payment method, view invoices, or cancel subscription</p>
                          </div>
                          <button
                            onClick={openBillingPortal}
                            disabled={loadingPortal}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium disabled:opacity-50"
                          >
                            {loadingPortal ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                Open Billing Portal
                                <ExternalLink className="w-4 h-4" />
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {!subscriptionInfo?.is_active && (
                      <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                        <p className="text-sm text-purple-800">
                          Upgrade to a paid plan to unlock unlimited opportunity access, deep analysis reports, and expert consultations.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* AI Token Usage Section */}
                <div className="mt-8">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="w-5 h-5 text-gray-600" />
                      <h3 className="text-base font-semibold text-gray-900">AI Token Usage</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      {[7, 30, 90].map((d) => (
                        <button
                          key={d}
                          onClick={() => setUsagePeriod(d)}
                          className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                            usagePeriod === d
                              ? 'bg-gray-900 text-white'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                        >
                          {d}d
                        </button>
                      ))}
                      <button
                        onClick={() => fetchTokenUsage(usagePeriod)}
                        disabled={loadingUsage}
                        className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-500 transition-colors disabled:opacity-40"
                        title="Refresh"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${loadingUsage ? 'animate-spin' : ''}`} />
                      </button>
                    </div>
                  </div>

                  {loadingUsage ? (
                    <div className="flex items-center justify-center py-10 bg-gray-50 rounded-xl border border-gray-200">
                      <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                    </div>
                  ) : tokenUsage ? (
                    <div className="space-y-4">
                      {/* Summary stats */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Cpu className="w-4 h-4 text-purple-500" />
                            <p className="text-xs text-gray-500 font-medium">Total Tokens</p>
                          </div>
                          <p className="text-xl font-bold text-gray-900">
                            {tokenUsage.total_tokens >= 1_000_000
                              ? `${(tokenUsage.total_tokens / 1_000_000).toFixed(2)}M`
                              : tokenUsage.total_tokens >= 1000
                              ? `${(tokenUsage.total_tokens / 1000).toFixed(1)}K`
                              : tokenUsage.total_tokens.toString()}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {tokenUsage.total_input_tokens.toLocaleString()} in · {tokenUsage.total_output_tokens.toLocaleString()} out
                          </p>
                        </div>

                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                          <div className="flex items-center gap-2 mb-1">
                            <DollarSign className="w-4 h-4 text-green-500" />
                            <p className="text-xs text-gray-500 font-medium">Est. Cost</p>
                          </div>
                          <p className="text-xl font-bold text-gray-900">
                            ${tokenUsage.total_estimated_cost_usd.toFixed(4)}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5">last {tokenUsage.period_days} days</p>
                        </div>

                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                          <div className="flex items-center gap-2 mb-1">
                            <TrendingUp className="w-4 h-4 text-blue-500" />
                            <p className="text-xs text-gray-500 font-medium">Models Used</p>
                          </div>
                          <p className="text-xl font-bold text-gray-900">{tokenUsage.by_model.length}</p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {tokenUsage.by_model.reduce((s, m) => s + m.requests, 0)} requests
                          </p>
                        </div>
                      </div>

                      {/* Per-model breakdown */}
                      {tokenUsage.by_model.length > 0 ? (
                        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Breakdown by Model</p>
                          </div>
                          <div className="divide-y divide-gray-100">
                            {tokenUsage.by_model.map((m) => {
                              const pct = tokenUsage.total_tokens > 0
                                ? Math.round((m.total_tokens / tokenUsage.total_tokens) * 100)
                                : 0
                              const shortName = m.model.replace('claude-', 'Claude ').replace('gpt-', 'GPT-').replace(/-\d{8}$/, '')
                              return (
                                <div key={m.model} className="px-4 py-3">
                                  <div className="flex items-center justify-between mb-1.5">
                                    <div className="flex items-center gap-2">
                                      <Bot className="w-3.5 h-3.5 text-gray-400" />
                                      <span className="text-sm font-medium text-gray-800">{shortName}</span>
                                      <span className="text-xs text-gray-400">{m.requests} req</span>
                                    </div>
                                    <div className="text-right">
                                      <span className="text-sm font-semibold text-gray-900">
                                        ${m.estimated_cost_usd.toFixed(4)}
                                      </span>
                                      <span className="text-xs text-gray-400 ml-2">{pct}%</span>
                                    </div>
                                  </div>
                                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                                    <div
                                      className="bg-purple-500 h-1.5 rounded-full transition-all"
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                  <div className="flex justify-between mt-1">
                                    <span className="text-xs text-gray-400">
                                      {m.total_tokens >= 1000
                                        ? `${(m.total_tokens / 1000).toFixed(1)}K`
                                        : m.total_tokens} tokens
                                    </span>
                                    {m.markup_percent > 0 && (
                                      <span className="text-xs text-gray-400">{m.markup_percent}% markup incl.</span>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      ) : (
                        <div className="p-6 bg-gray-50 rounded-xl border border-dashed border-gray-300 text-center">
                          <Bot className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-sm text-gray-500">No AI usage recorded in the last {usagePeriod} days.</p>
                          <p className="text-xs text-gray-400 mt-1">Usage is tracked after generating reports, analysis, or chat responses.</p>
                        </div>
                      )}

                      {tokenUsage.stripe_billing_enabled && (
                        <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg border border-green-200">
                          <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
                          <p className="text-xs text-green-700">
                            Usage is automatically reported to Stripe and included in your next invoice.
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-6 bg-gray-50 rounded-xl border border-dashed border-gray-300 text-center">
                      <BarChart2 className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                      <p className="text-sm text-gray-500">Could not load usage data.</p>
                      <button
                        onClick={() => fetchTokenUsage(usagePeriod)}
                        className="mt-2 text-xs text-purple-600 hover:text-purple-700 font-medium"
                      >
                        Try again
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {activeTab === 'security' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Security Settings</h2>
                
                {twoFactorError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    {twoFactorError}
                  </div>
                )}

                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">Password</p>
                        <p className="text-sm text-gray-500">Manage your account password</p>
                      </div>
                      <a 
                        href={`/reset-password.html?email=${encodeURIComponent(user?.email || '')}`}
                        className="text-sm font-medium text-gray-900 hover:underline"
                      >
                        Change
                      </a>
                    </div>
                  </div>

                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white rounded-lg border border-gray-200">
                          <Smartphone className="w-5 h-5 text-gray-600" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">Two-Factor Authentication</p>
                          <p className="text-sm text-gray-500">
                            {loading2FA ? (
                              'Checking status...'
                            ) : twoFactorStatus?.enabled ? (
                              <span className="text-green-600">Enabled - {twoFactorStatus.backup_codes_count} backup codes remaining</span>
                            ) : (
                              'Add an extra layer of security to your account'
                            )}
                          </p>
                        </div>
                      </div>
                      {loading2FA ? (
                        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                      ) : twoFactorStatus?.enabled ? (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={regenerateBackupCodes}
                            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                          >
                            <RefreshCw className="w-4 h-4" />
                            New Codes
                          </button>
                          <button
                            onClick={() => setShowDisable2FA(true)}
                            className="px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            Disable
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={initiate2FASetup}
                          className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
                        >
                          Enable
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {show2FASetup && setupData && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl max-w-md w-full p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">Set Up Two-Factor Authentication</h3>
                        <button 
                          onClick={() => { setShow2FASetup(false); setSetupData(null); setOtpCode(''); }}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <X className="w-5 h-5 text-gray-500" />
                        </button>
                      </div>
                      
                      <div className="space-y-4">
                        <p className="text-sm text-gray-600">
                          Scan this QR code with your authenticator app (like Google Authenticator or Authy):
                        </p>
                        
                        <div className="flex justify-center p-4 bg-white border border-gray-200 rounded-lg">
                          <img src={setupData.qr_code} alt="2FA QR Code" className="w-48 h-48" />
                        </div>

                        <div className="p-3 bg-gray-50 rounded-lg">
                          <p className="text-xs text-gray-500 mb-1">Or enter this code manually:</p>
                          <div className="flex items-center gap-2">
                            <code className="flex-1 text-sm font-mono bg-white px-2 py-1 rounded border border-gray-200 break-all">
                              {setupData.secret}
                            </code>
                            <button
                              onClick={() => copyToClipboard(setupData.secret)}
                              className="p-2 hover:bg-gray-200 rounded transition-colors"
                            >
                              {copiedCode === setupData.secret ? (
                                <Check className="w-4 h-4 text-green-600" />
                              ) : (
                                <Copy className="w-4 h-4 text-gray-500" />
                              )}
                            </button>
                          </div>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Enter the 6-digit code from your app:
                          </label>
                          <input
                            type="text"
                            value={otpCode}
                            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            placeholder="000000"
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg text-center text-lg tracking-widest font-mono focus:outline-none focus:ring-2 focus:ring-gray-900"
                            maxLength={6}
                          />
                        </div>

                        <button
                          onClick={enable2FA}
                          disabled={otpCode.length !== 6 || loading2FA}
                          className="w-full py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                          {loading2FA ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            'Verify and Enable'
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {showBackupCodes && backupCodes.length > 0 && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl max-w-md w-full p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">Save Your Backup Codes</h3>
                        <button 
                          onClick={() => { setShowBackupCodes(false); setBackupCodes([]); }}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <X className="w-5 h-5 text-gray-500" />
                        </button>
                      </div>

                      <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
                        <p className="text-sm text-yellow-800 flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                          Save these codes in a secure location. Each code can only be used once. You won't be able to see them again.
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-2 mb-4">
                        {backupCodes.map((code, idx) => (
                          <div 
                            key={idx}
                            className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded border border-gray-200"
                          >
                            <code className="font-mono text-sm">{code}</code>
                            <button
                              onClick={() => copyToClipboard(code)}
                              className="p-1 hover:bg-gray-200 rounded"
                            >
                              {copiedCode === code ? (
                                <Check className="w-3 h-3 text-green-600" />
                              ) : (
                                <Copy className="w-3 h-3 text-gray-400" />
                              )}
                            </button>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={copyAllBackupCodes}
                        className="w-full py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium flex items-center justify-center gap-2"
                      >
                        {copiedCode === 'all' ? (
                          <>
                            <Check className="w-4 h-4 text-green-600" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy All Codes
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => { setShowBackupCodes(false); setBackupCodes([]); }}
                        className="w-full mt-2 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
                      >
                        I've Saved My Codes
                      </button>
                    </div>
                  </div>
                )}

                {showDisable2FA && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl max-w-md w-full p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">Disable Two-Factor Authentication</h3>
                        <button 
                          onClick={() => { setShowDisable2FA(false); setDisablePassword(''); setTwoFactorError(''); }}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <X className="w-5 h-5 text-gray-500" />
                        </button>
                      </div>

                      <div className="p-3 bg-red-50 border border-red-200 rounded-lg mb-4">
                        <p className="text-sm text-red-800">
                          Disabling 2FA will make your account less secure. Are you sure you want to continue?
                        </p>
                      </div>

                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Enter your password to confirm:
                        </label>
                        <input
                          type="password"
                          value={disablePassword}
                          onChange={(e) => setDisablePassword(e.target.value)}
                          placeholder="Your password"
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
                        />
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => { setShowDisable2FA(false); setDisablePassword(''); setTwoFactorError(''); }}
                          className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={disable2FA}
                          disabled={!disablePassword || loading2FA}
                          className="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                          {loading2FA ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            'Disable 2FA'
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'ai' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Settings</h2>
                <p className="text-gray-600 mb-6">Configure your AI provider preferences for opportunity analysis and workspace features.</p>
                
                {aiError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    {aiError}
                  </div>
                )}
                
                {aiSuccess && (
                  <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700 text-sm">
                    <Check className="w-4 h-4" />
                    {aiSuccess}
                  </div>
                )}

                {loadingAI ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Model Selector */}
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-medium text-gray-900">Select AI Model</h3>
                        {loadingModels && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
                      </div>

                      {availableModels.length > 0 ? (
                        (() => {
                          // Group models by provider
                          const providerOrder = ['anthropic', 'openai', 'google', 'deepseek', 'xai']
                          const grouped: Record<string, AvailableModel[]> = {}
                          for (const m of availableModels) {
                            const p = m.provider.toLowerCase()
                            if (!grouped[p]) grouped[p] = []
                            grouped[p].push(m)
                          }
                          const providerMeta: Record<string, { label: string; initials: string; gradient: string }> = {
                            anthropic: { label: 'Anthropic', initials: 'A', gradient: 'from-orange-400 to-amber-500' },
                            openai:    { label: 'OpenAI',    initials: 'O', gradient: 'from-green-500 to-emerald-600' },
                            google:    { label: 'Google',    initials: 'G', gradient: 'from-blue-500 to-cyan-500' },
                            deepseek:  { label: 'DeepSeek',  initials: 'D', gradient: 'from-blue-600 to-violet-600' },
                            xai:       { label: 'xAI',       initials: 'X', gradient: 'from-gray-700 to-gray-900' },
                          }
                          const sortedProviders = Object.keys(grouped).sort(
                            (a, b) => providerOrder.indexOf(a) - providerOrder.indexOf(b)
                          )
                          return (
                            <div className="space-y-4">
                              {sortedProviders.map(provider => {
                                const meta = providerMeta[provider] || { label: provider, initials: provider[0].toUpperCase(), gradient: 'from-gray-400 to-gray-600' }
                                return (
                                  <div key={provider}>
                                    <div className="flex items-center gap-2 mb-2">
                                      <div className={`w-5 h-5 rounded-full bg-gradient-to-r ${meta.gradient} flex items-center justify-center`}>
                                        <span className="text-white text-[9px] font-bold">{meta.initials}</span>
                                      </div>
                                      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{meta.label}</span>
                                    </div>
                                    <div className="grid grid-cols-1 gap-2">
                                      {grouped[provider].map(m => {
                                        const isSelected = aiPreferences?.model === m.model_id
                                        return (
                                          <button
                                            key={m.model_id}
                                            onClick={() => saveAIPreferences({ model: m.model_id, provider })}
                                            disabled={savingAI}
                                            className={`w-full p-3 rounded-lg border-2 text-left transition-all ${
                                              isSelected
                                                ? 'border-purple-500 bg-purple-50'
                                                : 'border-gray-200 bg-white hover:border-gray-300'
                                            }`}
                                          >
                                            <div className="flex items-center justify-between">
                                              <div>
                                                <span className="text-sm font-medium text-gray-900">{m.display_name}</span>
                                                {m.is_default && (
                                                  <span className="ml-2 px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-medium rounded">
                                                    Default
                                                  </span>
                                                )}
                                                {m.description && (
                                                  <p className="text-xs text-gray-500 mt-0.5">{m.description}</p>
                                                )}
                                              </div>
                                              {isSelected && <Check className="w-4 h-4 text-purple-600 flex-shrink-0" />}
                                            </div>
                                          </button>
                                        )
                                      })}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          )
                        })()
                      ) : !loadingModels ? (
                        /* Fallback: two hardcoded options if model list fails to load */
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            onClick={() => saveAIPreferences({ provider: 'anthropic', mode: 'replit' })}
                            disabled={savingAI}
                            className={`p-4 rounded-lg border-2 transition-all text-left ${
                              aiPreferences?.provider === 'anthropic' || aiPreferences?.provider === 'claude'
                                ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-orange-400 to-amber-500 flex items-center justify-center">
                                <span className="text-white text-sm font-bold">A</span>
                              </div>
                              <span className="font-medium text-gray-900">Claude</span>
                            </div>
                            <p className="text-xs text-gray-500">Anthropic — best for nuanced analysis</p>
                          </button>
                          <button
                            onClick={() => saveAIPreferences({ provider: 'openai', mode: 'replit' })}
                            disabled={savingAI}
                            className={`p-4 rounded-lg border-2 transition-all text-left ${
                              aiPreferences?.provider === 'openai'
                                ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-green-500 to-emerald-600 flex items-center justify-center">
                                <span className="text-white text-sm font-bold">O</span>
                              </div>
                              <span className="font-medium text-gray-900">OpenAI</span>
                            </div>
                            <p className="text-xs text-gray-500">GPT-4o — fast and versatile</p>
                          </button>
                        </div>
                      ) : null}
                    </div>


                  </div>
                )}
              </div>
            )}
            
            {activeTab === 'network' && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-2">Join Our Network</h2>
                <p className="text-gray-600 mb-6">Select a role to join the OppGrid professional network using your LinkedIn profile.</p>
                
                <div className="grid md:grid-cols-2 gap-4">
                  {networkRoles.map((role) => {
                    const Icon = role.icon
                    
                    return (
                      <div
                        key={role.id}
                        onClick={() => window.location.href = `/api/v1/auth/linkedin/login?role=${role.id}`}
                        className="p-5 rounded-xl border-2 cursor-pointer transition-all border-gray-200 hover:border-indigo-500 hover:bg-indigo-50 group"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="p-2 rounded-lg bg-gray-100 text-gray-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                            <Icon className="w-5 h-5" />
                          </div>
                          <span className="text-xs text-gray-400 group-hover:text-indigo-600">Click to join →</span>
                        </div>
                        
                        <h3 className="font-semibold text-gray-900 mb-1">{role.title}</h3>
                        <p className="text-sm text-gray-600 mb-3">{role.description}</p>
                        
                        <ul className="space-y-1.5">
                          {role.benefits.map((benefit, idx) => (
                            <li key={idx} className="flex items-center gap-2 text-xs text-gray-500">
                              <ChevronRight className="w-3 h-3 text-gray-400" />
                              {benefit}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )
                  })}
                </div>
                
                <p className="mt-6 text-sm text-gray-500 text-center">
                  You'll be redirected to LinkedIn to verify your professional profile.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
      
    </div>
  )
}
