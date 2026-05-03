import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Database, Users } from 'lucide-react'
import DatasetsTab from '../components/marketplace/DatasetsTab'
import LeadsTab from '../components/marketplace/LeadsTab'

type TabId = 'datasets' | 'leads'

const TABS: { id: TabId; label: string; icon: React.ElementType; description: string }[] = [
  {
    id: 'datasets',
    label: 'Datasets',
    icon: Database,
    description: 'Verified market intelligence datasets',
  },
  {
    id: 'leads',
    label: 'Leads',
    icon: Users,
    description: 'Vetted, high-intent business opportunities',
  },
]

export default function Marketplace() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const activeTab: TabId = tabParam === 'leads' ? 'leads' : 'datasets'

  // Normalize URL so the active tab is always reflected (e.g. /marketplace -> /marketplace?tab=datasets).
  useEffect(() => {
    if (tabParam !== 'datasets' && tabParam !== 'leads') {
      const next = new URLSearchParams(searchParams)
      next.set('tab', 'datasets')
      setSearchParams(next, { replace: true })
    }
  }, [tabParam, searchParams, setSearchParams])

  const setActiveTab = (tab: TabId) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tab)
    setSearchParams(next, { replace: false })
  }

  const activeMeta = TABS.find((t) => t.id === activeTab) ?? TABS[0]

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50/40 via-white to-white">
      {/* Combined header + tab bar */}
      <div className="border-b border-gray-200 bg-white/80 backdrop-blur sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Marketplace</h1>
              <p className="text-sm text-gray-500">{activeMeta.description}</p>
            </div>
          </div>
          <div className="flex gap-1" role="tablist" aria-label="Marketplace sections">
            {TABS.map((tab) => {
              const Icon = tab.icon
              const isActive = tab.id === activeTab
              return (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`tabpanel-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                    isActive
                      ? 'border-emerald-600 text-emerald-700'
                      : 'border-transparent text-gray-500 hover:text-gray-900 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Tab content — both tabs stay mounted so each keeps its own filter/search state when switching */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div
          id="tabpanel-datasets"
          role="tabpanel"
          aria-labelledby="tab-datasets"
          hidden={activeTab !== 'datasets'}
        >
          <DatasetsTab />
        </div>
        <div
          id="tabpanel-leads"
          role="tabpanel"
          aria-labelledby="tab-leads"
          hidden={activeTab !== 'leads'}
        >
          <LeadsTab />
        </div>
      </div>
    </div>
  )
}
