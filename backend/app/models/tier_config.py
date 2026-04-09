"""
OppGrid Tier Configuration — v2.1

Single source of truth for all tier capabilities, rate limits, and
monthly opportunity caps. Matches the OppGrid API Spec v2.1 exactly.

Platform tiers: explorer, builder, scaler, enterprise
API-only tiers: api_starter, api_professional, api_enterprise
"""
from typing import Dict, Any, Optional


class TierConfig:
    """Configuration for each subscription tier with hard caps (Spec v2.1)."""

    CONFIGS: Dict[str, Dict[str, Any]] = {
        # ============ PLATFORM TIERS (dashboard + optional API) ============
        "explorer": {
            "has_dashboard": True,
            "has_api": False,
            "freshness_days": 91,
            "api_rpm": 0,
            "api_daily": 0,
            "monthly_included_opps": 0,
            "overage_per_opp": 30.00,
            "layers": [1],
            "consultant_studio": True,
            "price_monthly": 0,
            "display_name": "Explorer",
        },
        "builder": {
            "has_dashboard": True,
            "has_api": True,
            "freshness_days": 31,
            "api_rpm": 10,
            "api_daily": 250,
            "monthly_included_opps": 3,
            "overage_per_opp": 30.00,
            "layers": [1],
            "consultant_studio": True,
            "price_monthly": 99,
            "display_name": "Builder",
        },
        "scaler": {
            "has_dashboard": True,
            "has_api": True,
            "freshness_days": 8,
            "api_rpm": 50,
            "api_daily": 1250,
            "monthly_included_opps": 15,
            "overage_per_opp": 30.00,
            "layers": [1, 2, 3],
            "consultant_studio": True,
            "price_monthly": 499,
            "display_name": "Scaler",
        },
        "enterprise": {
            "has_dashboard": True,
            "has_api": True,
            "freshness_days": 0,
            "api_rpm": 500,
            "api_daily": 10000,
            "monthly_included_opps": 75,
            "overage_per_opp": 30.00,
            "layers": [1, 2, 3],
            "consultant_studio": True,
            "price_monthly": 2500,
            "display_name": "Enterprise",
        },

        # ============ API-ONLY TIERS (no dashboard) ========================
        "api_starter": {
            "has_dashboard": False,
            "has_api": True,
            "freshness_days": 31,
            "api_rpm": 10,
            "api_daily": 250,
            "monthly_included_opps": 3,
            "overage_per_opp": 30.00,
            "layers": [],
            "consultant_studio": False,
            "price_monthly": 99,
            "display_name": "API Starter",
        },
        "api_professional": {
            "has_dashboard": False,
            "has_api": True,
            "freshness_days": 8,
            "api_rpm": 50,
            "api_daily": 1250,
            "monthly_included_opps": 15,
            "overage_per_opp": 30.00,
            "layers": [],
            "consultant_studio": False,
            "price_monthly": 499,
            "display_name": "API Professional",
        },
        "api_enterprise": {
            "has_dashboard": False,
            "has_api": True,
            "freshness_days": 0,
            "api_rpm": 500,
            "api_daily": 10000,
            "monthly_included_opps": 75,
            "overage_per_opp": 30.00,
            "layers": [],
            "consultant_studio": False,
            "price_monthly": 2500,
            "display_name": "API Enterprise",
        },
    }

    # ---------------------------------------------------------------------------
    # Class-level accessors
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    # Legacy tier name → v2.1 tier name mapping (backward compat)
    # ---------------------------------------------------------------------------
    LEGACY_MAP: Dict[str, str] = {
        "starter":      "builder",
        "professional": "scaler",
        "growth":       "builder",
        "pro":          "scaler",
        "team":         "builder",
        "business":     "scaler",
        "free":         "explorer",
    }

    @classmethod
    def _resolve(cls, tier: str) -> str:
        """Normalise tier name: lowercase + resolve legacy aliases."""
        t = (tier or "").lower()
        return cls.LEGACY_MAP.get(t, t)

    @classmethod
    def get(cls, tier: str) -> Optional[Dict[str, Any]]:
        """Return the full config dict for *tier*, or None if unrecognised."""
        return cls.CONFIGS.get(cls._resolve(tier))

    @classmethod
    def get_monthly_cap(cls, tier: str) -> int:
        """Return the number of opportunities included in the monthly plan."""
        return cls.CONFIGS.get(cls._resolve(tier), {}).get("monthly_included_opps", 0)

    @classmethod
    def get_overage_rate(cls, tier: str) -> float:
        """Return the per-opportunity overage charge (USD)."""
        return cls.CONFIGS.get(cls._resolve(tier), {}).get("overage_per_opp", 30.00)

    @classmethod
    def get_rpm(cls, tier: str) -> int:
        """Return requests-per-minute limit for *tier*."""
        return cls.CONFIGS.get(cls._resolve(tier), {}).get("api_rpm", 10)

    @classmethod
    def get_daily(cls, tier: str) -> int:
        """Return daily request limit for *tier*."""
        return cls.CONFIGS.get(cls._resolve(tier), {}).get("api_daily", 250)

    @classmethod
    def get_freshness_days(cls, tier: str) -> int:
        """Return minimum data age in days (0 = real-time)."""
        return cls.CONFIGS.get(cls._resolve(tier), {}).get("freshness_days", 91)

    @classmethod
    def all_tiers(cls):
        """Return all tier name strings."""
        return list(cls.CONFIGS.keys())

    @classmethod
    def as_list(cls):
        """Return a list of dicts suitable for JSON serialisation."""
        result = []
        for tier_name, cfg in cls.CONFIGS.items():
            result.append({
                "tier": tier_name,
                **cfg,
            })
        return result
