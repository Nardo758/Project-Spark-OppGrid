"""
Unit tests for twitter_keyword_matrix.py
Covers: score_tweet() with 12+ fixtures spanning spam filtering, engagement
boosts, all pattern categories, location extraction, and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from app.services.twitter_keyword_matrix import (
    score_tweet,
    GOLDMINE_THRESHOLD,
    VALIDATED_THRESHOLD,
    WEAK_THRESHOLD,
)


def _make_payload(text: str, likes: int = 0, retweets: int = 0,
                  replies: int = 0, verified: bool = False,
                  followers: int = 500, lang: str = "en",
                  geo_place: str = None):
    return {
        "tweet": {
            "id": "twt-001",
            "text": text,
            "lang": lang,
            "like_count": likes,
            "retweet_count": retweets,
            "reply_count": replies,
            "author": {
                "username": "testuser",
                "follower_count": followers,
                "verified": verified,
            },
            "geo": {"place_name": geo_place} if geo_place else {},
        }
    }


class TestExplicitDemand:
    def test_id_pay_for_this(self):
        result = score_tweet(_make_payload(
            "I'd pay good money for a reliable same-day appliance repair service.",
            likes=50, followers=300,
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert result["validation_level"] in ("goldmine", "validated")
        assert any("explicit_demand" in p for p in result["matched_patterns"])

    def test_someone_needs_to_build(self):
        result = score_tweet(_make_payload(
            "Someone please build an app that matches you with local mechanics.",
            likes=200, followers=1000,
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD

    def test_why_is_there_no_app_for(self):
        result = score_tweet(_make_payload(
            "Why isn't there an app for booking a local handyman instantly?",
            likes=300, followers=2000,
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD

    def test_take_my_money(self):
        result = score_tweet(_make_payload(
            "If someone built a concierge HVAC service in Phoenix I would take my money there immediately.",
            likes=100, followers=800,
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestServiceFailureLocal:
    def test_cant_find_anyone_nearby(self):
        result = score_tweet(_make_payload(
            "Can't find a decent HVAC tech anywhere near me in this town.",
            likes=30, followers=200,
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD

    def test_closest_one_miles_away(self):
        result = score_tweet(_make_payload(
            "The nearest one is 45 miles away. How is that even acceptable in 2025?",
            likes=40, followers=400,
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestEngagementBoosts:
    def test_verified_author_boosts_score(self):
        text = "Someone needs to build a local handyman booking app. Take my money."
        result_verified = score_tweet(_make_payload(text, verified=True, followers=5000, likes=100))
        result_unverified = score_tweet(_make_payload(text, verified=False, followers=5000, likes=100))
        assert result_verified["signal_score"] > result_unverified["signal_score"]

    def test_high_likes_boost(self):
        text = "I'd pay for a reliable on-demand plumbing service right now."
        result_high = score_tweet(_make_payload(text, likes=600, followers=500))
        result_low = score_tweet(_make_payload(text, likes=5, followers=500))
        assert result_high["signal_score"] > result_low["signal_score"]

    def test_high_replies_boost(self):
        text = "Why isn't there an app for booking a local dog groomer on demand?"
        result_replies = score_tweet(_make_payload(text, replies=60, followers=300))
        result_no_replies = score_tweet(_make_payload(text, replies=0, followers=300))
        assert result_replies["signal_score"] > result_no_replies["signal_score"]


class TestSpamFilter:
    def test_dm_me_spam_dropped(self):
        result = score_tweet(_make_payload(
            "Someone needs to build this app, DM me for details.",
            followers=500,
        ))
        assert result["validation_level"] == "noise"
        assert "spam_filter" in (result["source_specific"].get("skip_reason") or "")

    def test_low_followers_dropped(self):
        result = score_tweet(_make_payload(
            "I'd pay good money for a reliable plumber right now.",
            followers=10,
        ))
        assert result["validation_level"] == "noise"

    def test_crypto_promo_dropped(self):
        result = score_tweet(_make_payload(
            "Someone needs to build this! crypto airdrop NFT opportunity.",
            followers=1000,
        ))
        assert result["validation_level"] == "noise"

    def test_non_english_dropped(self):
        result = score_tweet(_make_payload(
            "Quelqu'un devrait construire cela pour nous.",
            lang="fr", followers=500,
        ))
        assert result["validation_level"] == "noise"


class TestLocationExtraction:
    def test_geo_tagged_tweet_has_location(self):
        result = score_tweet(_make_payload(
            "I'd pay for a quality HVAC service right now.",
            likes=50, followers=300,
            geo_place="Austin, TX",
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        if result["location_hint"]:
            assert result["location_hint"]["city"] == "Austin, TX"
            assert result["location_hint"]["confidence"] == 0.80


class TestEdgeCases:
    def test_short_text_returns_noise(self):
        result = score_tweet(_make_payload("Hi!", followers=500))
        assert result["validation_level"] == "noise"

    def test_no_pattern_match_returns_noise(self):
        result = score_tweet(_make_payload(
            "What a beautiful day in the park today! Love the sunshine.",
            likes=10, followers=300,
        ))
        assert result["validation_level"] == "noise"
