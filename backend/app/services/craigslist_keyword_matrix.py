"""
OppGrid Keyword Matrix — Craigslist Expansion
=============================================
Scores Craigslist listing text against category-specific demand patterns with
confidence weights, co-occurrence gating, and scoring modifiers (urgency,
willingness-to-pay, agreement, repeat-post frequency, location specificity).

Primary entry point: score_craigslist_post()
"""

import re
from typing import Optional


# ============================================================================
# CRAIGSLIST-SPECIFIC CATEGORY BUCKETS
# ============================================================================
# Each pattern carries an individual confidence score.  The category-level
# baseline_confidence is the fallback when no specific score is set.
# Broad terms use requires_cooccurrence to avoid false positives: the
# pattern only counts if a gating pattern appears within COOCCURRENCE_WINDOW
# characters of the match.

CRAIGSLIST_CATEGORIES = {

    "craigslist_iso_explicit": {
        "baseline_confidence": 0.95,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"\bISO\b", "confidence": 0.95},
            {"pattern": r"\bin search of\b", "confidence": 0.95},
        ],
        "business_category_mapping": [],
        "note": "Craigslist-native abbreviation for explicit demand",
    },

    "craigslist_work_productivity": {
        "baseline_confidence": 0.75,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"wish there was a service", "confidence": 1.00},
            {"pattern": r"can't find anyone who", "confidence": 0.90},
            {"pattern": r"looking for someone to", "confidence": 0.85},
            {"pattern": r"seeking recommendations", "confidence": 0.75},
            {"pattern": r"need help with", "confidence": 0.75},
            {"pattern": r"tired of", "confidence": 0.70, "requires_cooccurrence": "friction"},
            {"pattern": r"frustrated with", "confidence": 0.70, "requires_cooccurrence": "friction"},
        ],
        "business_category_mapping": ["professional_services"],
    },

    "craigslist_money_finance": {
        "baseline_confidence": 0.75,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"can't afford", "confidence": 0.90},
            {"pattern": r"too expensive", "confidence": 0.85},
            {"pattern": r"looking for cheaper", "confidence": 0.85},
            {"pattern": r"payment plan", "confidence": 0.80},
            {"pattern": r"financing", "confidence": 0.70},
            {"pattern": r"cost of living", "confidence": 0.65},
            {"pattern": r"affordable", "confidence": 0.60, "requires_cooccurrence": "demand"},
            {"pattern": r"\bbudget\b", "confidence": 0.55, "requires_cooccurrence": "demand"},
        ],
        "business_category_mapping": ["financial_services"],
    },

    "craigslist_health_wellness": {
        "baseline_confidence": 0.80,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"doctor won't", "confidence": 0.95},
            {"pattern": r"insurance doesn't cover", "confidence": 0.95},
            {"pattern": r"can't get appointment", "confidence": 0.90},
            {"pattern": r"caregiver needed", "confidence": 0.90},
            {"pattern": r"waiting list", "confidence": 0.85},
            {"pattern": r"alternative to", "confidence": 0.70},
            {"pattern": r"home health", "confidence": 0.70},
            {"pattern": r"natural remedy", "confidence": 0.65},
        ],
        "business_category_mapping": ["healthcare"],
    },

    "craigslist_home_living": {
        "baseline_confidence": 0.80,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"contractor ghosted", "confidence": 0.95},
            {"pattern": r"handyman needed", "confidence": 0.85},
            {"pattern": r"emergency repair", "confidence": 0.85},
            {"pattern": r"background checked", "confidence": 0.75},
            {"pattern": r"same day", "confidence": 0.75, "requires_cooccurrence": "service"},
            {"pattern": r"can't find", "confidence": 0.70, "requires_cooccurrence": "noun"},
            {"pattern": r"trustworthy", "confidence": 0.60, "requires_cooccurrence": "demand"},
            {"pattern": r"reliable", "confidence": 0.55, "requires_cooccurrence": "demand"},
        ],
        "business_category_mapping": ["home_services"],
    },

    "craigslist_technology": {
        "baseline_confidence": 0.80,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"no app for", "confidence": 0.95},
            {"pattern": r"wish my phone could", "confidence": 0.95},
            {"pattern": r"broken website", "confidence": 0.80},
            {"pattern": r"doesn't work with", "confidence": 0.75},
            {"pattern": r"software that", "confidence": 0.70},
            {"pattern": r"automation", "confidence": 0.55, "requires_cooccurrence": "demand"},
            {"pattern": r"integrate", "confidence": 0.55, "requires_cooccurrence": "demand"},
            {"pattern": r"\bsync\b", "confidence": 0.50, "requires_cooccurrence": "demand"},
        ],
        "business_category_mapping": [],
    },

    "craigslist_transportation": {
        "baseline_confidence": 0.75,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"ride needed", "confidence": 0.90},
            {"pattern": r"moving help", "confidence": 0.85},
            {"pattern": r"car won't", "confidence": 0.85},
            {"pattern": r"mechanic recommendation", "confidence": 0.80},
            {"pattern": r"shipping", "confidence": 0.60, "requires_cooccurrence": "demand"},
            {"pattern": r"\bhaul\b", "confidence": 0.60, "requires_cooccurrence": "demand"},
            {"pattern": r"delivery", "confidence": 0.55, "requires_cooccurrence": "demand"},
            {"pattern": r"transport", "confidence": 0.55, "requires_cooccurrence": "demand"},
        ],
        "business_category_mapping": ["transportation"],
    },

    "craigslist_education": {
        "baseline_confidence": 0.75,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"tutor needed", "confidence": 0.90},
            {"pattern": r"teach me", "confidence": 0.85},
            {"pattern": r"learn how to", "confidence": 0.75},
            {"pattern": r"classes for", "confidence": 0.70},
            {"pattern": r"online course", "confidence": 0.65},
            {"pattern": r"\bmentor\b", "confidence": 0.65},
            {"pattern": r"certification", "confidence": 0.60, "requires_cooccurrence": "demand"},
            {"pattern": r"training", "confidence": 0.55, "requires_cooccurrence": "demand"},
        ],
        "business_category_mapping": ["childcare_education"],
    },

    "craigslist_shopping_services": {
        "baseline_confidence": 0.75,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"where can i buy", "confidence": 0.95},
            {"pattern": r"can't find in stores", "confidence": 0.95},
            {"pattern": r"hard to find", "confidence": 0.80},
            {"pattern": r"same day delivery", "confidence": 0.75},
            {"pattern": r"made to order", "confidence": 0.70},
            {"pattern": r"personalized", "confidence": 0.60, "requires_cooccurrence": "demand"},
            {"pattern": r"\bcustom\b", "confidence": 0.55, "requires_cooccurrence": "demand"},
            {"pattern": r"\blocal\b", "confidence": 0.50, "requires_cooccurrence": "demand"},
        ],
        "business_category_mapping": [],
    },
}


# ============================================================================
# GENERIC "X NEEDED" PATTERN
# ============================================================================

CRAIGSLIST_GENERIC_DEMAND = {
    "pattern": r"\b([a-z]+(?:\s[a-z]+)?)\s+needed\b",
    "baseline_confidence": 0.85,
    "extraction": "capture_group_1_as_service_type",
    "note": "Generic 'X needed' — extracts X as the service type",
}


# ============================================================================
# CRAIGSLIST SIGNAL MODIFIERS
# ============================================================================

CRAIGSLIST_SIGNAL_MODIFIERS = {

    "agreement_signals": {
        "patterns": [
            r"\bme too\b",
            r"\bsame here\b",
            r"\bthis[!.]",
            r"\bexactly\b",
            r"\bi feel this\b",
        ],
        "boost_per_match": 0.05,
        "max_boost": 0.20,
        "scope": "replies",
    },

    "urgency": {
        "patterns": [
            r"\basap\b",
            r"\burgent\b",
            r"\bemergency\b",
            r"\btoday\b",
            r"\bimmediately\b",
            r"\bdesperately\b",
        ],
        "boost": 0.10,
        "max_boost": 0.10,
        "scope": "post_text",
    },

    "willingness_to_pay": {
        "patterns": [
            r"\$\d+",
            r"will pay",
            r"budget is",
            r"how much",
            r"willing to pay",
            r"\d+\s*dollars?",
        ],
        "boost": 0.15,
        "max_boost": 0.15,
        "scope": "post_text",
    },

    "repeat_posts": {
        "implementation": "dedupe_aware",
        "logic": "count_similar_posts_in_window",
        "window_days": 30,
        "similarity_threshold": 0.80,
        "boost_per_duplicate": 0.05,
        "max_boost": 0.25,
        "note": "Requires post-dedup analysis; not inline regex",
    },

    "location_specificity": {
        "patterns": [
            r"\bin\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b",
            r"\b(near|by|around)\s+[A-Z][a-z]+\b",
            r"\b\d{5}\b",
        ],
        "boost": 0.10,
        "max_boost": 0.10,
        "scope": "post_text",
    },
}


# ============================================================================
# CO-OCCURRENCE GATES
# ============================================================================
# Broad terms only score when a demand/friction/service/noun context appears
# within COOCCURRENCE_WINDOW characters of the match.

COOCCURRENCE_GATES = {
    "demand": [
        r"\b(need|needs|want|wants|looking for|seeking|searching|wish|require|requires)\b",
    ],
    "friction": [
        r"\b(can't|cannot|won't|hard to|difficult|impossible|struggle)\b",
    ],
    "service": [
        r"\b(service|help|repair|fix|install|replace|clean|deliver)\b",
    ],
    "noun": [
        r"\b(a|an|the)\s+[a-z]+",
    ],
}

COOCCURRENCE_WINDOW = 50  # characters on either side of match


# ============================================================================
# HIGH-SIGNAL CRAIGSLIST SECTIONS
# ============================================================================
# Priority order for scraper URL rotation.  discussion_forums excluded here
# because it requires a separate scraper (different DOM structure).

CRAIGSLIST_HIGH_SIGNAL_SECTIONS = {
    "services_wanted": {
        "path": "sss",
        "priority": "critical",
        "reason": "Direct demand signals — explicit service requests",
        "frequency": "6h",
    },
    "gigs": {
        "path": "ggg",
        "priority": "high",
        "reason": "What people pay for now (explicit willingness to pay)",
        "frequency": "6h",
    },
    "for_sale_wanted": {
        "path": "waa",
        "priority": "high",
        "reason": "Product gaps — people asking to buy what doesn't exist locally",
        "frequency": "12h",
    },
    "community_general": {
        "path": "ccc",
        "priority": "high",
        "reason": "Raw complaints, unstructured asks",
        "frequency": "12h",
    },
    "housing_wanted": {
        "path": "hsw",
        "priority": "medium",
        "reason": "Housing pain points",
        "frequency": "12h",
    },
}


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _check_cooccurrence(text: str, match_pos: int, gate_key: str) -> bool:
    """Return True if any gate pattern appears within COOCCURRENCE_WINDOW chars."""
    gate_patterns = COOCCURRENCE_GATES.get(gate_key, [])
    if not gate_patterns:
        return True

    window_start = max(0, match_pos - COOCCURRENCE_WINDOW)
    window_end = min(len(text), match_pos + COOCCURRENCE_WINDOW)
    window_text = text[window_start:window_end]

    return any(re.search(gp, window_text, re.IGNORECASE) for gp in gate_patterns)


# ============================================================================
# PRIMARY SCORING FUNCTION
# ============================================================================

def score_craigslist_post(
    text: str,
    category: Optional[str] = None,
    replies: Optional[list] = None,
    duplicate_count: int = 0,
) -> dict:
    """
    Score a Craigslist post against the expanded keyword matrix.

    Args:
        text:            Post title + body concatenated
        category:        Craigslist URL section code (e.g., 'sss', 'hsw')
        replies:         List of reply text strings (for agreement detection)
        duplicate_count: Number of similar posts seen in the 30-day window

    Returns:
        {
            "signal_score":       float [0.0, 1.0],
            "matched_patterns":   list of match dicts,
            "business_categories": list of BUSINESS_CATEGORIES keys,
            "modifiers_applied":  list of modifier names,
            "validation_level":   "goldmine" | "strong_signal" | "moderate" | "weak",
            "extracted_services": list of strings (from generic "X needed"),
        }
    """
    result: dict = {
        "signal_score": 0.0,
        "matched_patterns": [],
        "business_categories": set(),
        "modifiers_applied": [],
        "validation_level": None,
        "extracted_services": [],
    }

    if not text:
        result["validation_level"] = "weak"
        result["business_categories"] = []
        return result

    text_lower = text.lower()
    max_pattern_score = 0.0

    # --- 1. Match primary category patterns ---
    for category_key, category_data in CRAIGSLIST_CATEGORIES.items():
        for pattern_entry in category_data["patterns"]:
            pattern = pattern_entry["pattern"]
            base_conf = pattern_entry["confidence"]
            gate = pattern_entry.get("requires_cooccurrence")

            match = re.search(pattern, text_lower, re.IGNORECASE)
            if not match:
                continue

            if gate and not _check_cooccurrence(text_lower, match.start(), gate):
                continue

            result["matched_patterns"].append({
                "category": category_key,
                "pattern": pattern,
                "confidence": base_conf,
            })
            result["business_categories"].update(
                category_data.get("business_category_mapping", [])
            )
            max_pattern_score = max(max_pattern_score, base_conf)

    # --- 2. Generic "X needed" extraction ---
    _already_specific = {"tutor", "handyman", "caregiver", "ride"}
    for m in re.finditer(CRAIGSLIST_GENERIC_DEMAND["pattern"], text_lower):
        service_type = m.group(1).strip()
        if service_type in _already_specific:
            continue
        result["matched_patterns"].append({
            "category": "generic_demand",
            "pattern": f"{service_type} needed",
            "confidence": CRAIGSLIST_GENERIC_DEMAND["baseline_confidence"],
            "extracted_service": service_type,
        })
        result["extracted_services"].append(service_type)
        max_pattern_score = max(max_pattern_score, CRAIGSLIST_GENERIC_DEMAND["baseline_confidence"])

    score = max_pattern_score

    # --- 3. Apply modifiers ---

    urgency = CRAIGSLIST_SIGNAL_MODIFIERS["urgency"]
    if any(re.search(p, text_lower) for p in urgency["patterns"]):
        score = min(1.0, score + urgency["boost"])
        result["modifiers_applied"].append("urgency")

    wtp = CRAIGSLIST_SIGNAL_MODIFIERS["willingness_to_pay"]
    if any(re.search(p, text_lower) for p in wtp["patterns"]):
        score = min(1.0, score + wtp["boost"])
        result["modifiers_applied"].append("willingness_to_pay")

    if replies:
        agreement = CRAIGSLIST_SIGNAL_MODIFIERS["agreement_signals"]
        count = sum(
            1 for reply in replies
            if any(re.search(p, reply.lower()) for p in agreement["patterns"])
        )
        if count > 0:
            boost = min(count * agreement["boost_per_match"], agreement["max_boost"])
            score = min(1.0, score + boost)
            result["modifiers_applied"].append(f"agreement_signals({count})")

    if duplicate_count > 0:
        rp = CRAIGSLIST_SIGNAL_MODIFIERS["repeat_posts"]
        boost = min(duplicate_count * rp["boost_per_duplicate"], rp["max_boost"])
        score = min(1.0, score + boost)
        result["modifiers_applied"].append(f"repeat_posts({duplicate_count})")

    loc = CRAIGSLIST_SIGNAL_MODIFIERS["location_specificity"]
    if any(re.search(p, text) for p in loc["patterns"]):
        score = min(1.0, score + loc["boost"])
        result["modifiers_applied"].append("location_specificity")

    result["signal_score"] = round(score, 3)

    # --- 4. Assign validation tier ---
    if score >= 0.90:
        result["validation_level"] = "goldmine"
    elif score >= 0.75:
        result["validation_level"] = "strong_signal"
    elif score >= 0.60:
        result["validation_level"] = "moderate"
    else:
        result["validation_level"] = "weak"

    result["business_categories"] = sorted(result["business_categories"])
    return result
