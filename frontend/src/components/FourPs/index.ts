/**
 * 4 P's Components
 * 
 * Market intelligence visualization powered by the ReportDataService 4 P's framework.
 * 
 * Components:
 * - FourPsIndicator: Mini 4-bar indicator for cards (lightweight)
 * - FourPsPanel: Full expandable panel for detail pages (comprehensive)
 * - WorkspaceIntelligence: Smart task suggestions for workspaces
 * 
 * Usage:
 * ```tsx
 * import { FourPsIndicator, FourPsPanel, WorkspaceIntelligence } from '@/components/FourPs'
 * 
 * // In cards
 * <FourPsIndicator scores={{ product: 85, price: 62, place: 78, promotion: 71 }} />
 * 
 * // In detail pages
 * <FourPsPanel opportunityId={123} showQuality={true} />
 * 
 * // In workspaces
 * <WorkspaceIntelligence workspaceId={456} />
 * ```
 */

export { default as FourPsIndicator, useFourPsMini } from './FourPsIndicator'
export { default as FourPsPanel } from './FourPsPanel'
export { default as WorkspaceIntelligence } from './WorkspaceIntelligence'
