"""
OppGrid Keyword Matrix — Yelp
==============================
Scores Yelp reviews for service-gap signals. Low-star reviews mentioning
"no one", "can't find", "no good X in [area]" are the high-confidence
patterns. Location is taken structurally from the business object.

Primary entry point: score_yelp_review()
"""

import re
from typing import Optional, Dict, List, Any


# ============================================================================
# RATING-BASED TIERS
# ============================================================================
# Lower-star reviews carry more demand signal. 1-2 star = explicit failure.

YELP_RATING_TIERS = {
    1: {"boost": 0.25, "reason": "Explicit service failure"},
    2: {"boost": 0.18, "reason": "Significant dissatisfaction"},
    3: {"boost": 0.08, "reason": "Mixed signal, possible gap"},
    4: {"boost": 0.00, "reason": "Mostly positive, low signal"},
    5: {"boost": 0.00, "reason": "Positive review, ignored"},
}


# ============================================================================
# CATEGORY-PRIORITY MAPPING
# ============================================================================
# Yelp categories that map to high-opportunity business types.

YELP_CATEGORY_PRIORITY = {
    "homeservices":  {"boost": 0.15, "category": "home_services"},
    "professional":  {"boost": 0.12, "category": "professional"},
    "auto":          {"boost": 0.10, "category": "automotive"},
    "health":        {"boost": 0.12, "category": "healthcare"},
    "education":     {"boost": 0.10, "category": "education"},
    "petservices":   {"boost": 0.10, "category": "pet_services"},
    "childcare":     {"boost": 0.15, "category": "childcare"},
    "elderlycare":   {"boost": 0.15, "category": "elderly_care"},
    "restaurants":   {"boost": 0.05, "category": "restaurant"},
    "shopping":      {"boost": 0.05, "category": "retail"},
}


# ============================================================================
# PATTERN CATEGORIES
# ============================================================================

YELP_CATEGORIES = {

    "explicit_market_gap": {
        "baseline_confidence": 0.92,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"\bno (?:one|where|body) (?:in|around) (?:this|the|our)", "confidence": 0.95},
            {"pattern": r"can(?:'?t|not) find (?:a|any|good)",                      "confidence": 0.92},
            {"pattern": r"no (?:good|decent|reliable) (?:option|place|business)",  "confidence": 0.90},
            {"pattern": r"(?:wish|need) (?:there was|someone would) (?:open|start)", "confidence": 0.95},
            {"pattern": r"only (?:option|one|game) in town",                       "confidence": 0.88},
            {"pattern": r"have to drive (?:to|all the way)",                       "confidence": 0.85},
        ],
        "business_category_mapping": ["any"],
    },

    "service_quality_failure": {
        "baseline_confidence": 0.78,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"(?:rude|unprofessional|incompetent|dishonest)",           "confidence": 0.75},
            {"pattern": r"(?:never|don'?t) (?:return|answer|respond|show up)",      "confidence": 0.82},
            {"pattern": r"overcharged|ripped off|scammed",                         "confidence": 0.78},
            {"pattern": r"(?:waited|wait(?:ed|ing)) (?:for )?(?:hours|forever|all day)", "confidence": 0.72},
            {"pattern": r"(?:bait and switch|hidden (?:fee|charge))",               "confidence": 0.80},
            {"pattern": r"(?:had to|ended up) (?:going|driving) (?:to|elsewhere)",  "confidence": 0.80},
        ],
        "business_category_mapping": ["any"],
    },

    "competitive_displacement": {
        "baseline_confidence": 0.82,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"used to (?:go to|use|love)",                               "confidence": 0.78},
            {"pattern": r"switched (?:to|from)",                                     "confidence": 0.82},
            {"pattern": r"(?:better|worse) than",                                    "confidence": 0.65},
            {"pattern": r"(?:closed|shut down|out of business)",                     "confidence": 0.85},
            {"pattern": r"under new (?:management|ownership)",                       "confidence": 0.72},
        ],
        "business_category_mapping": ["any"],
    },

    "demand_intensity": {
        "baseline_confidence": 0.70,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"booked (?:out|up|solid) (?:for|weeks|months)",             "confidence": 0.88},
            {"pattern": r"(?:can'?t|impossible to) get (?:an? )?appointment",        "confidence": 0.85},
            {"pattern": r"waitlist|waiting list",                                    "confidence": 0.78},
            {"pattern": r"(?:sold out|all gone) (?:by|before|within)",               "confidence": 0.75},
        ],
        "business_category_mapping": ["any"],
    },
}


GOLDMINE_THRESHOLD = 0.85
VALIDATED_THRESHOLD = 0.70
WEAK_THRESHOLD = 0.50


def _classify_level(score: float) -> str:
    if score >= GOLDMINE_THRESHOLD:
        return "goldmine"
    if score >= VALIDATED_THRESHOLD:
        return "validated"
    if score >= WEAK_THRESHOLD:
        return "weak_signal"
    return "noise"


def _extract_excerpt(text: str, matched_pattern: str, window: int = 140) -> str:
    """Return ~280 char excerpt centered on the first regex hit."""
    if not text:
        return ""
    if not matched_pattern:
        return text[:280]
    m = re.search(matched_pattern, text, re.IGNORECASE)
    if not m:
        return text[:280]
    start = max(0, m.start() - window)
    end = min(len(text), m.end() + window)
    return ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")


def _noise_result(reason: str) -> Dict[str, Any]:
    return {
        "signal_score": 0.0,
        "validation_level": "noise",
        "matched_patterns": [],
        "category_hint": "other",
        "location_hint": None,
        "raw_excerpt": "",
        "source_specific": {"skip_reason": reason},
    }


def score_yelp_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a single Yelp review payload.

    Args:
        payload: Dict matching the /v1/webhooks/yelp schema. Must contain:
                 review.text (str), review.rating (int), business.categories
                 (list[str]), business.location (dict).

    Returns:
        Standard signal output dict:
        {
            "signal_score": float,        # 0.0 – 1.0
            "validation_level": str,      # goldmine | validated | weak_signal | noise
            "matched_patterns": list[str],
            "category_hint": str,
            "location_hint": dict | None,
            "raw_excerpt": str,
            "source_specific": dict,
        }
    """
    review = payload.get("review", {})
    business = payload.get("business", {})

    text = (review.get("text") or "").strip()
    try:
        rating = int(review.get("rating") or 5)
    except (TypeError, ValueError):
        rating = 5

    categories = business.get("categories") or []
    location = business.get("location") or {}

    if not text or len(text) < 20:
        return _noise_result("text too short")

    # 1. Apply rating tier boost (low stars = high signal)
    tier_boost = YELP_RATING_TIERS.get(rating, {"boost": 0.0})["boost"]

    # 2. Category boost
    category_hint = "other"
    category_boost = 0.0
    for cat_slug in categories:
        cat_lower = (cat_slug or "").lower()
        for key, cfg in YELP_CATEGORY_PRIORITY.items():
            if key in cat_lower:
                if cfg["boost"] > category_boost:
                    category_boost = cfg["boost"]
                    category_hint = cfg["category"]

    # 3. Pattern matching
    best_score = 0.0
    matched: List[str] = []
    matched_pattern_for_excerpt: Optional[str] = None

    for cat_name, cat_cfg in YELP_CATEGORIES.items():
        for pat in cat_cfg["patterns"]:
            try:
                if re.search(pat["pattern"], text, re.IGNORECASE):
                    matched.append(f"{cat_name}:{pat['pattern']}")
                    if pat["confidence"] > best_score:
                        best_score = pat["confidence"]
                        matched_pattern_for_excerpt = pat["pattern"]
            except re.error:
                continue

    if not matched:
        return _noise_result("no patterns matched")

    # 4. Combine scores
    final_score = min(1.0, best_score + tier_boost + category_boost)

    return {
        "signal_score": round(final_score, 3),
        "validation_level": _classify_level(final_score),
        "matched_patterns": matched,
        "category_hint": category_hint,
        "location_hint": {
            "city": location.get("city"),
            "state": location.get("state"),
            "zip": location.get("zip_code"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "confidence": 1.0,  # Yelp business location is API-verified
        } if location.get("city") else None,
        "raw_excerpt": _extract_excerpt(text, matched_pattern_for_excerpt or ""),
        "source_specific": {
            "rating": rating,
            "yelp_business_id": business.get("id"),
        },
    }
