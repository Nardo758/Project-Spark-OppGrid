"""
Identify Location Report Generator
Creates professional PDF reports for location identification analysis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, Image as RLImage, KeepTogether

from .report_generator import ReportGenerator
from .map_snippet_generator import MapSnippetGenerator
from .comparison_table_generator import ComparisonTableGenerator

logger = logging.getLogger(__name__)


class IdentifyLocationReportGenerator(ReportGenerator):
    """Generate professional PDF reports for Identify Location analysis"""

    def __init__(
        self,
        identify_location_result: Dict[str, Any],
        request_id: str,
    ):
        """
        Initialize Identify Location report generator
        
        Args:
            identify_location_result: IdentifyLocationResponse object
            request_id: Unique request identifier
        """
        super().__init__(
            title="Location Identification Report",
            request_id=request_id,
            page_size="letter",
        )
        
        self.result = identify_location_result
        self.map_generator = MapSnippetGenerator()
        self.city = identify_location_result.get('city', 'Unknown')
        self.business_description = identify_location_result.get('business_description', '')
        self.category = identify_location_result.get('inferred_category', 'Uncategorized')
        
        # Extract candidates from result
        self.candidates = self._extract_candidates()
        self.candidates_by_archetype = self._group_by_archetype()
    
    def _extract_candidates(self) -> List[Dict[str, Any]]:
        """Extract and normalize candidate data from result"""
        candidates = []
        
        # Get site recommendations
        site_recs = self.result.get('site_recommendations', [])
        if site_recs:
            candidates.extend(site_recs)
        
        # Get micro markets
        micro_markets = self.result.get('micro_markets', [])
        if micro_markets:
            # Enrich micro market data
            for market in micro_markets:
                candidate = {
                    'name': market.get('name', 'Unnamed Market'),
                    'archetype': market.get('archetype', 'General'),
                    'score': market.get('fit_score', 0),
                    'population': market.get('population'),
                    'median_income': market.get('median_income'),
                    'competition_count': market.get('competitor_count', 0),
                    'demand_signal': market.get('demand_pct', 0),
                    'avg_rent': market.get('avg_rent'),
                    'risk_level': self._assess_risk_level(market),
                    'risk_factors': market.get('risk_factors', []),
                    'demographics': market.get('demographics'),
                    'strengths': market.get('strengths', []),
                    'lat': market.get('lat'),
                    'lng': market.get('lng'),
                }
                candidates.append(candidate)
        
        # Sort by score descending
        candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
        return candidates
    
    def _group_by_archetype(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group candidates by archetype"""
        grouped = {}
        
        for candidate in self.candidates:
            archetype = candidate.get('archetype', 'Other')
            if archetype not in grouped:
                grouped[archetype] = []
            grouped[archetype].append(candidate)
        
        return grouped
    
    def _assess_risk_level(self, location: Dict[str, Any]) -> str:
        """Assess risk level based on location metrics"""
        competition = location.get('competitor_count', 0)
        demand = location.get('demand_pct', 0)
        
        # Simple risk calculation
        if competition > 20 and demand < 30:
            return 'high'
        elif competition > 10 and demand < 50:
            return 'medium'
        else:
            return 'low'
    
    def build(self) -> None:
        """Build the complete report"""
        # Executive Summary Section
        self._build_executive_summary_section()
        self._add_page_break()
        
        # Market Overview Section
        self._build_market_overview_section()
        self._add_page_break()
        
        # Candidates by Archetype Section
        self._build_candidates_section()
        self._add_page_break()
        
        # Comparison Table
        self._build_comparison_section()
        self._add_page_break()
        
        # Investment Thesis Section
        self._build_investment_thesis_section()
        self._add_page_break()
        
        # Appendix
        self._build_appendix_section()
    
    def _build_executive_summary_section(self) -> None:
        """Build executive summary section"""
        summary_text = f"""
        <b>Market:</b> {self.city}, {self.category} Industry<br/>
        <b>Analysis Focus:</b> {self.business_description}<br/>
        <b>Report Generated:</b> {self.timestamp.strftime('%B %d, %Y')}<br/>
        <br/>
        This report identifies optimal locations for {self.business_description} in {self.city}.
        The analysis evaluated {len(self.candidates)} candidate locations across demographic, 
        competitive, and demand-based metrics. Each location is ranked by fit score and 
        includes risk assessment and investment recommendations.
        """
        
        key_findings = [
            f"Analyzed {len(self.candidates)} candidate locations",
            f"Identified {len(self.candidates_by_archetype)} distinct location archetypes",
            f"Top candidate: {self.candidates[0].get('name', 'Unknown') if self.candidates else 'N/A'} "
            f"(Score: {self.candidates[0].get('score', 0) if self.candidates else 0}/100)",
        ]
        
        # Add category-specific insights
        micro_markets = self.result.get('micro_markets', [])
        if micro_markets:
            key_findings.append(
                f"Identified {len(micro_markets)} micro-markets with strong demand signals"
            )
        
        metrics = {
            'Candidates Analyzed': len(self.candidates),
            'Location Archetypes': len(self.candidates_by_archetype),
            'Avg. Fit Score': f"{sum(c.get('score', 0) for c in self.candidates) / len(self.candidates) if self.candidates else 0:.0f}/100",
        }
        
        self._add_executive_summary(summary_text, key_findings, metrics)
    
    def _build_market_overview_section(self) -> None:
        """Build market overview section"""
        self.elements.append(Paragraph("Market Overview", self.styles['CustomHeading2']))
        
        # Geographic and demographic context
        geo_analysis = self.result.get('geo_analysis', {})
        market_report = self.result.get('market_report', {})
        
        overview_text = f"""
        <b>{self.city} Market Analysis</b><br/>
        {market_report.get('summary', 'Market analysis in progress...')}<br/>
        <br/>
        <b>Geographic Context:</b><br/>
        {geo_analysis.get('description', 'Geographic data unavailable')}
        """
        
        self.elements.append(Paragraph(overview_text, self.styles['CustomBody']))
        self.elements.append(Spacer(1, 0.2*inch))
        
        # Category analysis
        self.elements.append(Paragraph("Category Analysis", self.styles['CustomHeading3']))
        
        category_text = f"""
        <b>Inferred Category:</b> {self.category}<br/>
        <b>Business Type:</b> {self.business_description}<br/>
        <b>Market Opportunity:</b> Location-dependent retail/service operation<br/>
        <b>Key Success Factors:</b> Demographics, foot traffic, competition density, rent affordability
        """
        
        self.elements.append(Paragraph(category_text, self.styles['CustomBody']))
    
    def _build_candidates_section(self) -> None:
        """Build candidates by archetype section"""
        self.elements.append(Paragraph("Candidate Locations", self.styles['CustomHeading2']))
        
        # Summary of archetypes
        if self.candidates_by_archetype:
            archetype_summary = ComparisonTableGenerator.build_archetype_summary(
                self.candidates_by_archetype
            )
            
            summary_text = "<b>Location Archetypes Found:</b><br/>"
            for archetype, count, avg_score in archetype_summary:
                summary_text += f"• <b>{archetype}</b>: {count} location(s), Avg Score {avg_score:.0f}/100<br/>"
            
            self.elements.append(Paragraph(summary_text, self.styles['CustomBody']))
            self.elements.append(Spacer(1, 0.15*inch))
        
        # Show top 5 candidates with detail
        for idx, candidate in enumerate(self.candidates[:5], 1):
            self._build_candidate_card(candidate, idx)
            self.elements.append(Spacer(1, 0.15*inch))
            
            # Add page break after every 2 candidates to maintain readability
            if idx % 2 == 0 and idx < len(self.candidates[:5]):
                self._add_page_break()
    
    def _build_candidate_card(self, candidate: Dict[str, Any], rank: int) -> None:
        """Build individual candidate card"""
        name = candidate.get('name', 'Unknown')
        score = candidate.get('score', 0)
        archetype = candidate.get('archetype', 'General')
        
        # Header with score
        card_header = f"""
        <b>#{rank}: {name}</b><br/>
        <font size=9>Archetype: {archetype} | Fit Score: <font color='#0066CC'>{score}/100</font></font>
        """
        self.elements.append(Paragraph(card_header, self.styles['CustomHeading3']))
        
        # Key metrics
        metrics = {
            'Population': candidate.get('population', 'N/A'),
            'Median Income': f"${candidate.get('median_income', 0):,}" if candidate.get('median_income') else 'N/A',
            'Competitors': candidate.get('competition_count', 0),
            'Demand Signal': f"{candidate.get('demand_signal', 0):.0f}%",
            'Avg Rent': f"${candidate.get('avg_rent', 0):,}" if candidate.get('avg_rent') else 'N/A',
        }
        
        self._add_metrics_grid(metrics)
        self.elements.append(Spacer(1, 0.1*inch))
        
        # Risk factors
        if candidate.get('risk_factors'):
            self.elements.append(Paragraph("Risk Factors", self.styles['CustomHeading3']))
            for factor in candidate.get('risk_factors', [])[:3]:
                self._add_risk_indicator(
                    title=factor.get('title', 'Risk Factor'),
                    risk_level=factor.get('level', 'medium'),
                    description=factor.get('description', ''),
                )
        
        # Strengths
        if candidate.get('strengths'):
            self.elements.append(Spacer(1, 0.1*inch))
            self.elements.append(Paragraph("Key Strengths", self.styles['CustomHeading3']))
            strengths_text = "<br/>".join([f"✓ {s}" for s in candidate.get('strengths', [])[:3]])
            self.elements.append(Paragraph(strengths_text, self.styles['CustomBody']))
    
    def _build_comparison_section(self) -> None:
        """Build comparison table section"""
        self.elements.append(Paragraph("Location Comparison", self.styles['CustomHeading2']))
        
        headers, rows = ComparisonTableGenerator.create_identify_location_table(
            self.candidates
        )
        
        self._add_comparison_table(headers, rows)
    
    def _build_investment_thesis_section(self) -> None:
        """Build investment thesis section"""
        self.elements.append(Paragraph("Investment Thesis", self.styles['CustomHeading2']))
        
        if not self.candidates:
            self.elements.append(
                Paragraph("No candidates available for thesis.", self.styles['CustomBody'])
            )
            return
        
        top_candidate = self.candidates[0]
        
        # Rationale
        self.elements.append(Paragraph("Rationale", self.styles['CustomHeading3']))
        rationale = f"""
        <b>{top_candidate.get('name', 'Top Location')}</b> represents the optimal site for 
        {self.business_description} in {self.city}. With a fit score of {top_candidate.get('score', 0)}/100,
        this location excels in demographic alignment and demand potential. The location benefits from
        {top_candidate.get('population', 0):,} residents and demonstrates strong consumer demand
        signals ({top_candidate.get('demand_signal', 0):.0f}%).
        """
        self.elements.append(Paragraph(rationale, self.styles['CustomBody']))
        
        # Strengths
        self.elements.append(Spacer(1, 0.1*inch))
        self.elements.append(Paragraph("Strengths", self.styles['CustomHeading3']))
        
        strengths = top_candidate.get('strengths', [
            'Strong demographic fit',
            'Manageable competition',
            'High demand signals',
        ])
        
        strengths_text = "<br/>".join([f"• {s}" for s in strengths[:4]])
        self.elements.append(Paragraph(strengths_text, self.styles['CustomBody']))
        
        # Risks
        self.elements.append(Spacer(1, 0.1*inch))
        self.elements.append(Paragraph("Risks & Mitigation", self.styles['CustomHeading3']))
        
        risks = top_candidate.get('risk_factors', [])
        if risks:
            for risk in risks[:2]:
                level = risk.get('level', 'medium') if isinstance(risk, dict) else 'medium'
                desc = risk.get('description', str(risk)) if isinstance(risk, dict) else str(risk)
                self._add_risk_indicator(
                    title="Risk Factor",
                    risk_level=level,
                    description=desc,
                )
        
        # Next steps
        self.elements.append(Spacer(1, 0.1*inch))
        self.elements.append(Paragraph("Recommended Next Steps", self.styles['CustomHeading3']))
        
        next_steps = [
            "Site visit and ground truth verification",
            "Detailed lease negotiation analysis",
            "Traffic pattern validation during peak hours",
            "Competitor location and pricing benchmarking",
            "Local zoning and regulatory compliance review",
        ]
        
        next_steps_text = "<br/>".join([f"{i+1}. {step}" for i, step in enumerate(next_steps)])
        self.elements.append(Paragraph(next_steps_text, self.styles['CustomBody']))
    
    def _build_appendix_section(self) -> None:
        """Build appendix section"""
        self.elements.append(Paragraph("Appendix", self.styles['CustomHeading2']))
        
        # Methodology
        self.elements.append(Paragraph("Methodology", self.styles['CustomHeading3']))
        
        methodology = """
        <b>Candidate Selection:</b><br/>
        Candidates were identified using multi-factor analysis including demographic data,
        foot traffic patterns, competitive density, and consumer demand signals. Each location
        was scored on a 0-100 scale based on alignment with success factors for the category.<br/>
        <br/>
        <b>Scoring Methodology:</b><br/>
        • Demographics (30%): Population density, income levels, household composition<br/>
        • Competition (25%): Competitor count, market saturation, pricing analysis<br/>
        • Demand (25%): Search volume, consumer interest, market momentum<br/>
        • Logistics (20%): Rent affordability, zoning, accessibility<br/>
        <br/>
        <b>Data Sources:</b><br/>
        • U.S. Census Bureau (demographic, economic data)<br/>
        • Google Maps & Local Services (competitor data)<br/>
        • Traffic Analytics (foot traffic, demand patterns)<br/>
        • Market Research Partnerships (industry benchmarks)
        """
        
        self.elements.append(Paragraph(methodology, self.styles['CustomBody']))
        
        # Data quality
        self.elements.append(Spacer(1, 0.15*inch))
        self.elements.append(Paragraph("Data Quality", self.styles['CustomHeading3']))
        
        data_quality = self.result.get('data_quality', {})
        quality_text = f"""
        <b>Completeness:</b> {data_quality.get('completeness', 'N/A')}<br/>
        <b>Recency:</b> Data sourced within last 90 days<br/>
        <b>Coverage:</b> {len(self.candidates)} locations analyzed<br/>
        <b>Confidence Level:</b> {data_quality.get('confidence_score', 'N/A')}
        """
        
        self.elements.append(Paragraph(quality_text, self.styles['CustomBody']))
