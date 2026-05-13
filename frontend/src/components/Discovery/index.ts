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

// Enrichment sub-components (Part B of card enrichment spec)
export { default as ConfidenceTierBadge, getTierBorderClass, getTierHoverClass } from './ConfidenceTierBadge';
export { default as SourceMixIndicator } from './SourceMixIndicator';
export { default as LocationLine } from './LocationLine';
export { default as PainUrgencyRow } from './PainUrgencyRow';
export { default as MacroContextStrip } from './MacroContextStrip';
export { default as RealmTypeIcon } from './RealmTypeIcon';

export type {
  Opportunity,
  FilterState,
  PaginationState,
  ViewMode,
  UserTier,
  FreshnessBadge,
  MacroContext,
  ContributingSources,
} from './types';

export type { MarketBadge, CompositeMetrics } from './MarketBadges';
