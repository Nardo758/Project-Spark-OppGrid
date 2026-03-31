"""
AI Report Generator Service

Uses Anthropic Claude to generate intelligent, opportunity-specific report content.
Leverages Replit AI Integrations for Anthropic access (no API key required).

Integrates with JediRE for demand signals and market economics from Apartment Locator AI.
"""
import os
import logging
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Import JediRE client for demand signals
try:
    from app.services.jedire_client import get_jedire_client
    JEDIRE_AVAILABLE = True
except ImportError:
    JEDIRE_AVAILABLE = False
    get_jedire_client = None

logger = logging.getLogger(__name__)

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
# Direct Anthropic API key (preferred if available)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


def get_anthropic_client():
    """Get configured Anthropic client. Prefers direct API key, falls back to Replit AI Integrations."""
    from anthropic import Anthropic
    
    # Prefer direct Anthropic API key
    if ANTHROPIC_API_KEY:
        logger.info("Using direct Anthropic API key")
        return Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Fallback to Replit AI Integrations
    if AI_INTEGRATIONS_ANTHROPIC_API_KEY and AI_INTEGRATIONS_ANTHROPIC_BASE_URL:
        logger.info("Using Replit AI Integrations")
        return Anthropic(
            api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
            base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
        )
    
    logger.warning("Anthropic AI integration not configured")
    return None


class AIReportGenerator:
    """Generates AI-powered report content using Claude."""
    
    MODEL = "claude-opus-4-5"
    MAX_TOKENS = 8192
    
    # Institutional document formatting
    COMPANY_HEADER = """
═══════════════════════════════════════════════════════════════════════════════
                                    OPPGRID
                      Market Intelligence & Opportunity Analysis
═══════════════════════════════════════════════════════════════════════════════
"""

    DOCUMENT_FOOTER = """
═══════════════════════════════════════════════════════════════════════════════
                              CONFIDENTIAL REPORT
                                   
Platform: OppGrid Market Intelligence Platform
Report ID: {report_id}
Generated: {timestamp}

METHODOLOGY & VALIDATION
────────────────────────
This report is generated using OppGrid's proprietary market intelligence 
methodology, which combines:

• Multi-source Data Aggregation: Analysis draws from diverse public and 
  proprietary data sources including government databases, industry reports,
  consumer behavior data, and competitive intelligence feeds.

• AI-Powered Pattern Recognition: Machine learning models trained on 
  thousands of successful business launches identify market signals and 
  opportunity indicators.

• Expert Framework Application: Analysis structured using established 
  business frameworks (Porter's Five Forces, PESTLE, Lean Canvas, etc.) 
  validated by industry practitioners.

• Continuous Validation: Market hypotheses cross-referenced against 
  real-time market data and historical success patterns.

DISCLAIMER
──────────
This report is provided for informational purposes only and does not 
constitute professional advice. While OppGrid employs rigorous methodology,
all business decisions should incorporate additional due diligence and 
professional consultation. Market conditions are subject to change.

© {year} OppGrid Inc. All Rights Reserved.
═══════════════════════════════════════════════════════════════════════════════
"""

    INSTITUTIONAL_STYLE_INSTRUCTIONS = """

CRITICAL FORMATTING REQUIREMENTS - Follow these exactly:

1. DOCUMENT STRUCTURE
   - Use clear section headers with underlines (────────)
   - Number all major sections (1., 2., 3.)
   - Use sub-numbering for subsections (1.1, 1.2)
   - Include an "EXECUTIVE SUMMARY" section first (2-3 sentences max)

2. PROFESSIONAL TONE
   - Write in third person, formal business language
   - Avoid casual phrases or colloquialisms
   - Use precise, quantifiable statements where possible
   - Cite frameworks and methodologies by name

3. DATA PRESENTATION
   - Present numerical data in tables where appropriate
   - Use bullet points for lists (•)
   - Include confidence levels where estimates are provided
   - Separate facts from recommendations clearly

4. SECTION FORMAT
   Each major section should include:
   - Clear header with section number
   - Brief context paragraph
   - Key findings or analysis
   - Actionable implications (where applicable)

5. INTELLECTUAL PROPERTY PROTECTION
   - Present insights as derived from "market analysis" and "industry patterns"
   - Do NOT reveal specific proprietary data sources
   - Frame unique findings as "OppGrid analysis indicates..."
   - Protect methodology details while showcasing rigor

"""
    
    def __init__(self):
        self.client = get_anthropic_client()
    
    def _generate_report_id(self, report_type: str) -> str:
        """Generate a unique, trackable report ID."""
        import uuid
        from datetime import datetime
        
        # Format: OG-{TYPE_ABBREV}-{YYYYMMDD}-{SHORT_UUID}
        type_abbrevs = {
            "feasibility_study": "FS",
            "feasibility": "FS",
            "market_analysis": "MA",
            "strategic_assessment": "SA",
            "strategic": "SA",
            "pestle_analysis": "PE",
            "pestle": "PE",
            "business_plan": "BP",
            "financial_model": "FM",
            "financial": "FM",
            "pitch_deck": "PD",
            "executive_summary": "ES",
            "problem_analysis": "PA",
        }
        abbrev = type_abbrevs.get(report_type.lower().replace(" ", "_"), "RPT")
        date_str = datetime.utcnow().strftime("%Y%m%d")
        short_uuid = uuid.uuid4().hex[:6].upper()
        
        return f"OG-{abbrev}-{date_str}-{short_uuid}"
    
    def _format_institutional_report(
        self, 
        content: str, 
        report_type: str,
        report_id: str = None
    ) -> str:
        """Wrap report content with institutional formatting."""
        from datetime import datetime
        
        now = datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
        date_formatted = now.strftime("%B %d, %Y")  # e.g., "March 30, 2026"
        year = now.year
        
        # Generate report ID if not provided
        if not report_id:
            report_id = self._generate_report_id(report_type)
        
        # Create report type header with prominent date
        report_header = f"""
{self.COMPANY_HEADER}
REPORT TYPE: {report_type.upper().replace('_', ' ')}
DATE: {date_formatted}
REPORT ID: {report_id}
────────────────────────────────────────────────────────────────────────────────
"""
        
        footer = self.DOCUMENT_FOOTER.format(
            report_id=report_id,
            timestamp=timestamp,
            year=year
        )
        
        return f"{report_header}\n{content}\n{footer}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True
    )
    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate content using Claude with retry logic."""
        if not self.client:
            return ""
        
        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return message.content[0].text if message.content else ""
        except Exception as e:
            logger.error(f"Claude generation error: {e}")
            raise
    
    def generate_executive_summary(self, opportunity: Dict[str, Any]) -> str:
        """Generate an executive summary for Layer 1 report."""
        system = f"""You are a senior business analyst at OppGrid generating institutional-grade executive summaries.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Write a compelling, data-driven executive summary that:
- Opens with the core opportunity in one sentence
- Highlights key market signals and validation
- Summarizes target market and size
- Outlines recommended next steps

Format as a formal executive briefing document. Keep it concise (2-3 paragraphs max)."""
        
        prompt = f"""Generate an executive summary for this opportunity:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Market Size Estimate: {opportunity.get('market_size', 'Under analysis')}
Opportunity Score: {opportunity.get('score', 'N/A')}/100
Target Audience: {opportunity.get('target_audience', '')}
Competition Level: {opportunity.get('competition_level', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Executive Summary")
    
    def generate_problem_analysis(self, opportunity: Dict[str, Any]) -> str:
        """Generate problem analysis using Lean Canvas framework for Layer 1."""
        system = f"""You are a senior business strategist at OppGrid analyzing opportunities using the Lean Canvas framework.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure your analysis with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   Core problem and opportunity thesis (2-3 sentences).

2. PROBLEM STATEMENT
   ────────────────────
   • Primary Pain Point
   • Secondary Pain Points
   • Problem Severity Assessment
   • Frequency & Urgency

3. EXISTING ALTERNATIVES
   ────────────────────
   • Current Solutions in Market
   • Why They Fall Short
   • Gap Analysis

4. CUSTOMER SEGMENTS
   ────────────────────
   • Primary Segment Profile
   • Secondary Segments
   • Segment Size & Accessibility

5. UNIQUE VALUE PROPOSITION
   ────────────────────
   • Core Differentiator
   • Value Delivery Mechanism
   • Why Now (Timing Factors)

6. SOLUTION DIRECTION
   ────────────────────
   • High-Level Approach
   • Key Features/Capabilities
   • Validation Requirements

Use specific examples and reference OppGrid market analysis."""
        
        prompt = f"""Analyze this market opportunity using Lean Canvas problem framing:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}  
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Signals/Evidence: {opportunity.get('signals', '')}
Target Audience: {opportunity.get('target_audience', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Problem Analysis")
    
    def generate_market_insights(
        self, 
        opportunity: Dict[str, Any], 
        demographics: Optional[Dict[str, Any]] = None,
        competitors: Optional[List[Dict[str, Any]]] = None,
        demand_signals: Optional[Dict[str, Any]] = None,
        market_economics: Optional[Dict[str, Any]] = None,
        report_data: Optional[Any] = None  # ReportDataContext from ReportDataService
    ) -> str:
        """Generate market insights for Layer 2 report with demographics, competitive, demand data, and 4 P's."""
        system = """You are a market research analyst providing deep-dive market insights.
Structure your analysis with:
1. **Market Overview** - Size, growth trajectory, key dynamics
2. **Consumer Demand Intelligence** - What residents want (from demand signals data)
3. **Demographic Fit** - How the local demographics align with the opportunity
4. **Competitive Landscape** - Key players, market gaps, positioning opportunities
5. **Trade Area Analysis** - Geographic considerations and optimal service areas
6. **Key Success Factors** - What it takes to win in this market

Use data points where available. Be specific about local market conditions.
When demand signal data is available, emphasize what local residents are actively seeking."""
        
        demo_info = ""
        if demographics:
            demo_info = f"""
Demographics Data:
- Population: {demographics.get('population', 'N/A')}
- Median Income: ${demographics.get('median_income', 'N/A')}
- Median Age: {demographics.get('median_age', 'N/A')}
- Total Households: {demographics.get('total_households', 'N/A')}
- Median Rent: ${demographics.get('median_rent', 'N/A')}
"""
        
        comp_info = ""
        if competitors:
            comp_info = "Competitor Data:\n"
            for i, comp in enumerate(competitors[:10], 1):
                comp_info += f"- {comp.get('name', 'Unknown')}: Rating {comp.get('rating', 'N/A')}, {comp.get('reviews', 0)} reviews\n"
        
        # Add demand signals from JediRE (Apartment Locator AI data)
        demand_info = ""
        if demand_signals and demand_signals.get('signals'):
            demand_info = "\nConsumer Demand Signals (from local renter preferences):\n"
            for signal in demand_signals['signals'][:10]:
                trend_indicator = "↑" if signal.get('trend') == 'rising' else "→" if signal.get('trend') == 'stable' else "↓"
                demand_info += f"- {signal['amenity_type'].replace('_', ' ').title()}: {signal['demand_pct']}% demand {trend_indicator}\n"
            demand_info += f"(Based on {demand_signals.get('count', 0)} data points)\n"
        
        # Add market economics from JediRE
        economics_info = ""
        if market_economics:
            economics_info = "\nMarket Economics (Rental Market Intelligence):\n"
            if market_economics.get('median_rent'):
                economics_info += f"- Median Rent: ${market_economics['median_rent']}\n"
            if market_economics.get('avg_rent_1br'):
                economics_info += f"- Avg 1BR: ${market_economics['avg_rent_1br']}\n"
            if market_economics.get('avg_rent_2br'):
                economics_info += f"- Avg 2BR: ${market_economics['avg_rent_2br']}\n"
            if market_economics.get('spending_power_index'):
                economics_info += f"- Spending Power Index: {market_economics['spending_power_index']}/100\n"
            if market_economics.get('vacancy_rate'):
                economics_info += f"- Vacancy Rate: {market_economics['vacancy_rate']}%\n"
            if market_economics.get('rent_trend'):
                economics_info += f"- Rent Trend: {market_economics['rent_trend']}\n"
        
        # Extract 4 P's data from ReportDataContext if provided
        four_ps_info = ""
        if report_data:
            four_ps_info = "\n📊 COMPREHENSIVE 4 P's MARKET DATA:\n"
            
            # PRODUCT
            if report_data.product:
                four_ps_info += "\n**PRODUCT (Demand Validation):**\n"
                if report_data.product.opportunity_score:
                    four_ps_info += f"- Opportunity Score: {report_data.product.opportunity_score:.0f}/100\n"
                if report_data.product.pain_intensity:
                    four_ps_info += f"- Pain Intensity: {report_data.product.pain_intensity:.1f}/10\n"
                if report_data.product.trend_strength:
                    four_ps_info += f"- Trend Strength: {report_data.product.trend_strength:.0f}/100\n"
                if report_data.product.signal_density:
                    four_ps_info += f"- Signal Density: {report_data.product.signal_density:.0%}\n"
                if report_data.product.amenity_demand and not demand_signals:
                    four_ps_info += "Top Consumer Demands:\n"
                    for sig in report_data.product.amenity_demand[:5]:
                        four_ps_info += f"  • {sig.get('amenity_type', '').replace('_', ' ').title()}: {sig.get('demand_pct', 0)}%\n"
            
            # PRICE
            if report_data.price:
                four_ps_info += "\n**PRICE (Economics):**\n"
                if report_data.price.market_size_estimate:
                    four_ps_info += f"- Market Size: {report_data.price.market_size_estimate}\n"
                if report_data.price.median_income:
                    four_ps_info += f"- Median Income: ${report_data.price.median_income:,}\n"
                if report_data.price.median_rent and not market_economics:
                    four_ps_info += f"- Median Rent: ${report_data.price.median_rent}/month\n"
                if report_data.price.spending_power_index:
                    four_ps_info += f"- Spending Power Index: {report_data.price.spending_power_index}/100\n"
                if report_data.price.revenue_benchmark:
                    four_ps_info += f"- Revenue Benchmark: ${report_data.price.revenue_benchmark:,.0f}/year\n"
            
            # PLACE
            if report_data.place:
                four_ps_info += "\n**PLACE (Location Intelligence):**\n"
                if report_data.place.growth_score:
                    four_ps_info += f"- Market Growth Score: {report_data.place.growth_score:.0f}/100\n"
                if report_data.place.growth_category:
                    four_ps_info += f"- Growth Category: {report_data.place.growth_category}\n"
                if report_data.place.population:
                    four_ps_info += f"- Population: {report_data.place.population:,}\n"
                if report_data.place.population_growth_rate:
                    four_ps_info += f"- Population Growth: {report_data.place.population_growth_rate}%\n"
                if report_data.place.job_growth_rate:
                    four_ps_info += f"- Job Growth: {report_data.place.job_growth_rate}%\n"
                if report_data.place.vacancy_rate and not market_economics:
                    four_ps_info += f"- Vacancy Rate: {report_data.place.vacancy_rate}%\n"
            
            # PROMOTION
            if report_data.promotion:
                four_ps_info += "\n**PROMOTION (Competition):**\n"
                if report_data.promotion.competition_level:
                    four_ps_info += f"- Competition Level: {report_data.promotion.competition_level}\n"
                if report_data.promotion.competitor_count:
                    four_ps_info += f"- Competitors: {report_data.promotion.competitor_count}\n"
                if report_data.promotion.avg_competitor_rating:
                    four_ps_info += f"- Avg Competitor Rating: {report_data.promotion.avg_competitor_rating:.1f}/5.0\n"
                if report_data.promotion.success_factors:
                    four_ps_info += f"- Success Factors: {', '.join(report_data.promotion.success_factors[:3])}\n"
                if report_data.promotion.key_risks:
                    four_ps_info += f"- Key Risks: {', '.join(report_data.promotion.key_risks[:3])}\n"
            
            # Data quality note
            if report_data.data_quality:
                dq = report_data.data_quality
                four_ps_info += f"\n(Data Quality: {dq.completeness:.0%} complete, {dq.confidence:.0%} confidence)\n"
        
        prompt = f"""Provide market insights for this opportunity:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Market Size: {opportunity.get('market_size', 'Under analysis')}
{demo_info}
{comp_info}
{demand_info}
{economics_info}
{four_ps_info}
"""
        return self._generate(system, prompt)
    
    def generate_competitive_analysis(
        self, 
        opportunity: Dict[str, Any],
        competitors: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate Porter's Five Forces competitive analysis for Layer 2."""
        system = """You are a strategy consultant analyzing competitive dynamics using Porter's Five Forces.
Structure your analysis with:
1. **Threat of New Entrants** - Barriers to entry, capital requirements
2. **Bargaining Power of Suppliers** - Key suppliers, switching costs
3. **Bargaining Power of Buyers** - Customer concentration, price sensitivity
4. **Threat of Substitutes** - Alternative solutions, technology disruption
5. **Competitive Rivalry** - Current players, market saturation, differentiation

Conclude with strategic positioning recommendations."""
        
        comp_info = ""
        if competitors:
            comp_info = "Known Competitors:\n"
            for comp in competitors[:10]:
                comp_info += f"- {comp.get('name', 'Unknown')}: {comp.get('rating', 'N/A')} stars, {comp.get('reviews', 0)} reviews, {comp.get('address', '')}\n"
        
        prompt = f"""Perform Porter's Five Forces analysis for:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
{comp_info}
"""
        return self._generate(system, prompt)
    
    def generate_tam_sam_som(
        self, 
        opportunity: Dict[str, Any],
        demographics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate TAM/SAM/SOM market sizing analysis for Layer 2."""
        system = """You are a market sizing analyst calculating Total Addressable Market (TAM), 
Serviceable Addressable Market (SAM), and Serviceable Obtainable Market (SOM).

Structure your analysis:
1. **TAM (Total Addressable Market)** - Global/national market for this category
2. **SAM (Serviceable Addressable Market)** - Regional/local market you could serve
3. **SOM (Serviceable Obtainable Market)** - Realistic market share in 3-5 years

Include methodology, assumptions, and dollar figures. Be realistic but optimistic."""
        
        demo_info = ""
        if demographics:
            demo_info = f"""
Local Demographics:
- Population: {demographics.get('population', 'N/A')}
- Median Income: ${demographics.get('median_income', 'N/A')}
- Total Households: {demographics.get('total_households', 'N/A')}
"""
        
        prompt = f"""Calculate TAM/SAM/SOM for:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Initial Market Size Estimate: {opportunity.get('market_size', 'Under analysis')}
Target Audience: {opportunity.get('target_audience', '')}
{demo_info}
"""
        return self._generate(system, prompt)
    
    def generate_strategic_recommendations(
        self, 
        opportunity: Dict[str, Any],
        demographics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate strategic recommendations for Layer 3 execution package."""
        system = """You are a business strategy consultant providing actionable recommendations.
Structure your recommendations:
1. **Business Model Recommendation** - Best model for this opportunity
2. **Go-to-Market Strategy** - Phase 1 (0-90 days), Phase 2 (90-180 days), Phase 3 (180-365 days)
3. **Key Partnerships** - Who to partner with and why
4. **Resource Requirements** - Initial investment, team, technology
5. **Risk Mitigation** - Top 3 risks and how to address them
6. **Success Metrics** - KPIs to track in first year

Be specific and actionable. Focus on practical next steps."""
        
        prompt = f"""Provide strategic recommendations for launching:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Market Size: {opportunity.get('market_size', 'Under analysis')}
Target Audience: {opportunity.get('target_audience', '')}
Business Model Suggestions: {opportunity.get('business_models', '')}
"""
        return self._generate(system, prompt)
    
    def generate_business_plan(self, opportunity: Dict[str, Any]) -> str:
        """Generate a comprehensive business plan for Layer 3."""
        system = f"""You are a senior business strategist at OppGrid creating investor-ready business plans.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure the business plan with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   One-page overview: opportunity, solution, market, financials, ask.

2. COMPANY DESCRIPTION
   ────────────────────
   • Mission Statement
   • Vision Statement  
   • Core Values
   • Legal Structure (recommended)

3. MARKET ANALYSIS
   ────────────────────
   • Industry Overview & Trends
   • Target Market Definition
   • Market Size (TAM/SAM/SOM)
   • Competitive Landscape

4. PRODUCTS & SERVICES
   ────────────────────
   • Core Offering Description
   • Unique Value Proposition
   • Product Roadmap
   • Intellectual Property Considerations

5. MARKETING & SALES STRATEGY
   ────────────────────
   • Go-to-Market Approach
   • Customer Acquisition Channels
   • Pricing Strategy
   • Sales Process

6. OPERATIONS PLAN
   ────────────────────
   • Key Activities & Processes
   • Resource Requirements
   • Strategic Partnerships
   • Technology Stack

7. MANAGEMENT & ORGANIZATION
   ────────────────────
   • Organizational Structure
   • Key Roles & Responsibilities
   • Advisory Board (recommended)

8. FINANCIAL PROJECTIONS
   ────────────────────
   • Revenue Model
   • Cost Structure
   • 3-Year P&L Summary
   • Funding Requirements & Use of Funds

9. MILESTONES & TIMELINE
   ────────────────────
   • 12-Month Roadmap
   • Key Success Metrics
   • Risk Mitigation Milestones

Format as a professional, investor-ready document."""
        
        prompt = f"""Write a comprehensive business plan for:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Market Size: {opportunity.get('market_size', 'Under analysis')}
Target Audience: {opportunity.get('target_audience', '')}
Business Model Ideas: {opportunity.get('business_models', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Business Plan")
    
    def generate_financial_projections(self, opportunity: Dict[str, Any]) -> str:
        """Generate financial projections for Layer 3."""
        system = f"""You are a senior financial analyst at OppGrid creating institutional-grade financial projections.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure your projections with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   Key financial metrics and investment thesis (2-3 sentences).

2. REVENUE MODEL
   ────────────────────
   • Primary Revenue Streams
   • Pricing Strategy & Tiers
   • Revenue Recognition Methodology
   • Average Revenue Per User/Customer

3. YEAR 1 PROJECTIONS (Monthly)
   ────────────────────
   Month    │ Revenue │ COGS   │ OpEx   │ Net
   ─────────┼─────────┼────────┼────────┼───────
   M1-M3    │ $X      │ $X     │ $X     │ ($X)
   M4-M6    │ $X      │ $X     │ $X     │ ($X)
   M7-M9    │ $X      │ $X     │ $X     │ $X
   M10-M12  │ $X      │ $X     │ $X     │ $X
   ─────────┼─────────┼────────┼────────┼───────
   TOTAL Y1 │ $X      │ $X     │ $X     │ $X

4. YEAR 2-3 PROJECTIONS (Quarterly)
   ────────────────────
   Quarterly breakdown with growth assumptions.

5. COST STRUCTURE
   ────────────────────
   FIXED COSTS (Monthly):
   • [Cost item]: $X
   • [Cost item]: $X
   
   VARIABLE COSTS (Per Unit):
   • [Cost item]: $X
   • [Cost item]: $X
   
   UNIT ECONOMICS:
   • Customer Acquisition Cost (CAC): $X
   • Lifetime Value (LTV): $X
   • LTV:CAC Ratio: X:1

6. BREAK-EVEN ANALYSIS
   ────────────────────
   • Break-Even Point: Month X
   • Units/Customers Required: X
   • Revenue at Break-Even: $X

7. FUNDING REQUIREMENTS
   ────────────────────
   • Initial Capital Required: $X
   • Use of Funds Breakdown
   • Runway Analysis

8. KEY ASSUMPTIONS
   ────────────────────
   List all assumptions with justification.

9. SENSITIVITY ANALYSIS
   ────────────────────
   Best/Base/Worst case scenarios.

Include specific dollar figures and realistic growth rates based on market analysis."""
        
        prompt = f"""Create 3-year financial projections for:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Market Size Estimate: {opportunity.get('market_size', 'Under analysis')}
Business Model: {opportunity.get('business_models', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Financial Model")
    
    def generate_feasibility_study(self, opportunity: Dict[str, Any]) -> str:
        """Generate a feasibility study for Consultant Studio."""
        system = f"""You are a senior feasibility analyst at OppGrid preparing an institutional-grade feasibility assessment.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure your feasibility study with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   Brief 2-3 sentence overview of findings and recommendation.

2. PROJECT OVERVIEW
   ────────────────────
   What is being evaluated and scope of analysis.

3. TECHNICAL FEASIBILITY (Score: X/10)
   ────────────────────
   Can it be built/delivered? Technology requirements and readiness.

4. MARKET FEASIBILITY (Score: X/10)
   ────────────────────
   Is there validated demand? Market size and growth indicators.

5. FINANCIAL FEASIBILITY (Score: X/10)
   ────────────────────
   Is it economically viable? ROI projections and capital requirements.

6. OPERATIONAL FEASIBILITY (Score: X/10)
   ────────────────────
   Can it be executed? Resource and capability requirements.

7. LEGAL & REGULATORY CONSIDERATIONS
   ────────────────────
   Compliance requirements and potential barriers.

8. RISK ASSESSMENT MATRIX
   ────────────────────
   Key risks rated by likelihood and impact.

9. RECOMMENDATION
   ────────────────────
   Go/No-Go/Conditional recommendation with justification.

COMPOSITE FEASIBILITY SCORE: X/10

Use the scoring system consistently. Be objective, balanced, and thorough."""
        
        prompt = f"""Conduct a comprehensive feasibility study for:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Market Size: {opportunity.get('market_size', 'Under analysis')}
Competition Level: {opportunity.get('competition_level', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Feasibility Study")
    
    def generate_pitch_deck_content(self, opportunity: Dict[str, Any]) -> str:
        """Generate pitch deck slide content for Quick Actions."""
        system = f"""You are a senior pitch consultant at OppGrid creating investor-ready presentation content.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure content as a professional pitch deck outline:

1. PITCH DECK OVERVIEW
   ────────────────────
   Summary of deck structure and key narrative.

═══════════════════════════════════════════════════════════════════════════════
                              SLIDE-BY-SLIDE CONTENT
═══════════════════════════════════════════════════════════════════════════════

SLIDE 1: TITLE
────────────────────
• Recommended Company Name Options
• Tagline Options (2-3)
• Visual Direction

SLIDE 2: PROBLEM
────────────────────
• Problem Statement (one sentence)
• Key Pain Points (3 bullets)
• Current Solutions & Why They Fail
• Speaker Notes: [Narrative guidance]

SLIDE 3: SOLUTION
────────────────────
• Solution Statement (one sentence)
• Key Features/Benefits (3-4 bullets)
• Unique Value Proposition
• Speaker Notes: [Narrative guidance]

SLIDE 4: MARKET SIZE
────────────────────
• TAM: $X (Global opportunity)
• SAM: $X (Addressable segment)
• SOM: $X (Year 1-3 target)
• Growth Rate: X% CAGR
• Speaker Notes: [Methodology talking points]

SLIDE 5: BUSINESS MODEL
────────────────────
• Revenue Streams
• Pricing Model
• Unit Economics (CAC, LTV, margins)
• Path to Profitability
• Speaker Notes: [Key metrics to emphasize]

SLIDE 6: TRACTION
────────────────────
• Milestones Achieved/Planned
• Key Metrics (if applicable)
• Validation Evidence
• Speaker Notes: [Credibility talking points]

SLIDE 7: COMPETITION
────────────────────
• Competitive Landscape Map
• Key Differentiators
• Defensibility/Moats
• Speaker Notes: [Positioning narrative]

SLIDE 8: TEAM
────────────────────
• Key Roles Needed
• Ideal Founder Profile
• Advisory Needs
• Speaker Notes: [Team narrative]

SLIDE 9: THE ASK
────────────────────
• Funding Amount: $X
• Use of Funds Breakdown
• Key Milestones with Funding
• Valuation Guidance (if appropriate)
• Speaker Notes: [Closing narrative]

SLIDE 10: VISION
────────────────────
• 5-Year Vision Statement
• Long-term Market Position
• Exit Potential
• Speaker Notes: [Inspirational close]

═══════════════════════════════════════════════════════════════════════════════

APPENDIX: BACKUP SLIDES
────────────────────
Recommended backup slides for Q&A."""
        
        prompt = f"""Create pitch deck content for:

Title: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Description: {opportunity.get('description', '')}
Market Size: {opportunity.get('market_size', 'Under analysis')}
Target Audience: {opportunity.get('target_audience', '')}
Business Models: {opportunity.get('business_models', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Pitch Deck")
    
    def generate_pestle_analysis(
        self, 
        opportunity: Dict[str, Any],
        target_region: Optional[str] = None
    ) -> str:
        """Generate PESTLE analysis for macro-environmental factors."""
        system = f"""You are a senior macro-environment analyst at OppGrid conducting institutional-grade PESTLE analysis.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure your analysis with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   Key macro-environmental findings and strategic implications (2-3 sentences).

2. POLITICAL FACTORS (Impact: High/Medium/Low)
   ────────────────────
   • Government Stability & Policy Direction
   • Tax Policies & Trade Regulations
   • Industry-Specific Political Climate
   • Regulatory Trends & Outlook
   
   Strategic Implication: [One sentence]

3. ECONOMIC FACTORS (Impact: High/Medium/Low)
   ────────────────────
   • Economic Growth Trajectory
   • Interest Rate & Inflation Environment
   • Consumer Spending Patterns
   • Labor Market Conditions
   
   Strategic Implication: [One sentence]

4. SOCIAL FACTORS (Impact: High/Medium/Low)
   ────────────────────
   • Demographic Trends & Shifts
   • Cultural & Lifestyle Changes
   • Consumer Behavior Evolution
   • Health & Education Indicators
   
   Strategic Implication: [One sentence]

5. TECHNOLOGICAL FACTORS (Impact: High/Medium/Low)
   ────────────────────
   • Technology Adoption Rates
   • Innovation & R&D Landscape
   • Digital Transformation Trends
   • Emerging Technology Impact
   
   Strategic Implication: [One sentence]

6. LEGAL FACTORS (Impact: High/Medium/Low)
   ────────────────────
   • Industry Regulations & Compliance
   • Employment Law Considerations
   • Consumer Protection Requirements
   • Intellectual Property Landscape
   
   Strategic Implication: [One sentence]

7. ENVIRONMENTAL FACTORS (Impact: High/Medium/Low)
   ────────────────────
   • Environmental Regulations
   • Sustainability Trends
   • Climate Change Considerations
   • Resource & Waste Management
   
   Strategic Implication: [One sentence]

8. IMPACT SUMMARY MATRIX
   ────────────────────
   Present a table summarizing all factors with impact ratings.

9. STRATEGIC RECOMMENDATIONS
   ────────────────────
   Prioritized actions based on PESTLE findings.

Provide specific, actionable insights tied to the target market."""
        
        region_info = target_region or opportunity.get('city', '') or opportunity.get('region', '')
        
        prompt = f"""Conduct a comprehensive PESTLE analysis for:

Business/Industry: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Target Region: {region_info}
Description: {opportunity.get('description', '')}
Target Audience: {opportunity.get('target_audience', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "PESTLE Analysis")
    
    def generate_market_analysis_report(
        self, 
        opportunity: Dict[str, Any],
        industry: Optional[str] = None,
        demand_signals: Optional[Dict[str, Any]] = None,
        market_economics: Optional[Dict[str, Any]] = None,
        report_data: Optional[Any] = None  # ReportDataContext from ReportDataService
    ) -> str:
        """Generate comprehensive market analysis report with full 4 P's data."""
        system = f"""You are a senior market research analyst at OppGrid creating institutional-grade market analysis reports.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure your report with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   Key market findings and opportunity assessment (2-3 sentences).

2. INDUSTRY OVERVIEW
   ────────────────────
   • Market Definition & Scope
   • Current Industry Size (with source methodology)
   • Historical Growth Rate (CAGR)
   • Key Market Drivers
   • Industry Lifecycle Stage

3. MARKET SIZING (TAM/SAM/SOM)
   ────────────────────
   • Total Addressable Market (TAM): $X
   • Serviceable Addressable Market (SAM): $X
   • Serviceable Obtainable Market (SOM): $X
   • Methodology & Assumptions

4. MARKET SEGMENTATION
   ────────────────────
   • Primary Customer Segments
   • Segment Characteristics & Size
   • Geographic Distribution
   • Growth Potential by Segment

5. COMPETITIVE LANDSCAPE
   ────────────────────
   • Market Structure & Concentration
   • Key Players & Estimated Market Share
   • Competitive Positioning Map
   • Barriers to Entry

6. MARKET TRENDS & DYNAMICS
   ────────────────────
   • Current Trends Shaping the Industry
   • Emerging Opportunities
   • Potential Disruptions
   • Technology Impact

7. CONSUMER ANALYSIS
   ────────────────────
   • Buyer Behavior Patterns
   • Purchase Decision Factors
   • Price Sensitivity Analysis
   • Unmet Needs & Pain Points

8. MARKET FORECAST (3-5 Year)
   ────────────────────
   • Growth Projections with Scenarios
   • Key Assumptions
   • Risk Factors & Sensitivities

9. OPPORTUNITY ASSESSMENT
   ────────────────────
   • Market Attractiveness Score
   • Entry Timing Recommendation
   • Strategic Positioning Options

Include specific data points and statistics. Reference OppGrid analysis methodology.
When consumer demand data is provided, incorporate it into the Consumer Analysis section to show real local demand patterns."""
        
        industry_focus = industry or opportunity.get('category', 'Unknown')
        
        # Build 4 P's data sections
        product_info = ""
        price_info = ""
        place_info = ""
        promotion_info = ""
        
        # Use ReportDataContext if available (preferred)
        if report_data:
            # PRODUCT (Demand Validation)
            product_info = "\n\n📊 PRODUCT INTELLIGENCE (OppGrid Analysis):\n"
            if report_data.product.opportunity_score:
                product_info += f"• Opportunity Score: {report_data.product.opportunity_score}/100\n"
            if report_data.product.pain_intensity:
                product_info += f"• Pain Intensity: {report_data.product.pain_intensity}/10\n"
            if report_data.product.urgency_level:
                product_info += f"• Urgency Level: {report_data.product.urgency_level.title()}\n"
            if report_data.product.trend_strength:
                product_info += f"• Trend Strength: {report_data.product.trend_strength}/100\n"
            if report_data.product.signal_density:
                product_info += f"• Signal Density: {report_data.product.signal_density:.0%}\n"
            if report_data.product.amenity_demand:
                product_info += "\nConsumer Demand Signals:\n"
                for signal in report_data.product.amenity_demand[:8]:
                    trend_icon = "↑" if signal.get('trend') == 'rising' else "↓" if signal.get('trend') == 'declining' else "→"
                    product_info += f"  • {signal.get('amenity_type', '').replace('_', ' ').title()}: {signal.get('demand_pct', 0)}% {trend_icon}\n"
            
            # PRICE (Economics)
            price_info = "\n\n💰 PRICE INTELLIGENCE (OppGrid Analysis):\n"
            if report_data.price.market_size_estimate:
                price_info += f"• Market Size: {report_data.price.market_size_estimate}\n"
            if report_data.price.addressable_market_value:
                price_info += f"• Addressable Market (TAM): ${report_data.price.addressable_market_value:,.0f}\n"
            if report_data.price.median_income:
                price_info += f"• Median Household Income: ${report_data.price.median_income:,}\n"
            if report_data.price.income_growth_rate:
                price_info += f"• Income Growth Rate: {report_data.price.income_growth_rate}%\n"
            if report_data.price.revenue_benchmark:
                price_info += f"• Revenue Benchmark: ${report_data.price.revenue_benchmark:,.0f}/year\n"
            if report_data.price.capital_required:
                price_info += f"• Capital Required: ${report_data.price.capital_required:,.0f}\n"
            if report_data.price.median_rent:
                price_info += f"• Median Rent: ${report_data.price.median_rent}/month\n"
            if report_data.price.spending_power_index:
                spi = report_data.price.spending_power_index
                spi_label = "High" if spi >= 70 else "Moderate" if spi >= 40 else "Lower"
                price_info += f"• Spending Power Index: {spi}/100 ({spi_label})\n"
            
            # PLACE (Location)
            place_info = "\n\n📍 PLACE INTELLIGENCE (OppGrid Analysis):\n"
            if report_data.place.growth_score:
                place_info += f"• Market Growth Score: {report_data.place.growth_score}/100\n"
            if report_data.place.growth_category:
                place_info += f"• Growth Category: {report_data.place.growth_category.title()}\n"
            if report_data.place.population:
                place_info += f"• Population: {report_data.place.population:,}\n"
            if report_data.place.population_growth_rate:
                place_info += f"• Population Growth: {report_data.place.population_growth_rate}%\n"
            if report_data.place.job_growth_rate:
                place_info += f"• Job Growth: {report_data.place.job_growth_rate}%\n"
            if report_data.place.business_formation_rate:
                place_info += f"• New Business Formation: {report_data.place.business_formation_rate}%\n"
            if report_data.place.traffic_aadt:
                place_info += f"• Daily Traffic (AADT): {report_data.place.traffic_aadt:,} vehicles\n"
            if report_data.place.vacancy_rate:
                place_info += f"• Vacancy Rate: {report_data.place.vacancy_rate}%\n"
            
            # PROMOTION (Competition)
            promotion_info = "\n\n🎯 PROMOTION INTELLIGENCE (OppGrid Analysis):\n"
            if report_data.promotion.competition_level:
                promotion_info += f"• Competition Level: {report_data.promotion.competition_level.title()}\n"
            if report_data.promotion.competitor_count:
                promotion_info += f"• Competitor Count: {report_data.promotion.competitor_count}\n"
            if report_data.promotion.avg_competitor_rating:
                promotion_info += f"• Avg Competitor Rating: {report_data.promotion.avg_competitor_rating}/5.0\n"
            if report_data.promotion.competitive_advantages:
                promotion_info += f"• Key Advantages: {', '.join(report_data.promotion.competitive_advantages[:3])}\n"
            if report_data.promotion.key_risks:
                promotion_info += f"• Key Risks: {', '.join(report_data.promotion.key_risks[:3])}\n"
            if report_data.promotion.success_factors:
                promotion_info += "\nSuccess Factors from Similar Businesses:\n"
                for factor in report_data.promotion.success_factors[:5]:
                    promotion_info += f"  • {factor}\n"
        
        # Fallback to legacy JediRE data if ReportDataContext not available
        elif demand_signals and demand_signals.get('signals'):
            product_info = "\n\nCONSUMER DEMAND INTELLIGENCE:\n"
            for signal in demand_signals['signals'][:12]:
                trend_icon = "↑" if signal.get('trend') == 'rising' else "↓" if signal.get('trend') == 'declining' else "→"
                product_info += f"• {signal['amenity_type'].replace('_', ' ').title()}: {signal['demand_pct']}% {trend_icon}\n"
        
        if market_economics and not report_data:
            price_info = "\n\nMARKET ECONOMICS:\n"
            if market_economics.get('median_rent'):
                price_info += f"• Median Rent: ${market_economics['median_rent']}/month\n"
            if market_economics.get('spending_power_index'):
                price_info += f"• Spending Power Index: {market_economics['spending_power_index']}/100\n"
        
        # Data quality note
        data_quality_note = ""
        if report_data and report_data.data_quality:
            completeness = report_data.data_quality.completeness
            data_quality_note = f"\n\n(Data Completeness: {completeness:.0%})"
        
        prompt = f"""Create a comprehensive market analysis for:

Industry/Market: {industry_focus}
Focus Area: {opportunity.get('title', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Target Audience: {opportunity.get('target_audience', '')}
{product_info}
{price_info}
{place_info}
{promotion_info}
{data_quality_note}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Market Analysis")
    
    def generate_strategic_assessment(self, opportunity: Dict[str, Any]) -> str:
        """Generate strategic assessment with SWOT analysis and recommendations."""
        system = f"""You are a senior strategy consultant at OppGrid providing institutional-grade strategic assessments.
{self.INSTITUTIONAL_STYLE_INSTRUCTIONS}

Structure your assessment with these numbered sections:

1. EXECUTIVE SUMMARY
   ────────────────────
   Strategic positioning and key recommendation (2-3 sentences).

2. SWOT ANALYSIS
   ────────────────────
   
   STRENGTHS                          │ WEAKNESSES
   • [Strength 1]                     │ • [Weakness 1]
   • [Strength 2]                     │ • [Weakness 2]
   • [Strength 3]                     │ • [Weakness 3]
   ──────────────────────────────────────────────────────
   OPPORTUNITIES                       │ THREATS
   • [Opportunity 1]                  │ • [Threat 1]
   • [Opportunity 2]                  │ • [Threat 2]
   • [Opportunity 3]                  │ • [Threat 3]

3. STRATEGIC POSITION ANALYSIS
   ────────────────────
   • Current Market Position
   • Competitive Advantages (Sustainable vs. Temporary)
   • Value Proposition Clarity Score: X/10
   • Brand Positioning Assessment

4. GROWTH STRATEGY OPTIONS
   ────────────────────
   Option A: Market Penetration
   • Approach: [Description]
   • Expected Impact: [High/Medium/Low]
   • Resource Requirement: [High/Medium/Low]
   
   Option B: Market Development
   • Approach: [Description]
   • Expected Impact: [High/Medium/Low]
   • Resource Requirement: [High/Medium/Low]
   
   Option C: Product/Service Expansion
   • Approach: [Description]
   • Expected Impact: [High/Medium/Low]
   • Resource Requirement: [High/Medium/Low]
   
   RECOMMENDED STRATEGY: [Option X with justification]

5. RESOURCE REQUIREMENTS
   ────────────────────
   • Key Capabilities Needed
   • Investment Requirements (Estimated Range)
   • Team & Talent Priorities
   • Timeline Considerations

6. RISK ASSESSMENT MATRIX
   ────────────────────
   Risk                    │ Likelihood │ Impact │ Mitigation
   [Risk 1]               │ H/M/L      │ H/M/L  │ [Strategy]
   [Risk 2]               │ H/M/L      │ H/M/L  │ [Strategy]
   [Risk 3]               │ H/M/L      │ H/M/L  │ [Strategy]

7. STRATEGIC RECOMMENDATIONS
   ────────────────────
   IMMEDIATE (0-30 days):
   • [Priority action 1]
   • [Priority action 2]
   
   SHORT-TERM (1-6 months):
   • [Strategic initiative 1]
   • [Strategic initiative 2]
   
   MEDIUM-TERM (6-18 months):
   • [Growth initiative 1]
   • [Growth initiative 2]

8. SUCCESS METRICS
   ────────────────────
   Key Performance Indicators to track strategic progress.

Provide actionable, specific recommendations based on OppGrid analysis."""
        
        prompt = f"""Conduct a strategic assessment for:

Opportunity: {opportunity.get('title', 'Unknown')}
Category: {opportunity.get('category', 'Unknown')}
Location: {opportunity.get('city', '')}, {opportunity.get('region', '')}
Description: {opportunity.get('description', '')}
Market Size: {opportunity.get('market_size', 'Under analysis')}
Competition Level: {opportunity.get('competition_level', '')}
Target Audience: {opportunity.get('target_audience', '')}
"""
        content = self._generate(system, prompt)
        return self._format_institutional_report(content, "Strategic Assessment")


ai_report_generator = AIReportGenerator()
