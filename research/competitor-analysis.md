# Competitive Intelligence Analysis: Business Opportunity Detail Page Patterns

**Research Date:** 2026-06-27  
**Analyst:** Competitive Intelligence Team (AI-Augmented)  
**Scope:** Detail card / page UX patterns of 6 leading B2B intelligence platforms  
**Target Audience:** OppGrid Product & Design Team  

---

## Executive Summary

After analyzing **6 major B2B intelligence platforms** — Crunchbase, PitchBook, LinkedIn, Wellfound (AngelList), G2/Capterra, and CB Insights — a clear pattern emerges: **the most effective detail pages compress complex data into a single, scannable "health score" above the fold, then use progressive disclosure to unpack depth.** Platforms that gate premium data too aggressively above the fold (PitchBook, CB Insights) create friction for free users, while those that reveal too little (LinkedIn) fail to differentiate. The sweet spot — exemplified by Crunchbase's new profile experience — combines **predictive scoring, clear visual hierarchy, and contextual CTAs** that adapt to the user's tier.

**Key findings for OppGrid:**

1. **Predictive scoring is the new table stakes.** CB Insights' Mosaic Score and Crunchbase's Growth/Heat Scores demonstrate that users want a single number to prioritize opportunities. OppGrid's `feasibility_score` is well-positioned but lacks sub-component transparency.
2. **Progressive disclosure wins over density.** PitchBook's dense tables overwhelm; Crunchbase's left-nav sections with expandable depth feel more manageable. OppGrid's two-tier model (Free/Pro) is directionally correct but could benefit from "preview snippets" rather than full blur locks.
3. **Comparison is a conversion multiplier.** G2/Capterra's side-by-side comparison grids drive engagement. OppGrid currently lacks peer comparison on its detail page — a high-ROI gap.
4. **Mobile-first metric visualization is under-invested across all platforms.** Most B2B intelligence sites treat mobile as a secondary viewport. A responsive, card-first mobile design would be a genuine differentiator for OppGrid.

---

## 1. Crunchbase — Company Profile Page

### Overview
Crunchbase is the most widely accessible startup intelligence platform, serving ~2 million organizations with a freemium model. Its 2024–2025 profile redesign shifted from a static directory listing to an **AI-powered predictive dashboard**.

### Above-the-Fold Content
- **Growth Score** and **Heat Score** prominently displayed as large numeric badges at the top of the profile
- **Company performance metrics graph** showing momentum and historical events that led to current growth status
- **Funding summary** (last round, total raised, valuation if available)
- **Key people** (CEO, CTO, founders) with quick-contact links
- **Profile activity** indicator measuring Crunchbase user engagement within the industry
- **Left navigation bar** with sections: Overview, Predictions & Insights, Financials, People, News, Technology [1]

### Key Metrics & Visualization
- **Growth Score**: Quantifies private company growth using predictions and historical data (funding, operations, headcount, market share, financial, customer growth, product usage, M&A). Displayed as a 0–100 style number with color coding.
- **Heat Score**: Measures market interest/prominence based on profile activity and media presence.
- **Performance graph**: Line chart showing momentum over time with annotated funding events.
- **Predictions**: AI/ML-powered Growth Prediction, IPO Prediction, Acquisition Prediction with "top contributing factors" that users can click to explore [1].

### Premium/Free Tier Gating
- **Starter ($29/user/month)**: Basic profiles, limited search.
- **Pro ($49/user/month)**: Full predictions, CRM integrations (Salesforce, HubSpot), export to Outreach.
- **Enterprise**: Custom pricing, API access.
- **Gating strategy**: Free users see headline scores and basic funding data. Predictions, contact info, and detailed financials are locked behind "Upgrade to Pro" banners with preview snippets (e.g., "Growth Prediction: High — upgrade to see contributing factors"). The gating is **contextual** rather than page-level [2].

### CTA Placement & Hierarchy
1. **Primary**: "Follow Company" (free, top-right)
2. **Secondary**: "Add to List" / "Export to CRM" (Pro-gated)
3. **Tertiary**: "Contact" / "Request Intro" (gated, contextual)
4. **Bottom of each section**: "Upgrade to see more" with specific data points listed

### Mobile Adaptation
- Crunchbase's mobile app collapses the left nav into a bottom sheet or tab bar.
- Scores remain visible but graphs are simplified to sparklines.
- The "Follow" CTA becomes a sticky bottom bar.
- Search filters are pre-templated to reduce typing [2].

### Effectiveness Analysis
- **Effective**: The predictive scores (Growth/Heat) create instant comprehension. The left-nav structure prevents scroll fatigue. Contextual gating (showing what you're missing) has higher conversion than blanket locks.
- **Ineffective**: Free profiles can feel thin — some companies have minimal data, making the AI predictions feel speculative. The graph can be misleading for early-stage companies with few data points.
- **What to steal**: The "Prediction with contributing factors" pattern is perfect for OppGrid's feasibility_score. Also, the "Profile Activity" metric (user engagement on the page) is a clever social proof signal.

### Citations
[1] Crunchbase Support, "Navigating a company profile on Crunchbase," Aug 2025. https://support.crunchbase.com/hc/en-us/articles/360052260893  
[2] Clay Blog, "Crunchbase vs. PitchBook: Key Differences Compared," 2026. https://www.clay.com/blog/crunchbase-vs-pitchbook  

---

## 2. PitchBook — Deal/Company Detail Page

### Overview
PitchBook is the premium standard for VC/PE intelligence, covering ~4.2 million organizations with a focus on **granular deal data, valuations, and non-financial signals**. Its UI is designed for experienced analysts, not casual browsers.

### Above-the-Fold Content
- **Company overview strip**: Year Founded, Status (Private/Acquired), Employees, Latest Deal Type, Latest Deal Amount — displayed as a horizontal icon+text row [3]
- **General Information**: Company description (often dense, analyst-written), Contact Information section
- **Prominent CTA**: "Want to dig into this profile? Learn more" — drives to free trial request
- **Timeline**: Visual financing round timeline (Year → Round → Employee Count) [3]

### Key Metrics & Visualization
- **Valuation & Funding table**: Deal Type | Date | Amount | Raised to Date | Post-Val | Status | Stage. Free users see only the first 1–2 rows; full table is locked.
- **Opportunity Score**: Visual gauge (pie-chart style) showing exit probability based on stage and historical returns data.
- **Exit Type**: Likelihood chart (IPO vs. M&A vs. None) with probability percentages.
- **Signals section** (Premium): Growth Rate, Weekly Growth, Size Multiple, Similarweb Unique Visitors, Majestic Referring Domains — each with mini charts (pie, bell curve, line) [3].
- **Comparisons**: Side-by-side table against similar companies across Description, Industry, HQ, Employees, Total Raised, Post Valuation.

### Premium/Free Tier Gating
- **Pricing**: $25,000+/year base for 3 users, +$7,000 per additional user. No self-serve free tier.
- **Gating strategy**: PitchBook uses a **hard paywall** for almost all valuable data. Public preview pages show only the overview strip and a truncated funding table. The phrase "This information is available in the PitchBook Platform. To explore [Company]'s full profile, request access" appears repeatedly [3].
- **Freemium**: Effectively non-existent. Even basic contact info requires trial.

### CTA Placement & Hierarchy
1. **Primary**: "Request a free trial" (appears 3–4 times per page)
2. **Secondary**: "Add Comparison" (drives to trial)
3. **Tertiary**: "Learn more" (about data methodology)

### Mobile Adaptation
- PitchBook is primarily a desktop product. Mobile experience is limited to a responsive web view that stacks tables vertically.
- Charts are simplified but still dense.
- No native mobile app with full feature parity.

### Effectiveness Analysis
- **Effective**: The data density is unmatched for power users. The Opportunity Score and Exit Type visualizations are genuinely useful for quick screening. The comparison feature is powerful for benchmarking.
- **Ineffective**: The page is **overwhelming for non-experts**. The hard paywall creates a poor discovery experience — there's no "taste" of the data before committing to a sales call. The visual design feels dated compared to Crunchbase.
- **What to steal**: The **non-financial signals** (web traffic, referring domains) are a brilliant way to gauge traction for private companies. OppGrid could integrate Similarweb/Majestic-style signals. The **side-by-side comparison** is a must-have feature.

### Citations
[3] PitchBook public profile previews for Parallel Domain, London Dynamics, Dink, Nuwa Robotics, accessed via search-indexed previews, 2025–2026. https://pitchbook.com/profiles/company/  
[4] 11x.ai, "Top 10 PitchBook Alternatives for Sales Intelligence," Jan 2026. https://www.11x.ai/sales-tools/pitchbook  

---

## 3. LinkedIn — Company Page

### Overview
LinkedIn Company Pages are the **most visited B2B profile pages on the internet**, but they are intentionally designed for brand presence rather than deep intelligence. Their layout prioritizes engagement and recruitment over financial analysis.

### Above-the-Fold Content
- **Hero banner** (cover image) + **Logo** (300×300px)
- **Company name + Tagline** (120 characters — optimized for LinkedIn and Google search)
- **Follow button** (primary CTA, always visible)
- **Custom CTA button** (top-right): Options include "Contact us," "Learn more," "Register," "Sign up," "Visit website," "View jobs" [5]
- **About section** (first 150 characters are critical for SEO)
- **Employee count** + Company size category
- **Industry + Location**
- **Products & Services** showcase (if configured)
- **Customer testimonials** (if configured — 35% higher conversion when present) [6]

### Key Metrics & Visualization
- **Follower count** (social proof)
- **Employee count** (with trend: "+15% in the past year")
- **Engagement metrics** (for admins): Views, Clicks, Shares, Comments by post, aggregated over time
- **Analytics dashboard**: Follower demographics by company size, country, function, industry, seniority [7]
- **Lead Gen Forms**: Organic forms appearing below the About section, collecting name, company, job title, email [8]

### Premium/Free Tier Gating
- **Free**: All company pages are free to view. Basic analytics for page admins.
- **Premium Company Pages**: Enhanced features, custom CTA analytics, lead gen form analytics.
- **LinkedIn Sales Navigator**: Deep prospecting, InMail, advanced search — $99+/month.
- **Gating strategy**: LinkedIn **does not gate content viewing** — it gates *actions* (messaging, detailed analytics, lead gen).

### CTA Placement & Hierarchy
1. **Primary**: "Follow" (top-right, persistent)
2. **Secondary**: Custom CTA (admin-configurable, also top-right)
3. **Tertiary**: "View jobs" / "Visit website" / Message (if connected)
4. **In-feed**: Sponsored content and job postings

### Mobile Adaptation
- **Mobile-first design**: LinkedIn's company page is natively responsive. The banner and logo are touch-optimized.
- **Sticky bottom bar** on mobile for primary actions (Follow, Message, CTA).
- **Tabbed navigation**: About, Jobs, Posts, Products — swipeable on mobile.
- **Vertical stacking**: All content reflows to single column. The CTA remains prominent.

### Effectiveness Analysis
- **Effective**: The **custom CTA button** is a powerful, underutilized conversion tool. The mobile experience is polished. The social proof (follower count, employee trends) builds trust instantly.
- **Ineffective**: LinkedIn pages are **shallow for intelligence gathering**. No financial data, no predictive scoring, no competitive comparison. The "About" section is often marketing fluff. For opportunity assessment, LinkedIn is a starting point, not a destination.
- **What to steal**: The **custom CTA with analytics** is a perfect model for OppGrid's tiered CTAs. The **testimonial showcase** could be adapted for "user validations" or "success stories." The mobile tabbed navigation is a clean pattern for OppGrid's detail page sections.

### Citations
[5] Social Media Today, "LinkedIn Adds New Custom CTA Buttons for Pages," Jun 2019. https://www.socialmediatoday.com/news/linkedin-adds-new-custom-cta-buttons-for-pages-helping-to-direct-visitor-a/557726/  
[6] LigoSocial, "LinkedIn Business Page Optimization: 10 Steps to More Engagement," Mar 2025. https://ligosocial.com/blog/linkedin-business-page-optimization-10-steps-to-more-engagement  
[7] Sprinklr Help Center, "LinkedIn Company Page Insights," Jun 2026. https://www.sprinklr.com/help/articles/company-page-insights/linkedin-company-page-insights/649aeb19efca565f6513b916  
[8] Social Media Examiner, "4 LinkedIn Company Page Features to Start Using Now," Jul 2022. https://www.socialmediaexaminer.com/4-linkedin-company-page-features-to-start-using-now/  

---

## 4. Wellfound (AngelList) — Startup Profile

### Overview
Wellfound (formerly AngelList Talent) is the leading startup hiring marketplace. While it spun off from AngelList Venture in 2022, it retains a strong startup discovery use case. Its profile design is **founder- and candidate-centric** rather than investor-centric.

### Above-the-Fold Content
- **Company name + logo + mission statement** (one paragraph, specific: "We're building X for Y")
- **Funding stage badge** (Seed, Series A, etc.)
- **Team size** and **Tech stack**
- **Culture + Perks** summary
- **Founder bios** with photos
- **Equity transparency**: Job listings show cash compensation + equity percentage upfront (e.g., "0.5%–1.5% equity") [9]
- **Team/office photos** (if available)

### Key Metrics & Visualization
- **Funding stage** as a progress-style badge
- **Company size** with growth trajectory
- **Tech stack** tags (React, Python, etc.)
- **Equity ranges** displayed as inline text in job listings — no complex charts, just radical transparency [9]
- **Profile completeness score** (algorithm uses this to determine search prominence; 100% complete profiles get featured in the 3.2M-subscriber newsletter) [10]
- **Analytics**: Profile views, application rates (for employers)

### Premium/Free Tier Gating
- **Free (Access)**: Unlimited job posts, branded profile, Track ATS, integrations with Greenhouse/Lever/Ashby/Workable.
- **Essentials ($149/month)**: Custom screening questions, advanced filters, response templates.
- **Recruit Pro ($499/month)**: Outbound sourcing, 3.2M+ candidate profiles, advanced filters, unlimited messaging.
- **Curated ($499/month + 20% success fee)**: Concierge sourcing with pre-vetted candidates.
- **Gating strategy**: Wellfound is **free for both candidates and employers** at the base level. Premium features are additive (more tools, not more data). This low-friction model has helped 25,000+ companies and 10M+ candidates join [9].

### CTA Placement & Hierarchy
1. **Primary**: "Apply" (for candidates) / "Post a Job" (for employers)
2. **Secondary**: "Connect ATS" / "Promote Listing"
3. **Tertiary**: "Share profile" / "Refer a friend"

### Mobile Adaptation
- Wellfound's mobile app is focused on job discovery. Company profiles are card-based with swipeable photo galleries.
- **Equity data is prominently displayed** on mobile — a key differentiator.
- **Direct messaging** from founders to candidates is a core mobile flow.

### Effectiveness Analysis
- **Effective**: The **equity transparency** is a genuinely unique trust signal. The profile completeness incentive drives high-quality data. The free-for-all model creates massive network effects.
- **Ineffective**: **No verified revenue** — founders enter whatever they want, making traction metrics unreliable. No predictive scoring. No market intelligence. The profile is purely descriptive, not analytical.
- **What to steal**: The **profile completeness algorithm** is brilliant — OppGrid could reward users (or data sources) for completing opportunity profiles. The **equity transparency model** could be adapted for "investment required" or "revenue potential" transparency on OppGrid opportunity cards.

### Citations
[9] ctaio.dev, "Wellfound (AngelList): Startup Jobs Guide (2026)," Apr 2026. https://ctaio.dev/en/job-portals/wellfound/  
[10] Pin.com, "How to Recruit on AngelList (Wellfound): Guide for In-House Teams," May 2026. https://www.pin.com/blog/recruit-angellist/  

---

## 5. G2 / Capterra — Product Detail Page

### Overview
G2 and Capterra (both owned by G2) are the dominant B2B software review platforms. They represent the **buyer-intent** side of business intelligence — users are actively evaluating solutions, not just researching companies.

### Above-the-Fold Content (G2)
- **Product name + logo + star rating** (out of 5)
- **Total review count** (e.g., "1,247 reviews")
- **G2 Grid® placement** — quadrant position (Leader, High Performer, Niche, Contender) with visual quadrant chart
- **"Visit Website"** and **"Request a Demo"** CTAs (prominent, often sponsored)
- **Category ranking** (e.g., "#1 in CRM Software")
- **Review sentiment summary** (pros/cons tags)
- **Seller profile** (company info, contact details)

### Key Metrics & Visualization
- **G2 Score**: Aggregated from satisfaction and market presence data, displayed as a large number with a circular progress indicator.
- **Star rating breakdown**: 5-star, 4-star, 3-star, 2-star, 1-star distribution as a horizontal bar chart.
- **Feature comparison grid**: Side-by-side feature checklist comparing the product to 1–3 competitors.
- **Market Presence chart**: X-axis = Satisfaction, Y-axis = Market Presence — the famous G2 Grid [11].
- **Review filtering**: By company size, role, industry, feature — with dynamic count updates.
- **Capterra comparison**: Up to 4 products compared side-by-side with features, pricing, pros/cons [12].

### Premium/Free Tier Gating
- **Free for buyers**: All reviews, comparisons, and Grid reports are free.
- **Paid for vendors**: Software providers pay for profile enhancement, sponsored placement, and lead generation ("G2 Vendor Solutions").
- **G2 Pro**: Enhanced analytics, buyer intent data, competitive insights — pricing varies.
- **Capterra PPC model**: Vendors bid for position; some reviewers note it feels "more like a CPC platform than a genuine review site" [12].
- **Gating strategy**: The platform is **fully open for readers**. Gating is on the vendor side (lead gen forms to download reports, contact sales).

### CTA Placement & Hierarchy
1. **Primary**: "Visit Website" / "Request a Demo" (top-right, vendor-sponsored)
2. **Secondary**: "Compare" (drives to side-by-side grid)
3. **Tertiary**: "Write a Review" (drives to review form, often incentivized)
4. **In-content**: "See all reviews" / "Read full review" (pagination)

### Mobile Adaptation
- G2's mobile site collapses the comparison grid into a swipeable carousel.
- Reviews are stacked vertically with "Helpful" thumbs-up buttons.
- The G2 Grid is simplified to a static image on mobile (not interactive).
- CTA buttons are full-width on mobile for thumb-friendly tapping.

### Effectiveness Analysis
- **Effective**: The **comparison grid** is the most powerful conversion tool — it lets buyers self-serve their evaluation. The **G2 Grid** is a brilliant visual shorthand for market position. Review filtering by role/company size makes feedback feel relevant.
- **Ineffective**: **Pay-per-click bias** creates trust issues — vendors with bigger budgets get more visibility. Review authenticity is sometimes questioned due to incentivized reviews. The pages can feel cluttered with vendor ads.
- **What to steal**: The **side-by-side comparison** is essential for OppGrid. Users should be able to compare 2–3 opportunities across metrics (feasibility, market size, competition, growth). The **star distribution histogram** could be adapted for "validation confidence" distribution. The **review filtering by persona** is a pattern OppGrid should copy for its "expert validation" feed.

### Citations
[11] G2.com, "G2 Grid® Scoring Methodology," accessed via multiple product pages, 2025–2026.  
[12] getoden.com, "G2 vs Capterra vs TrustRadius vs Gartner Peer Insights - Comparison," Dec 2025. https://getoden.com/blog/g2-vs-capterra-vs-trustradius-vs-gartner-peer-insights  

---

## 6. CB Insights — Company Intelligence Card

### Overview
CB Insights is the premium predictive intelligence platform for enterprise strategy and VC. Its signature feature is the **Mosaic Score**, a proprietary algorithm that predicts startup health and success probability with 83% accuracy [13].

### Above-the-Fold Content
- **Mosaic Score** (0–1000) displayed as a large, prominent number with color coding (e.g., 832 = "High")
- **Score trend**: "-22 points in the past 30 days" (historic context)
- **Commercial Maturity** score (1–5 scale, e.g., "4 out of 5 — Scaling")
- **Company description** (analyst-curated)
- **Quick facts**: Founded, HQ, Industry, Employees, Funding status
- **Left navigation**: Overview & Products, Financials [14]

### Key Metrics & Visualization
- **Mosaic Score breakdown**: Four sub-scores (0–1000 each) with visual gauges:
  - **Momentum**: Individual performance vs. peers (social media, news sentiment, web traffic, mobile app data)
  - **Market**: Industry health (funding, deals, sentiment, exit activity)
  - **Money**: Financial strength (burn rate, financing history, investor quality)
  - **Management**: Team quality (founding/management prior accomplishments) [13][15]
- **Exit Probability**: Broken out by IPO and M&A with probability percentages.
- **Customer Sentiment**: Client satisfaction scores and renewal likelihood.
- **Business relationships**: Customer, partner, vendor mapping.
- **Market Map integration**: Visual market map showing the company's position relative to competitors in a 2D space [16].
- **Collections/Advanced Search**: Mosaic scores can be applied at scale to sort/watchlist companies.

### Premium/Free Tier Gating
- **Pricing**: ~$60,000+/year for enterprise access. No self-serve free tier.
- **Gating strategy**: CB Insights is **fully walled**. No public profiles. All data requires subscription. The platform does offer **Scouting Reports** and **market maps** as gated content marketing (email required).
- **Browser extension**: "ChatCBI" AI assistant provides instant insights while viewing a company's website — a clever top-of-funnel acquisition tool [17].

### CTA Placement & Hierarchy
1. **Primary**: "Request a demo" / "Start free trial"
2. **Secondary**: "Download market map" (gated)
3. **Tertiary**: "ChatCBI" (AI assistant for logged-in users)
4. **In-content**: "Run Market Research Agent" (AI-powered analysis)

### Mobile Adaptation
- CB Insights offers a **mobile app** with predictive AI on the phone.
- The Mosaic Score and key alerts are surfaced as push notifications.
- The full platform is complex; mobile is optimized for "quick checks" rather than deep analysis.
- G2 reviewers note the interface is "clunky" and advanced search requires significant training [17].

### Effectiveness Analysis
- **Effective**: The **Mosaic Score is the most sophisticated predictive metric** in the industry. The four-factor breakdown provides genuine analytical depth. The **market map integration** is visually compelling for thesis-driven investors. The AI assistant (ChatCBI) is a forward-looking feature.
- **Ineffective**: The **price point ($60K+) excludes SMBs and individual entrepreneurs**. The UI complexity is a barrier to adoption. The complete paywall means no organic discovery or SEO traffic. G2 reviewers specifically flag the "clunky" interface and steep learning curve [17].
- **What to steal**: The **4-factor score breakdown** is the perfect model for OppGrid's 4 P's (Product, Price, Place, Promotion). Instead of a single feasibility score, OppGrid should show sub-scores with explanations. The **market map visualization** is a high-value feature for showing where an opportunity sits in the competitive landscape. The **AI assistant** pattern (ChatCBI) aligns with OppGrid's AI Copilot vision.

### Citations
[13] CB Insights, "About Mosaic Health," Aug 2024. https://www.cbinsights.com/mosaic-health/  
[14] CB Insights public profile preview for statpile, accessed via search, 2025. https://www.cbinsights.com/company/statpile  
[15] CB Insights Research Blog, "Moneyball For Startups — CB Insights Lands $1.15M From NSF And Launches Mosaic," Aug 2015. https://www.cbinsights.com/research/team-blog/mosaic-moneyball-for-startups/  
[16] Crustdata Blog, "7 Best Startup Databases for Investors in 2026," May 2026. https://crustdata.com/blog/7-best-startup-databases-for-investors-in-2026  
[17] 11x.ai, "Top 10 Owler Alternatives for Sales Intel & Triggers," Jan 2026. https://www.11x.ai/sales-tools/owler  

---

## Cross-Platform Pattern Matrix

| Feature | Crunchbase | PitchBook | LinkedIn | Wellfound | G2/Capterra | CB Insights |
|---------|------------|-----------|----------|-----------|-------------|-------------|
| **Predictive Score (Above Fold)** | ✅ Growth/Heat | ✅ Opportunity Score | ❌ | ❌ | ✅ G2 Score | ✅ Mosaic Score |
| **Score Sub-Components** | ✅ (Contributing factors) | ✅ (Exit type) | ❌ | ❌ | ✅ (Satisfaction + Presence) | ✅ (4 M's) |
| **Side-by-Side Comparison** | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Freemium Data Tier** | ✅ (Generous) | ❌ (Hard paywall) | ✅ (Free viewing) | ✅ (Free core) | ✅ (Free reading) | ❌ (Fully walled) |
| **Contextual Gating** | ✅ (Per-section) | ❌ (Page-level) | ❌ (Action-gated) | ❌ (Feature-gated) | ❌ (Vendor-gated) | ❌ (Fully walled) |
| **Custom CTA** | ❌ | ❌ | ✅ (Admin config) | ❌ | ✅ (Vendor-sponsored) | ❌ |
| **Non-Financial Signals** | ✅ (Tech stack, traffic) | ✅ (Web, social, jobs) | ❌ | ❌ | ❌ | ✅ (Patents, news, jobs) |
| **Mobile-Native Design** | ✅ (App + responsive) | ❌ (Desktop-first) | ✅ (Responsive) | ✅ (App-centric) | ✅ (Responsive) | ✅ (App for alerts) |
| **Social Proof (Followers/Validations)** | ✅ (Profile activity) | ❌ | ✅ (Followers) | ✅ (Profile views) | ✅ (Review count) | ❌ |
| **AI Assistant / Copilot** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (ChatCBI) |
| **Review/Validation Aggregation** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Market Map Visualization** | ❌ | ❌ | ❌ | ❌ | ✅ (Grid) | ✅ (Market Map) |
| **Progressive Disclosure (Tabs/Nav)** | ✅ (Left nav) | ✅ (Sections) | ✅ (Tabbed) | ✅ (Scroll sections) | ✅ (Tabbed) | ✅ (Left nav) |
| **Estimated Annual Cost** | $348–$588/user | $25,000+ | Free–$1,200/user | Free–$499/mo | Free–$10,000+ (vendor) | $60,000+ |

---

## Recommended Feature Stack for OppGrid's Opportunity Detail Card

Based on the competitive analysis, the following features are prioritized by **impact** and **feasibility** for OppGrid's existing architecture.

### P0 — Implement Immediately (High Impact, Low Effort)

1. **Sub-Score Breakdown for Feasibility Score**
   - **What**: Decompose OppGrid's `feasibility_score` into 4 P's sub-scores (Product, Price, Place, Promotion) with visual gauges, CB Insights-style.
   - **Why**: CB Insights' Mosaic Score is the gold standard. OppGrid already has 4 P's data — it just needs to be surfaced as a breakdown.
   - **Where**: Above the fold, next to the main score badge.
   - **Evidence**: CB Insights users rely on sub-scores for initial screening; G2 reviewers call it "the most powerful way to use the platform" [13][17].

2. **Contextual Preview Snippets (Replace Full Blur Locks)**
   - **What**: Instead of blurring entire sections with "Upgrade to Unlock," show 2–3 preview data points (e.g., "2 more pain points — including a CRITICAL severity finding") with an upgrade CTA.
   - **Why**: Crunchbase's contextual gating converts better than PitchBook's hard locks. The current OppGrid blur overlay is intimidating.
   - **Where**: Problem Detail and Research Dashboard sections.
   - **Evidence**: Crunchbase's "top contributing factors" preview for predictions drives Pro upgrades [1].

3. **Opportunity Comparison (Side-by-Side)**
   - **What**: Allow users to select 2–3 opportunities from their watchlist or search results and compare them across feasibility, market size, competition, growth, and 4 P's scores.
   - **Why**: G2/Capterra's comparison feature is their highest-engagement tool. PitchBook's comparison is a key differentiator.
   - **Where**: New "Compare" button on OpportunityCard and OpportunityDetail header.
   - **Evidence**: G2 comparison pages drive 3x longer session times; Capterra users call it "effortless" [12].

### P1 — Implement Next Quarter (High Impact, Medium Effort)

4. **Non-Financial Signal Badges**
   - **What**: Add small, auto-generated badges for web traffic growth, search interest trend, Reddit sentiment, and job posting growth — similar to PitchBook's Signals section.
   - **Why**: PitchBook's non-financial metrics (Similarweb, Majestic) are cited as a key reason for its $25K+ price point. These signals are available via APIs.
   - **Where**: Inline with the Market Intelligence badges on the detail page.
   - **Evidence**: PitchBook's "Signals" section appears on every profile and is a major selling point [3].

5. **User Validation as Social Proof**
   - **What**: Surface the number of users who have validated/saved an opportunity, with a breakdown by user type ("12 entrepreneurs validated this"). Add a "Recent validations" activity feed.
   - **Why**: LinkedIn's follower counts and Crunchbase's "profile activity" build trust. Wellfound's profile views drive engagement.
   - **Where**: Below the score badge, and as a tab in the Research Dashboard.
   - **Evidence**: LinkedIn pages with featured testimonials see 35% higher conversion [6].

6. **Adaptive CTA Hierarchy**
   - **What**: Dynamic primary CTA based on user state:
     - Free/unauth: "Unlock Full Analysis ($15)" or "Sign Up to Save"
     - Pro (unlocked): "Deep Dive WorkHub" or "Generate Report"
     - Enterprise: "Contact Analyst" or "Export to Workspace"
   - **Why**: LinkedIn's custom CTA is one of its most powerful (and underutilized) features. One-size-fits-all CTAs miss conversion opportunities.
   - **Where**: Top-right of the header, sticky on mobile.
   - **Evidence**: LinkedIn's custom CTA analytics allow admins to test and optimize conversion paths [5].

### P2 — Strategic Investments (High Impact, High Effort)

7. **Predictive Trend Graphs**
   - **What**: Interactive line charts showing opportunity momentum over time (validation velocity, search interest, traffic growth) with annotated events ("Featured in Reddit thread," "New competitor entered").
   - **Why**: Crunchbase's performance graph is a core differentiator. Static numbers feel stale; trends feel alive.
   - **Where**: New "Momentum" tab in the Research Dashboard.
   - **Evidence**: Crunchbase's graph "helps users understand the momentum of the company and the historical events that led to the current growth" [1].

8. **Market Map Integration**
   - **What**: A 2D scatter plot positioning the opportunity against peers on axes like "Feasibility vs. Market Size" or "Growth vs. Competition."
   - **Why**: CB Insights' market maps are a premium feature that justifies $60K+ pricing. It's visually compelling and thesis-building.
   - **Where**: New "Landscape" tab in the Research Dashboard.
   - **Evidence**: CB Insights' market maps are "genuinely useful for thesis development, more substantive than what you'd assemble manually" [16].

9. **AI Copilot Panel (Chat-style)**
   - **What**: A persistent AI assistant on the detail page that answers questions like "Why is the competition score high?" or "What are the top 3 risks?" — similar to CB Insights' ChatCBI.
   - **Why**: CB Insights' ChatCBI is its most praised new feature. It reduces the learning curve and increases data utilization.
   - **Where**: Right sidebar on desktop, bottom sheet on mobile.
   - **Evidence**: CB Insights' AI assistant "uses proprietary data and automates tasks with its Magic Mode" [17].

10. **Mobile-First Card Layout**
    - **What**: Redesign the detail page as a stack of swipeable cards for mobile, with each card representing a section (Overview, Problem, Market, Competition, Solutions).
    - **Why**: Every platform analyzed treats mobile as a second-class citizen. A native-feeling mobile experience would be a genuine differentiator for field researchers and entrepreneurs.
    - **Where**: Responsive redesign of OpportunityDetail.tsx.
    - **Evidence**: LinkedIn is the only platform with a truly polished mobile experience; it sees 60%+ of engagement on mobile [7].

---

## What *Not* to Copy

| Platform Pattern | Why OppGrid Should Avoid It |
|------------------|------------------------------|
| **PitchBook's hard paywall** | OppGrid's current two-tier model is better. Hard paywalls kill organic growth and SEO. |
| **CB Insights' $60K+ pricing** | OppGrid's freemium + pay-per-unlock model is more accessible. Don't fully wall content. |
| **G2's pay-per-click vendor bias** | OppGrid's data should be algorithmic, not auction-based. Never let vendors pay for placement. |
| **Wellfound's unverified revenue** | Any traction metric on OppGrid must be data-backed, not founder-entered. Trust is the currency. |
| **LinkedIn's shallow intelligence** | OppGrid must go deeper than brand pages. Surface real market data, not just descriptions. |

---

## Conclusion

The most successful B2B intelligence platforms share three principles: **compress complexity into scores, disclose depth progressively, and gate contextually rather than absolutely.** OppGrid's existing OpportunityDetail page already has strong bones — the two-tier structure, the 4 P's data model, and the problem-centric narrative are all differentiated. The next evolution should focus on:

1. **Making the score explainable** (sub-components, trends, contributing factors)
2. **Making comparison effortless** (side-by-side, market maps)
3. **Making the mobile experience native** (card stacks, swipeable sections)
4. **Making social proof visible** (validation counts, expert activity, recency signals)

These investments will move OppGrid from a "report generator" to a **living intelligence platform** — the standard that Crunchbase, PitchBook, and CB Insights have set, but accessible to the entrepreneurs and small businesses they ignore.

---

## Appendix: Full Citation Index

[1] Crunchbase Support, "Navigating a company profile on Crunchbase," Aug 2025. https://support.crunchbase.com/hc/en-us/articles/360052260893  
[2] Clay Blog, "Crunchbase vs. PitchBook: Key Differences Compared," 2026. https://www.clay.com/blog/crunchbase-vs-pitchbook  
[3] PitchBook public profile previews (Parallel Domain, London Dynamics, Dink, Nuwa Robotics), 2025–2026. https://pitchbook.com/profiles/company/  
[4] 11x.ai, "Top 10 PitchBook Alternatives for Sales Intelligence," Jan 2026. https://www.11x.ai/sales-tools/pitchbook  
[5] Social Media Today, "LinkedIn Adds New Custom CTA Buttons for Pages," Jun 2019. https://www.socialmediatoday.com/news/linkedin-adds-new-custom-cta-buttons-for-pages-helping-to-direct-visitor-a/557726/  
[6] LigoSocial, "LinkedIn Business Page Optimization: 10 Steps to More Engagement," Mar 2025. https://ligosocial.com/blog/linkedin-business-page-optimization-10-steps-to-more-engagement  
[7] Sprinklr Help Center, "LinkedIn Company Page Insights," Jun 2026. https://www.sprinklr.com/help/articles/company-page-insights/linkedin-company-page-insights/649aeb19efca565f6513b916  
[8] Social Media Examiner, "4 LinkedIn Company Page Features to Start Using Now," Jul 2022. https://www.socialmediaexaminer.com/4-linkedin-company-page-features-to-start-using-now/  
[9] ctaio.dev, "Wellfound (AngelList): Startup Jobs Guide (2026)," Apr 2026. https://ctaio.dev/en/job-portals/wellfound/  
[10] Pin.com, "How to Recruit on AngelList (Wellfound): Guide for In-House Teams," May 2026. https://www.pin.com/blog/recruit-angellist/  
[11] G2.com, "G2 Grid® Scoring Methodology," 2025–2026. https://www.g2.com/  
[12] getoden.com, "G2 vs Capterra vs TrustRadius vs Gartner Peer Insights - Comparison," Dec 2025. https://getoden.com/blog/g2-vs-capterra-vs-trustradius-vs-gartner-peer-insights  
[13] CB Insights, "About Mosaic Health," Aug 2024. https://www.cbinsights.com/mosaic-health/  
[14] CB Insights public profile preview for statpile, 2025. https://www.cbinsights.com/company/statpile  
[15] CB Insights Research Blog, "Moneyball For Startups — CB Insights Lands $1.15M From NSF And Launches Mosaic," Aug 2015. https://www.cbinsights.com/research/team-blog/mosaic-moneyball-for-startups/  
[16] Crustdata Blog, "7 Best Startup Databases for Investors in 2026," May 2026. https://crustdata.com/blog/7-best-startup-databases-for-investors-in-2026  
[17] 11x.ai, "Top 10 Owler Alternatives for Sales Intel & Triggers," Jan 2026. https://www.11x.ai/sales-tools/owler  
[18] Plusvibe.ai, "Did You Know Crunchbase and PitchBook Offer These Key Features?" Jul 2024. https://plusvibe.ai/blog/crunchbase-and-pitchbook  
[19] Veridion.com, "S&P Global Alternatives Offering Private Company Data," Oct 2024. https://veridion.com/blog-posts/sp-global-alternatives/  
[20] lpbacked.com, "PitchBook vs Preqin 2026: Which Wins for LP Fundraising?" Feb 2026. https://lpbacked.com/alternatives/vs/pitchbook-vs-preqin  
