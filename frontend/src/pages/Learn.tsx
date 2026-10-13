import { Link } from 'react-router-dom'
import { launchFlags } from '../config/launchFlags'
import SimplePage from '../components/SimplePage'

export default function Learn() {
  return (
    <SimplePage
      title="Learn"
      subtitle="Playbooks, templates, and guides for launching faster."
      actions={
        <>
          <Link to="/discover" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
            Start with an opportunity
          </Link>
          {launchFlags.services ? <Link to="/services" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">Get a report</Link> : <Link to="/pricing" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">View plans</Link>}
        </>
      }
    >
      <div className="bg-white border border-gray-200 rounded-2xl p-6 text-gray-700">
        Placeholder page. Next we can add the phased roadmap content and learning tracks.
      </div>
    </SimplePage>
  )
}

