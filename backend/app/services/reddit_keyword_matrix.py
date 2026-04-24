"""
OppGrid Keyword Matrix — Reddit
================================
Scores Reddit post text against demand-signal patterns tuned for entrepreneurship,
small-business, and service-seeking subreddits.

Primary entry point: score_reddit_post()

Field mapping from Apify reddit-scraper-lite payload:
  title              → post title
  body               → post body text
  parsedCommunityName → subreddit slug (no "r/" prefix)
  upVotes            → upvote count
  numberOfComments   → comment count
  flair              → post flair (may be None)
"""

import re
from typing import Optional


# ============================================================================
# SUBREDDIT TIERS
# ============================================================================
# Subreddits are tiered by how directly they map to real market demand.
# Boost is added to the raw pattern score as a flat modifier.

SUBREDDIT_TIERS = {
    # Tier 1 — Explicit transaction / hiring intent
    "forhire":          {"boost": 0.20, "reason": "People paying for services right now"},
    "slavelabour":      {"boost": 0.20, "reason": "Explicit gig/task demand"},
    "hiring":           {"boost": 0.18, "reason": "Active employer demand"},
    "jobbit":           {"boost": 0.15, "reason": "Job postings = service demand"},

    # Tier 2 — Active entrepreneur / small business operators
    "entrepreneur":     {"boost": 0.15, "reason": "Founder pain points and ideas"},
    "smallbusiness":    {"boost": 0.15, "reason": "Real owner pain points"},
    "startups":         {"boost": 0.12, "reason": "Pre-revenue founders seeking solutions"},
    "business":         {"boost": 0.10, "reason": "General business discussions"},
    "ecommerce":        {"boost": 0.12, "reason": "Operator tool and service gaps"},
    "dropshipping":     {"boost": 0.10, "reason": "Operator friction signals"},
    "Entrepreneur":     {"boost": 0.15, "reason": "Alias capitalisation"},

    # Tier 3 — Side hustle / freelance
    "sidehustle":       {"boost": 0.10, "reason": "Income-seeking = willingness to invest"},
    "freelance":        {"boost": 0.12, "reason": "Service supply/demand intersection"},
    "freelancing":      {"boost": 0.12, "reason": "Alias"},
    "digitalnomad":     {"boost": 0.08, "reason": "Remote service demand"},

    # Tier 4 — Idea validation (moderate signal)
    "businessideas":    {"boost": 0.08, "reason": "Explicit gap articulation"},
    "growmybusiness":   {"boost": 0.10, "reason": "Active growth-seeking owners"},
    "marketing":        {"boost": 0.08, "reason": "Marketing tool gaps"},
    "socialmedia":      {"boost": 0.06, "reason": "Platform friction"},
    "content_marketing":{"boost": 0.06, "reason": "Content tool gaps"},

    # Tier 5 — Consumer pain (lower but still valuable)
    "personalfinance":  {"boost": 0.06, "reason": "Financial service gaps"},
    "povertyfinance":   {"boost": 0.08, "reason": "Underserved market friction"},
    "frugal":           {"boost": 0.06, "reason": "Affordability gaps"},
    "legaladvice":      {"boost": 0.08, "reason": "Professional service gaps"},
    "tax":              {"boost": 0.08, "reason": "Tax service demand"},
    "realestate":       {"boost": 0.06, "reason": "Real estate service gaps"},
    "landlord":         {"boost": 0.08, "reason": "Property management gaps"},
    "humanresources":   {"boost": 0.08, "reason": "HR tool/service gaps"},
}


# ============================================================================
# PATTERN CATEGORIES
# ============================================================================

REDDIT_CATEGORIES = {

    "explicit_service_demand": {
        "baseline_confidence": 0.88,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"\bISO\b",                                   "confidence": 0.95},
            {"pattern": r"\bin search of\b",                          "confidence": 0.95},
            {"pattern": r"looking (?:to hire|for someone to|for a)",  "confidence": 0.90},
            {"pattern": r"need(?:ing)? (?:help|someone) (?:with|to)", "confidence": 0.88},
            {"pattern": r"can anyone (?:recommend|help|suggest)",     "confidence": 0.85},
            {"pattern": r"looking for (?:a|an) (?:good |reliable |affordable )?(?:service|tool|freelancer|agency|consultant|developer|designer|VA|virtual assistant)", "confidence": 0.88},
            {"pattern": r"any (?:recommendations|suggestions) for",   "confidence": 0.75},
            {"pattern": r"who (?:do|can|should) I (?:hire|use|contact|call)", "confidence": 0.85},
        ],
        "business_category_mapping": ["professional_services"],
    },

    "market_gap_signals": {
        "baseline_confidence": 0.92,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"why isn['']t there",                        "confidence": 0.98},
            {"pattern": r"I wish there (?:was|were|is)",              "confidence": 0.95},
            {"pattern": r"no (?:app|tool|service|software|platform) (?:for|that)",  "confidence": 0.95},
            {"pattern": r"someone should (?:build|make|create)",      "confidence": 0.95},
            {"pattern": r"doesn['']t exist",                          "confidence": 0.90},
            {"pattern": r"gap in the market",                         "confidence": 0.92},
            {"pattern": r"nobody (?:offers|does|makes|provides)",     "confidence": 0.90},
            {"pattern": r"hard to find (?:a|an|good)",                "confidence": 0.80},
            {"pattern": r"can['']t find (?:a|an|anyone|any)",         "confidence": 0.85},
            {"pattern": r"there['']s no (?:good|reliable|affordable)", "confidence": 0.85},
        ],
        "business_category_mapping": [],
    },

    "pain_point_friction": {
        "baseline_confidence": 0.72,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"frustrated (?:with|by|at)",                 "confidence": 0.80},
            {"pattern": r"hate (?:that|how|when|the fact)",           "confidence": 0.78},
            {"pattern": r"struggling (?:with|to)",                    "confidence": 0.75},
            {"pattern": r"impossible to",                             "confidence": 0.80},
            {"pattern": r"drives me (?:crazy|nuts|insane)",           "confidence": 0.78},
            {"pattern": r"such a pain",                               "confidence": 0.75},
            {"pattern": r"(?:no one|nobody) (?:helps|cares|responds)", "confidence": 0.80},
            {"pattern": r"gave up (?:trying|looking|searching)",      "confidence": 0.82},
            {"pattern": r"couldn['']t find (?:a|anyone|anything)",    "confidence": 0.78},
            {"pattern": r"wasted (?:hours|days|weeks|money) (?:on|trying)", "confidence": 0.80},
        ],
        "business_category_mapping": [],
    },

    "willingness_to_pay": {
        "baseline_confidence": 0.88,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"(?:I |would |will )pay (?:for|someone|good)",   "confidence": 0.95},
            {"pattern": r"worth paying for",                          "confidence": 0.92},
            {"pattern": r"willing to pay",                            "confidence": 0.92},
            {"pattern": r"budget (?:of|is|around|for) (?:\$|\d)",    "confidence": 0.90},
            {"pattern": r"\$\d+\s*(?:per|/|a) (?:month|hour|week|project)", "confidence": 0.90},
            {"pattern": r"how much (?:would|should|does) it cost",    "confidence": 0.80},
            {"pattern": r"price (?:for|of|on) (?:a|the|this)",       "confidence": 0.70,
             "requires_cooccurrence": "demand"},
            {"pattern": r"what (?:do|would) you charge",              "confidence": 0.88},
        ],
        "business_category_mapping": [],
    },

    "business_opportunity": {
        "baseline_confidence": 0.70,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"business (?:idea|opportunity|model|gap)",   "confidence": 0.82},
            {"pattern": r"thinking (?:about|of) (?:starting|building|launching)", "confidence": 0.78},
            {"pattern": r"underserved (?:market|niche|audience)",     "confidence": 0.90},
            {"pattern": r"untapped (?:market|niche|opportunity)",     "confidence": 0.90},
            {"pattern": r"demand for (?:a|this|more)",               "confidence": 0.80},
            {"pattern": r"validated (?:idea|demand|market)",         "confidence": 0.82},
            {"pattern": r"people (?:keep|always) asking (?:me|us|for)", "confidence": 0.85},
            {"pattern": r"customers (?:always|keep|constantly) (?:ask|want|request)", "confidence": 0.85},
        ],
        "business_category_mapping": [],
    },

    "service_recommendation_request": {
        "baseline_confidence": 0.72,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"(?:any|anyone) (?:use|used|using) (?:a|an|the)",  "confidence": 0.70,
             "requires_cooccurrence": "demand"},
            {"pattern": r"recommend (?:a|an|any|good)",              "confidence": 0.75},
            {"pattern": r"best (?:way|tool|service|platform|option) (?:to|for)", "confidence": 0.72},
            {"pattern": r"alternatives? to",                         "confidence": 0.70},
            {"pattern": r"what (?:do|does) (?:everyone|you|people) use for", "confidence": 0.78},
            {"pattern": r"switch(?:ing)? (?:from|away from)",        "confidence": 0.72},
            {"pattern": r"looking for (?:something|an alternative|a replacement)", "confidence": 0.75},
        ],
        "business_category_mapping": [],
    },

    "hiring_freelance": {
        "baseline_confidence": 0.85,
        "validation_level": "strong_signal",
        "patterns": [
            {"pattern": r"\[for hire\]",                             "confidence": 0.95},
            {"pattern": r"\[hiring\]",                               "confidence": 0.95},
            {"pattern": r"hiring (?:a|an|now|remotely)",             "confidence": 0.90},
            {"pattern": r"freelancer (?:needed|wanted|required)",    "confidence": 0.90},
            {"pattern": r"contractor (?:needed|for|wanted)",         "confidence": 0.85},
            {"pattern": r"part.time (?:help|assistant|support)",     "confidence": 0.80},
            {"pattern": r"virtual assistant",                        "confidence": 0.82},
            {"pattern": r"outsource (?:my|our|this)",                "confidence": 0.82},
        ],
        "business_category_mapping": ["professional_services"],
    },
}


# ============================================================================
# GENERIC "X NEEDED" PATTERN  (same as Craigslist)
# ============================================================================

REDDIT_GENERIC_DEMAND = {
    "pattern": r"\b([a-z]+(?:\s[a-z]+)?)\s+needed\b",
    "baseline_confidence": 0.82,
    "extraction": "capture_group_1_as_service_type",
}


# ============================================================================
# SIGNAL MODIFIERS
# ============================================================================

REDDIT_SIGNAL_MODIFIERS = {

    "urgency": {
        "patterns": [
            r"\basap\b",
            r"\burgent(?:ly)?\b",
            r"\bemergency\b",
            r"\btoday\b",
            r"\bimmediately\b",
            r"\bdesperately\b",
            r"\bright now\b",
        ],
        "boost": 0.10,
        "scope": "post_text",
    },

    "willingness_to_pay_inline": {
        "patterns": [
            r"\$\d+",
            r"will pay",
            r"budget is",
            r"willing to pay",
            r"\d+\s*dollars?",
            r"per (?:hour|month|project|week)",
        ],
        "boost": 0.15,
        "scope": "post_text",
    },

    "high_upvotes": {
        "thresholds": [
            {"min": 100, "boost": 0.15},
            {"min":  50, "boost": 0.10},
            {"min":  10, "boost": 0.05},
        ],
        "scope": "upvotes",
    },

    "high_comments": {
        "thresholds": [
            {"min": 50, "boost": 0.10},
            {"min": 20, "boost": 0.07},
            {"min":  5, "boost": 0.04},
        ],
        "scope": "num_comments",
    },

    "demand_flair": {
        "patterns": [
            r"seeking advice",
            r"question",
            r"hiring",
            r"for hire",
            r"help",
            r"need",
            r"request",
        ],
        "boost": 0.05,
        "scope": "flair",
    },
}


# ============================================================================
# CO-OCCURRENCE GATES  (mirrors Craigslist matrix)
# ============================================================================

COOCCURRENCE_GATES = {
    "demand": [
        r"\b(need|needs|want|wants|looking for|seeking|searching|wish|require|requires)\b",
    ],
}

COOCCURRENCE_WINDOW = 60


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _check_cooccurrence(text: str, match_pos: int, gate_key: str) -> bool:
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

def score_reddit_post(
    text: str,
    subreddit: Optional[str] = None,
    upvotes: int = 0,
    num_comments: int = 0,
    flair: Optional[str] = None,
) -> dict:
    """
    Score a Reddit post against the OppGrid demand-signal keyword matrix.

    Args:
        text:         Post title + body concatenated (caller's responsibility)
        subreddit:    Subreddit slug without "r/" prefix (parsedCommunityName)
        upvotes:      upVotes field from Apify payload
        num_comments: numberOfComments field from Apify payload
        flair:        Post flair string (may be None)

    Returns:
        {
            "signal_score":        float [0.0, 1.0]
            "matched_patterns":    list of match dicts
            "business_categories": list of category keys
            "modifiers_applied":   list of modifier name strings
            "validation_level":    "goldmine" | "strong_signal" | "moderate" | "weak"
            "extracted_services":  list of strings (from generic "X needed")
            "subreddit_tier":      subreddit boost applied (0 if unknown sub)
        }
    """
    result: dict = {
        "signal_score": 0.0,
        "matched_patterns": [],
        "business_categories": set(),
        "modifiers_applied": [],
        "validation_level": None,
        "extracted_services": [],
        "subreddit_tier": 0.0,
    }

    if not text:
        result["validation_level"] = "weak"
        result["business_categories"] = []
        return result

    text_lower = text.lower()
    max_pattern_score = 0.0

    # --- 1. Match primary category patterns ---
    for category_key, category_data in REDDIT_CATEGORIES.items():
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
    _already_specific = {"tutor", "handyman", "caregiver", "ride", "developer", "designer"}
    for m in re.finditer(REDDIT_GENERIC_DEMAND["pattern"], text_lower):
        service_type = m.group(1).strip()
        if service_type in _already_specific:
            continue
        result["matched_patterns"].append({
            "category": "generic_demand",
            "pattern": f"{service_type} needed",
            "confidence": REDDIT_GENERIC_DEMAND["baseline_confidence"],
            "extracted_service": service_type,
        })
        result["extracted_services"].append(service_type)
        max_pattern_score = max(max_pattern_score, REDDIT_GENERIC_DEMAND["baseline_confidence"])

    score = max_pattern_score

    # --- 3. Subreddit tier boost ---
    sub = (subreddit or "").strip().lower().lstrip("r/")
    sub_info = SUBREDDIT_TIERS.get(sub) or SUBREDDIT_TIERS.get(subreddit or "")
    if sub_info:
        sub_boost = sub_info["boost"]
        score = min(1.0, score + sub_boost)
        result["subreddit_tier"] = sub_boost
        result["modifiers_applied"].append(f"subreddit:{sub}(+{sub_boost})")

    # --- 4. Urgency ---
    urgency = REDDIT_SIGNAL_MODIFIERS["urgency"]
    if any(re.search(p, text_lower) for p in urgency["patterns"]):
        score = min(1.0, score + urgency["boost"])
        result["modifiers_applied"].append("urgency")

    # --- 5. Inline willingness-to-pay ---
    wtp = REDDIT_SIGNAL_MODIFIERS["willingness_to_pay_inline"]
    if any(re.search(p, text_lower) for p in wtp["patterns"]):
        score = min(1.0, score + wtp["boost"])
        result["modifiers_applied"].append("willingness_to_pay")

    # --- 6. Upvote boost ---
    for threshold in REDDIT_SIGNAL_MODIFIERS["high_upvotes"]["thresholds"]:
        if upvotes >= threshold["min"]:
            score = min(1.0, score + threshold["boost"])
            result["modifiers_applied"].append(f"upvotes:{upvotes}(+{threshold['boost']})")
            break

    # --- 7. Comment volume boost ---
    for threshold in REDDIT_SIGNAL_MODIFIERS["high_comments"]["thresholds"]:
        if num_comments >= threshold["min"]:
            score = min(1.0, score + threshold["boost"])
            result["modifiers_applied"].append(f"comments:{num_comments}(+{threshold['boost']})")
            break

    # --- 8. Flair boost ---
    if flair:
        flair_lower = flair.lower()
        demand_flair = REDDIT_SIGNAL_MODIFIERS["demand_flair"]
        if any(re.search(p, flair_lower) for p in demand_flair["patterns"]):
            score = min(1.0, score + demand_flair["boost"])
            result["modifiers_applied"].append(f"flair:{flair}")

    result["signal_score"] = round(score, 3)

    # --- 9. Validation tier ---
    if score >= 0.90:
        result["validation_level"] = "goldmine"
    elif score >= 0.75:
        result["validation_level"] = "strong_signal"
    elif score >= 0.55:
        result["validation_level"] = "moderate"
    else:
        result["validation_level"] = "weak"

    result["business_categories"] = sorted(result["business_categories"])
    return result
