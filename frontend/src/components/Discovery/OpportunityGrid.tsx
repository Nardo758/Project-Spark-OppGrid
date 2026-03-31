/**
 * OpportunityGrid Component
 * 
 * Container for displaying opportunities in grid or list view.
 * Includes view toggle and handles loading states.
 * 
 * Features:
 * - Grid/List view toggle
 * - Responsive layout
 * - Loading skeletons
 * - Empty state
 * - Staggered animations
 * 
 * @component
 */

import React from 'react';
import { Opportunity, ViewMode, UserTier } from './types';
import OpportunityCard from './OpportunityCard';
import OpportunityCardSkeleton from './OpportunityCardSkeleton';

interface OpportunityGridProps {
  opportunities: Opportunity[];
  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;
  isLoading?: boolean;
  userTier?: UserTier;
  onValidate?: (id: number) => void;
  onSave?: (id: number) => void;
  onAnalyze?: (id: number) => void;
  onShare?: (id: number) => void;
  validatedIds?: number[];
  savedIds?: number[];
  emptyMessage?: string;
  /** Show 4 P's market intelligence indicator on cards */
  showFourPs?: boolean;
}

export const OpportunityGrid: React.FC<OpportunityGridProps> = ({
  opportunities,
  viewMode = 'grid',
  onViewModeChange,
  isLoading = false,
  userTier = 'free',
  onValidate,
  onSave,
  onAnalyze,
  onShare,
  validatedIds = [],
  savedIds = [],
  emptyMessage = 'No opportunities found. Be the first to submit one!',
  showFourPs = false,
}) => {
  const renderViewToggle = () => {
    if (!onViewModeChange) return null;

    return (
      <div className="flex items-center gap-2 bg-white border border-stone-200 rounded-lg p-1">
        <button
          onClick={() => onViewModeChange('grid')}
          className={`p-2 rounded transition-colors ${
            viewMode === 'grid'
              ? 'bg-stone-900 text-white'
              : 'text-stone-600 hover:bg-stone-100'
          }`}
          title="Grid view"
          aria-label="Grid view"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
        </button>
        <button
          onClick={() => onViewModeChange('list')}
          className={`p-2 rounded transition-colors ${
            viewMode === 'list'
              ? 'bg-stone-900 text-white'
              : 'text-stone-600 hover:bg-stone-100'
          }`}
          title="List view"
          aria-label="List view"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="8" y1="6" x2="21" y2="6"/>
            <line x1="8" y1="12" x2="21" y2="12"/>
            <line x1="8" y1="18" x2="21" y2="18"/>
            <line x1="3" y1="6" x2="3.01" y2="6"/>
            <line x1="3" y1="12" x2="3.01" y2="12"/>
            <line x1="3" y1="18" x2="3.01" y2="18"/>
          </svg>
        </button>
      </div>
    );
  };

  const renderResults = () => {
    // Loading state
    if (isLoading) {
      return (
        <div className={`grid gap-4 ${viewMode === 'list' ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'}`}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <OpportunityCardSkeleton key={i} />
          ))}
        </div>
      );
    }

    // Empty state
    if (opportunities.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="mb-4">
            <svg
              className="w-16 h-16 mx-auto text-stone-300"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.3-4.3"/>
            </svg>
          </div>
          <p className="text-stone-500 text-lg">{emptyMessage}</p>
          <a
            href="/idea-generator.html"
            className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-stone-900 text-white rounded-lg font-medium hover:bg-stone-800 transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
            </svg>
            Generate an Idea
          </a>
        </div>
      );
    }

    // Opportunities grid
    return (
      <div
        className={`grid gap-4 ${
          viewMode === 'list' ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'
        }`}
      >
        {opportunities.map((opportunity, index) => (
          <div
            key={opportunity.id}
            className="animate-fadeIn"
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <OpportunityCard
              opportunity={opportunity}
              userTier={userTier}
              onValidate={onValidate}
              onSave={onSave}
              onAnalyze={onAnalyze}
              onShare={onShare}
              isValidated={validatedIds.includes(opportunity.id)}
              isSaved={savedIds.includes(opportunity.id)}
              showFourPs={showFourPs}
            />
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="opportunity-grid-container">
      {/* Header with view toggle */}
      <div className="flex items-center justify-between mb-6">
        <div className="text-sm text-stone-600">
          Showing <strong className="text-stone-900">{opportunities.length}</strong>{' '}
          {opportunities.length === 1 ? 'opportunity' : 'opportunities'}
        </div>
        {renderViewToggle()}
      </div>

      {/* Results */}
      {renderResults()}

    </div>
  );
};

export default OpportunityGrid;
