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

  const setActiveTab = (tab: TabId) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tab)
    setSearchParams(next, { replace: false })
  }

  const activeMeta = TABS.find((t) => t.id === activeTab) ?? TABS[0]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 border-b border-gray-700 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-white mb-2">Marketplace</h1>
          <p className="text-gray-400 text-lg">{activeMeta.description}</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b border-gray-700 bg-gray-900/60 sticky top-16 z-30 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1" role="tablist" aria-label="Marketplace sections">
            {TABS.map((tab) => {
              const Icon = tab.icon
              const isActive = tab.id === activeTab
              return (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-5 py-4 text-sm font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-blue-500 text-white'
                      : 'border-transparent text-gray-400 hover:text-white hover:border-gray-600'
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div
          role="tabpanel"
          aria-labelledby="tab-datasets"
          hidden={activeTab !== 'datasets'}
        >
          <DatasetsTab />
        </div>
        <div
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
