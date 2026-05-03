import { useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

export default function Login() {
  const location = useLocation()
  const navigate = useNavigate()
  const next = useMemo(() => {
    const params = new URLSearchParams(location.search)
    return params.get('next') || '/dashboard'
  }, [location.search])

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [magicStatus, setMagicStatus] = useState('')
  const [magicSending, setMagicSending] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [linkedinLoading, setLinkedinLoading] = useState(false)

  const { login, isLoading, startReplitAuth, startGoogleAuth, startLinkedInAuth, sendMagicLink } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMagicStatus('')

    try {
      await login(email, password)
      navigate(next)
    } catch {
      setError('Invalid email or password')
    }
  }

  const handleReplit = () => {
    startReplitAuth(next)
  }

  const handleMagicLink = async () => {
    setError('')
    setMagicStatus('')
    const trimmed = email.trim()
    if (!trimmed) {
      setError('Enter your email to receive a magic link.')
      return
    }
    try {
      setMagicSending(true)
      const message = await sendMagicLink(trimmed)
      setMagicStatus(message || 'Magic link sent. Check your email.')
    } catch {
      setError('Failed to send magic link. Please try again.')
    } finally {
      setMagicSending(false)
    }
  }

  const handleGoogle = async () => {
    setError('')
    setMagicStatus('')
    try {
      setGoogleLoading(true)
      await startGoogleAuth(next)
    } catch {
      setError('Failed to start Google sign-in. Please try again.')
      setGoogleLoading(false)
    }
  }

  const handleLinkedIn = async () => {
    setError('')
    setMagicStatus('')
    try {
      setLinkedinLoading(true)
      await startLinkedInAuth(next)
    } catch {
      setError('Failed to start LinkedIn sign-in. Please try again.')
      setLinkedinLoading(false)
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome back</h1>
          <p className="text-gray-600">Sign in to your account to continue</p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-8">
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleGoogle}
              disabled={googleLoading}
              className="w-full py-3 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {googleLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Continue with Google
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleLinkedIn}
              disabled={linkedinLoading}
              className="w-full py-3 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {linkedinLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                  </svg>
                  Continue with LinkedIn
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleReplit}
              className="w-full py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium"
            >
              Continue with Replit
            </button>
          </div>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">Or use email</span>
              </div>
            </div>
          </div>

          {magicStatus && (
            <div className="mt-4 bg-green-50 text-green-700 px-4 py-3 rounded-lg text-sm">
              {magicStatus}
            </div>
          )}
          {error && (
            <div className="mt-4 bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="mt-5 space-y-3">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="you@example.com"
              />
            </div>

            <button
              type="button"
              onClick={handleMagicLink}
              disabled={magicSending}
              className="w-full py-3 border border-gray-200 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {magicSending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Sending link...
                </>
              ) : (
                'Send magic link'
              )}
            </button>
          </div>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">Or sign in with password</span>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-gray-900 text-white rounded-lg hover:bg-emerald-700 font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-gray-600">
          Don&apos;t have an account?{' '}
          <Link to="/signup" className="text-blue-600 hover:text-blue-700 font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
