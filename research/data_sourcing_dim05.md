# THE HISTORIAN — Dimension 05: Other Places to Source Data

## Core Position

Today's B2B data sourcing frenzy is replaying the exact cycle that transformed thousands of local credit bureaus into three national oligopolists between 1960 and 1990: a gold rush of data collection, followed by technological consolidation, then regulatory crackdown, and finally commoditization of what was once proprietary. For platform operators, this means that spending heavily to acquire or scrape third-party data is a temporary advantage at best—historically, the durable winners are those who build proprietary data generation into their core workflow, not those who rent, buy, or scrape what others already have.

---

## Strongest Evidence Supporting My View

### 1. The Credit Bureau Consolidation: From Thousands to Three

In the 1960s, the United States had thousands of local credit bureaus—often literally clipping wedding announcements from newspapers to build consumer profiles. Computerization in the 1970s and 1980s triggered a brutal consolidation: only well-funded companies could afford the expensive mainframe systems and custom software required to operate at scale. As Josh Lauer, author of *Creditworthy*, documented, "Once consolidation began, smaller non-computerized bureaus simply could not compete with the speed, reduced cost, and growing geographical reach of computerized credit reporting networks."[^1] By the late 1990s, three firms—TransUnion, Experian, and Equifax—controlled the market. The political response was inevitable: the Fair Credit Reporting Act of 1970 (FCRA) was passed after public exposure of abuses, including investigators collecting "lifestyle" information on consumers, noting sexual orientation, couples "living out of wedlock," and even fabricating negative information.[^2] Regulation did not create competition; it cemented the incumbents' advantage by raising compliance costs that only giants could bear.

The parallels to today's B2B data market are exact. We are in the "thousands of local bureaus" phase—ZoomInfo, Apollo.io, Cognism, Crustdata, Clearbit, and dozens of others collecting similar firmographic and contact data. The consolidation phase has already begun. ZoomInfo acquired DiscoverOrg and RainKing. The question is not whether consolidation will happen, but who will be among the three left standing—and whether your platform's data sourcing strategy depends on assets that will soon be commoditized or acquired.

### 2. Dun & Bradstreet: The Fragility of a 150-Year Data Monopoly

Dun & Bradstreet is the most instructive case in business history for anyone building a "data moat." Founded in 1841, D&B achieved what appeared to be an unassailable monopoly on commercial credit information. After the Civil War, an industry shakeout left an oligopoly of R.G. Dun, the Bradstreet Company, and one or two others. When the two largest merged in 1933, D&B achieved what the World Bank described as "a monopoly on national credit-reporting."[^3] D&B's dominance was so extensive that for decades it was the "system of record for business information worldwide."[^4]

Yet even D&B's monopoly was vulnerable in two ways that directly mirror today's AI data landscape. First, the government can destroy a proprietary standard overnight. In 1996, the federal government required all companies doing business with it to obtain a DUNS number—D&B's proprietary identifier. This created a government-mandated monopoly worth over $20 million per year in sole-source contracts. But by 2012, the Government Accountability Office (GAO) concluded that D&B's monopoly "resulted in higher costs," limited government visibility into data accuracy, and restricted use due to proprietary constraints.[^5] In April 2022, the federal government ended the DUNS requirement entirely, replacing it with a free, government-owned Unique Entity Identifier (UEI). A monopoly that took 150 years to build was dismantled by a single procurement policy change. As Benedict Evans observed, a company's structural competitive advantage can be "ordered by a king to be knocked down."[^6]

Second, D&B failed to evolve its business model while it still had monopoly power. As one executive estimated, "80% of all D&B data was inaccurate, fabricated, or stale."[^7] D&B's processes remained largely unchanged for a century: thousands of telemarketers calling 200 million businesses annually. While D&B remained a "standard," it "did not transition into analytics."[^8] The lesson is brutal: a data monopoly without continuous quality improvement and analytical layering is just a directory waiting to be replaced.

### 3. Jigsaw / Data.com: The Crowdsourced Data Graveyard

Jigsaw launched in 2004 as a "Wikipedia-style" crowdsourced business contact platform. Users contributed and updated contact information, earning credits to access other contacts. It was genuinely innovative—by 2010, it claimed 21 million business professional profiles and 3 million company profiles, with 1.2 million active members. Salesforce acquired Jigsaw for $142 million in 2010, rebranded it as Data.com, and promised to revolutionize CRM data enrichment.[^9]

What happened next is a textbook case of why crowdsourced third-party data fails as a durable moat. Salesforce never invested in the product after acquisition. The "corporate tree" feature—Jigsaw's most valuable unique capability—was removed immediately due to liability concerns. By 2018, CEO Marc Benioff pulled the plug, giving users one year notice before shutting down Data.com Connect entirely in May 2019.[^10] The data quality was always mediocre: on average, only about 25% of leads for any given organization were valid. Competitors like ZoomInfo and DiscoverOrg (themselves now merged) grew by building proprietary research teams and verification infrastructure, not by relying on crowdsourced contributions.

Jigsaw's fate is the fate of any platform that relies on user-generated or third-party data without building proprietary collection workflows. The community contributed to Jigsaw for years, but when Salesforce decided the product was a "giant pickle" in its portfolio, the entire dataset was rendered worthless to users. Data that you do not control the sourcing of is data you do not truly own.

### 4. Acxiom and LiveRamp: The Pivot from Data Broker to Data Infrastructure

Acxiom, founded in 1969 using phone book mailing lists, became the world's largest commercial data broker, holding up to 3,000 data points on every U.S. consumer and 2.5 billion consumer profiles globally. But when the Cambridge Analytica scandal and GDPR transformed the regulatory landscape, Acxiom made a move that historians of business strategy will study for decades: it sold its data assets. In 2018, Acxiom divested its Marketing Solutions (data broker) division to Interpublic Group for $2.3 billion, rebranded the remaining company as LiveRamp, and pivoted to being a "neutral plumbing layer" for data onboarding and identity resolution.[^11]

This was not a retreat; it was an admission that raw data brokerage was becoming a regulated, commoditized liability. LiveRamp's CEO explicitly noted that GDPR "adds a massive amount of complexity and compliance to marketing," and that "more entrenched companies such as LiveRamp... will be beneficiaries" because smaller competitors cannot afford compliance costs.[^12] Facebook cutting ties with Acxiom in March 2018 caused Acxiom's shares to tumble 34% overnight—demonstrating that a data broker's value can evaporate the moment a major platform changes its data partnership policy.[^13] By 2026, LiveRamp itself was acquired by Publicis Groupe for $2.2 billion, having successfully transformed from a data owner into a data infrastructure provider.

The historical pattern is clear: owning raw data was the winning strategy in the unregulated era; enabling others to use their own data is the winning strategy in the regulated era. The platforms that will survive are not those that accumulate the most third-party data, but those that build the infrastructure for compliant, first-party data collaboration.

### 5. Yellow Pages: The Directory Value Collapse

The Yellow Pages telephone directory, born in 1883, was once so essential that it was delivered to every household. In the pre-internet era, it was the default source for finding plumbers, builders, and gardeners. Telstra's directories subsidiary, Sensis, was valued at approximately A$12 billion in 2005. CEO Sol Trujillo famously dismissed Google's threat with "Google Schmoogle."[^14] In 2014, Telstra sold a 70% stake of Sensis for A$454 million—just 2.4 times projected earnings. Google, meanwhile, grew tenfold.

The economics are unforgiving. The Yellow Pages provided generic, supplier-provided data. As the internet reduced search costs to zero, the value of static directories collapsed. Specialized sites—TripAdvisor for restaurants, Yelp for services, LinkedIn for professionals—provided richer, dynamic, user-generated information that static directories could never match. The Yellow Pages' paper directory ceased publication entirely in 2019.[^15]

This is the same dynamic threatening today's B2B data brokers. If your platform's value proposition is "we have a big database of company information," you are building a Yellow Pages in a LinkedIn world. Static firmographic data—headcount, revenue, industry codes—is increasingly available through open APIs, government filings, and LLMs that can extract structured information from unstructured text. The value of merely *having* the data is approaching zero; the value of *using* it in a proprietary workflow is what matters.

### 6. The Big Data Hype Cycle (2012–2016): Precedent for the AI Data Rush

Between 2012 and 2016, enterprises poured billions into "big data" initiatives, believing that accumulating massive datasets would automatically yield competitive advantage. Gartner estimated that 60% to 85% of big data projects failed.[^16] Data lakes, meant to be "large bodies of water in a more natural state" (as Pentaho CTO James Dixon described in 2010), turned into "data swamps"—expensive repositories of unstructured, unusable information.[^17] The NewVantage Partners 2020 survey found that although 98.8% of Fortune 1000 companies were investing in data initiatives, only 37.8% reported having built a data-driven organization.[^18]

The failure pattern was consistent: organizations accumulated data without governance, without analytical talent, and without clear use cases. As one analysis noted, "The ambiguity of the term and lack of tangible value from investments ascribed to it led to its eventual downfall."[^19] The same pattern is repeating today with AI training data. Companies are scrambling to acquire "proprietary datasets" without asking whether those datasets will actually improve model performance in a way that justifies the cost, or whether foundation models will soon render those datasets redundant.

### 7. Regulation: The Inevitable Consolidation Accelerator

The FCRA of 1970 was not the end of credit bureau regulation; it was the beginning. Comprehensive amendments followed in 1996 (Consumer Credit Reporting Reform Act), 2003 (FACTA), and 2010 (Dodd-Frank, which created the CFPB). Each wave of regulation raised compliance costs, making it harder for smaller bureaus to compete. The CFPB's December 2024 proposed rule to classify data brokers as credit reporting agencies under FCRA represents the latest expansion—one that, if implemented, would subject the entire B2B data enrichment industry to the same regulatory framework that cemented the three credit bureau oligopoly.[^20]

GDPR, enacted in 2018, demonstrates the same pattern in Europe. Studies consistently found that GDPR increased market concentration. One analysis found that GDPR led to a 17% increase in market concentration in the website vendor market, as smaller vendors disproportionately suffered from consent requirements and compliance costs.[^21] Another found that EU firms experienced 26% declines in data storage and 15% declines in data processing relative to comparable U.S. firms.[^22] The regulation that was meant to limit data brokers instead made it harder for small competitors to enter the market.

The lesson is unambiguous: regulation of data markets does not create a level playing field. It creates a moat for incumbents who can afford compliance infrastructure. If your platform's data sourcing strategy depends on thin-margin data aggregation or scraping, regulation will not save you from larger competitors—it will bury you.

### 8. The Economics of Information Goods: Why Data Moats Are Inherently Fragile

Carl Shapiro and Hal Varian, in their seminal 1998 work *Information Rules*, established the foundational economics of information markets: "Information is costly to produce but cheap to reproduce."[^23] This cost structure—high fixed costs, near-zero marginal costs—means that competitive markets tend to push prices toward marginal cost, which "can lead to devastating price wars and ruin."[^24] The only sustainable strategy is differentiation through versioning, speed, or proprietary workflow integration—not through accumulating raw data that competitors can replicate at trivial cost.

This is why "data moats" are far more fragile than they appear. A 2025 analysis bluntly stated: "When GPT-4 can reason about complex problems using training data from across the internet, your proprietary customer dataset stops being a castle wall and starts looking like a speed bump."[^25] The moat is not the data; it is the proprietary workflow that generates and acts on the data. Amazon's data moat is not its product database—it is its supply chain optimization powered by purchase history. Netflix's moat is not its movie list—it is its recommendation engine powered by viewing behavior.

### 9. Web Scraping and Legal Uncertainty: The Sword of Damocles

The legal environment around data sourcing through web scraping remains dangerously unsettled. The *hiQ Labs v. LinkedIn* case, which reached the Ninth Circuit and Supreme Court, established that scraping publicly accessible data is likely not a violation of the Computer Fraud and Abuse Act (CFAA).[^26] However, the courts explicitly left open liability under breach of contract, trespass to chattels, copyright infringement, and state unfair competition laws. LinkedIn continues to sue scrapers using alternative theories, and in 2025 filed suit against ProAPIs for using "industrial-scale" scraping via fake accounts.[^27]

Meanwhile, Clearview AI's scraping of billions of social media photos prompted lawsuits from multiple tech giants. Reddit's legal action against Perplexity for unauthorized scraping, and Meta's litigation against Bright Data, signal that platform owners are increasingly willing to use both technical and legal means to block data extraction.[^28] Any platform whose data sourcing strategy depends on scraping is building on a foundation that can be removed by a court decision, a terms-of-service change, or an API policy update at any moment.

### 10. The Historical Pattern: Data Gold Rush → Oversupply → Commoditization → Consolidation → Regulatory Crackdown

This pattern has repeated across every information market in modern history:

- **Credit bureaus (1890s–1970s):** Thousands of local bureaus → computerization → consolidation to three → FCRA regulation → entrenched oligopoly.
- **Phone directories (1880s–2010s):** Essential household items → internet reduces search costs to zero → value collapses → Yellow Pages ceases print publication.
- **Business directories (1840s–present):** D&B monopoly → government-mandated standard (DUNS) → open-source replacement (UEI) → D&B's core moat evaporates.
- **Data brokers (1960s–present):** Acxiom builds massive consumer database → GDPR/Cambridge Analytica → sells data assets → pivots to infrastructure.
- **Big data (2010–2016):** Hype cycle → massive investment → 60–85% failure rate → commoditization of analytics tools → only workflow-integrated platforms survive.
- **B2B contact data (2000s–present):** Jigsaw crowdsourcing → acquisition by Salesforce → neglect → shutdown in 2019.

Today's AI data demand is the latest iteration of this cycle. The "proprietary data as AI moat" narrative is compelling because it was also compelling in 1970 (credit bureaus), 1995 (D&B's DUNS monopoly), 2005 (Yellow Pages' "bigger than Google" claim), and 2012 (big data). In each case, the platforms that won were not those that accumulated the most data, but those that built the most defensible workflows around data that they themselves generated.

---

## The One Thing No Other Perspective Would Tell Me

The single historical lesson that would prevent a platform operator from making a mistake that countless others have made before is this: **the data you rent, buy, or scrape today will be the liability that destroys your margins tomorrow, but the data your users generate through your workflow is the only asset that compounds in value as regulation tightens.**

Consider the counterintuitive evidence. Dun & Bradstreet's 150-year data monopoly was destroyed not by a better data collector, but by a government procurement officer deciding to use a free identifier instead of a proprietary one. Acxiom's $2.3 billion data empire became a compliance liability that it had to sell to survive. Jigsaw's 21 million crowdsourced contacts were worthless the moment Salesforce decided they weren't worth maintaining. The Yellow Pages' directory business went from A$12 billion to A$454 million because Google made search free. In every case, the value of *accumulated third-party data* proved ephemeral.

By contrast, the platforms that survived and thrived were those that built data generation into their core user experience. LinkedIn didn't become the #1 B2B sales intelligence tool by buying contact lists; it became indispensable because professionals *choose* to maintain their profiles there. Credit bureaus didn't become durable because they bought data from other sources; they became durable because lenders *must* report to them to access the reciprocal database. Amazon's recommendation engine isn't powerful because it bought customer data; it's powerful because customers *shop* on Amazon, generating first-party behavioral signals that no competitor can replicate.

The specific implication for a platform operator sourcing data today is radical: **stop trying to find "other places to source data" and start designing your product so that every user interaction generates proprietary data that no third party can access.** If you are sourcing data from ZoomInfo, Apollo, or web scraping to improve your dataset, you are not building a moat—you are renting a temporary advantage that will be commoditized, regulated, or litigated away. The only data sourcing strategy that has survived every cycle in information market history is to become the source.

---

## Footnotes

[^1]: Josh Lauer, *Creditworthy: A History of Consumer Surveillance and Financial Identity in America*, 2017; also Federal Reserve Bank of Philadelphia, "An Overview and History of Credit Reporting," 2002. https://www.philadelphiafed.org/-/media/frbp/assets/consumer-finance/discussion-papers/creditreportinghistory_062002.pdf

[^2]: Electronic Privacy Information Center (EPIC), "The Fair Credit Reporting Act (FCRA)," 2025. https://epic.org/fcra/

[^3]: World Bank, "Dun & Bradstreet's industry dominance," in *World Development Report* background paper. https://documents1.worldbank.org/curated/en/209261468762614853/txt/wdr27825.txt

[^4]: Forbes, "Why Dun & Bradstreet's Monopoly Has Stifled Innovation For 100 Years," 2013. https://gist.github.com/orls/6301561

[^5]: U.S. Government Accountability Office (GAO), "Unique Identification Codes for Federal Contractors: DUNS Numbers and CAGE Codes," R44490, 2017. https://www.everycrsreport.com/files/20170531_R44490_78e0b3b91f9c41eb1f1c97101f0790857a711dca.html

[^6]: Benedict Evans, "How to Lose a Monopoly," 2020; cited in C WorldWide Asset Management, "How to Extract Value from Data?" https://cworldwide.com/insights-news/item/?id=20578&title=how-to-extract-value-from-data%3F

[^7]: Forbes, "Why Dun & Bradstreet's Monopoly Has Stifled Innovation For 100 Years (Part 1 of 2)," 2013. https://gist.github.com/orls/6301561

[^8]: C WorldWide Asset Management, "How to Extract Value from Data?" 2024. https://www.harborcapital.com/insights/how-to-extract-value-from-data/

[^9]: Cyntexa, "Top 25 Biggest Salesforce Acquisitions and Their Impact," 2026. https://cyntexa.com/blog/top-salesforce-acquisitions/; ShellBlack, "Salesforce Buys Jigsaw Crowd Sourced Data," 2010. https://www.shellblack.com/data/jigsaw/

[^10]: UnpublishedArticles.com, "Data.com and Jigsaw Says Goodbye To The Internet," 2019. https://unpublishedarticles.com/data-com-and-jigsaw-says-goodbye-to-the-internet/

[^11]: AdExchanger, "Acxiom's Next Steps And The LiveRamp Acquisition Four Years Later," 2018. https://www.adexchanger.com/data-driven-thinking/acxioms-next-steps-and-the-liveramp-acquisition-four-years-later/

[^12]: Ibid.

[^13]: CIPPIC, "Data Broker Profiles – Acxiom and LiveRamp," 2019. https://www.cippic.ca/articles/data-broker-profiles-acxiom-and-live-ramp-1

[^14]: InDaily, "'Google Schmoogle': The decline of the Yellow Pages," 2014. https://www.indailysa.com.au/news/archive/2014/06/23/google-schmoogle-decline-yellow-pages

[^15]: Economics Help, "The decline of Yellow Pages," 2017. https://www.economicshelp.org/blog/27868/economics/the-decline-of-yellow-pages/

[^16]: Gartner, cited in arXiv, "What Went Wrong with Data Lakes? A 15-Year Reality Check from the Field," 2026. https://arxiv.org/html/2606.08266v1

[^17]: Ibid.

[^18]: NewVantage Partners, "Data and AI Leadership Executive Survey," 2020; cited in arXiv 2606.08266v1.

[^19]: Teradata, "What Happened to Big Data?" 2019. https://www.teradata.com/blogs/what-happened-to-big-data

[^20]: CFPB, "CFPB Classifies Data Brokers as Credit Reporting Agencies in New Proposal," 2024. https://www.bhfs.com/insight/cfpb-classifies-data-brokers-as-credit-reporting-agencies-in-new-proposal/

[^21]: Garrett A. Johnson, Scott K. Shriver & Samuel G. Goldberg, "Privacy and Market Concentration: Intended and Unintended Consequences of the GDPR," *Management Science*, 2023; cited in George Mason Law Review, "A Report Card on the Impact of Europe's Privacy Regulation (GDPR) on Digital Markets," 2024. https://lawreview.gmu.edu/forum/a-report-card-on-the-impact-of-europes-privacy-regulation-gdpr-on-digital-markets/

[^22]: Mert Demirer et al., "Data, Privacy Laws and Firm Production: Evidence from the GDPR," NBER Working Paper No. 32146, 2024; cited in George Mason Law Review, 2024.

[^23]: Carl Shapiro and Hal R. Varian, *Information Rules: A Strategic Guide to the Network Economy*, Harvard Business School Press, 1998. https://people.ischool.berkeley.edu/~hal/Papers/japan/

[^24]: Ibid.

[^25]: V7 Labs, "Are Data Moats Dead in the Age of AI?" 2025. https://www.v7labs.com/blog/data-moats-a-guide

[^26]: *hiQ Labs, Inc. v. LinkedIn Corp.*, 9th Circuit; TechCrunch, "Web scraping is legal, US appeals court reaffirms," 2022. https://techcrunch.com/2022/04/18/web-scraping-legal-court/

[^27]: Lawfold, "LinkedIn Scraping Lawsuit News: Key Updates for 2026," 2026. https://lawfold.com/linkedin-scraping-lawsuit-news/

[^28]: IAB, "Legal Issues and Business Considerations When Using Generative AI in Digital Advertising," 2024. https://www.iab.com/wp-content/uploads/2024/06/IAB_GenerativeAI_WhitePaper_June2024.pdf
