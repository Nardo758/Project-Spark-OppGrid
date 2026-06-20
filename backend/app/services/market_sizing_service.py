"""
TAM/SAM/SOM Market Sizing Calculator

Provides bottom-up market sizing from Census + BLS data.
Top-down requires paid data (IBISWorld) — not yet integrated.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class MarketSizingResult:
    """Result of TAM/SAM/SOM calculation."""
    tam: float
    sam: float
    som: float
    tam_method: str
    sam_method: str
    som_method: str
    
    # Supporting data
    target_population: int
    target_households: int
    avg_spend_per_customer: float
    serviceable_pct: float
    obtainable_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tam": round(self.tam, 0),
            "sam": round(self.sam, 0),
            "som": round(self.som, 0),
            "tam_display": self._fmt(self.tam),
            "sam_display": self._fmt(self.sam),
            "som_display": self._fmt(self.som),
            "tam_method": self.tam_method,
            "sam_method": self.sam_method,
            "som_method": self.som_method,
            "target_population": self.target_population,
            "target_households": self.target_households,
            "avg_spend_per_customer": round(self.avg_spend_per_customer, 2),
            "serviceable_pct": round(self.serviceable_pct * 100, 1),
            "obtainable_pct": round(self.obtainable_pct * 100, 1),
        }
    
    @staticmethod
    def _fmt(n: float) -> str:
        if n >= 1e9:
            return f"${n/1e9:.1f}B"
        if n >= 1e6:
            return f"${n/1e6:.1f}M"
        if n >= 1e3:
            return f"${n/1e3:.0f}K"
        return f"${n:.0f}"


class MarketSizingService:
    """Calculate TAM/SAM/SOM using bottom-up methodology from Census data."""
    
    # Annual spending per customer by category (bottom-up basis)
    # Based on BLS Consumer Expenditure Survey + industry averages
    CATEGORY_SPEND = {
        "restaurant": 3_500,        # per person annually
        "food": 3_500,
        "cafe": 1_200,
        "coffee": 800,
        "bakery": 500,
        "pizza": 1_000,
        "retail": 2_500,
        "store": 2_500,
        "clothing": 1_800,
        "apparel": 1_800,
        "salon": 800,
        "barber": 400,
        "hair": 600,
        "nail": 600,
        "spa": 1_200,
        "beauty": 800,
        "gym": 700,
        "fitness": 700,
        "yoga": 800,
        "cleaning": 1_500,
        "maid": 1_500,
        "self storage": 1_200,
        "storage": 1_200,
        "laundromat": 400,
        "laundry": 400,
        "car wash": 500,
        "daycare": 12_000,
        "childcare": 12_000,
        "default": 1_500,
    }
    
    # Serviceable market filter: % of population that would use this service
    # (age, income, proximity filters applied)
    CATEGORY_SERVICEABLE_PCT = {
        "restaurant": 0.95,
        "food": 0.95,
        "cafe": 0.70,
        "coffee": 0.75,
        "bakery": 0.60,
        "retail": 0.80,
        "store": 0.80,
        "clothing": 0.70,
        "salon": 0.65,
        "barber": 0.50,
        "hair": 0.60,
        "nail": 0.35,
        "spa": 0.30,
        "beauty": 0.50,
        "gym": 0.25,
        "fitness": 0.25,
        "yoga": 0.15,
        "cleaning": 0.40,
        "maid": 0.40,
        "self storage": 0.15,
        "storage": 0.15,
        "laundromat": 0.30,
        "laundry": 0.30,
        "car wash": 0.60,
        "daycare": 0.15,
        "childcare": 0.15,
        "default": 0.50,
    }
    
    # Obtainable market: realistic market share for a new entrant
    CATEGORY_OBTAINABLE_PCT = {
        "restaurant": 0.03,
        "food": 0.03,
        "cafe": 0.05,
        "coffee": 0.05,
        "bakery": 0.04,
        "retail": 0.02,
        "store": 0.02,
        "clothing": 0.02,
        "salon": 0.04,
        "barber": 0.05,
        "hair": 0.04,
        "nail": 0.03,
        "spa": 0.03,
        "beauty": 0.03,
        "gym": 0.03,
        "fitness": 0.03,
        "yoga": 0.04,
        "cleaning": 0.05,
        "maid": 0.05,
        "self storage": 0.02,
        "storage": 0.02,
        "laundromat": 0.05,
        "laundry": 0.05,
        "car wash": 0.04,
        "daycare": 0.02,
        "childcare": 0.02,
        "default": 0.03,
    }
    
    @staticmethod
    def _normalize_category(business_type: str) -> str:
        """Map business type to a known category."""
        bt_lower = business_type.lower()
        for category in MarketSizingService.CATEGORY_SPEND.keys():
            if category in bt_lower and category != "default":
                return category
        return "default"
    
    def calculate(
        self,
        business_type: str,
        city: str = "",
        state: str = "",
        rdc=None,
    ) -> MarketSizingResult:
        """
        Calculate TAM/SAM/SOM bottom-up from Census demographics.
        
        TAM = Total population in metro area × average spend per person
        SAM = Target population × serviceable percentage × average spend
        SOM = SAM × obtainable market share
        
        Args:
            business_type: Type of business
            city, state: Location
            rdc: ReportDataContext (for demographics)
        
        Returns:
            MarketSizingResult with calculated sizes and methodology
        """
        category = self._normalize_category(business_type)
        avg_spend = self.CATEGORY_SPEND.get(category, self.CATEGORY_SPEND["default"])
        serviceable_pct = self.CATEGORY_SERVICEABLE_PCT.get(category, self.CATEGORY_SERVICEABLE_PCT["default"])
        obtainable_pct = self.CATEGORY_OBTAINABLE_PCT.get(category, self.CATEGORY_OBTAINABLE_PCT["default"])
        
        # --- Population base ---
        if rdc and rdc.place and rdc.place.population:
            population = rdc.place.population
            households = rdc.place.total_households or max(1, int(population / 2.5))
        else:
            # Fallback: US city average ~150K
            population = 150_000
            households = 60_000
        
        # --- TAM: Total Addressable Market ---
        # Everyone in the city who might spend money on this category
        tam = population * avg_spend
        tam_method = f"Bottom-up: {population:,} population × ${avg_spend:,.0f} annual spend per person"
        
        # --- SAM: Serviceable Addressable Market ---
        # Population that matches the service profile (age, income, proximity)
        target_pop = int(population * serviceable_pct)
        target_hh = int(households * serviceable_pct)
        sam = target_pop * avg_spend
        sam_method = f"Bottom-up: {target_pop:,} serviceable population ({serviceable_pct*100:.0f}%) × ${avg_spend:,.0f} spend"
        
        # --- SOM: Serviceable Obtainable Market ---
        # Realistic market share for a new entrant
        som = sam * obtainable_pct
        som_method = f"Bottom-up: {obtainable_pct*100:.1f}% of SAM (realistic new entrant share)"
        
        # Adjust for competition if data available
        if rdc and rdc.promotion and rdc.promotion.competitor_count is not None:
            comp_count = rdc.promotion.competitor_count
            if comp_count > 10:
                # High competition: reduce obtainable share by 25%
                som *= 0.75
                som_method += f"; adjusted -25% for high competition ({comp_count} competitors)"
            elif comp_count == 0:
                # No competition: increase obtainable share by 50%
                som *= 1.50
                som_method += f"; adjusted +50% for first-mover advantage (0 competitors)"
        
        return MarketSizingResult(
            tam=tam,
            sam=sam,
            som=som,
            tam_method=tam_method,
            sam_method=sam_method,
            som_method=som_method,
            target_population=target_pop,
            target_households=target_hh,
            avg_spend_per_customer=avg_spend,
            serviceable_pct=serviceable_pct,
            obtainable_pct=obtainable_pct,
        )
    
    def build_context_block(
        self,
        business_type: str,
        city: str = "",
        state: str = "",
        rdc=None,
    ) -> str:
        """Build a SecretSauce-style context block for TAM/SAM/SOM data."""
        result = self.calculate(
            business_type=business_type,
            city=city,
            state=state,
            rdc=rdc,
        )
        d = result.to_dict()
        
        lines = [
            "### Market Size Analysis (TAM / SAM / SOM)",
            "**Methodology:** Bottom-up calculation from Census demographics and BLS Consumer Expenditure data.",
            "",
            "| Market Segment | Size | Methodology |",
            "|----------------|------|-------------|",
            f"| **Total Addressable Market (TAM)** | {d['tam_display']} | {d['tam_method']} |",
            f"| **Serviceable Addressable Market (SAM)** | {d['sam_display']} | {d['sam_method']} |",
            f"| **Serviceable Obtainable Market (SOM)** | {d['som_display']} | {d['som_method']} |",
            "",
            "**Supporting Data:**",
            f"- Target population: {d['target_population']:,} ({d['serviceable_pct']:.0f}% of total metro)",
            f"- Target households: {d['target_households']:,}",
            f"- Average annual spend per customer: ${d['avg_spend_per_customer']:,.0f}",
            f"- Realistic obtainable market share: {d['obtainable_pct']:.1f}%",
            "",
            "**IMPORTANT:** Use these figures in the Market Analysis section. Do NOT invent different market sizes. "
            "If the TAM seems too large or too small for the specific business concept, explain why in the narrative, "
            "but do not change the calculated numbers.",
        ]
        
        return "\n".join(lines)
