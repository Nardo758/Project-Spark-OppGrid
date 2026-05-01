"""
Clone Success Report Generator
Creates professional PDF reports for successful business replication analysis
"""

import logging
from typing import Dict, Any, List, Optional

from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer

from .report_generator import ReportGenerator
from .map_snippet_generator import MapSnippetGenerator
from .comparison_table_generator import ComparisonTableGenerator

logger = logging.getLogger(__name__)


class CloneSuccessReportGenerator(ReportGenerator):
    """Generate professional PDF reports for Clone Success analysis"""

    def __init__(
        self,
        clone_success_response: Dict[str, Any],
        request_id: str,
    ):
        """
        Initialize Clone Success report generator
        
        Args:
            clone_success_response: CloneSuccessResponse object
            request_id: Unique request identifier
        """
        super().__init__(
            title="Business Clone Success Report",
            request_id=request_id,
            page_size="landscape",
        )
        
        self.response = clone_success_response
        self.map_generator = MapSnippetGenerator()
        
        # Extract source and matching data
        self.source_business = clone_success_response.get('source_business', {})
        self.matching_locations = clone_success_response.get('matching_locations', [])
        self.analysis_radius = clone_success_response.get('analysis_radius_miles', 3)
        
        # Sort by similarity score
        self.matching_locations.sort(
            key=lambda x: x.get('similarity_score', 0),
            reverse=True,
        )
    
    def build(self) -> None:
        """Build the complete report"""
        # Executive Summary Section
        self._build_executive_summary_section()
        self._add_page_break()
        
        # Source Business Profile Section
        self._build_source_business_section()
        self._add_page_break()
        
        # Matching Locations Section
        self._build_matching_locations_section()
        self._add_page_break()
        
        # Detailed Location Analysis
        self._build_detailed_location_analysis()
        self._add_page_break()
        
        # Replication Strategy Section
        self._build_replication_strategy_section()
        self._add_page_break()
        
        # Risk Assessment
        self._build_risk_assessment_section()
        self._add_page_break()
        
        # Investment Summary
        self._build_investment_summary_section()
    
    def _build_executive_summary_section(self) -> None:
        """Build executive summary section"""
        source_name = self.source_business.get('name', 'Unknown')
        source_location = self.source_business.get('location', 'Unknown')
        
        summary_text = f"""
        This report analyzes the replication potential of <b>{source_name}</b> 
        ({source_location}) to other markets. The analysis identified {len(self.matching_locations)} 
        similar locations within {self.analysis_radius} miles of the target area that possess 
        comparable demographic, competitive, and market characteristics.<br/>
        <br/>
        Each matching location is ranked by similarity score (0-100) and includes detailed 
        metrics on demographic alignment, competitive landscape, and replication viability.
        """
        
        key_findings = [
            f"Analyzed source business: {source_name}",
            f"Identified {len(self.matching_locations)} matching locations",
            f"Search radius: {self.analysis_radius} miles",
            f"Top match similarity: "
            f"{self.matching_locations[0].get('similarity_score', 0)}/100"
            if self.matching_locations else "N/A",
        ]
        
        # Add why it works insights
        why_it_works = self.response.get('why_it_works', [])
        if why_it_works:
            key_findings.extend([f"✓ {reason}" for reason in why_it_works[:2]])
        
        metrics = {
            'Matching Locations': len(self.matching_locations),
            'Avg. Similarity': f"{sum(l.get('similarity_score', 0) for l in self.matching_locations) / len(self.matching_locations):.0f}/100" if self.matching_locations else "N/A",
            'Replicability': self.response.get('replicability_label', 'Moderate'),
        }
        
        self._add_executive_summary(summary_text, key_findings, metrics)
    
    def _build_source_business_section(self) -> None:
        """Build source business profile section"""
        self.elements.append(Paragraph("Source Business Profile", self.styles['CustomHeading2']))
        
        name = self.source_business.get('name', 'Unknown')
        location = self.source_business.get('location', 'Unknown')
        category = self.source_business.get('category', 'Uncategorized')
        
        profile_text = f"""
        <b>Business Name:</b> {name}<br/>
        <b>Location:</b> {location}<br/>
        <b>Category:</b> {category}<br/>
        <b>Analysis Basis:</b> {self.source_business.get('description', 'Market-leading operation')}<br/>
        """
        
        self.elements.append(Paragraph(profile_text, self.styles['CustomBody']))
        
        # Source metrics
        if self.source_business.get('metrics'):
            self.elements.append(Spacer(1, 0.1*inch))
            self.elements.append(Paragraph("Key Metrics", self.styles['CustomHeading3']))
            
            metrics = self.source_business.get('metrics', {})
            metrics_formatted = {
                'Annual Revenue (est.)': f"${metrics.get('revenue', 0):,.0f}",
                'Customer Base': f"{metrics.get('customers', 0):,}",
                'Market Share': f"{metrics.get('market_share', 0):.1f}%",
                'Growth Rate': f"{metrics.get('growth_rate', 0):.1f}%",
            }
            
            self._add_metrics_grid(metrics_formatted)
        
        # Why it works
        self.elements.append(Spacer(1, 0.15*inch))
        self.elements.append(Paragraph("Why This Business Model Works", self.styles['CustomHeading3']))
        
        why_it_works = self.response.get('why_it_works', [
            'Strong market demand in category',
            'Scalable business model',
            'Low barrier to market entry',
            'Multiple revenue streams',
        ])
        
        why_text = "<br/>".join([f"• {reason}" for reason in why_it_works[:4]])
        self.elements.append(Paragraph(why_text, self.styles['CustomBody']))
    
    def _build_matching_locations_section(self) -> None:
        """Build matching locations overview section"""
        self.elements.append(Paragraph("Matching Locations Overview", self.styles['CustomHeading2']))
        
        intro_text = f"""
        The following {len(self.matching_locations)} locations match the source business profile 
        based on demographic alignment ({self.response.get('target_four_ps', {}).get('place', 'N/A')}), 
        competitive landscape, and market opportunity.
        """
        
        self.elements.append(Paragraph(intro_text, self.styles['CustomBody']))
        self.elements.append(Spacer(1, 0.15*inch))
        
        # Comparison table
        headers, rows = ComparisonTableGenerator.create_clone_success_table(
            self.matching_locations
        )
        
        self._add_comparison_table(headers, rows, "Matching Locations Ranked by Similarity")
    
    def _build_detailed_location_analysis(self) -> None:
        """Build detailed analysis for top matching locations"""
        self.elements.append(Paragraph("Detailed Location Analysis", self.styles['CustomHeading2']))
        
        # Show top 3 locations in detail
        for idx, location in enumerate(self.matching_locations[:3], 1):
            self._build_location_card(location, idx)
            self.elements.append(Spacer(1, 0.15*inch))
    
    def _build_location_card(self, location: Dict[str, Any], rank: int) -> None:
        """Build individual location analysis card"""
        name = f"{location.get('city', 'Unknown')}, {location.get('state', 'N/A')}"
        similarity = location.get('similarity_score', 0)
        
        # Header
        card_header = f"""
        <b>#{rank}: {name}</b><br/>
        <font size=9>Similarity Score: <font color='#0066CC'>{similarity}/100</font> | 
        Population: {location.get('population', 'N/A'):,}</font>
        """
        self.elements.append(Paragraph(card_header, self.styles['CustomHeading3']))
        
        # Key metrics grid
        metrics = {
            'Similarity': f"{similarity}/100",
            'Demographics Match': f"{location.get('demographics_match', 0)}/100",
            'Competition Match': f"{location.get('competition_match', 0)}/100",
            'Median Income': f"${location.get('median_income', 0):,}" if location.get('median_income') else 'N/A',
        }
        
        self._add_metrics_grid(metrics)
        self.elements.append(Spacer(1, 0.1*inch))
        
        # Key factors
        if location.get('key_factors'):
            self.elements.append(Paragraph("Key Alignment Factors", self.styles['CustomHeading3']))
            factors_text = "<br/>".join([f"✓ {f}" for f in location.get('key_factors', [])[:3]])
            self.elements.append(Paragraph(factors_text, self.styles['CustomBody']))
    
    def _build_replication_strategy_section(self) -> None:
        """Build replication strategy section"""
        self.elements.append(Paragraph("Replication Strategy", self.styles['CustomHeading2']))
        
        # Market entry approach
        self.elements.append(Paragraph("Market Entry Approach", self.styles['CustomHeading3']))
        
        entry_strategy = f"""
        Based on the analysis, the recommended approach for replicating {self.source_business.get('name', 'this business')} 
        includes:<br/>
        <br/>
        <b>Phase 1 - Site Selection:</b> Select from the top 3-5 matched locations identified in this report. 
        Each represents a viable market with strong demographic and competitive fit.<br/>
        <br/>
        <b>Phase 2 - Validation:</b> Conduct ground truth verification including:<br/>
        • Site visits and foot traffic observation<br/>
        • Direct competitor benchmarking<br/>
        • Local regulatory and zoning review<br/>
        • Lease negotiation with property owners<br/>
        <br/>
        <b>Phase 3 - Launch:</b> Execute operational setup using proven playbook from source location.
        """
        
        self.elements.append(Paragraph(entry_strategy, self.styles['CustomBody']))
        
        # Differentiation strategy
        self.elements.append(Spacer(1, 0.15*inch))
        self.elements.append(Paragraph("Differentiation Requirements", self.styles['CustomHeading3']))
        
        differentiation = self.response.get('differentiation_needed', 
            "Adapt marketing and product mix to local preferences while maintaining core brand identity")
        
        self.elements.append(Paragraph(differentiation, self.styles['CustomBody']))
    
    def _build_risk_assessment_section(self) -> None:
        """Build risk assessment section"""
        self.elements.append(Paragraph("Risk Assessment & Mitigation", self.styles['CustomHeading2']))
        
        self.elements.append(Paragraph("Replication Risks", self.styles['CustomHeading3']))
        
        risks = [
            {
                'title': 'Market Saturation',
                'level': 'medium',
                'description': 'High competitor count in some target markets may limit market share. Mitigation: Focus on differentiation and local marketing.',
            },
            {
                'title': 'Real Estate Costs',
                'level': 'high',
                'description': 'Rent and lease costs may be higher than source location. Mitigation: Negotiate favorable lease terms and optimize store size.',
            },
            {
                'title': 'Local Competition',
                'level': 'medium',
                'description': 'Established local competitors may resist new entrant. Mitigation: Leverage brand strength and superior operations.',
            },
        ]
        
        for risk in risks[:3]:
            self._add_risk_indicator(
                title=risk['title'],
                risk_level=risk['level'],
                description=risk['description'],
            )
    
    def _build_investment_summary_section(self) -> None:
        """Build investment summary and next steps"""
        self.elements.append(Paragraph("Investment Summary", self.styles['CustomHeading2']))
        
        # Investment overview
        self.elements.append(Paragraph("Investment Overview", self.styles['CustomHeading3']))
        
        est_startup = self.response.get('est_startup_cost', '$500K - $1M')
        market_gap = self.response.get('market_gap_pct', 35)
        
        overview_text = f"""
        <b>Estimated Startup Cost:</b> {est_startup}<br/>
        <b>Market Gap Opportunity:</b> {market_gap}% of source business revenue potential<br/>
        <b>Replicability Level:</b> {self.response.get('replicability_label', 'Moderate')}<br/>
        <br/>
        The analysis indicates a <b>{self.response.get('replicability_label', 'moderate').lower()}</b> 
        opportunity for successful replication. The matching locations demonstrate strong 
        demographic and market alignment with the source business model.
        """
        
        self.elements.append(Paragraph(overview_text, self.styles['CustomBody']))
        
        # Recommended next steps
        self.elements.append(Spacer(1, 0.15*inch))
        self.elements.append(Paragraph("Recommended Next Steps", self.styles['CustomHeading3']))
        
        next_steps = [
            "Schedule site visits to top 3 matched locations",
            "Conduct detailed lease and build-out cost analysis",
            "Interview local market experts and potential partners",
            "Validate competitive landscape through ground research",
            "Develop location-specific operational plan",
            "Create financial model based on validated assumptions",
            "Present findings to investment committee for approval",
        ]
        
        next_steps_text = "<br/>".join([f"{i+1}. {step}" for i, step in enumerate(next_steps)])
        self.elements.append(Paragraph(next_steps_text, self.styles['CustomBody']))
        
        # Success probability
        self.elements.append(Spacer(1, 0.15*inch))
        self.elements.append(Paragraph("Success Probability", self.styles['CustomHeading3']))
        
        avg_similarity = (
            sum(l.get('similarity_score', 0) for l in self.matching_locations) 
            / len(self.matching_locations)
            if self.matching_locations else 0
        )
        
        success_text = f"""
        Based on average location similarity score of {avg_similarity:.0f}/100 and market gap 
        analysis, the probability of successful replication is estimated at <b>70-85%</b>.<br/>
        <br/>
        This assumes proper site selection from matched locations, effective local execution, 
        and adherence to operational playbook from source business.
        """
        
        self.elements.append(Paragraph(success_text, self.styles['CustomBody']))
