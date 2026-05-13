"""
OppGrid Keyword Matrix — GreatSchools
=======================================
Scores GreatSchools parent reviews and school stat payloads for education-
services and family-decision-driver business opportunities.

TWO entry points:
  score_greatschools_review()      — parent/student review text mode
  score_greatschools_school_stats() — structural signal: low GS rating ×
                                      high enrollment × growing ZIP

A 3-star-or-below school with active parent complaints in a growing ZIP is
a high-confidence education-services opportunity (tutoring, after-school,
test prep, specialized programs, private-school alternatives).
"""

import re
from typing import Any, Dict, List, Optional


# ============================================================================
# RATING TIERS (GS school rating 1-10; lower = more service demand)
# ============================================================================

GREATSCHOOLS_RATING_TIERS: List[Dict[str, Any]] = [
    {"range": range(1, 4),  "boost": 0.20, "reason": "Underperforming school = service demand"},
    {"range": range(4, 7),  "boost": 0.10, "reason": "Mid-performing, supplemental services market"},
    {"range": range(7, 11), "boost": 0.02, "reason": "Strong school, low supplemental demand"},
]


# ============================================================================
# PATTERN CATEGORIES (review-mode)
# ============================================================================

GREATSCHOOLS_CATEGORIES = {

    "tutoring_demand": {
        "baseline_confidence": 0.88,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"need(?:s|ed)? (?:a )?tutor",                      "confidence": 0.95},
            {"pattern": r"(?:falling|fell) behind",                         "confidence": 0.85},
            {"pattern": r"(?:struggling|struggle) with (?:math|reading|writing|science)", "confidence": 0.88},
            {"pattern": r"(?:supplement|extra help|outside help)",          "confidence": 0.85},
        ],
        "business_category_mapping": ["education", "tutoring"],
    },

    "specialized_program_gap": {
        "baseline_confidence": 0.90,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"no (?:gifted|GATE|honors|AP|IB) program",          "confidence": 0.95},
            {"pattern": r"(?:special needs|IEP|504|autism|ADHD) (?:support|services|program)", "confidence": 0.92},
            {"pattern": r"(?:no|lack of) (?:music|art|drama|sports|STEM)",   "confidence": 0.88},
            {"pattern": r"(?:overcrowded|too many students|class sizes too)", "confidence": 0.85},
        ],
        "business_category_mapping": ["education", "enrichment"],
    },

    "safety_environment_gap": {
        "baseline_confidence": 0.78,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"(?:bullying|unsafe|fights|drugs)",                 "confidence": 0.78},
            {"pattern": r"(?:considering|looking at) (?:private|charter|homeschool)", "confidence": 0.85},
            {"pattern": r"(?:moved|moving|leaving) (?:the )?district",       "confidence": 0.82},
        ],
        "business_category_mapping": ["education", "alternative_schools"],
    },

    "facilities_gap": {
        "baseline_confidence": 0.70,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"(?:outdated|run-?down|falling apart)",             "confidence": 0.72},
            {"pattern": r"no (?:after-?school|aftercare|extended day)",      "confidence": 0.88},
            {"pattern": r"(?:lack of|no) (?:counselors|nurses|specialists)", "confidence": 0.82},
        ],
        "business_category_mapping": ["childcare", "after_school"],
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


def _get_rating_boost(school_rating: int) -> float:
    """Look up boost for a given GS school rating (1-10)."""
    for tier in GREATSCHOOLS_RATING_TIERS:
        if school_rating in tier["range"]:
            return tier["boost"]
    return 0.0


def score_greatschools_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a GreatSchools parent/student review payload (review-mode).

    Args:
        payload: Dict with:
                 school.{id, name, level, rating (1-10), enrollment}
                 school.location.{address, city, state, zip, lat, lng, district}
                 review.{rating (1-5), text, role, posted_at}

    Returns:
        Standard signal output dict with category_hint = "education".
    """
    school = payload.get("school", {})
    review = payload.get("review", {})
    location = school.get("location", {})

    text = (review.get("text") or "").strip()
    if not text or len(text) < 20:
        return _noise_result("review text too short")

    try:
        school_rating = int(school.get("rating") or 5)
    except (TypeError, ValueError):
        school_rating = 5

    # 1. School-level rating boost
    rating_boost = _get_rating_boost(school_rating)

    # 2. Pattern matching
    best_score = 0.0
    matched: List[str] = []
    matched_pattern_for_excerpt: Optional[str] = None

    for cat_name, cat_cfg in GREATSCHOOLS_CATEGORIES.items():
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
    final_score = min(1.0, best_score + rating_boost)

    location_hint: Optional[Dict[str, Any]] = None
    if location.get("city"):
        location_hint = {
            "city": location.get("city"),
            "state": location.get("state"),
            "zip": location.get("zip"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "confidence": 1.0,
        }

    return {
        "signal_score": round(final_score, 3),
        "validation_level": _classify_level(final_score),
        "matched_patterns": matched,
        "category_hint": "education",
        "location_hint": location_hint,
        "raw_excerpt": _extract_excerpt(text, matched_pattern_for_excerpt or ""),
        "source_specific": {
            "school_rating": school_rating,
            "school_name": school.get("name"),
            "district": location.get("district"),
            "enrollment": school.get("enrollment"),
            "reviewer_role": review.get("role"),
        },
    }


def score_greatschools_school_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a GreatSchools school stats payload (structural-signal mode).

    Pure structural signal: low GS rating × high enrollment × growing ZIP.
    No review text required — generates a signal from school data alone.

    signal_score = rating_boost + enrollment_boost + growth_boost (capped 1.0)
    category_hint = "education"
    validation_level = "weak_signal" by default unless enrollment > 800.

    Args:
        payload: Dict with school.{rating, enrollment, zip_growth_pct}
                 and school.location.{city, state, zip, lat, lng, district}

    Returns:
        Standard signal output dict.
    """
    school = payload.get("school", {})
    location = school.get("location", {})

    try:
        school_rating = int(school.get("rating") or 5)
    except (TypeError, ValueError):
        school_rating = 5

    try:
        enrollment = int(school.get("enrollment") or 0)
    except (TypeError, ValueError):
        enrollment = 0

    try:
        zip_growth_pct = float(school.get("zip_growth_pct") or 0.0)
    except (TypeError, ValueError):
        zip_growth_pct = 0.0

    # Must have at least a city to be useful
    if not location.get("city") and not school.get("name"):
        return _noise_result("no school location available")

    # 1. Rating-based structural boost (spec formula)
    # max(0, (5 - school.rating/2) * 0.15)
    # rating=1 → (5-0.5)*0.15=0.675; rating=5 → (5-2.5)*0.15=0.375; rating=9 → (5-4.5)*0.15=0.075
    rating_boost = max(0.0, (5 - school_rating / 2) * 0.15)

    # 2. Enrollment boost — large student bodies = larger addressable market
    if enrollment >= 1000:
        enrollment_boost = 0.15
    elif enrollment >= 800:
        enrollment_boost = 0.10
    elif enrollment >= 500:
        enrollment_boost = 0.05
    else:
        enrollment_boost = 0.0

    # 3. ZIP growth boost — growing population amplifies education demand
    if zip_growth_pct >= 0.10:
        growth_boost = 0.10
    elif zip_growth_pct >= 0.05:
        growth_boost = 0.05
    else:
        growth_boost = 0.0

    final_score = min(1.0, rating_boost + enrollment_boost + growth_boost)

    if final_score < WEAK_THRESHOLD:
        return _noise_result("insufficient structural signal")

    location_hint: Optional[Dict[str, Any]] = None
    if location.get("city"):
        location_hint = {
            "city": location.get("city"),
            "state": location.get("state"),
            "zip": location.get("zip"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "confidence": 1.0,
        }

    return {
        "signal_score": round(final_score, 3),
        "validation_level": _classify_level(final_score),
        "matched_patterns": [f"structural:low_rating_{school_rating}_enrollment_{enrollment}"],
        "category_hint": "education",
        "location_hint": location_hint,
        "raw_excerpt": (
            f"School rating {school_rating}/10, enrollment {enrollment}, "
            f"ZIP growth {zip_growth_pct:.1%}"
        ),
        "source_specific": {
            "school_rating": school_rating,
            "school_name": school.get("name"),
            "district": location.get("district"),
            "enrollment": enrollment,
            "zip_growth_pct": zip_growth_pct,
            "signal_mode": "school_stats",
        },
    }
