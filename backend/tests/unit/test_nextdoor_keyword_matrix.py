"""
Unit tests for nextdoor_keyword_matrix.py
Covers: score_nextdoor_post() with 12 fixtures spanning all pattern categories,
category tiers, location hint (including polygon), and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from app.services.nextdoor_keyword_matrix import (
    score_nextdoor_post,
    GOLDMINE_THRESHOLD,
    VALIDATED_THRESHOLD,
    WEAK_THRESHOLD,
)


def _make_payload(title: str, body: str = "", category: str = "General",
                  neighborhood_name: str = "Westwood", city: str = "Denver",
                  state: str = "CO", polygon=None):
    return {
        "post": {
            "id": "nd-post-001",
            "title": title,
            "body": body,
            "category": category,
            "neighborhood": {
                "name": neighborhood_name,
                "city": city,
                "state": state,
                "zip": "80210",
                "centroid": {"lat": 39.72, "lng": -104.95},
                "polygon": polygon,
            },
        }
    }


class TestExplicitRecommendationRequest:
    def test_anyone_know_a_plumber(self):
        payload = _make_payload(
            "Anyone know a good plumber?",
            body="Need one urgently for a leak.",
            category="Recommendations",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD
        assert result["validation_level"] == "goldmine"
        assert any("explicit_recommendation_request" in p for p in result["matched_patterns"])

    def test_looking_for_recommendations(self):
        payload = _make_payload(
            "Looking for recommendations for a reliable electrician",
            category="Recommendations",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD

    def test_who_do_you_trust_for_childcare(self):
        payload = _make_payload(
            "Who do you trust for childcare in our area?",
            category="Recommendations",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD

    def test_need_reliable_contractor(self):
        payload = _make_payload(
            "I need a reliable contractor for my basement renovation.",
            body="Someone trustworthy please.",
            category="Recommendations",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD


class TestNeighborhoodGap:
    def test_why_isnt_there_a_coffee_shop(self):
        payload = _make_payload(
            "Why isn't there a good coffee shop in our neighborhood?",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= GOLDMINE_THRESHOLD
        assert any("neighborhood_gap" in p for p in result["matched_patterns"])

    def test_we_need_a_grocery_store(self):
        payload = _make_payload(
            "We need a grocery store in our area!",
            body="The closest one is in another town.",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD

    def test_have_to_drive_out(self):
        payload = _make_payload(
            "We have to drive out of this entire neighborhood to find a dentist.",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestServiceComplaint:
    def test_beware_of_contractor(self):
        payload = _make_payload(
            "Beware of this pest control company. Horrible experience.",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert any("service_complaint" in p for p in result["matched_patterns"])

    def test_would_never_recommend(self):
        payload = _make_payload(
            "I would never recommend this plumber to anyone.",
            body="They overcharged and scammed me.",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestCategoryTierBoosts:
    def test_recommendations_category_boost(self):
        text = "Anyone know a good vet nearby?"
        result_rec = score_nextdoor_post(_make_payload(text, category="Recommendations"))
        result_gen = score_nextdoor_post(_make_payload(text, category="General"))
        assert result_rec["signal_score"] > result_gen["signal_score"]

    def test_classifieds_category_boost(self):
        payload = _make_payload(
            "Anyone know a good cleaning service?",
            category="Classifieds",
        )
        result = score_nextdoor_post(payload)
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestLocationHint:
    def test_location_hint_with_neighborhood(self):
        payload = _make_payload(
            "Who do you trust for landscaping in our neighborhood?",
            category="Recommendations",
            neighborhood_name="Capitol Hill",
            city="Denver",
            state="CO",
        )
        result = score_nextdoor_post(payload)
        assert result["location_hint"] is not None
        assert result["location_hint"]["confidence"] == 1.0
        assert result["location_hint"]["neighborhood"] == "Capitol Hill"
        assert result["location_hint"]["city"] == "Denver"

    def test_polygon_preserved_in_location_hint(self):
        polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        payload = _make_payload(
            "Looking for a recommendation for an HVAC tech.",
            category="Recommendations",
            polygon=polygon,
        )
        result = score_nextdoor_post(payload)
        assert result["location_hint"]["polygon"] == polygon


class TestEdgeCases:
    def test_short_text_returns_noise(self):
        payload = _make_payload("Hi", body="", category="General")
        result = score_nextdoor_post(payload)
        assert result["validation_level"] == "noise"

    def test_no_match_returns_noise(self):
        payload = _make_payload(
            "The weather today is really beautiful outside.",
            body="I love this neighborhood.",
        )
        result = score_nextdoor_post(payload)
        assert result["validation_level"] == "noise"
