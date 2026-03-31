/**
 * 4 P's Components
 * 
 * Market intelligence visualization powered by the ReportDataService 4 P's framework.
 * 
 * Components:
 * - FourPsIndicator: Mini 4-bar indicator for cards (lightweight)
 * - FourPsPanel: Full expandable panel for detail pages (comprehensive)
 * 
 * Usage:
 * ```tsx
 * import { FourPsIndicator, FourPsPanel } from '@/components/FourPs'
 * 
 * // In cards
 * <FourPsIndicator scores={{ product: 85, price: 62, place: 78, promotion: 71 }} />
 * 
 * // In detail pages
 * <FourPsPanel opportunityId={123} showQuality={true} />
 * ```
 */

export { default as FourPsIndicator, useFourPsMini } from './FourPsIndicator'
export { default as FourPsPanel } from './FourPsPanel'
