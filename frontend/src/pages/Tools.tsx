import { Link } from 'react-router-dom'
import SimplePage from '../components/SimplePage'

export default function Tools() {
  return (
    <SimplePage
      title="Tools"
      subtitle="Quick utilities to move from opportunity to execution."
      actions={
        <>
          <Link to="/idea-engine" className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 font-medium">
            Validate an idea
          </Link>
          <Link to="/services" className="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 font-medium">
            Browse services
          </Link>
        </>
      }
    >
      <div className="bg-white border border-gray-200 rounded-2xl p-6 text-gray-700">
        Placeholder page. We can add integrations (Upwork, LegalZoom, templates) here.
      </div>
    </SimplePage>
  )
}

