"""
OppGrid Keyword Matrix — Nextdoor
===================================
Scores Nextdoor posts for hyper-local service-gap signals. Posts in the
"Recommendations" category are near-pure demand signals — residents
literally asking for a business that doesn't yet exist nearby.

Location confidence is always 1.0 (neighborhood-tagged). The neighborhood
polygon from the payload is propagated into location_hint so the geographic
extractor can persist the boundary directly.

Primary entry point: score_nextdoor_post()
"""

import re
from typing import Any, Dict, List, Optional


# ============================================================================
# CATEGORY TIERS (replaces rating tiers used by Yelp)
# ============================================================================
# Post category is the primary demand-signal discriminator on Nextdoor.

NEXTDOOR_CATEGORY_TIERS = {
    "Recommendations":  {"boost": 0.25, "reason": "Explicit ask for services"},
    "Classifieds":      {"boost": 0.15, "reason": "Local commerce signal"},
    "General":          {"boost": 0.05, "reason": "Mixed signal"},
    "Crime & Safety":   {"boost": 0.08, "reason": "Security service demand"},
    "Lost & Found":     {"boost": 0.10, "reason": "Pet/property service demand"},
    "Free Items":       {"boost": 0.00, "reason": "Low commercial signal"},
}


# ============================================================================
# PATTERN CATEGORIES
# ============================================================================

NEXTDOOR_CATEGORIES = {

    "explicit_recommendation_request": {
        "baseline_confidence": 0.94,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"(?:anyone|anybody) (?:know|recommend)",          "confidence": 0.92},
            {"pattern": r"looking for (?:a|recommendations? for)",         "confidence": 0.94},
            {"pattern": r"(?:can|could) anyone (?:suggest|recommend)",     "confidence": 0.92},
            {"pattern": r"need (?:a |someone )(?:good|reliable|trustworthy)", "confidence": 0.88},
            {"pattern": r"who do you (?:use|recommend|trust) for",         "confidence": 0.95},
            {"pattern": r"in (?:dire )?need of",                           "confidence": 0.85},
        ],
        "business_category_mapping": ["any"],
    },

    "neighborhood_gap": {
        "baseline_confidence": 0.88,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"why (?:isn'?t|aren'?t) there (?:a|any)",          "confidence": 0.95},
            {"pattern": r"we need (?:a|more) (?:in|around) (?:our|the)",    "confidence": 0.92},
            {"pattern": r"closest (?:one|option) is (?:in|over|like)",      "confidence": 0.88},
            {"pattern": r"have to (?:go|drive) (?:to|out of)",              "confidence": 0.82},
        ],
        "business_category_mapping": ["any"],
    },

    "service_complaint": {
        "baseline_confidence": 0.72,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"(?:beware|warning|stay away)",                    "confidence": 0.78},
            {"pattern": r"would (?:not|never) (?:recommend|use|hire)",      "confidence": 0.75},
            {"pattern": r"(?:terrible|horrible|awful) (?:experience|service)", "confidence": 0.72},
            {"pattern": r"(?:overcharged|scammed|cheated)",                 "confidence": 0.78},
        ],
        "business_category_mapping": ["any"],
    },

    "demand_volume": {
        "baseline_confidence": 0.70,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"(?:everyone|so many people) (?:asking|looking)",   "confidence": 0.78},
            {"pattern": r"keep seeing (?:posts|requests|people asking)",     "confidence": 0.75},
            {"pattern": r"(?:third|fourth|fifth|another) (?:post|request) about", "confidence": 0.82},
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


def score_nextdoor_post(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a single Nextdoor post payload.

    Args:
        payload: Dict matching the /v1/webhooks/nextdoor schema. Must contain:
                 post.title (str), post.body (str), post.category (str),
                 post.neighborhood (dict with name, city, state, zip, polygon,
                 centroid).

    Returns:
        Standard signal output dict:
        {
            "signal_score": float,
            "validation_level": str,      # goldmine | validated | weak_signal | noise
            "matched_patterns": list[str],
            "category_hint": str,
            "location_hint": dict | None, # includes polygon when available
            "raw_excerpt": str,
            "source_specific": dict,
        }
    """
    post = payload.get("post", {})
    neighborhood = post.get("neighborhood", {})

    title = (post.get("title") or "").strip()
    body = (post.get("body") or "").strip()
    text = f"{title} {body}".strip()
    post_category = (post.get("category") or "General").strip()

    if not text or len(text) < 10:
        return _noise_result("text too short")

    # 1. Category tier boost
    tier_info = NEXTDOOR_CATEGORY_TIERS.get(post_category, {"boost": 0.02})
    tier_boost = tier_info["boost"]

    # 2. Pattern matching across all NEXTDOOR_CATEGORIES
    best_score = 0.0
    matched: List[str] = []
    matched_pattern_for_excerpt: Optional[str] = None

    for cat_name, cat_cfg in NEXTDOOR_CATEGORIES.items():
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

    # 3. Combine
    final_score = min(1.0, best_score + tier_boost)

    # 4. Build location hint — always 1.0 confidence (neighborhood-tagged)
    location_hint: Optional[Dict[str, Any]] = None
    if neighborhood.get("city") or neighborhood.get("name"):
        location_hint = {
            "city": neighborhood.get("city"),
            "state": neighborhood.get("state"),
            "zip": neighborhood.get("zip"),
            "neighborhood": neighborhood.get("name"),
            "centroid": neighborhood.get("centroid"),
            "polygon": neighborhood.get("polygon"),   # GeoJSON polygon preserved
            "confidence": 1.0,
        }

    return {
        "signal_score": round(final_score, 3),
        "validation_level": _classify_level(final_score),
        "matched_patterns": matched,
        "category_hint": "community_social" if post_category == "General" else "home_services",
        "location_hint": location_hint,
        "raw_excerpt": _extract_excerpt(text, matched_pattern_for_excerpt or ""),
        "source_specific": {
            "post_category": post_category,
            "post_id": post.get("id"),
            "neighborhood_name": neighborhood.get("name"),
        },
    }
