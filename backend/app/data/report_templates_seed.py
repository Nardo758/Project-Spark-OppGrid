REPORT_TEMPLATES = [
    {
        "slug": "ad_creatives",
        "name": "Ad Creatives",
        "description": "High-converting ad copy and creative concepts",
        "category": "popular",
        "min_tier": "pro",
        "price_cents": 4900,
        "display_order": 1,
        "ai_prompt": """Generate high-converting ad creatives for this business opportunity. Include:
1. 3 Facebook/Instagram ad variations with headlines, body copy, and CTA
2. 3 Google Ads variations with headlines and descriptions
3. 3 LinkedIn ad variations for B2B audiences
4. Creative direction notes for visual elements
5. A/B testing suggestions

Business Context:
{context}

Format the output as structured sections with ready-to-use copy."""
    },
    {
        "slug": "brand_package",
        "name": "Brand Package",
        "description": "Complete brand identity with logo, colors, and voice",
        "category": "popular",
        "min_tier": "pro",
        "price_cents": 5900,
        "display_order": 2,
        "ai_prompt": """Create a complete brand identity package for this business opportunity. Include:
1. Brand name suggestions (5 options with rationale)
2. Tagline options (3-5 variations)
3. Brand voice and tone guidelines
4. Color palette recommendations with hex codes
5. Typography suggestions (font pairings)
6. Logo concept descriptions
7. Brand values and personality traits
8. Target audience positioning

Business Context:
{context}

Provide actionable brand guidelines that can be used immediately."""
    },
    {
        "slug": "landing_page",
        "name": "Landing Page",
        "description": "Copy + wireframe blocks",
        "category": "popular",
        "min_tier": "pro",
        "price_cents": 4900,
        "display_order": 3,
        "ai_prompt": """Create a high-converting landing page blueprint for this business opportunity. Include:
1. Above-the-fold section (headline, subheadline, hero CTA)
2. Problem/pain point section
3. Solution overview with key benefits
4. Features breakdown with icons/descriptions
5. Social proof section structure
6. Pricing section framework
7. FAQ section with 5-7 common questions
8. Final CTA section
9. SEO meta title and description

Business Context:
{context}

Format as wireframe blocks with actual copy ready to use."""
    },
    {
        "slug": "content_calendar",
        "name": "Content Calendar",
        "description": "90-day content marketing plan",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 3900,
        "display_order": 10,
        "ai_prompt": """Create a 90-day content marketing calendar for this business opportunity. Include:
1. Week-by-week content themes
2. Blog post topics (12 posts minimum)
3. Social media content ideas (30+ posts)
4. Email newsletter topics (12 issues)
5. Video/podcast content ideas (6 minimum)
6. Content pillars and categories
7. SEO keyword targets per content piece
8. Distribution strategy for each channel
9. Engagement tactics and CTAs

Business Context:
{context}

Format as a structured calendar with dates and content types."""
    },
    {
        "slug": "email_funnel",
        "name": "Email Funnel System",
        "description": "Complete email marketing funnel with sequences, triggers & more",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 4900,
        "display_order": 11,
        "ai_prompt": """Design a complete email marketing funnel system for this business opportunity. Include:
1. Lead magnet email sequence (5 emails)
2. Nurture sequence (7 emails)
3. Sales sequence (5 emails)
4. Onboarding sequence for new customers (5 emails)
5. Re-engagement sequence (3 emails)
6. Trigger-based automations
7. Subject line variations for A/B testing
8. Segmentation strategy
9. Key metrics to track

Business Context:
{context}

Provide full email copy for each sequence."""
    },
    {
        "slug": "email_sequence",
        "name": "Email Sequence",
        "description": "5-email nurture sequence",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 2900,
        "display_order": 12,
        "ai_prompt": """Create a 5-email nurture sequence for this business opportunity. Include:
1. Email 1: Welcome & value proposition
2. Email 2: Problem awareness & education
3. Email 3: Solution introduction & social proof
4. Email 4: Overcome objections & case study
5. Email 5: Call to action & urgency

For each email provide:
- Subject line (with 2 alternatives)
- Preview text
- Full body copy
- CTA button text
- Optimal send timing

Business Context:
{context}"""
    },
    {
        "slug": "lead_magnet",
        "name": "Lead Magnet",
        "description": "Irresistible lead generation offers",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 2900,
        "display_order": 13,
        "ai_prompt": """Create 5 lead magnet concepts for this business opportunity. For each include:
1. Lead magnet title and format (ebook, checklist, template, etc.)
2. Compelling description
3. Table of contents or outline
4. Landing page headline and copy
5. Opt-in form messaging
6. Thank you page copy
7. Delivery email template
8. Follow-up sequence trigger

Business Context:
{context}

Provide one fully-developed lead magnet outline ready for creation."""
    },
    {
        "slug": "sales_funnel",
        "name": "Sales Funnel",
        "description": "Customer journey optimization strategy",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 3900,
        "display_order": 14,
        "ai_prompt": """Design a complete sales funnel for this business opportunity. Include:
1. Awareness stage tactics and content
2. Interest stage nurturing strategy
3. Decision stage conversion tactics
4. Action stage optimization
5. Retention and referral strategies
6. Funnel visualization with conversion targets
7. Traffic sources and acquisition strategy
8. Upsell and cross-sell opportunities
9. Key metrics and benchmarks per stage
10. Tools and platforms recommended

Business Context:
{context}"""
    },
    {
        "slug": "seo_content",
        "name": "SEO Content Strategy",
        "description": "Search-optimized content strategy",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 3900,
        "display_order": 15,
        "ai_prompt": """Create a comprehensive SEO content strategy for this business opportunity. Include:
1. Primary keyword targets (10 keywords with search volume estimates)
2. Long-tail keyword opportunities (20+ keywords)
3. Content cluster strategy with pillar pages
4. Blog post outlines for top 5 keywords
5. On-page SEO checklist
6. Internal linking strategy
7. Backlink acquisition tactics
8. Local SEO recommendations (if applicable)
9. Technical SEO priorities
10. 6-month ranking timeline

Business Context:
{context}"""
    },
    {
        "slug": "tweet_landing",
        "name": "Tweet-Sized Landing Page",
        "description": "Ultra-minimal 280-character landing page",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 1900,
        "display_order": 16,
        "ai_prompt": """Create 10 tweet-sized landing page concepts for this business opportunity. Each should be:
1. Under 280 characters
2. Include value proposition
3. Have a clear CTA

Also provide:
- 5 bio variations for social profiles
- 10 one-liner descriptions
- 5 elevator pitches (30 seconds)
- 3 tagline options

Business Context:
{context}"""
    },
    {
        "slug": "user_personas",
        "name": "User Personas",
        "description": "Detailed customer persona cards with motivations",
        "category": "marketing",
        "min_tier": "pro",
        "price_cents": 2900,
        "display_order": 17,
        "ai_prompt": """Create 4 detailed user personas for this business opportunity. For each persona include:
1. Name, age, occupation, location
2. Demographics and psychographics
3. Goals and motivations
4. Pain points and frustrations
5. Buying behavior and decision factors
6. Preferred channels and media consumption
7. Objections and concerns
8. Key messaging that resonates
9. Customer journey touchpoints
10. Persona-specific marketing tactics

Business Context:
{context}

Format as detailed persona cards ready for team use."""
    },
    {
        "slug": "feature_specs",
        "name": "Feature Specs",
        "description": "Detailed feature specifications and user stories",
        "category": "product",
        "min_tier": "pro",
        "price_cents": 4900,
        "display_order": 20,
        "ai_prompt": """Create detailed feature specifications for this business opportunity. Include:
1. Core feature list with priorities (P0, P1, P2)
2. User stories in format: As a [user], I want [goal], so that [benefit]
3. Acceptance criteria for each feature
4. Technical requirements and constraints
5. Dependencies and integrations
6. Edge cases and error handling
7. Performance requirements
8. Security considerations
9. Accessibility requirements
10. Feature comparison vs competitors

Business Context:
{context}

Format as actionable specs for development team."""
    },
    {
        "slug": "mvp_roadmap",
        "name": "MVP Roadmap",
        "description": "90-day development plan with feature prioritization",
        "category": "product",
        "min_tier": "pro",
        "price_cents": 5900,
        "display_order": 21,
        "ai_prompt": """Create a 90-day MVP development roadmap for this business opportunity. Include:
1. Week 1-2: Foundation and setup
2. Week 3-4: Core feature development
3. Week 5-6: Essential integrations
4. Week 7-8: Testing and refinement
5. Week 9-10: Beta launch preparation
6. Week 11-12: Launch and iteration

For each phase include:
- Specific deliverables
- Resource requirements
- Risk factors
- Success metrics
- Dependencies

Business Context:
{context}"""
    },
    {
        "slug": "prd",
        "name": "Product Requirements Doc",
        "description": "Complete PRD with technical specifications",
        "category": "product",
        "min_tier": "business",
        "price_cents": 7900,
        "display_order": 22,
        "ai_prompt": """Create a comprehensive Product Requirements Document (PRD) for this business opportunity. Include:
1. Executive Summary
2. Problem Statement
3. Goals and Success Metrics
4. User Personas
5. User Stories and Use Cases
6. Functional Requirements
7. Non-Functional Requirements
8. System Architecture Overview
9. Data Model and API Specifications
10. UI/UX Requirements
11. Integration Requirements
12. Security and Compliance
13. Launch Criteria
14. Future Considerations
15. Appendix: Competitive Analysis

Business Context:
{context}

Format as a professional PRD document."""
    },
    {
        "slug": "gtm_calendar",
        "name": "GTM Launch Calendar",
        "description": "90-day launch timeline with team coordination",
        "category": "business",
        "min_tier": "pro",
        "price_cents": 4900,
        "display_order": 30,
        "ai_prompt": """Create a 90-day Go-To-Market launch calendar for this business opportunity. Include:
1. Pre-launch phase (Day 1-30): Build anticipation
2. Launch phase (Day 31-45): Execute launch
3. Post-launch phase (Day 46-90): Scale and optimize

For each week include:
- Marketing activities
- Sales enablement tasks
- PR and communications
- Product milestones
- Team responsibilities
- Budget allocation
- KPIs to track

Business Context:
{context}

Format as actionable calendar with dates and owners."""
    },
    {
        "slug": "gtm_strategy",
        "name": "GTM Strategy",
        "description": "Go-to-market strategy and launch plan",
        "category": "business",
        "min_tier": "pro",
        "price_cents": 6900,
        "display_order": 31,
        "ai_prompt": """Create a comprehensive Go-To-Market strategy for this business opportunity. Include:
1. Market Analysis and Sizing
2. Target Customer Segments
3. Value Proposition and Positioning
4. Competitive Differentiation
5. Pricing Strategy
6. Distribution Channels
7. Marketing Mix (4Ps)
8. Sales Strategy and Process
9. Partnership Opportunities
10. Launch Milestones
11. Budget Allocation
12. Success Metrics and KPIs
13. Risk Mitigation Plan

Business Context:
{context}"""
    },
    {
        "slug": "kpi_dashboard",
        "name": "KPI Dashboard",
        "description": "Pre-built metrics tracker with formulas",
        "category": "business",
        "min_tier": "pro",
        "price_cents": 3900,
        "display_order": 32,
        "ai_prompt": """Create a comprehensive KPI dashboard framework for this business opportunity. Include:
1. Financial Metrics (Revenue, MRR, ARR, CAC, LTV, etc.)
2. Marketing Metrics (Traffic, Conversion, CPL, etc.)
3. Sales Metrics (Pipeline, Win Rate, Deal Size, etc.)
4. Product Metrics (DAU, MAU, Retention, NPS, etc.)
5. Operational Metrics (Efficiency, Quality, etc.)

For each metric provide:
- Definition and formula
- Target benchmarks
- Data source
- Update frequency
- Action triggers

Business Context:
{context}

Format as dashboard specification with visualization recommendations."""
    },
    {
        "slug": "pricing_strategy",
        "name": "Pricing Strategy",
        "description": "Strategic pricing framework and psychology",
        "category": "business",
        "min_tier": "business",
        "price_cents": 5900,
        "display_order": 33,
        "ai_prompt": """Create a comprehensive pricing strategy for this business opportunity. Include:
1. Value-Based Pricing Analysis
2. Competitive Pricing Comparison
3. Cost-Plus Pricing Calculation
4. Pricing Model Options (subscription, usage, tiered, freemium)
5. Price Point Recommendations
6. Pricing Psychology Tactics
7. Discount and Promotion Strategy
8. Enterprise/Custom Pricing Framework
9. Price Testing Methodology
10. Margin Analysis
11. Price Increase Strategy
12. International Pricing Considerations

Business Context:
{context}"""
    },
    {
        "slug": "competitive_analysis",
        "name": "Competitive Analysis",
        "description": "Deep dive into competitors and market gaps",
        "category": "research",
        "min_tier": "pro",
        "price_cents": 4900,
        "display_order": 40,
        "ai_prompt": """Create a comprehensive competitive analysis for this business opportunity. Include:
1. Direct Competitors (5-10 companies)
2. Indirect Competitors (3-5 companies)
3. Competitive Matrix (features, pricing, positioning)
4. SWOT Analysis for top 3 competitors
5. Market Share Estimates
6. Competitor Strengths and Weaknesses
7. Differentiation Opportunities
8. Pricing Comparison
9. Marketing Strategy Analysis
10. Product Roadmap Intelligence
11. Customer Review Analysis
12. Market Gap Identification

Business Context:
{context}

Format as actionable competitive intelligence report."""
    },
    {
        "slug": "customer_interview",
        "name": "Customer Interview Guide",
        "description": "Structured interviews for validation and insights",
        "category": "research",
        "min_tier": "pro",
        "price_cents": 2900,
        "display_order": 41,
        "ai_prompt": """Create a customer interview guide for this business opportunity. Include:
1. Interview Objectives
2. Participant Screening Criteria
3. Interview Script (30-45 minute format)
4. Opening Questions (rapport building)
5. Problem Discovery Questions (10-15)
6. Solution Validation Questions (10-15)
7. Pricing Sensitivity Questions (5-7)
8. Closing Questions
9. Follow-up Survey Template
10. Analysis Framework
11. Insight Synthesis Template
12. Common Pitfalls to Avoid

Business Context:
{context}

Format as ready-to-use interview guide with tips for moderators."""
    },

    # ── Analysis Reports (7 Consultant Studio originals) ─────────────────────
    {
        "slug": "feasibility_study",
        "name": "Feasibility Study",
        "description": "Quick viability check with market validation",
        "category": "analysis",
        "min_tier": "free",
        "price_cents": 2500,
        "display_order": 50,
        "ai_prompt": """Conduct a comprehensive feasibility study for the following business idea. Structure your analysis as:

1. Executive Summary (viability verdict + confidence score 0-100)
2. Market Feasibility – demand signals, addressable market size, customer segments
3. Technical Feasibility – required capabilities, technology stack, build complexity
4. Financial Feasibility – estimated startup costs, break-even timeline, revenue potential
5. Operational Feasibility – team requirements, processes, regulatory considerations
6. Risk Assessment – top 5 risks with likelihood and mitigation strategies
7. Go / No-Go Recommendation with clear reasoning

Business Context:
{context}

Be direct and evidence-based. Provide specific numbers where possible."""
    },
    {
        "slug": "business_plan",
        "name": "Business Plan",
        "description": "Comprehensive strategy document",
        "category": "analysis",
        "min_tier": "pro",
        "price_cents": 14900,
        "display_order": 51,
        "ai_prompt": """Create a comprehensive business plan for the following opportunity. Include:

1. Executive Summary
2. Company Description – mission, vision, values, legal structure
3. Problem & Solution – pain points addressed, unique value proposition
4. Market Analysis – TAM/SAM/SOM, target customer profiles, market trends
5. Competitive Analysis – key competitors, differentiation strategy, moat
6. Product / Service Description – features, roadmap, IP considerations
7. Marketing & Sales Strategy – channels, customer acquisition, retention
8. Operations Plan – team structure, processes, key milestones
9. Financial Projections – 3-year P&L, cash flow, unit economics
10. Funding Requirements (if applicable)
11. Risk Management

Business Context:
{context}

Write in a professional tone suitable for investors and partners."""
    },
    {
        "slug": "financial_model",
        "name": "Financial Model",
        "description": "5-year projections and unit economics",
        "category": "analysis",
        "min_tier": "pro",
        "price_cents": 12900,
        "display_order": 52,
        "ai_prompt": """Build a detailed financial model for the following business opportunity. Include:

1. Revenue Model – pricing tiers, revenue streams, assumptions
2. Unit Economics – CAC, LTV, LTV:CAC ratio, payback period
3. Monthly P&L Projection (Year 1, month by month)
4. Annual Summary (Years 1–5) – revenue, gross profit, EBITDA
5. Cash Flow Statement – operating, investing, financing activities
6. Break-Even Analysis – fixed costs, variable costs, break-even point
7. Funding Scenarios – bootstrapped vs. seed vs. Series A paths
8. Key Metrics Dashboard – MRR, ARR, churn, NPS targets
9. Sensitivity Analysis – best / base / worst case scenarios

Business Context:
{context}

Present numbers in clear tables. State all assumptions explicitly."""
    },
    {
        "slug": "market_analysis",
        "name": "Market Analysis",
        "description": "TAM/SAM/SOM with competitive landscape",
        "category": "analysis",
        "min_tier": "business",
        "price_cents": 9900,
        "display_order": 53,
        "ai_prompt": """Produce a detailed market analysis report for the following business opportunity. Cover:

1. Market Overview – industry definition, current size, growth rate (CAGR)
2. TAM / SAM / SOM Calculation with methodology explained
3. Market Segmentation – demographic, psychographic, behavioral, geographic
4. Customer Analysis – buyer personas, jobs-to-be-done, willingness to pay
5. Competitive Landscape – direct and indirect competitors, market share map
6. Porter's Five Forces Analysis
7. Market Trends – macro forces shaping the market (3–5 year outlook)
8. Regulatory Environment – key regulations, compliance requirements
9. Market Entry Strategy – recommended approach and timing
10. Opportunity Sizing Summary

Business Context:
{context}

Use data-driven language. Cite categories of sources where applicable."""
    },
    {
        "slug": "pestle_analysis",
        "name": "PESTLE Analysis",
        "description": "Political, Economic, Social, Technological, Legal, Environmental factors",
        "category": "analysis",
        "min_tier": "business",
        "price_cents": 9900,
        "display_order": 54,
        "ai_prompt": """Conduct a thorough PESTLE analysis for the following business opportunity. For each factor provide current state, trend direction, and business impact (High / Medium / Low):

1. Political Factors – government policy, trade regulations, political stability, tax policy
2. Economic Factors – economic growth, inflation, interest rates, consumer spending, labour costs
3. Social Factors – demographics, lifestyle trends, cultural shifts, consumer attitudes
4. Technological Factors – emerging tech, R&D activity, automation, digital adoption
5. Legal Factors – employment law, consumer protection, IP law, health & safety regulations
6. Environmental Factors – sustainability pressures, climate risk, ESG expectations

Then provide:
7. Overall Risk Rating (Low / Medium / High) with justification
8. Strategic Recommendations – how to leverage opportunities and mitigate threats from each factor
9. Monitoring Checklist – signals to watch over the next 12 months

Business Context:
{context}

Be specific to the industry and geography where applicable."""
    },
    {
        "slug": "strategic_assessment",
        "name": "Strategic Assessment",
        "description": "SWOT analysis and strategic positioning",
        "category": "analysis",
        "min_tier": "pro",
        "price_cents": 8900,
        "display_order": 55,
        "ai_prompt": """Deliver a strategic assessment for the following business opportunity. Structure it as:

1. Executive Overview – strategic position summary
2. SWOT Analysis
   - Strengths (internal advantages)
   - Weaknesses (internal gaps)
   - Opportunities (external tailwinds)
   - Threats (external risks)
3. Strategic Positioning – value proposition, differentiation, target segment fit
4. Competitive Moat Assessment – network effects, switching costs, brand, IP, scale
5. Strategic Options (3 paths) – conservative, growth, and bold strategies
6. Recommended Strategy – rationale, trade-offs, resource requirements
7. 90-Day Action Plan – prioritised initiatives with owners and success metrics
8. KPIs to Track – 5–7 metrics that signal strategic health

Business Context:
{context}

Be opinionated. Give a clear strategic recommendation, not just a list of options."""
    },
    {
        "slug": "pitch_deck",
        "name": "Pitch Deck Assistant",
        "description": "Investor presentation outline and key slides",
        "category": "analysis",
        "min_tier": "pro",
        "price_cents": 7900,
        "display_order": 56,
        "ai_prompt": """Create investor-ready pitch deck content for the following business opportunity. Produce slide-by-slide content for a 10-slide deck:

Slide 1 – Cover: company name, one-line tagline, presenter info
Slide 2 – Problem: the pain, who feels it, how big the gap is
Slide 3 – Solution: what you've built, the "aha" moment
Slide 4 – Market Size: TAM / SAM / SOM with methodology
Slide 5 – Business Model: how you make money, pricing, unit economics
Slide 6 – Traction: key metrics, milestones, social proof (or early signals)
Slide 7 – Competition: market map, why you win
Slide 8 – Go-To-Market: acquisition strategy, channels, growth levers
Slide 9 – Team: key roles, relevant experience, why this team
Slide 10 – Ask: funding amount, use of funds, 18-month milestones

Then add:
- 5 likely investor questions with suggested answers
- Design tips for each slide (visuals, layout guidance)
- Common mistakes to avoid

Business Context:
{context}

Write in confident, clear language. Every word should earn its place on the slide."""
    },
]
