# Dimension 2: Data Sourcing & Quality — THE ACADEMIC Perspective

## 1. Core Position

Peer-reviewed evidence from information economics demonstrates that data markets suffer from classic "market for lemons" dynamics, where information asymmetry between sellers and buyers causes low-quality data to systematically crowd out high-quality data—directly contradicting the industry narrative that simply aggregating more data sources automatically improves dataset quality [^1][^2]. Furthermore, empirical studies on data decay, diminishing statistical returns, and the prevalence of spurious correlations in large datasets show that the marginal value of additional data volume is far lower than vendors claim, and in many cases, more data actively degrades decision-making quality [^3][^4][^5].

---

## 2. Strongest Evidence Supporting Your View

### A. Data Markets as "Markets for Lemons"

The foundational work in information economics applies directly to B2B data enrichment. George Akerlof's Nobel Prize-winning model shows that when quality is uncertain and asymmetrically known, average prices fall until only low-quality ("lemon") goods remain in the market [^1]. Subsequent empirical testing in digital used-good markets confirms that reputation systems and disclosures—analogous to vendor "accuracy guarantees"—fail to fully eliminate adverse selection from information asymmetry [^6]. In the data context, this means buyers cannot reliably distinguish high-quality datasets from stale or fabricated ones, so price competition drives quality toward the floor.

### B. Data Decay and Temporal Bias

Academic and industry-verified research demonstrates that B2B contact data decays at approximately **2.1% per month**, compounding to **22–30% annually** [^7][^8]. Dun & Bradstreet's data advisory team confirms B2B master data decay at 22–30% per year [^8]. Independent testing reveals a stark gap between vendor claims and reality: providers routinely advertise 90–95% accuracy, while independent tests show single-source databases deliver valid emails for only **~50–62% of contacts** at the moment of use [^8][^9]. This temporal degradation is distinct from concept drift; Vela et al. (2022) showed that even in stable data environments, AI models exhibit "aging" with error patterns ranging from gradual drift to explosive failure—meaning data freshness is not just a coverage issue but a dynamic stability problem [^10].

### C. Diminishing Returns to Data Volume

The "more data is better" narrative is statistically contradicted by multiple lines of research. Google's chief economist Hal Varian noted that measurement accuracy improves only with the **square root of sample size**, meaning you need four times as much data to get twice the precision—a natural statistical ceiling on data returns [^11]. Arnold et al. (2018) reviewed empirical advertising literature and found "numerous instances where more data either produces negligible gain, or in some cases negative gain" [^3]. A 2025 tokenizer study trained on 1GB to 900GB of data and found that intrinsic quality metrics plateau at roughly **150GB**, with further data providing "minimal to no improvements"—suggesting saturation effects are fundamental to algorithmic scaling, not just a language quirk [^12].

### D. The Spurious Correlation Problem

Calude & Longo (2015) mathematically proved that in large enough databases, "the overwhelming majority of correlations are spurious"—patterns that emerge from random noise rather than genuine predictive structure [^4]. The study showed that given sufficiently large datasets, regularities will appear independent of any underlying law, rendering most discovered correlations mathematically unreliable for prediction. This is not a theoretical edge case: Google Flu Trends, once touted as a big-data triumph, completely missed the 2013 influenza peak due to spurious correlations and overfitting [^13].

### E. Data Quality Is Not Self-Evident

Wang & Strong (1996) established that data quality is inherently contextual and consumer-dependent, not an intrinsic property of the dataset; their empirical framework identified dimensions including accuracy, timeliness, completeness, and fitness for use—most of which are systematically ignored by vendors optimizing for database size [^14]. Karr (2005) argued that modern data quality problems create "significant economic and political inefficiencies" and called for greater statistical rigor in evaluating data quality, noting that academic engagement has been "virtually nil" in this space [^15]. Sadiq (2017) reinforced that the data quality research community must embrace empiricism with transparent, reproducible experimental designs rather than relying on synthetic benchmarks or vendor claims [^16].

### F. Weakness of Data Network Effects

While platforms often claim "data network effects" as a moat, peer-reviewed research distinguishes between *user-generated* data loops (where feedback improves the product) and *alternative-source* data aggregation (where more data does not automatically improve user value) [^17]. Farboodi & Veldkamp (2023) review the data economy literature and note that data markets tend toward "monopolistic competition" where prices and volumes do not adequately reflect true valuation, and non-rivalry means that "not enough data are being shared" while negative externalities (e.g., privacy costs) mean "too much data sharing at too low a price" [^18]. Jones & Tonetti (2020) formalize that data's non-rival nature creates fundamental misalignments between private incentives and social value, meaning platforms may hoard data that would be more valuable if shared—and share data that is socially harmful [^19].

---

## 3. The One Thing No Other Perspective Would Tell Me

**The platform's data strategy should be inverted: stop trying to source "more" data and instead build a credible signal of dataset quality.** The academic literature on information asymmetry is unambiguous: in markets where buyers cannot verify quality before purchase (like data), the only sustainable competitive advantage is a *credible commitment mechanism*—not volume, not coverage, and not price [^1][^20]. Akerlof's original model showed that warranties, certification, and reputation can prevent market collapse, but only if they are costly to fake [^1]. For a data platform, this means investing in transparent, third-party-audited accuracy metrics with real-time decay tracking; publishing independent validation studies; and offering conditional guarantees (e.g., credit-backs for stale records). The counterintuitive insight is that a *smaller* dataset with verified, time-stamped, independently audited accuracy will command higher willingness-to-pay and stronger user lock-in than a massive dataset with opaque sourcing—because the smaller dataset solves the lemons problem, while the larger one exacerbates it. Most platforms die not from lack of data, but from the adverse-selection spiral that begins when buyers realize they cannot trust what they are buying.

---

## Footnotes

[^1]: Akerlof, G. A. "The Market for 'Lemons': Quality Uncertainty and the Market Mechanism." *The Quarterly Journal of Economics*, Vol. 84, No. 3, 1970, pp. 488–500. https://www.jstor.org/stable/1879431

[^2]: Archak, N., Ghose, A., and Ipeirotis, P. "Internet Exchanges for Used Goods: An Empirical Analysis of Trade Patterns and Adverse Selection." *NYU Working Paper*, 2008. http://archive.nyu.edu/bitstream/2451/27747/2/CPP-03-07.pdf

[^3]: Arnold, R., et al. "Is data the new oil? Diminishing returns to scale." *Econstor Discussion Paper*, 2018. https://www.econstor.eu/bitstream/10419/184927/1/Arnold-et-al.pdf

[^4]: Calude, C. S., and Longo, G. "The Deluge of Spurious Correlations in Big Data." *HAL Archives*, 2015. https://hal.science/hal-01380626v1/document

[^5]: Lamata, P., et al. "Avoiding big data pitfalls." *PMC*, 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC7610672/

[^6]: Archak, N., Ghose, A., and Ipeirotis, P. "Internet Exchanges for Used Goods: An Empirical Analysis of Trade Patterns and Adverse Selection." *Working Paper*, 2008. http://archive.nyu.edu/bitstream/2451/27747/2/CPP-03-07.pdf

[^7]: IndustrySelect / Unify GTM. "Waterfall Enrichment: The 2026 B2B Contact Data Architecture." June 2026. https://www.unifygtm.com/explore/waterfall-enrichment-b2b-contact-data

[^8]: Unify GTM / Landbase. "B2B Contact Data Accuracy Statistics." January 2026. https://www.landbase.com/blog/b2b-contact-data-accuracy-statistic

[^9]: Cleanlist / Industry testing. "B2B Data Enrichment: How It Works." February 2026. https://www.cleanlist.ai/blog/2026-02-20-b2b-data-enrichment-complete-guide

[^10]: Vela, D., et al. "Temporal Quality Degradation in AI Models." *Scientific Reports*, Vol. 12, Article 11654, 2022. https://doi.org/10.1038/s41598-022-15245-z

[^11]: Varian, H. (Google Chief Economist). Interview on search scale and diminishing returns. *CNet / Rough Type*, 2008. https://www.roughtype.com/?p=1283

[^12]: Reddy, V., et al. "How Much is Enough? The Diminishing Returns of Tokenization Training Data." *arXiv:2502.20273*, 2025. https://arxiv.org/html/2502.20273

[^13]: Lazer, D. "What We Can Learn From the Epic Failure of Google Flu Trends." *Wired / Science*, 2015. Cited in: "Saving the Life of Medical Ethics in the Age of AI and Big Data." *Delft Design for Values*, 2018. https://delftdesignforvalues.nl/2018/saving-the-life-of-medical-edics-in-the-age-of-ai-and-big-data/

[^14]: Wang, R. Y., and Strong, D. M. "Beyond Accuracy: What Data Quality Means to Data Consumers." *Journal of Management Information Systems*, Vol. 12, No. 4, 1996, pp. 5–33.

[^15]: Karr, A. F. "Data Quality: A Statistical Perspective." *NISS Technical Report 151*, 2005. https://www.niss.org/sites/default/files/technicalreports/tr151.pdf

[^16]: Sadiq, S. "Data Quality – The Role of Empiricism." *HPI Technical Report*, 2017. https://hpi.de/fileadmin/user_upload/fachgebiete/naumann/publications/PDFs/2018_sadiq_data.pdf

[^17]: Mitomo, H. "Data Network Effects: Implications for Data Business." *Econstor Working Paper*, 2017. https://www.econstor.eu/bitstream/10419/169484/1/Mitomo.pdf

[^18]: Farboodi, M., and Veldkamp, L. "Data and Markets." *Annual Review of Economics*, Vol. 15, 2023, pp. 23–40. https://doi.org/10.1146/annurev-economics-082322-023244

[^19]: Jones, C. I., and Tonetti, C. "Nonrivalry and the Economics of Data." *American Economic Review*, Vol. 110, No. 9, 2020, pp. 2819–2858.

[^20]: Signaling theory and insurance intermediation literature: "Does Signaling Work in Markets for Information Services?" *Econstor Working Paper*, 2008. https://www.econstor.eu/bitstream/10419/39746/1/610621645.pdf
