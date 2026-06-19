# Research Plan: How to Make Each Report Better & Differentiate Beyond the 4 P's

## Context
The Consultant Studio has 4 AI analysis paths (Validate Idea, Search Ideas, Identify Location, Clone Success) and 8 report types. The 4 P's (Product, Price, Place, Promotion) data pipeline is strong, but the user wants it to be *part* of the analysis, not the *only* thing. Reports need better differentiation, more proprietary data blends, and less reliance on generic AI output.

## Research Questions

### Dimension 1: Report Tier Differentiation
- What data depth should each price tier ($25, $79, $89, $99, $119, $129, $149) receive?
- How do platforms like CB Insights, PitchBook, IBISWorld, Grand View Research tier their offerings?
- What makes a $149 Business Plan objectively more valuable than a $25 Feasibility Study?

### Dimension 2: Proprietary Data Sources Beyond 4 P's
- What unique data sources can differentiate OppGrid from generic AI?
- Patent databases, trademark filings, regulatory filings, SEC 10-Ks, job postings, social signals, supply chain data, trade show data, grant awards, etc.
- What data sources are already partially integrated but underutilized?

### Dimension 3: Competitive Intelligence Integration
- How do top platforms integrate competitor analysis into their reports?
- What makes competitor analysis proprietary vs. generic?
- How to use Google Maps data, Yelp reviews, Reddit sentiment, BBB ratings more effectively?

### Dimension 4: Financial & Economic Intelligence
- How to make Financial Model and Business Plan reports truly differentiated?
- What live economic data should be integrated? (FRED, BLS, Census, Zillow, Bureau of Economic Analysis)
- How to build unit economics that a user can't get from Excel templates?

### Dimension 5: Location Intelligence Deep Dive
- What makes the Location Analysis report worth $119?
- What data sources should be added? (Walk Score, transit scores, crime stats, school ratings, commercial vacancy rates, permit data, utility costs)
- How to avoid the "recompute formulas" anti-pattern?

### Dimension 6: Fix Hardcoded Data in Validate Idea
- How to replace consultant_studio_enhancements.py with real data-driven analysis?
- What data should drive the 6 analysis sections (market, business model, financials, risks, next steps, competition)?
- How to make the preview content dynamically generated from the same data pipeline as paid reports?

### Dimension 7: Anti-Hallucination & Data Quality
- How to make reports more data-grounded and less AI-hallucinated?
- What data quality scoring should be visible to users?
- How to handle low-data markets gracefully (don't produce thin reports)?

### Dimension 8: User Experience & Report Value Perception
- What makes a report feel "worth $149" vs. "worth $25"?
- Visual differentiation, data depth, actionable insights, proprietary scoring, exclusivity
- How to communicate data provenance to users ("This report includes data from X, Y, Z")?

## Output
After research, implement fixes:
1. Differentiate report data pipelines by tier
2. Add new proprietary data sources
3. Replace hardcoded Validate Idea preview with real data
4. Fix Location Analysis formula recomputation issue
5. Add data quality transparency to all reports

