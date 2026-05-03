/**
 * DiscoveryFeed Components - Unified Exports
 * Combines components from Discovery/ and DiscoveryFeed/ directories
 */

// Core Discovery Components
export { default as OpportunityCard } from '../Discovery/OpportunityCard'
export { default as OpportunityGrid } from '../Discovery/OpportunityGrid'
export { default as FilterBar } from '../Discovery/FilterBar'
export { default as Pagination } from '../Discovery/Pagination'
export { default as OpportunityCardSkeleton } from '../Discovery/OpportunityCardSkeleton'

// Personalization Components  
export { default as RecommendedSection } from './RecommendedSection'
export { default as MatchScoreBadge } from './MatchScoreBadge'
export { default as SocialProof } from './SocialProof'

// Comparison & Actions
export { default as QuickActions } from './QuickActions'
export { default as ComparisonPanel } from './ComparisonPanel'
export { default as ComparisonModal } from './ComparisonModal'
export { default as SavedSearchModal } from './SavedSearchModal'

// Types
export type * from './types'
