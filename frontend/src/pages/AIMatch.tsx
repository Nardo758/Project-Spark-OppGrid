import { Link } from 'react-router-dom'
import { launchFlags } from '../config/launchFlags'
import SimplePage from '../components/SimplePage'

export default function AIMatch() {
  return (
    <SimplePage
      title="AI Expert Match"
      subtitle="Get matched with the right experts for your opportunity and stage."
      actions={
        <>
          <Link to="/network" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
            Browse network
          </Link>
          {launchFlags.services ? <Link to="/services" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">Services</Link> : <Link to="/pricing" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">View plans</Link>}
        </>
      }
    >
      <div className="bg-white border border-gray-200 rounded-2xl p-6 text-gray-700">
        Placeholder page. Next we can add intake questions + matching results.
      </div>
    </SimplePage>
  )
}

