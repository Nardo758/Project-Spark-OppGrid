import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { 
  Menu, 
  X, 
  ChevronDown
} from 'lucide-react'

const guestNavItems = [
  { name: 'Discover', path: '/discover' },
  { name: 'Marketplace', path: '/marketplace' },
  { name: 'Consultant Studio', path: '/build/reports' },
  { name: 'Leads', path: '/leads' },
  { 
    name: 'Join Our Network',
    dropdown: [
      { name: 'As an Expert/Consultant', path: '/network/experts', description: 'Offer your expertise to entrepreneurs' },
      { name: 'Find Partners', path: '/network/partners', description: 'Connect with potential business partners' },
      { name: 'Investor', path: '/network/investors', description: 'Discover investment opportunities' },
      { name: 'Lender', path: '/network/lenders', description: 'Provide funding to startups' },
    ]
  },
  { name: 'API', path: '/developer' },
  { name: 'Pricing', path: '/pricing' },
]

const paidNavItems = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Discover', path: '/discover' },
  { name: 'Marketplace', path: '/marketplace' },
  { name: 'Consultant Studio', path: '/build/reports' },
  { 
    name: 'My Projects',
    dropdown: [
      { name: 'Active Projects', path: '/projects', description: 'Opportunities you are working on' },
      { name: 'Saved Ideas', path: '/saved', description: 'Bookmarked opportunities' },
    ]
  },
  { 
    name: 'Build',
    dropdown: [
      { name: 'Find Expert Help', path: '/build/experts', description: 'Connect with industry experts' },
      { name: 'Business Plan', path: '/build/business-plan', description: 'AI-powered business planning' },
      { name: 'Find Money', path: '/build/funding', description: 'Explore funding options' },
      { name: 'Leads', path: '/leads', description: 'Generate and manage leads' },
    ]
  },
  { name: 'API', path: '/developer' },
  { name: 'Pricing', path: '/pricing' },
]

type DropdownItem = {
  name: string
  path: string
  description?: string
}

type NavItem = {
  name: string
  path?: string
  dropdown?: DropdownItem[]
}

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
  const [dropdownTimeout, setDropdownTimeout] = useState<NodeJS.Timeout | null>(null)
  const { isAuthenticated, user, logout } = useAuthStore()
  const location = useLocation()

  const navItems: NavItem[] = isAuthenticated ? paidNavItems : guestNavItems

  useEffect(() => {
    setActiveDropdown(null)
    setMobileMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    return () => {
      if (dropdownTimeout) clearTimeout(dropdownTimeout)
    }
  }, [dropdownTimeout])

  const handleDropdownEnter = (name: string) => {
    if (dropdownTimeout) clearTimeout(dropdownTimeout)
    setActiveDropdown(name)
  }

  const handleDropdownLeave = () => {
    const timeout = setTimeout(() => {
      setActiveDropdown(null)
    }, 150)
    setDropdownTimeout(timeout)
  }

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/welcome" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">OG</span>
              </div>
              <div className="flex flex-col">
                <span className="font-semibold text-xl text-gray-900 leading-tight">OppGrid</span>
                <span className="text-[9px] text-gray-500 leading-tight">The Opportunity Intelligence Platform</span>
              </div>
            </Link>
          </div>

          {/* Centered Navigation */}
          <div className="hidden md:flex items-center justify-center flex-1">
            <div className="flex items-center gap-1">
              {navItems.map((item: NavItem) => (
                item.dropdown ? (
                  <div 
                    key={item.name} 
                    className="relative"
                    onMouseEnter={() => handleDropdownEnter(item.name)}
                    onMouseLeave={handleDropdownLeave}
                  >
                    <button
                      className={`flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                        activeDropdown === item.name
                          ? 'text-gray-900 bg-gray-100'
                          : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
                      }`}
                    >
                      {item.name}
                      <ChevronDown className={`w-4 h-4 transition-transform ${activeDropdown === item.name ? 'rotate-180' : ''}`} />
                    </button>
                    {activeDropdown === item.name && (
                      <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg py-2">
                        {item.dropdown.map((subItem) => (
                          <Link
                            key={subItem.path}
                            to={subItem.path}
                            className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                          >
                            <div>
                              <div className="text-sm font-medium text-gray-900">{subItem.name}</div>
                              {subItem.description && (
                                <div className="text-xs text-gray-500 mt-0.5">{subItem.description}</div>
                              )}
                            </div>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <Link
                    key={item.path}
                    to={item.path || '/'}
                    className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      location.pathname === item.path
                        ? 'text-gray-900 bg-gray-100'
                        : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    {item.name}
                  </Link>
                )
              ))}
            </div>
          </div>

          {/* Right side - Auth buttons or User menu */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <button
                  onClick={logout}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
                >
                  Sign Out
                </button>
                <Link to="/settings" className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-white">
                      {user?.name?.charAt(0) || 'U'}
                    </span>
                  </div>
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/pricing"
                  className="px-4 py-2 text-sm font-medium text-white bg-black hover:bg-gray-800 rounded-lg transition-colors"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-gray-700"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200 bg-white">
          <div className="px-4 py-3 space-y-1">
            
            {navItems.map((item: NavItem) => (
              item.dropdown ? (
                <div key={item.name} className="py-2">
                  <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-500">
                    {item.name}
                  </div>
                  <div className="ml-4 space-y-1">
                    {item.dropdown.map((subItem) => (
                      <Link
                        key={subItem.path}
                        to={subItem.path}
                        className="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        {subItem.name}
                      </Link>
                    ))}
                  </div>
                </div>
              ) : (
                <Link
                  key={item.path}
                  to={item.path || '/'}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-md"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item.name}
                </Link>
              )
            ))}
            
            {isAuthenticated ? (
              <button
                onClick={() => {
                  logout()
                  setMobileMenuOpen(false)
                }}
                className="w-full text-left px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-md"
              >
                Sign Out
              </button>
            ) : (
              <div className="pt-3 border-t border-gray-200 space-y-2">
                <Link
                  to="/login"
                  className="block px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-md"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  to="/pricing"
                  className="block px-3 py-2 text-sm font-medium text-white bg-black rounded-lg text-center"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
