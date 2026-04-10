"""
Report Pricing Configuration - January 2026

Pricing structure:
- Individual Track (Starter/Growth/Pro): Base prices with tier discounts (0%/10%/15%)
- Business Track (Team/Business/Enterprise): Different base prices with white-label + discounts (0%/20%/50%)

Format: {report_type: {"individual_base": price_cents, "business_base": price_cents}}
"""

from app.models.subscription import SubscriptionTier

REPORT_PRICING = {
    "ad_creatives": {
        "individual_base": 7900,
        "business_base": 12900,
        "delivery_hours": "1-2",
    },
    "brand_package": {
        "individual_base": 14900,
        "business_base": 24900,
        "delivery_hours": "2-4",
    },
    "landing_page": {
        "individual_base": 9900,
        "business_base": 17900,
        "delivery_hours": "2-3",
    },
    "content_calendar": {
        "individual_base": 12900,
        "business_base": 22900,
        "delivery_hours": "2-3",
    },
    "email_funnel_system": {
        "individual_base": 17900,
        "business_base": 29900,
        "delivery_hours": "3-4",
    },
    "email_sequence": {
        "individual_base": 7900,
        "business_base": 12900,
        "delivery_hours": "1-2",
    },
    "lead_magnet": {
        "individual_base": 8900,
        "business_base": 14900,
        "delivery_hours": "2-3",
    },
    "sales_funnel": {
        "individual_base": 14900,
        "business_base": 24900,
        "delivery_hours": "3-4",
    },
    "seo_content": {
        "individual_base": 12900,
        "business_base": 22900,
        "delivery_hours": "2-3",
    },
    "tweet_landing_page": {
        "individual_base": 4900,
        "business_base": 7900,
        "delivery_hours": "0.5-1",
    },
    "user_personas": {
        "individual_base": 9900,
        "business_base": 17900,
        "delivery_hours": "2-3",
    },
    "feature_specs": {
        "individual_base": 14900,
        "business_base": 24900,
        "delivery_hours": "3-4",
    },
    "mvp_roadmap": {
        "individual_base": 17900,
        "business_base": 29900,
        "delivery_hours": "3-5",
    },
    "product_requirements_doc": {
        "individual_base": 16900,
        "business_base": 27900,
        "delivery_hours": "4-6",
    },
    "gtm_launch_calendar": {
        "individual_base": 15900,
        "business_base": 26900,
        "delivery_hours": "2-3",
    },
    "gtm_strategy": {
        "individual_base": 18900,
        "business_base": 31900,
        "delivery_hours": "3-5",
    },
    "kpi_dashboard": {
        "individual_base": 11900,
        "business_base": 19900,
        "delivery_hours": "2-3",
    },
    "pricing_strategy": {
        "individual_base": 13900,
        "business_base": 22900,
        "delivery_hours": "2-4",
    },
    "competitive_analysis": {
        "individual_base": 14900,
        "business_base": 24900,
        "delivery_hours": "3-4",
    },
    "customer_interview_guide": {
        "individual_base": 8900,
        "business_base": 14900,
        "delivery_hours": "2-3",
    },
    "location_analysis": {
        "individual_base": 11900,
        "business_base": 17900,
        "delivery_hours": "10-15 min",
    },
}

REPORT_BUNDLES = {
    "marketing_bundle": {
        "name": "Marketing Bundle",
        "description": "Complete marketing foundation for launch",
        "reports": ["content_calendar", "email_funnel_system", "lead_magnet", "sales_funnel", "user_personas"],
        "individual_base": 59900,
        "business_base": 99900,
        "save_percentage": 25,
    },
    "launch_bundle": {
        "name": "Launch Bundle",
        "description": "Coordinated product launch with tracking",
        "reports": ["gtm_strategy", "gtm_launch_calendar", "mvp_roadmap", "kpi_dashboard"],
        "individual_base": 89900,
        "business_base": 149900,
        "save_percentage": 25,
    },
    "complete_starter_bundle": {
        "name": "Complete Starter Bundle",
        "description": "Everything you need to launch from zero to one",
        "reports": [
            "brand_package", "landing_page", "ad_creatives", "email_sequence", "user_personas",
            "mvp_roadmap", "gtm_strategy", "kpi_dashboard", "competitive_analysis", "pricing_strategy"
        ],
        "individual_base": 129900,
        "business_base": 229900,
        "save_percentage": 30,
    },
}

TIER_DISCOUNTS = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.STARTER: 0,
    SubscriptionTier.GROWTH: 10,
    SubscriptionTier.PRO: 15,
    SubscriptionTier.TEAM: 0,
    SubscriptionTier.BUSINESS: 20,
    SubscriptionTier.ENTERPRISE: 50,
}

def is_business_track(tier: SubscriptionTier) -> bool:
    """Check if tier is on the business track"""
    return tier in [SubscriptionTier.TEAM, SubscriptionTier.BUSINESS, SubscriptionTier.ENTERPRISE]

def get_report_price(report_type: str, tier: SubscriptionTier) -> int:
    """
    Calculate report price in cents based on report type and subscription tier.
    
    Args:
        report_type: The report type key (e.g., 'ad_creatives')
        tier: The user's subscription tier
        
    Returns:
        Price in cents after tier discount
    """
    if report_type not in REPORT_PRICING:
        raise ValueError(f"Unknown report type: {report_type}")
    
    pricing = REPORT_PRICING[report_type]
    discount = TIER_DISCOUNTS.get(tier, 0)
    
    if is_business_track(tier):
        base_price = pricing["business_base"]
    else:
        base_price = pricing["individual_base"]
    
    final_price = int(base_price * (100 - discount) / 100)
    return final_price

def get_bundle_price(bundle_type: str, tier: SubscriptionTier) -> int:
    """
    Calculate bundle price in cents based on bundle type and subscription tier.
    
    Args:
        bundle_type: The bundle type key (e.g., 'marketing_bundle')
        tier: The user's subscription tier
        
    Returns:
        Price in cents after tier discount
    """
    if bundle_type not in REPORT_BUNDLES:
        raise ValueError(f"Unknown bundle type: {bundle_type}")
    
    bundle = REPORT_BUNDLES[bundle_type]
    discount = TIER_DISCOUNTS.get(tier, 0)
    
    if is_business_track(tier):
        base_price = bundle["business_base"]
    else:
        base_price = bundle["individual_base"]
    
    final_price = int(base_price * (100 - discount) / 100)
    return final_price

def get_all_report_prices(tier: SubscriptionTier) -> dict:
    """Get all report prices for a given tier"""
    return {
        report_type: get_report_price(report_type, tier)
        for report_type in REPORT_PRICING
    }

def get_all_bundle_prices(tier: SubscriptionTier) -> dict:
    """Get all bundle prices for a given tier"""
    return {
        bundle_type: get_bundle_price(bundle_type, tier)
        for bundle_type in REPORT_BUNDLES
    }
