import { useState } from 'react'
import { Star, Heart, ChevronDown } from 'lucide-react'
import { useSaveOpportunity, useSavedStatus, useCollections } from '../hooks/useSavedOpportunities'
import { useAuthStore } from '../stores/authStore'

interface SaveOpportunityButtonProps {
  opportunityId: number
  compact?: boolean
}

export default function SaveOpportunityButton({
  opportunityId,
  compact = false,
}: SaveOpportunityButtonProps) {
  const { token } = useAuthStore()
  const [showDropdown, setShowDropdown] = useState(false)
  const [priority, setPriority] = useState(3) // 1-5 stars
  const { isSaved, priority: savedPriority } = useSavedStatus(opportunityId)
  const { mutate: saveOpportunity, isPending } = useSaveOpportunity()
  const { collections } = useCollections()

  const currentPriority = isSaved ? (savedPriority || 3) : priority

  const handleSave = (newPriority: number) => {
    saveOpportunity({ opportunityId, priority: newPriority })
    setShowDropdown(false)
  }

  if (!token) {
    return null // Don't show for unauthenticated users
  }

  if (compact) {
    return (
      <div className="relative inline-block">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className={`inline-flex items-center gap-1 px-2 py-1 rounded text-sm transition-colors ${
            isSaved
              ? 'bg-red-50 text-red-600 hover:bg-red-100'
              : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
          }`}
        >
          <Heart className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
          {isSaved && <span className="text-xs">{currentPriority}★</span>}
        </button>

        {showDropdown && (
          <div className="absolute top-full right-0 mt-2 bg-white border border-stone-200 rounded-lg shadow-lg z-10 p-3 w-48">
            <p className="text-xs font-medium text-stone-600 mb-2">Priority (1-5 stars)</p>
            <div className="flex gap-1 mb-3">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleSave(star)}
                  disabled={isPending}
                  className={`px-2 py-1 rounded text-sm transition-colors ${
                    currentPriority >= star
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-stone-100 text-stone-400 hover:bg-stone-200'
                  }`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border transition-all ${
          isSaved
            ? 'bg-red-50 border-red-200 text-red-900 hover:bg-red-100'
            : 'bg-white border-stone-200 text-stone-900 hover:bg-stone-50'
        }`}
      >
        <div className="flex items-center gap-2">
          <Heart className={`w-5 h-5 ${isSaved ? 'fill-current' : ''}`} />
          <span className="font-semibold">{isSaved ? 'Saved' : 'Save'}</span>
        </div>

        {isSaved && (
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <Star
                key={star}
                className={`w-4 h-4 ${
                  currentPriority >= star ? 'fill-amber-400 text-amber-400' : 'text-stone-300'
                }`}
              />
            ))}
          </div>
        )}

        {!isSaved && <ChevronDown className={`w-5 h-5 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />}
      </button>

      {showDropdown && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-stone-200 rounded-lg shadow-lg z-10 p-4">
          <div className="mb-4">
            <p className="text-sm font-semibold text-stone-900 mb-3">Priority (1-5 stars)</p>
            <div className="grid grid-cols-5 gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleSave(star)}
                  disabled={isPending}
                  className={`py-2 rounded-lg text-lg transition-colors font-semibold ${
                    currentPriority >= star
                      ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                      : 'bg-stone-100 text-stone-400 hover:bg-stone-200'
                  } disabled:opacity-50`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>

          {collections.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-stone-900 mb-2">Add to Collection</p>
              <div className="space-y-1">
                {collections.slice(0, 3).map((collection) => (
                  <button
                    key={collection.id}
                    className="w-full text-left px-2 py-1 text-sm rounded hover:bg-stone-100 text-stone-700"
                  >
                    <span
                      className="inline-block w-3 h-3 rounded-full mr-2"
                      style={{ backgroundColor: collection.color }}
                    />
                    {collection.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
