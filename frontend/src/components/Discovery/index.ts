/**
 * Discovery Feed Components
 * 
 * Export all Discovery Feed components and types
 */

export { default as OpportunityCard } from './OpportunityCard';
export { default as OpportunityCardSkeleton } from './OpportunityCardSkeleton';
export { default as OpportunityGrid } from './OpportunityGrid';
export { default as FilterBar } from './FilterBar';
export { default as Pagination } from './Pagination';
export { default as MarketBadges, computeBadges } from './MarketBadges';

export type {
  Opportunity,
  FilterState,
  PaginationState,
  ViewMode,
  UserTier,
  FreshnessBadge,
} from './types';

export type { MarketBadge, CompositeMetrics } from './MarketBadges';
