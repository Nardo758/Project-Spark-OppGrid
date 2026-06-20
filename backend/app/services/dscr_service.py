"""
DSCR (Debt Service Coverage Ratio) Calculator

Provides lender-grade DSCR calculation for OppGrid reports.
SBA SOP 50 10 8 requires DSCR >= 1.25x for preferred approval.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class DSCRResult:
    """Result of DSCR calculation."""
    dscr: float
    annual_ebitda: float
    annual_debt_service: float
    owner_compensation: float
    capex: float
    working_capital: float
    status: str  # "strong", "acceptable", "marginal", "rejected"
    threshold: float = 1.25
    sba_minimum: float = 1.15
    
    @property
    def status_display(self) -> str:
        if self.dscr >= 1.5:
            return "Strong (≥ 1.50x)"
        if self.dscr >= 1.25:
            return "Acceptable (1.25–1.50x)"
        if self.dscr >= 1.15:
            return "Marginal (1.15–1.25x)"
        return "Rejected (< 1.15x)"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dscr": round(self.dscr, 2),
            "annual_ebitda": round(self.annual_ebitda, 0),
            "annual_debt_service": round(self.annual_debt_service, 0),
            "owner_compensation": round(self.owner_compensation, 0),
            "capex": round(self.capex, 0),
            "working_capital": round(self.working_capital, 0),
            "status": self.status,
            "status_display": self.status_display,
            "threshold": self.threshold,
            "sba_minimum": self.sba_minimum,
        }


class DSCRService:
    """Calculate DSCR using available OppGrid data."""
    
    # Industry-typical cost structure benchmarks (% of revenue)
    # Sourced from BLS, IBISWorld, and trade association data
    INDUSTRY_BENCHMARKS = {
        "restaurant": {"cogs_pct": 0.32, "labor_pct": 0.30, "rent_pct": 0.08, "other_pct": 0.15},
        "retail": {"cogs_pct": 0.65, "labor_pct": 0.15, "rent_pct": 0.06, "other_pct": 0.08},
        "salon": {"cogs_pct": 0.10, "labor_pct": 0.45, "rent_pct": 0.10, "other_pct": 0.15},
        "gym": {"cogs_pct": 0.05, "labor_pct": 0.35, "rent_pct": 0.12, "other_pct": 0.18},
        "cleaning": {"cogs_pct": 0.15, "labor_pct": 0.50, "rent_pct": 0.03, "other_pct": 0.12},
        "self storage": {"cogs_pct": 0.05, "labor_pct": 0.08, "rent_pct": 0.15, "other_pct": 0.12},
        "laundromat": {"cogs_pct": 0.20, "labor_pct": 0.15, "rent_pct": 0.10, "other_pct": 0.20},
        "car wash": {"cogs_pct": 0.25, "labor_pct": 0.20, "rent_pct": 0.08, "other_pct": 0.15},
        "daycare": {"cogs_pct": 0.08, "labor_pct": 0.50, "rent_pct": 0.10, "other_pct": 0.12},
        "default": {"cogs_pct": 0.30, "labor_pct": 0.25, "rent_pct": 0.08, "other_pct": 0.12},
    }
    
    # Typical revenue per establishment by industry (annual, USD)
    # Used as fallback when no specific revenue estimate is available
    INDUSTRY_REVENUE_PER_EST = {
        "restaurant": 800_000,
        "retail": 1_200_000,
        "salon": 300_000,
        "gym": 600_000,
        "cleaning": 400_000,
        "self storage": 500_000,
        "laundromat": 250_000,
        "car wash": 600_000,
        "daycare": 500_000,
        "default": 500_000,
    }
    
    @staticmethod
    def _normalize_business_type(business_type: str) -> str:
        """Map business type to a known industry category."""
        bt_lower = business_type.lower()
        
        mappings = {
            "restaurant": ["restaurant", "food", "cafe", "coffee", "bakery", "pizza", "burger"],
            "retail": ["retail", "store", "shop", "boutique", "clothing", "apparel"],
            "salon": ["salon", "barber", "hair", "nail", "spa", "beauty"],
            "gym": ["gym", "fitness", "yoga", "pilates", "crossfit", "studio"],
            "cleaning": ["cleaning", "maid", "janitorial", "pressure wash"],
            "self storage": ["storage", "self storage", "warehouse"],
            "laundromat": ["laundromat", "laundry", "dry clean"],
            "car wash": ["car wash", "auto detail", "detailing"],
            "daycare": ["daycare", "childcare", "preschool", "learning center"],
        }
        
        for industry, keywords in mappings.items():
            if any(kw in bt_lower for kw in keywords):
                return industry
        return "default"
    
    def calculate(
        self,
        business_type: str,
        city: str = "",
        state: str = "",
        annual_revenue: Optional[float] = None,
        debt_amount: Optional[float] = None,
        interest_rate: float = 0.085,  # 8.5% SBA 7(a) typical rate
        loan_term_years: int = 10,
        owner_compensation_pct: Optional[float] = None,
        rdc=None,
        labor_data=None,
    ) -> DSCRResult:
        """
        Calculate DSCR for a business.
        
        DSCR = (EBITDA - Owner Compensation - CapEx) / Annual Debt Service
        
        Args:
            business_type: Type of business (e.g., "restaurant", "retail")
            city, state: Location
            annual_revenue: Known annual revenue (if None, estimated from industry benchmarks)
            debt_amount: Total loan amount (if None, estimated from startup costs)
            interest_rate: Annual interest rate (default 8.5% for SBA 7(a))
            loan_term_years: Loan amortization term (default 10 years)
            owner_compensation_pct: Owner salary as % of revenue (if None, estimated)
            rdc: ReportDataContext (for competitor count, demographics, etc.)
            labor_data: BLS IndustryLaborData (for wage benchmarks)
        
        Returns:
            DSCRResult with calculated ratios and status
        """
        industry = self._normalize_business_type(business_type)
        benchmarks = self.INDUSTRY_BENCHMARKS.get(industry, self.INDUSTRY_BENCHMARKS["default"])
        
        # --- Revenue estimate ---
        if annual_revenue is None:
            # Estimate from industry benchmark
            annual_revenue = self.INDUSTRY_REVENUE_PER_EST.get(
                industry, self.INDUSTRY_REVENUE_PER_EST["default"]
            )
            
            # Adjust for location if demographics available
            if rdc and rdc.price and rdc.price.median_income:
                median_income = rdc.price.median_income
                # Adjust revenue by income ratio vs. US median (~$74,580)
                income_ratio = median_income / 74_580
                # Scale by square root to avoid over-correction
                annual_revenue *= (income_ratio ** 0.5)
            
            # Adjust for competition
            if rdc and rdc.promotion and rdc.promotion.competitor_count is not None:
                comp_count = rdc.promotion.competitor_count
                if comp_count > 10:
                    annual_revenue *= 0.85  # High competition reduces revenue
                elif comp_count == 0:
                    annual_revenue *= 1.15  # First-mover advantage
        
        # --- Cost structure ---
        cogs = annual_revenue * benchmarks["cogs_pct"]
        labor = annual_revenue * benchmarks["labor_pct"]
        rent = annual_revenue * benchmarks["rent_pct"]
        other = annual_revenue * benchmarks["other_pct"]
        
        # Adjust labor with BLS data if available
        if labor_data and labor_data.avg_weekly_wage:
            avg_weekly = labor_data.avg_weekly_wage
            annual_wage_per_worker = avg_weekly * 52
            # Estimate workers from revenue / industry benchmark
            est_workers = max(1, int(annual_revenue / 150_000))  # rough heuristic
            labor = annual_wage_per_worker * est_workers * 1.3  # +30% for benefits/payroll taxes
        
        # EBITDA
        ebitda = annual_revenue - cogs - labor - rent - other
        
        # Owner compensation
        if owner_compensation_pct is None:
            # Typical owner comp: 10-15% of revenue for small businesses
            owner_compensation_pct = 0.12
        owner_compensation = annual_revenue * owner_compensation_pct
        
        # CapEx (annualized)
        # Typical CapEx: 2-5% of revenue for most small businesses
        capex = annual_revenue * 0.03
        
        # Working capital reserve (3 months operating costs)
        monthly_op_cost = (cogs + labor + rent + other) / 12
        working_capital = monthly_op_cost * 3
        
        # --- Debt service ---
        if debt_amount is None:
            # Estimate startup costs: typically 6-12 months of operating costs
            debt_amount = monthly_op_cost * 9 + (annual_revenue * 0.15)  # equipment + 9 months run
        
        # Monthly loan payment (amortizing)
        r = interest_rate / 12
        n = loan_term_years * 12
        if r > 0:
            monthly_payment = debt_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        else:
            monthly_payment = debt_amount / n
        annual_debt_service = monthly_payment * 12
        
        # --- DSCR calculation ---
        # SBA standard: (EBITDA - Owner Comp - CapEx) / Annual Debt Service
        dscr = (ebitda - owner_compensation - capex) / max(annual_debt_service, 1)
        
        status = "rejected"
        if dscr >= 1.5:
            status = "strong"
        elif dscr >= 1.25:
            status = "acceptable"
        elif dscr >= 1.15:
            status = "marginal"
        
        return DSCRResult(
            dscr=dscr,
            annual_ebitda=ebitda,
            annual_debt_service=annual_debt_service,
            owner_compensation=owner_compensation,
            capex=capex,
            working_capital=working_capital,
            status=status,
        )
    
    def calculate_for_report(
        self,
        business_type: str,
        city: str = "",
        state: str = "",
        rdc=None,
        labor_data=None,
    ) -> Dict[str, Any]:
        """Calculate DSCR and return a formatted dict for injection into reports."""
        result = self.calculate(
            business_type=business_type,
            city=city,
            state=state,
            rdc=rdc,
            labor_data=labor_data,
        )
        return result.to_dict()
    
    def build_context_block(
        self,
        business_type: str,
        city: str = "",
        state: str = "",
        rdc=None,
        labor_data=None,
    ) -> str:
        """Build a SecretSauce-style context block for DSCR data."""
        result = self.calculate(
            business_type=business_type,
            city=city,
            state=state,
            rdc=rdc,
            labor_data=labor_data,
        )
        d = result.to_dict()
        
        lines = [
            "### DSCR Analysis (SBA Lending Standard)",
            f"**Projected DSCR: {d['dscr']:.2f}x** — {d['status_display']}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Annual Revenue (est.) | ${d['annual_ebitda'] + d['annual_debt_service'] + d['owner_compensation'] + d['capex']:,.0f} |",
            f"| Annual EBITDA | ${d['annual_ebitda']:,.0f} |",
            f"| Owner Compensation | ${d['owner_compensation']:,.0f} |",
            f"| Annual CapEx | ${d['capex']:,.0f} |",
            f"| Annual Debt Service | ${d['annual_debt_service']:,.0f} |",
            f"| DSCR | **{d['dscr']:.2f}x** |",
            f"| SBA Preferred Threshold | {d['threshold']:.2f}x |",
            f"| SBA Minimum | {d['sba_minimum']:.2f}x |",
            "",
        ]
        
        if d["dscr"] >= 1.25:
            lines.append(
                f"**Lender Readiness:** This business projects a DSCR of {d['dscr']:.2f}x, "
                f"which exceeds the SBA preferred threshold of {d['threshold']:.2f}x. "
                "Lenders should view this favorably."
            )
        elif d["dscr"] >= 1.15:
            lines.append(
                f"**Lender Readiness:** This business projects a DSCR of {d['dscr']:.2f}x, "
                f"which meets the SBA minimum of {d['sba_minimum']:.2f}x but is below the preferred "
                f"threshold of {d['threshold']:.2f}x. Consider increasing equity injection or reducing debt."
            )
        else:
            lines.append(
                f"**Lender Readiness:** This business projects a DSCR of {d['dscr']:.2f}x, "
                f"which is below the SBA minimum of {d['sba_minimum']:.2f}x. "
                "This would likely be rejected by SBA lenders without significant adjustments."
            )
        
        return "\n".join(lines)
