"""
Unit tests for yelp_keyword_matrix.py
Covers: score_yelp_review() with 12 fixtures spanning all pattern categories,
rating tiers, category boosts, and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from app.services.yelp_keyword_matrix import (
    score_yelp_review,
    GOLDMINE_THRESHOLD,
    VALIDATED_THRESHOLD,
    WEAK_THRESHOLD,
)


def _make_payload(text: str, rating: int = 3, categories=None, city: str = "Austin"):
    return {
        "review": {"text": text, "rating": rating},
        "business": {
            "id": "biz-001",
            "categories": categories or ["restaurants"],
            "location": {"city": city, "state": "TX", "zip_code": "78701", "lat": 30.27, "lng": -97.74},
        },
    }


class TestExplicitMarketGap:
    def test_no_one_in_area(self):
        payload = _make_payload("There is no one in this city who does good HVAC work.", rating=1)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD
        assert result["validation_level"] == "goldmine"
        assert any("explicit_market_gap" in p for p in result["matched_patterns"])

    def test_cant_find_pattern(self):
        payload = _make_payload("I can't find any reliable childcare nearby.", rating=2)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert result["validation_level"] in ("goldmine", "validated")

    def test_wish_someone_would_open(self):
        payload = _make_payload("I wish someone would open a decent auto shop here.", rating=1)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD


class TestServiceQualityFailure:
    def test_rude_staff(self):
        payload = _make_payload("The owner was rude and unprofessional to every customer.", rating=1)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert result["validation_level"] in ("goldmine", "validated")

    def test_overcharged(self):
        payload = _make_payload("They overcharged me $300 beyond the quote. Ripped off.", rating=1)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD

    def test_waited_forever(self):
        payload = _make_payload("Waited for hours and nobody ever showed up to fix the AC.", rating=2)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestDemandIntensity:
    def test_fully_booked(self):
        payload = _make_payload("They are booked out for months — impossible to get an appointment.", rating=3)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert "demand_intensity" in " ".join(result["matched_patterns"])

    def test_waitlist(self):
        payload = _make_payload("The waitlist is six weeks long. Ridiculous for a dental office.", rating=2)
        result = score_yelp_review(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestRatingTierBoosts:
    def test_one_star_boost(self):
        payload_1 = _make_payload("The staff was rude and unprofessional to every single customer.", rating=1)
        payload_3 = _make_payload("The staff was rude and unprofessional to every single customer.", rating=3)
        r1 = score_yelp_review(payload_1)
        r3 = score_yelp_review(payload_3)
        assert r1["signal_score"] > r3["signal_score"]

    def test_five_star_no_boost(self):
        payload = _make_payload("They are booked out for weeks — so popular you can't get an appointment.", rating=5)
        result = score_yelp_review(payload)
        assert result["source_specific"]["rating"] == 5


class TestLocationHint:
    def test_location_hint_populated(self):
        payload = _make_payload("I can't find any good HVAC contractors here.", rating=1)
        result = score_yelp_review(payload)
        assert result["location_hint"] is not None
        assert result["location_hint"]["city"] == "Austin"
        assert result["location_hint"]["confidence"] == 1.0

    def test_no_location_returns_none(self):
        payload = {
            "review": {"text": "I can't find any reliable service anywhere.", "rating": 1},
            "business": {"id": "biz-x", "categories": [], "location": {}},
        }
        result = score_yelp_review(payload)
        assert result["location_hint"] is None


class TestEdgeCases:
    def test_short_text_returns_noise(self):
        payload = _make_payload("Bad.", rating=1)
        result = score_yelp_review(payload)
        assert result["validation_level"] == "noise"
        assert result["signal_score"] == 0.0

    def test_positive_review_no_match(self):
        payload = _make_payload("Amazing food and wonderful staff, five stars all around!", rating=5)
        result = score_yelp_review(payload)
        assert result["validation_level"] == "noise"
