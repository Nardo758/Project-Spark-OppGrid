"""
OppGrid Keyword Matrix — Twitter/X
=====================================
Scores tweets for business-opportunity demand signals. Twitter is high-volume,
high-noise — the matrix applies a spam/promo filter FIRST, then engagement
credibility multipliers, before running pattern matching.

Geographic data is sparse: use geo.place_name when available (confidence 0.80),
otherwise fall back to hashtag inference (confidence 0.40).

Primary entry point: score_tweet()
"""

import re
from typing import Any, Dict, List, Optional


# ============================================================================
# SPAM / PROMO FILTER — drop tweets matching any of these conditions
# ============================================================================

TWITTER_SPAM_FILTERS = {
    "max_links_in_text": 1,
    "min_account_age_days": 30,
    "min_follower_count": 25,
    "promo_keyword_drop": [
        r"\b(?:DM me|link in bio|crypto|airdrop|NFT|OnlyFans)\b",
    ],
}


# ============================================================================
# ENGAGEMENT BOOSTS — credibility multipliers applied after spam filter
# ============================================================================

TWITTER_ENGAGEMENT_BOOST = {
    "verified_author":  0.10,
    "likes_gt_500":     0.10,
    "likes_gt_100":     0.05,
    "replies_gt_50":    0.08,
    "retweets_gt_100":  0.05,
}


# ============================================================================
# PATTERN CATEGORIES
# ============================================================================

TWITTER_CATEGORIES = {

    "explicit_demand": {
        "baseline_confidence": 0.90,
        "validation_level": "goldmine",
        "patterns": [
            {"pattern": r"(?:i'?d|would) pay (?:for|good money)",                         "confidence": 0.95},
            {"pattern": r"someone (?:please |needs to )?(?:build|make|create)",            "confidence": 0.88},
            {"pattern": r"why (?:isn'?t|aren'?t|is there no) (?:there )?(?:an? )?app for", "confidence": 0.92},
            {"pattern": r"take my money",                                                  "confidence": 0.85},
        ],
        "business_category_mapping": ["any"],
    },

    "service_failure_local": {
        "baseline_confidence": 0.75,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"can'?t find (?:anyone|anybody|a|any)\b.{0,30}(?:near|in|around)", "confidence": 0.85},
            {"pattern": r"nobody (?:in|near) (?:me|here|this) (?:that|who)",                "confidence": 0.82},
            {"pattern": r"(?:every|all the) (?:place|business|company) (?:in|around) [A-Z]", "confidence": 0.80},
            {"pattern": r"(?:closest|nearest) one is (?:\d+\s*(?:miles?|hours?))",           "confidence": 0.82},
        ],
        "business_category_mapping": ["any"],
    },

    "trend_signal": {
        "baseline_confidence": 0.68,
        "validation_level": "validated",
        "patterns": [
            {"pattern": r"(?:everyone|all my friends) is (?:doing|using|buying)", "confidence": 0.72},
            {"pattern": r"(?:why is|how is) [a-z\s]+ (?:so expensive|hard to find)", "confidence": 0.72},
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


def _is_spam(tweet: Dict[str, Any], author: Dict[str, Any]) -> Optional[str]:
    """
    Apply spam filter. Returns a reason string if the tweet should be dropped,
    or None if it passes.
    """
    text = tweet.get("text") or ""

    # Promo keyword check
    for pattern in TWITTER_SPAM_FILTERS["promo_keyword_drop"]:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return f"promo keyword: {pattern}"
        except re.error:
            continue

    # Link count check (URLs contain "://" or "t.co/")
    link_count = len(re.findall(r"https?://\S+", text))
    if link_count > TWITTER_SPAM_FILTERS["max_links_in_text"]:
        return f"too many links ({link_count})"

    # Follower count check
    try:
        followers = int(author.get("follower_count") or 0)
        if followers < TWITTER_SPAM_FILTERS["min_follower_count"]:
            return f"low followers ({followers})"
    except (TypeError, ValueError):
        pass

    return None


def _calculate_engagement_boost(tweet: Dict[str, Any], author: Dict[str, Any]) -> float:
    """Calculate engagement credibility boost."""
    boost = 0.0

    if author.get("verified"):
        boost += TWITTER_ENGAGEMENT_BOOST["verified_author"]

    try:
        likes = int(tweet.get("like_count") or 0)
        if likes > 500:
            boost += TWITTER_ENGAGEMENT_BOOST["likes_gt_500"]
        elif likes > 100:
            boost += TWITTER_ENGAGEMENT_BOOST["likes_gt_100"]
    except (TypeError, ValueError):
        pass

    try:
        replies = int(tweet.get("reply_count") or 0)
        if replies > 50:
            boost += TWITTER_ENGAGEMENT_BOOST["replies_gt_50"]
    except (TypeError, ValueError):
        pass

    try:
        retweets = int(tweet.get("retweet_count") or 0)
        if retweets > 100:
            boost += TWITTER_ENGAGEMENT_BOOST["retweets_gt_100"]
    except (TypeError, ValueError):
        pass

    return boost


def _extract_location(geo: Dict[str, Any], text: str) -> Optional[Dict[str, Any]]:
    """
    Extract location hint from geo data or hashtag inference.
    Confidence is 0.80 for geo-tagged tweets, 0.40 for hashtag inference.
    """
    if geo.get("place_name"):
        return {
            "city": geo.get("place_name"),
            "place_id": geo.get("place_id"),
            "coordinates": geo.get("coordinates"),
            "confidence": 0.80,
        }

    # Hashtag geo inference: look for #CityName or #CityNameUSA patterns
    hashtags = re.findall(r"#([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)*)", text)
    city_candidates = [h for h in hashtags if len(h) >= 4 and not h.isupper()]

    if len(city_candidates) >= 2:
        return {
            "city": city_candidates[0],
            "confidence": 0.40,
            "inferred_from": "hashtags",
        }

    return None


def score_tweet(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a single tweet payload.

    Applies spam filter FIRST. If the tweet passes, applies engagement
    credibility boosts then pattern matching.

    Args:
        payload: Dict matching the /v1/webhooks/twitter schema. Must contain:
                 tweet.{id, text, created_at, lang, retweet_count, like_count,
                        reply_count}
                 tweet.author.{username, follower_count, verified}
                 tweet.geo.{place_id, place_name, coordinates}  (optional)

    Returns:
        Standard signal output dict:
        {
            "signal_score": float,
            "validation_level": str,
            "matched_patterns": list[str],
            "category_hint": str,
            "location_hint": dict | None,
            "raw_excerpt": str,
            "source_specific": dict,
        }
    """
    tweet = payload.get("tweet", {})
    author = tweet.get("author", {})
    geo = tweet.get("geo", {})

    text = (tweet.get("text") or "").strip()

    if not text or len(text) < 10:
        return _noise_result("tweet text too short")

    # Only process English tweets (or untagged)
    lang = tweet.get("lang", "en")
    if lang and lang not in ("en", "und"):
        return _noise_result(f"non-English tweet (lang={lang})")

    # 1. Spam filter — must pass before any scoring
    spam_reason = _is_spam(tweet, author)
    if spam_reason:
        return _noise_result(f"spam_filter: {spam_reason}")

    # 2. Engagement credibility boost
    engagement_boost = _calculate_engagement_boost(tweet, author)

    # 3. Pattern matching
    best_score = 0.0
    matched: List[str] = []
    matched_pattern_for_excerpt: Optional[str] = None

    for cat_name, cat_cfg in TWITTER_CATEGORIES.items():
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

    # 4. Combine (cap at 1.0)
    final_score = min(1.0, best_score + engagement_boost)

    # 5. Location extraction
    location_hint = _extract_location(geo, text)

    return {
        "signal_score": round(final_score, 3),
        "validation_level": _classify_level(final_score),
        "matched_patterns": matched,
        "category_hint": "other",
        "location_hint": location_hint,
        "raw_excerpt": _extract_excerpt(text, matched_pattern_for_excerpt or ""),
        "source_specific": {
            "tweet_id": tweet.get("id"),
            "author_username": author.get("username"),
            "follower_count": author.get("follower_count"),
            "verified": author.get("verified", False),
            "like_count": tweet.get("like_count", 0),
            "retweet_count": tweet.get("retweet_count", 0),
        },
    }
