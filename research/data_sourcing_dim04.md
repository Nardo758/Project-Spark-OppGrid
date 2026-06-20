# DIM04 — Data Sourcing: The Economist's Analysis

## 1. Core Position

The B2B data enrichment market operates as a **monopolistic-competition trap**: it is large enough to attract endless entrants (Apollo.io, Lusha, Cognism, Clay) yet structured so that the dominant incumbent (ZoomInfo) extracts rents through opaque pricing and contractual lock-in, while the underlying commodity—contact data—decays at roughly 22% annually and cannot be reliably verified before purchase. For a platform operator, this means that every dollar spent on third-party B2B data is a bet on vendor reputation rather than verifiable quality, and the economics strongly favor **arbitraging multiple low-cost sources** over signing a five-figure annual contract with a single provider whose "data moat" is mostly marketing fiction.

## 2. Strongest Evidence Supporting This View

### Market Structure: Monopolistic Competition with a Dominant Rent-Extractor

The global data broker market is massive—valued at approximately **$290–$342 billion in 2025** and projected to reach **$473–$656 billion by 2032–2031** [^1][^2][^3]. Yet the B2B sales intelligence segment specifically is a tiny fraction of this, estimated at only **$4.1–$4.9 billion in 2025** [^4][^5]. This disparity is crucial: the B2B contact-data niche is a small pond within an ocean, which is why ZoomInfo can dominate the narrative while dozens of challengers eat the low end. The market exhibits classic monopolistic competition—many sellers, differentiated branding, but the core product (contact records) is largely fungible. M&A activity confirms this: HubSpot acquired Clearbit in late 2023 to embed enrichment into its CRM, effectively removing a standalone competitor from the market [^6]. Experian acquired AtData in February 2026 to add 10 billion email addresses [^7]. Publicis acquired LiveRamp for $2.2 billion in May 2026 [^7]. The strategic imperative is consolidation, not innovation, because data at scale is a commodity that survives only through lock-in.

### Pricing Power: How ZoomInfo Raises Prices 10–20% at Renewal

ZoomInfo's pricing power is not derived from data quality but from **contractual architecture and switching costs**. The median ZoomInfo contract runs **$31,875 per year** across verified purchases, with Professional plans starting at **$14,995/year**, Advanced at **$24,995/year**, and Elite at **$39,995+** [^8]. Real-world costs quickly escalate to **$30,000–$60,000 annually** once add-ons (intent data, international data passport, API access, credit overages) are included [^8]. Critically, renewal increases of **10–20% are standard**, with some buyers reporting **20–40% jumps** at renewal [^8][^9]. Contracts are annual-only with mandatory auto-renewal and a **60–90 day cancellation window**—miss it by one day and you're locked in for another year at a higher rate [^8]. This is not pricing power from superior value; it is pricing power from **friction and legal lock-in**. The ZoomInfo 10-K reveals that in 2023, sales and marketing expenses alone exceeded **$500 million**, indicating that customer acquisition is a massive cost center that must be recovered through aggressive renewal pricing [^10].

### Net Revenue Retention: The Canary in the Coal Mine

ZoomInfo's Net Revenue Retention (NRR) collapsed from a peak of **116%** to **85% in FY2024**, recovering only slightly to **87–90%** by 2025–2026 [^11][^12][^13]. An NRR below 100% means the existing customer base is shrinking, and the company must acquire new customers just to tread water. This is catastrophic for a SaaS business: the peer median for sales and marketing tech is **97%**, leaving ZoomInfo **7 percentage points below** healthy competitors [^11]. The decline was driven by SMB cohort collapse while enterprise expansion masked the underlying churn—what analysts call "mean-NRR masking" [^12]. In Q4 2024, ZoomInfo's CEO admitted the company was "migrating customers over to Copilot" at renewal time to drive "pricing discipline" and prevent downsell [^13]. The auto-renewal policies have been so aggressive that ZoomInfo was **sued by a shareholder in September 2024** for allegedly using "manipulative and coercive" tactics to hide customer churn [^14]. This is not the behavior of a company with durable pricing power; it is the behavior of a vendor fighting to maintain revenue as customers discover alternatives.

### Information Asymmetry: The "Lemons Problem" in Data Markets

The economics of data markets suffer from acute information asymmetry. Buyers cannot verify data quality before purchase, and sellers have every incentive to prioritize quantity over accuracy. Academic research on data marketplaces simulates three seller types—honest, strategic, and predatory—and finds that **predatory sellers extract the highest profits ($13,650) while driving buyer surplus deeply negative (−$2,353)**; honest markets produce positive buyer surplus (+$3,196) but the lowest seller profits ($5,282) [^15]. In opaque markets, even sophisticated buyers perform no better than naive ones, and transparency improves surplus by only ~8% because the fundamental price-quality asymmetry persists [^15]. A separate study on data provider pricing strategies under quality information asymmetry finds that "the increased information asymmetry and inefficient data production make data providers more inclined to generate low-quality datasets, which adversely affects the data trading market" [^16]. This is the structural reality: **vendors are rewarded for database size, not accuracy**, because buyers have no efficient way to audit the 500 millionth contact record.

### Data Decay: The Hidden Cost of "More Data"

B2B contact data decays at approximately **2.1% per month**, or **22% annually** [^17][^18]. In high-turnover industries, decay rates can spike to **60–70% per year** [^17]. Gartner estimates that **poor data quality costs organizations $12.9 million annually** on average [^17][^18]. SignalHire analysis reveals that **30% of B2B contact records go stale within 12 months**, costing sales teams an average of **546 hours per year** in lost productivity [^19]. The fastest-decaying fields are job titles, direct phone numbers, and work email addresses [^19]. This means a platform operator paying $30,000/year for a database is effectively renting a depreciating asset with a half-life of roughly three years. The "more data = better" narrative is economically absurd: **the marginal record is likely stale, and the vendor's incentive is to inflate count metrics rather than refresh cadence** because renewal contracts are signed based on database size claims, not accuracy audits.

### Data Network Effects: Overstated and Fragile

The "data moat" narrative assumes that more data leads to better models, which leads to more users, which generates more data—a virtuous flywheel. This is theoretically appealing but empirically weak in B2B data markets. As one industry analysis bluntly puts it: **"data moat is bullshit"** [^20]. The data generated through product interactions is "deeply entangled with private customer data. You can't export it, can't reuse it safely. I haven't seen a single vertical AI company with a real data moat built this way" [^20]. The Google two-sided market literature makes a finer point: not all platforms exhibit true network effects. Search quality improvements from more queries are "learning economies," not network externalities, because a user's utility does not depend on the *future* number of users [^21]. In B2B data, the same logic applies: having 500 million contacts does not make the 500 million-and-first contact more valuable to a buyer. The "moat" is a marketing construct that justifies higher prices, not an economic barrier. Data is non-rivalrous and non-excludable; once scraped, it can be replicated by competitors at near-zero marginal cost.

### Regulatory Arbitrage: Following the Compliance Cost Gradient

Data brokers operate in a fragmented regulatory landscape that creates significant cost differentials. The EU's GDPR imposes fines of up to **€20 million or 4% of global revenue**, whichever is higher [^22][^23]. Estimated GDPR compliance costs for firms range from **$3 million to $13.2 million**, with ongoing costs that do not diminish over time [^24]. By contrast, the CCPA's penalties are far weaker—**$2,500–$7,500 per violation**—with no maximum aggregate penalty [^22][^23]. In 2025–2026, EU regulators imposed **€1.2 billion in GDPR fines**, while CCPA enforcement totaled only **$50 million** [^25]. This **83:1 enforcement ratio** creates a massive incentive for data brokers to structure operations in lower-compliance jurisdictions. The practical result is that US-based B2B data vendors (ZoomInfo, Apollo, Lusha) operate under a lighter regulatory burden than their EU counterparts, allowing them to sell data with lower consent-verification costs. Cognism, for example, differentiates itself by being "GDPR-compliant," which is essentially a way to charge a premium for doing what EU law requires anyway [^26]. For a platform operator, this means that **buying from US vendors may expose you to data of dubious provenance**, while buying from EU-verified vendors carries a compliance premium that is rarely priced transparently.

### The Opportunity Cost of Building vs. Buying

For a platform operator considering whether to build proprietary data infrastructure or buy from brokers, the economics are stark. Building in-house data infrastructure for a mid-market operation costs **$305,000–$610,000+ in year one** (salaries, cloud, tools, recruiting), with a **6–9 month time-to-first-dashboard** [^27]. Buying a managed platform costs **$60,000–$200,000** in year one with a **2–3 week time-to-value** [^27]. The gap widens in year two because internal builds carry full salary loads plus maintenance, while managed platform costs stay flat or scale only with usage [^27]. However, the "buy" path creates **vendor dependency and data lock-in**—the same ZoomInfo contracts include a data destruction clause that requires deletion of all exported contacts when the contract ends [^8]. For a platform like OppGrid, the optimal strategy is neither pure build nor pure buy: it is to **build lightweight scraping and enrichment infrastructure for publicly available data** (government filings, LinkedIn, company websites) while **buying only narrowly targeted, high-accuracy data** from low-cost providers (Apollo at $49/user/month, Lusha at $37–49/month) rather than signing enterprise contracts with ZoomInfo.

## 3. The One Thing No Other Perspective Would Tell Me

**The "data moat" is not just overstated—it is a liability disguised as an asset.** Every platform operator chasing "proprietary data" as a competitive advantage is actually accumulating a **depreciating, legally toxic inventory**. B2B contact data decays at 22% annually, but more importantly, the regulatory winds are shifting: the EU-U.S. Data Privacy Framework remains legally uncertain, 20 U.S. state privacy laws are now active, and the CFPB is targeting data brokers under the Fair Credit Reporting Act [^28]. A dataset that is legal to hold today may require expensive consent remediation, deletion, or regulatory disclosure tomorrow. The hidden cost of a "data moat" is **compliance risk compounding invisibly on your balance sheet**.

Here is the unexploited arbitrage opportunity: **platform operators should stop buying contact databases and start buying *signal infrastructure***. Instead of paying ZoomInfo $30,000/year for 5,000 credits of static contact data, pay Apollo.io $49/month for access, use free government APIs (SEC EDGAR, Companies House, USPTO, SAM.gov) for firmographic data, and invest in **real-time event detection** (funding announcements, job changes, procurement awards) that signals *timing* rather than *identity*. The economic insight is that **the value of B2B data is not in the contact record but in the timing of the outreach**. A smaller, fresher dataset of 1,000 contacts with high-intent triggers is worth more than 500,000 stale email addresses. The vendors know this—they charge premiums for "intent data" and "buying signals" because they know raw contact data is commoditized. But you can replicate intent signals cheaply by monitoring public data feeds (LinkedIn job changes, SEC filings, government contract awards) and combining them with low-cost enrichment. The data brokers' real profit center is **selling you the same public information repackaged with a 10x markup**. Build the signal-detection layer yourself, buy the contact lookup layer cheaply, and leave the enterprise data contracts to the CFOs who haven't read the NRR disclosures.

---

## Footnotes

[^1]: Grand View Research. "Data Broker Market Size & Share Report, 2025–2033." 2025. https://www.grandviewresearch.com/industry-analysis/data-broker-market-report

[^2]: Mordor Intelligence. "Data Broker Market Size & Share Analysis, 2026–2031." 2026. https://www.mordorintelligence.com/industry-reports/data-broker-market

[^3]: Knowledge Sourcing Intelligence. "Global Data Broker Market Forecasts from 2025 to 2030." 2026. https://www.knowledge-sourcing.com/report/global-data-broker-market

[^4]: Fortune Business Insights. "Sales Intelligence Market Size, Share & Statistics, 2026–2034." 2026. https://www.fortunebusinessinsights.com/sales-intelligence-market-109103

[^5]: Mordor Intelligence. "Sales Intelligence Market Size, Growth, Share & Industry Report 2031." 2026. https://www.mordorintelligence.com/industry-reports/sales-intelligence-market

[^6]: CB Insights. "M&A Strategy Teardown: Why Did HubSpot Acquire Clearbit?" 2023. https://www.cbinsights.com/research/ma-strategy-teardown-hubspot-clearbit/

[^7]: Knowledge Sourcing Intelligence. "Data Broker Market Insights: Growth, Trends, Forecast 2031." 2026. https://www.knowledge-sourcing.com/report/global-data-broker-market

[^8]: Pin. "ZoomInfo Pricing 2026: Plans, Costs, and Alternatives." 2026. https://www.pin.com/blog/zoominfo-pricing/

[^9]: Skrapp.io. "ZoomInfo Pricing: Is It Worth It in 2025?" 2025. https://skrapp.io/blog/zoominfo-pricing/

[^10]: ZoomInfo Technologies Inc. Form 10-K, Annual Report. SEC Filing, February 15, 2024. https://fintel.io/doc/sec-zoominfo-technologies-inc-1794515-10k-2024-february-15-19768-2660

[^11]: Cust.co. "ZoomInfo NRR: 90% · FY2026-Q1." 2026. https://cust.co/companies/zoominfo/

[^12]: PulseRevOps. "How Do I Calculate LTV When Expansion Is Meaningful?" 2026. https://pulserevops.com/knowledge/q105

[^13]: Investing.com. "Earnings Call Transcript: ZoomInfo Q4 2024." 2025. https://ca.investing.com/news/transcripts/earnings-call-transcript-zoominfo-q4-2024-beats-earnings-forecast-stock-surges-93CH-3866656

[^14]: Bloomberg Law. "ZoomInfo Shareholder Sues Over Customer Churn After Pandemic." 2024. https://news.bloomberglaw.com/securities-law/zoominfo-shareholder-sues-over-customer-churn-following-pandemic

[^15]: Clawrxiv. "Information Asymmetry in AI Data Markets: When Data Sellers Exploit Bayesian Buyers." 2026. https://clawrxiv.io/abs/2604.00675

[^16]: Xing, A. & Wang, H. "Pricing and sample set strategies of data providers under quality information asymmetry." *Journal of the Operational Research Society*, 75(2), 278–296, 2024. https://ideas.repec.org/a/taf/tjorxx/v75y2024i2p278-296.html

[^17]: Landbase. "Why B2B Data Goes Stale." 2025. https://www.landbase.com/blog/why-b2b-data-goes-stale

[^18]: Databar.ai. "The Complete Guide to CRM Data Quality." 2026. https://databar.ai/blog/article/the-complete-guide-to-crm-data-quality-metrics-standards-best-practices

[^19]: EIN Presswire / SignalHire. "SignalHire Data Reveals 30% of B2B Contact Records Go Stale Every Year." 2026. https://natlawreview.com/press-releases/signalhire-data-reveals-30-b2b-contact-records-go-stale-every-year-database

[^20]: Unique.ai. "The Myth of the Data Moat in Vertical AI." 2025. https://www.unique.ai/en/blog/the-myth-of-the-data-moat-in-vertical-ai

[^21]: Luchetta, G. "Is the Google Platform a Two-Sided Market?" EconStor, 2012. https://www.econstor.eu/bitstream/10419/60367/1/720236207.pdf

[^22]: FPF. "Comparing Privacy Laws: GDPR v. CCPA." 2018. https://fpf.org/wp-content/uploads/2018/11/GDPR_CCPA_Comparison-Guide.pdf

[^23]: Clifford Chance. "GDPR Compliance for US Corporations, Funds, and Broker-Dealers." 2018. https://www.cliffordchance.com/content/dam/cliffordchance/briefings/2018/01/gdpr-compliance-for-us-corporations-funds-and-brokerdealers.pdf

[^24]: Demirer, V. et al. "Data, Privacy Laws and Firm Production: Evidence from the GDPR." 2023. https://www.diegojimenezh.com/assets/pdf/Demirer_et_al2023_Privacy.pdf

[^25]: Track360. "Affiliate Marketing Compliance: GDPR, LGPD, CCPA 2026." 2026. https://track360.io/blog/multi-region-affiliate-compliance-gdpr-lgpd-bets-angb-2026

[^26]: Cognism. "Cognism vs Clearbit in 2026." 2024. https://www.cognism.com/cognism-vs-clearbit

[^27]: Saras Analytics. "Why Most $20M+ DTC Brands Regret Building Data Infrastructure In-House." 2026. https://www.sarasanalytics.com/blog/why-most-20m-dtc-brands-regret-building-data-infrastructure-in-house

[^28]: Grand View Research. "Data Broker Market Report: CFPB Oversight Measures." 2026. https://www.grandviewresearch.com/industry-analysis/data-broker-market-report
