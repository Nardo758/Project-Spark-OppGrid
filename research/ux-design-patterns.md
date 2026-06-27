# UX/UI Design Patterns for Business Intelligence Opportunity Detail Cards

**Research Date:** 2026-06-27
**Researcher:** UX Design Research Agent
**Scope:** Evidence-based patterns for presenting 15–20 complex business data points (market size, competition, demographics, scores, validation metrics) in a single opportunity detail card / page.

---

## Executive Summary

- **The human brain processes only 7±2 items simultaneously** (Miller's Law). Opportunity cards displaying 15–20 raw data points without hierarchy guarantee cognitive overload and reduced decision accuracy.
- **Progressive disclosure is the primary antidote** — platforms like Linear, Stripe, and modern SaaS dashboards lead with 4–6 high-priority KPIs and bury granular detail behind one-click drill-downs, tabs, or expandable drawers.
- **Visual density must be managed through consistent card systems**: fixed 8px/16px spacing grids, restrained 4–6 color palettes, and typography scales limited to 2–3 sizes prevent clutter while preserving scanability.
- **Accessibility is non-negotiable for data-heavy cards**: WCAG 2.1 AA requires 4.5:1 text contrast, prohibits color-only information encoding, and mandates keyboard-navigable disclosure controls; compliant designs improve usability for *all* users, not just those with disabilities.

---

## 1. Information Hierarchy Recommendations

### 1.1 The "F-Pattern" + Z-Pattern Hybrid for Dense Cards
Users scan text-heavy dashboards in an **F-pattern** (top-left first, then down the left edge), while visually heavy dashboards follow a **Z-pattern** (top-left → top-right → diagonal → bottom-right).
**Implementation for opportunity cards:**

| Zone | Content Priority | Visual Treatment |
|------|------------------|----------------|
| **Top-left** | Primary decision metric (e.g., Overall Opportunity Score / Market Size) | Largest font (24–32px), bold weight, high-contrast color |
| **Top row** | 3–4 critical KPIs (TAM, Competition Index, Validation Grade) | Medium font (16–20px), grouped in a horizontal "KPI ribbon" |
| **Left column** | Categorical metadata (Industry, Location, Stage, Founded) | Small font (12–14px), label + value pairs, muted labels |
| **Center / Right** | Secondary charts (demographics pie, trend sparkline) | Contained inside bordered cards with 16px padding |
| **Bottom** | Granular tables, raw data sources, methodology notes | Collapsed by default; expand on user request |

> **Visual description:** Imagine a 3-column top section: a massive "72/100" opportunity score on the left, a row of 4 mini-stat cards (TAM $4.2B, Competition: Medium, etc.) in the center, and a small "Verified" badge with timestamp on the right. Below this, a 2-column grid of collapsible topic cards.

**Source:**
- Pencil & Paper — "Dashboard Design UX Patterns Best Practices" (https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards)
- Setproduct — "Dashboard UI design: From KPIs to layouts that convert" (https://www.setproduct.com/blog/dashboard-ui-design)

### 1.2 Chunking by Business Function
Group the 15–20 data points into 4–5 thematic "chunks" that users can process as single units:

1. **Executive Summary** (Score, Signal, Recommendation)
2. **Market Context** (TAM/SAM/SOM, Growth Rate, Trend Direction)
3. **Competitive Landscape** (Incumbents, Saturation, Moat)
4. **Validation & Evidence** (Data Sources, Confidence Level, Last Updated)
5. **Action Panel** (Save, Share, Export, Connect)

Use 32px vertical spacing between chunks and a subtle 1px divider or background color shift (e.g., `#FAFAFA` vs `#FFFFFF`) to reinforce boundaries without heavy borders.

**Source:**
- UK Data Services — "BI Dashboard Design: 2025 UX Best Practices" (https://ukdataservices.co.uk/blog/articles/business-intelligence-dashboard-design)

### 1.3 The 3-Second Rule
Users must grasp the "health" of an opportunity within **3 seconds of landing**. This means:
- The single most important metric (composite score or "Go / No-Go" signal) must occupy the top-left.
- Avoid paragraphs of explanation above the fold. Labels should be 1–3 words.
- Reserve color saturation for the primary score and alerts only; everything else should be neutrally toned.

**Source:**
- Dev.to / Daisy Jones — "How to Redesign Dashboards That Actually Retain Customers" (https://dev.to/daisy_jones_21bdcc6b40f9d/how-to-redesign-dashboards-that-actually-retain-customers-237d)

---

## 2. Progressive Disclosure Strategies

### 2.1 Tiered Disclosure Architecture
Instead of showing all 20 data points, expose information in three tiers:

| Tier | Visibility | Content Example | Interaction |
|------|------------|-----------------|-------------|
| **Tier 1: At-a-glance** | Always visible | Overall score, 4 primary KPIs, action buttons | None — instant scan |
| **Tier 2: Topic summary** | Visible on scroll | Demographics chart, competitor list, funding timeline | Static cards below the fold |
| **Tier 3: Deep detail** | Hidden until requested | Raw census data, methodology PDF, source URLs | Expand/collapse, tabs, or modal drawer |

### 2.2 Before / After: Flat vs. Layered Card

**BEFORE (Flat Layout):**
```
┌──────────────────────────────────────────────┐
│ Opportunity: Urban Micro-Grid TAM: $4.2B ... │
│ Score: 72/100   Competition: High   Demos:... │
│ [Full Demographics Table] [Full Competitor List]│
│ [Source URLs] [Methodology Notes] [Export]   │
│ (20 data points crammed, user must scroll 3x)│
└──────────────────────────────────────────────┘
```
*Problem:* No clear priority; every metric competes for attention; tables push primary KPIs out of view.

**AFTER (Layered Disclosure):**
```
┌──────────────────────────────────────────────┐
│ [Score: 72/100]  [TAM $4.2B] [Comp: High]   │
│ [Growth ↑12%]    [Verified: Today]           │
├──────────────────────────────────────────────┤
│ 📊 Market Size        [Expand ▼]             │
│   (Sparkline + 3 key numbers visible)        │
├──────────────────────────────────────────────┤
│ 🏢 Competition        [Expand ▼]             │
│   (Top 3 competitors + saturation gauge)     │
├──────────────────────────────────────────────┤
│ 👥 Demographics       [Expand ▼]             │
│   (Donut chart + age/income summary)         │
└──────────────────────────────────────────────┘
```
*Improvement:* Primary metrics are scannable in 3 seconds. Secondary content is discoverable but not overwhelming. Users choose what to expand based on their current task.

**Source:**
- Rafiki AI / Interaction Design Foundation — "Progressive Disclosure: Smarter Sales Tool UX Design" (https://getrafiki.ai/thought-leadership/progressive-disclosure-sales-tool-ux-design/)
- IxDF — "What is Progressive Disclosure?" (https://ixdf.org/literature/topics/progressive-disclosure)

### 2.3 Specific Disclosure Patterns
- **Accordion sections:** Best for mobile and narrow layouts. Use chevron icons that rotate 180° on expand. Ensure only one section opens at a time to prevent excessive scrolling.
- **Tabbed sub-panels:** Best for desktop when 3–5 related data themes exist (e.g., "Market," "Competition," "Financials"). Keep tabs sticky below the primary KPI ribbon.
- **Modal drawers / side panels:** Best for deep-dive source tables or methodology without losing the context of the main card.
- **Tooltip micro-disclosure:** Hover (desktop) or long-press (mobile) on a metric label reveals a 1-sentence definition and data source. Prevents label clutter.

**Source:**
- Yellowslice — "B2B SaaS Dashboard Best Practices" (https://www.yellowslice.in/blog/best-practices-for-designing-a-b2b-saas-dashboard)
- F1Studioz — "Smart SaaS Dashboard Design Guide (2026)" (https://f1studioz.com/blog/smart-saas-dashboard-design/)

---

## 3. Visual Density Management Techniques

### 3.1 The Data-Ink Ratio
Following Edward Tufte's principle: **maximize data, minimize non-data ink.**
- Remove 3D effects, heavy drop shadows, and decorative gradients.
- Use 1px hairline borders (`#E5E7EB`) instead of thick card shadows.
- Let whitespace do the separation work.

### 3.2 Spacing Grid System
Use a **4px or 8px base unit** consistently:

| Element | Spacing |
|---------|---------|
| Page margins | 64px (8× base) |
| Section gaps | 32px (4× base) |
| Card internal padding | 16px (2× base) |
| Between related metrics | 8px (1× base) |

### 3.3 Component Recommendations for Dense Data

| Data Type | Recommended Component | Why It Works |
|-----------|----------------------|--------------|
| **Composite Score** | Large circular gauge or bold number + color badge | Instant emotional + rational read; humans process color + shape faster than digits alone |
| **Trend (time)** | Sparkline (mini line chart, 40px tall) | Shows direction without consuming full chart space |
| **Categorical comparison** | Horizontal bar chart | Easier to read labels than vertical bars or pie charts |
| **Status / Severity** | Pill badge (e.g., "High Competition") | Rounded corners and solid fill draw attention without aggressive colors |
| **Progress / Completion** | Thin progress bar (4px height) | Shows proportional data without heavy visual weight |
| **Geographic** | Small thumbnail map with hot-spot dots | Provides spatial context; expand for full interactive map |

**Source:**
- Stan Vision — "UI card design: examples, best practices and common patterns" (https://www.stan.vision/journal/ui-card-design-examples-best-practices-and-common-patterns)
- Code Theorem — "SaaS Dashboard UX Design: Trends and Best Practices" (https://codetheorem.co/blogs/saas-dashboard-ux/)
- BoldBI — "10 Dashboard Design Best Practices for Insights" (https://www.boldbi.com/blog/10-dashboard-design-best-practices/)

### 3.4 "Calm" Color Philosophy
- **Neutral base:** 80% of the card should be white, light gray, or very subtle tint.
- **Semantic accent:** Reserve strong colors for status only:
  - Green = positive growth / validated
  - Amber = warning / medium risk / needs review
  - Red = critical / high risk / outdated data
- **Blue/Indigo:** Use for primary actions and links (never for both positive and negative status).
- **Limit total palette to 4–6 core colors.** Additional chart colors should be desaturated pastels.

**Source:**
- Number Analytics — "Data Visualization in Dashboard Design" (https://www.numberanalytics.com/blog/data-visualization-in-dashboard-design)
- Bamboo Digital Technologies — "Designing a Payment Operations Dashboard" (https://www.bamboodt.com/designing-a-payment-operations-dashboard-for-fintechs-a-practical-guide-by-bamboo-digital-technologies/)

---

## 4. Color and Typography Best Practices

### 4.1 Typography Scale for Data Cards
Restrict the card to **2–3 font sizes**:

| Role | Size | Weight | Example |
|------|------|--------|---------|
| Primary metric (score) | 28–32px | Bold (700) | "72" |
| Secondary metric | 18–20px | Semibold (600) | "$4.2B" |
| Body / label | 13–14px | Regular (400) | "Total Addressable Market" |
| Caption / metadata | 11–12px | Medium (500) | "Updated 2h ago" |

- Use a **clean sans-serif** (Inter, Roboto, or system-ui) for numbers and labels.
- Ensure labels are **horizontal**; avoid rotated text on axis labels.
- Numbers should be **tabular-nums** (fixed-width) so columns align when comparing metrics.

**Source:**
- DEV3LOP — "Typography Best Practices for Data-Dense Displays" (https://dev3lop.com/typography-best-practices-for-data-dense-displays/)
- ClicData — "Preventing Dashboard Misreads" (https://www.clicdata.com/blog/preventing-dashboard-misreads/)

### 4.2 Avoiding Color Overload
- **Do not** assign a unique color to every data point. This creates "rainbow overload" and destroys semantic meaning.
- **Do not** use red/green as the sole differentiators for critical metrics (8% of males are colorblind). Always pair color with an icon (↑/↓), text label, or pattern.
- **Do** use a single accent color family (e.g., slate-blue) for non-status data, varying opacity or lightness to show hierarchy.

**Source:**
- A11y Collective — "The Ultimate Checklist for Accessible Data Visualisations" (https://www.a11y-collective.com/blog/accessible-charts/)
- W3C — "Web Content Accessibility Guidelines (WCAG) 2.1" (https://www.w3.org/TR/WCAG21/)

---

## 5. Accessibility Checklist for Data-Heavy Cards

### Perceivable
- [ ] **Color contrast:** All text meets WCAG 2.1 AA 4.5:1 against background; large text (18px+) meets 3:1.
- [ ] **Color is not the sole means:** Every status conveyed by color (red/green/amber) also has an icon, text label, or pattern.
- [ ] **Text resizing:** Layout remains functional when browser zoom is set to 200% (responsive grid, no horizontal overflow clipping).
- [ ] **Chart alternatives:** Provide a visually hidden table or aria-describedby summary for complex charts.

### Operable
- [ ] **Keyboard navigation:** All expand/collapse accordions, tabs, and modal drawers are operable via `Tab`, `Enter`, and `Escape`.
- [ ] **Focus indicators:** Visible 2px outline or ring on focused interactive elements (score breakdown buttons, tabs, source links).
- [ ] **Touch targets:** Minimum 44×44px (iOS) or 48×48dp (Android) for all buttons on mobile.
- [ ] **Hover alternatives:** Tooltip content is also accessible via focus or a persistent "info" button.

### Understandable
- [ ] **Consistent labels:** Use the same terminology across cards (e.g., "TAM" not "Market Size" on one card and "Total Market" on another).
- [ ] **Plain language:** Avoid jargon in tooltips; write for a 10th-grade reading level.
- [ ] **Predictable interactions:** Clicking the same element type always behaves the same way (e.g., all chevrons expand content).

### Robust
- [ ] **ARIA roles:** Accordions use `aria-expanded`, tabs use `role="tablist"`, and live regions announce score updates.
- [ ] **Screen reader friendly:** Primary metric values are read first, followed by labels (e.g., "Seventy-two out of one hundred, opportunity score").

**Source:**
- W3C — "WCAG 2.1" (https://www.w3.org/TR/WCAG21/)
- A11y Collective — "Accessible Charts Checklist" (https://www.a11y-collective.com/blog/accessible-charts/)
- GitHub `awesome-copilot` — Accessibility Agent Guidelines (https://github.com/github/awesome-copilot/blob/main/agents/accessibility.agent.md)

---

## 6. Specific Design Patterns to Implement

### Pattern 1: The "KPI Ribbon" Header
**Purpose:** Present the 4 most critical numbers in a single scannable row.

**Structure:**
```jsx
<header className="kpi-ribbon">
  <KpiCard label="Opportunity Score" value="72" visual={<Gauge value={72} />} />
  <KpiCard label="TAM" value="$4.2B" trend="+12%" />
  <KpiCard label="Competition" value="High" badge="amber" />
  <KpiCard label="Validation" value="Strong" badge="green" />
</header>
```

**Styling notes:**
- Each card: `padding: 16px; border-radius: 8px; background: white; border: 1px solid #E5E7EB;`
- Value text: `font-size: 24px; font-weight: 700; color: #111827;`
- Label text: `font-size: 12px; font-weight: 500; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em;`
- Container: `display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;`

**Source:**
- Yellowslice — "B2B SaaS Dashboard Best Practices" (https://www.yellowslice.in/blog/best-practices-for-designing-a-b2b-saas-dashboard)
- Stan Vision — "Dashboard and stat cards" (https://www.stan.vision/journal/ui-card-design-examples-best-practices-and-common-patterns)

---

### Pattern 2: Expandable Topic Cards (Accordion)
**Purpose:** Group secondary data into thematic chunks without overwhelming the initial view.

**Structure:**
```jsx
<section className="topic-card">
  <button aria-expanded={isOpen} onClick={toggle}>
    <Icon name="chart" /> Market Size
    <span className="summary">TAM $4.2B • CAGR 12%</span>
    <Chevron direction={isOpen ? 'up' : 'down'} />
  </button>
  {isOpen && (
    <div className="panel">
      <Sparkline data={growth} />
      <DataTable columns={['Segment', 'Size', 'Growth']} rows={...} />
    </div>
  )}
</section>
```

**UX rules:**
- Only one topic card open at a time (optional but recommended for mobile).
- Closed card still shows a **micro-summary** (2–3 data nuggets) so users know if it's worth expanding.
- Transition: `max-height` or `grid-template-rows` animation over 200ms with `ease-out`.

**Source:**
- Interaction Design Foundation / Rafiki AI — Progressive Disclosure principles (https://getrafiki.ai/thought-leadership/progressive-disclosure-sales-tool-ux-design/)
- UXPin — "Dashboard Design Principles" (https://www.uxpin.com/studio/blog/dashboard-design-principles/)

---

### Pattern 3: Score Breakdown with Segmented Visual
**Purpose:** Show a composite score and let users inspect its sub-components.

**Structure:**
```jsx
<div className="score-card">
  <div className="score-main">
    <CircularGauge value={72} size={120} />
    <div>
      <h2>72<span className="out-of">/100</span></h2>
      <p className="grade">B+ — Strong Opportunity</p>
    </div>
  </div>
  <div className="score-factors">
    <FactorBar label="Market" score={85} />
    <FactorBar label="Team" score={60} />
    <FactorBar label="Timing" score={78} />
    <FactorBar label="Competition" score={45} />
  </div>
</div>
```

**Styling notes:**
- `FactorBar` is a horizontal stacked bar or a thin progress bar per factor.
- Color coding per factor: use opacity, not drastically different hues (e.g., all slate-blue, varying fill %).
- Hovering a factor bar reveals a tooltip: "Market score = 85. Based on TAM, CAGR, and regulatory tailwinds."

**Source:**
- UK Data Services — "BI Dashboard Design" (https://ukdataservices.co.uk/blog/articles/business-intelligence-dashboard-design)
- Code Theorem — "SaaS Dashboard UX Design" (https://codetheorem.co/blogs/saas-dashboard-ux/)

---

### Pattern 4: Data Table with Progressive Columns
**Purpose:** Present dense tabular data (competitors, demographics) without a wall of text.

**Structure:**
```jsx
<DataTable>
  <thead>
    <tr>
      <th>Competitor</th>
      <th>Market Share</th>
      <th className="collapsed-on-mobile">Funding</th>
      <th className="collapsed-on-mobile">Headcount</th>
      <th>Action</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</DataTable>
```

**UX rules:**
- Show the **3 most important columns** by default; hide secondary columns on screens <768px behind a "View Details" toggle or horizontal scroll.
- Use **zebra striping** (`#FAFAFA` / `#FFFFFF`) for readability, but ensure contrast between text and background still meets 4.5:1.
- Row hover: `background-color: #F3F4F6;` with a 150ms transition.
- Empty state: Show a message "No competitor data available" rather than a blank table.

**Source:**
- Eleken — "SaaS Dashboard Design: Examples, Patterns & Practical Tips" (https://www.eleken.co/blog-posts/saas-dashboard-design)
- Context.dev — "10 Essential Dashboard Design Best Practices" (https://www.context.dev/blog/dashboard-design-best-practices)

---

### Pattern 5: Contextual Tooltip / Definition Popover
**Purpose:** Keep labels concise while offering deep definitions on demand.

**Structure:**
```jsx
<span className="metric-label">
  TAM
  <InfoButton aria-label="Total Addressable Market definition" />
  {isOpen && (
    <Popover role="tooltip">
      <p>Total Addressable Market: the total revenue opportunity if 100% market share were achieved.</p>
      <footer>Source: US Census + IBISWorld, updated 2026-06-27</footer>
    </Popover>
  )}
</span>
```

**Accessibility rules:**
- Popover is dismissible via `Escape` and does not obscure the triggering label.
- Focus moves into the popover when opened, and returns to the trigger on close.
- On mobile, use a bottom sheet instead of a hover-dependent popover.

**Source:**
- W3C — WCAG 2.1 Content on Hover or Focus (https://www.w3.org/TR/WCAG21/)
- Bamboo Digital Technologies — "Payment Operations Dashboard" (https://www.bamboodt.com/designing-a-payment-operations-dashboard-for-fintechs-a-practical-guide-by-bamboo-digital-technologies/)

---

## 7. Citations & Sources

| # | Source | URL |
|---|--------|-----|
| 1 | UK Data Services — BI Dashboard Design: 2025 UX Best Practices | https://ukdataservices.co.uk/blog/articles/business-intelligence-dashboard-design |
| 2 | Pencil & Paper — Dashboard Design UX Patterns Best Practices | https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards |
| 3 | Setproduct — Dashboard UI design: From KPIs to layouts that convert | https://www.setproduct.com/blog/dashboard-ui-design |
| 4 | Bricx Labs — 7 Proven B2B UX Design Examples You Can Learn From | https://bricxlabs.com/blogs/b2b-ux-design-examples |
| 5 | Rafiki AI / IxDF — Progressive Disclosure: Smarter Sales Tool UX Design | https://getrafiki.ai/thought-leadership/progressive-disclosure-sales-tool-ux-design/ |
| 6 | Interaction Design Foundation — What is Progressive Disclosure? | https://ixdf.org/literature/topics/progressive-disclosure |
| 7 | Yellowslice — B2B SaaS Dashboard Best Practices | https://www.yellowslice.in/blog/best-practices-for-designing-a-b2b-saas-dashboard |
| 8 | UXDesign.cc — Design Thoughtful Dashboards for B2B SaaS | https://uxdesign.cc/design-thoughtful-dashboards-for-b2b-saas-ff484385960d |
| 9 | F1Studioz — Smart SaaS Dashboard Design Guide (2026) | https://f1studioz.com/blog/smart-saas-dashboard-design/ |
| 10 | Code Theorem — SaaS Dashboard UX Design: Trends and Best Practices | https://codetheorem.co/blogs/saas-dashboard-ux/ |
| 11 | Context.dev — 10 Essential Dashboard Design Best Practices | https://www.context.dev/blog/dashboard-design-best-practices |
| 12 | Eleken — SaaS Dashboard Design: Examples, Patterns & Practical Tips | https://www.eleken.co/blog-posts/saas-dashboard-design |
| 13 | Stan Vision — UI card design: examples, best practices and common patterns | https://www.stan.vision/journal/ui-card-design-examples-best-practices-and-common-patterns |
| 14 | A11y Collective — The Ultimate Checklist for Accessible Data Visualisations | https://www.a11y-collective.com/blog/accessible-charts/ |
| 15 | W3C — Web Content Accessibility Guidelines (WCAG) 2.1 | https://www.w3.org/TR/WCAG21/ |
| 16 | UXPin — Dashboard Design Principles: The Definitive Guide (2026) | https://www.uxpin.com/studio/blog/dashboard-design-principles/ |
| 17 | BoldBI — 10 Dashboard Design Best Practices for Insights | https://www.boldbi.com/blog/10-dashboard-design-best-practices/ |
| 18 | Number Analytics — Data Visualization in Dashboard Design | https://www.numberanalytics.com/blog/data-visualization-in-dashboard-design |
| 19 | DEV3LOP — Typography Best Practices for Data-Dense Displays | https://dev3lop.com/typography-best-practices-for-data-dense-displays/ |
| 20 | ClicData — Preventing Dashboard Misreads | https://www.clicdata.com/blog/preventing-dashboard-misreads/ |
| 21 | GitNexa — UI/UX Best Practices for SaaS | Complete 2026 Guide | https://www.gitnexa.com/blogs/saas-ui-ux-design-guide |
| 22 | Make My Brand Labs — Best Practices for Designing SaaS Dashboards & Portals | https://www.makemybrandlabs.com/blogs/designing-saas-dashboards-and-portals |
| 23 | Bamboo Digital Technologies — Designing a Payment Operations Dashboard | https://www.bamboodt.com/designing-a-payment-operations-dashboard-for-fintechs-a-practical-guide-by-bamboo-digital-technologies/ |
| 24 | GitHub `awesome-copilot` — Accessibility Agent Guidelines | https://github.com/github/awesome-copilot/blob/main/agents/accessibility.agent.md |

---

## 8. Cross-Referenced Findings Summary

| Theme | Consensus Across Sources | Dissent / Nuance |
|-------|------------------------|----------------|
| **Information Hierarchy** | F-pattern scanning is universal; place the single most important metric top-left. | Some visual-heavy dashboards may benefit from Z-pattern, but B2B intelligence cards are predominantly text+number scanning tasks. |
| **Progressive Disclosure** | 100% of sources agree: show summaries first, detail on demand. | Tabs vs. accordions vs. modals depends on device width and user role; no single pattern wins universally. |
| **Color Palette** | 4–6 core colors max; semantic color must be consistent. | Dark mode is debated: great for ops/monitoring, less ideal for printed strategic reports. |
| **Typography** | 2–3 font sizes; sans-serif; tabular numerals. | Some editorial dashboards use serif for headlines, but data cards should stay sans for legibility. |
| **Accessibility** | WCAG 2.1 AA is the minimum standard; color alone is insufficient. | AAA is often impossible for complex charts; AA is the pragmatic target. |

---

*End of Report*