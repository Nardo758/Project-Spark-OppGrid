"""
Unit tests for greatschools_keyword_matrix.py
Covers: score_greatschools_review() and score_greatschools_school_stats()
with 12+ fixtures spanning all pattern categories, rating tiers, and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from app.services.greatschools_keyword_matrix import (
    score_greatschools_review,
    score_greatschools_school_stats,
    GOLDMINE_THRESHOLD,
    VALIDATED_THRESHOLD,
    WEAK_THRESHOLD,
)


def _review_payload(text: str, school_rating: int = 5, enrollment: int = 400,
                    city: str = "Tampa", state: str = "FL", role: str = "parent"):
    return {
        "school": {
            "id": "gs-001",
            "name": "Lincoln Elementary",
            "rating": school_rating,
            "enrollment": enrollment,
            "location": {
                "city": city,
                "state": state,
                "zip": "33602",
                "lat": 27.94,
                "lng": -82.45,
                "district": "Hillsborough County",
            },
        },
        "review": {"rating": 2, "text": text, "role": role, "posted_at": "2025-01-01"},
    }


def _stats_payload(school_rating: int = 3, enrollment: int = 900,
                   zip_growth_pct: float = 0.08, city: str = "Tampa"):
    return {
        "school": {
            "id": "gs-002",
            "name": "Westside Middle School",
            "rating": school_rating,
            "enrollment": enrollment,
            "zip_growth_pct": zip_growth_pct,
            "location": {
                "city": city,
                "state": "FL",
                "zip": "33614",
                "lat": 27.99,
                "lng": -82.52,
                "district": "Hillsborough County",
            },
        },
    }


class TestTutoringDemand:
    def test_needs_tutor(self):
        result = score_greatschools_review(
            _review_payload("My son needs a tutor badly — the school provides no help.", school_rating=2)
        )
        assert result["signal_score"] >= GOLDMINE_THRESHOLD
        assert result["validation_level"] == "goldmine"
        assert any("tutoring_demand" in p for p in result["matched_patterns"])

    def test_falling_behind(self):
        result = score_greatschools_review(
            _review_payload("My daughter has been falling behind in reading and math.", school_rating=3)
        )
        assert result["signal_score"] >= VALIDATED_THRESHOLD

    def test_struggling_with_math(self):
        result = score_greatschools_review(
            _review_payload("Several kids in her class are struggling with math and science.", school_rating=2)
        )
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestSpecializedProgramGap:
    def test_no_gifted_program(self):
        result = score_greatschools_review(
            _review_payload("There is no gifted program and no GATE program here at all.", school_rating=5)
        )
        assert result["signal_score"] >= GOLDMINE_THRESHOLD
        assert any("specialized_program_gap" in p for p in result["matched_patterns"])

    def test_iep_support_missing(self):
        result = score_greatschools_review(
            _review_payload("They have no special needs or IEP support services in place.", school_rating=3)
        )
        assert result["signal_score"] >= GOLDMINE_THRESHOLD

    def test_no_stem(self):
        result = score_greatschools_review(
            _review_payload("There is no STEM program and no art or music whatsoever.", school_rating=4)
        )
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestSafetyEnvironmentGap:
    def test_bullying_issue(self):
        result = score_greatschools_review(
            _review_payload("Bullying is rampant and the school feels unsafe for my kids.", school_rating=2)
        )
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert any("safety_environment_gap" in p for p in result["matched_patterns"])

    def test_considering_homeschool(self):
        result = score_greatschools_review(
            _review_payload("We are considering homeschool after this year — it's that bad.", school_rating=2)
        )
        assert result["signal_score"] >= VALIDATED_THRESHOLD


class TestFacilitiesGap:
    def test_no_afterschool(self):
        result = score_greatschools_review(
            _review_payload("There is no after-school care or aftercare program available.", school_rating=4)
        )
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert any("facilities_gap" in p for p in result["matched_patterns"])


class TestSchoolStatMode:
    def test_low_rating_high_enrollment_growing_zip(self):
        result = score_greatschools_school_stats(_stats_payload(
            school_rating=2, enrollment=1000, zip_growth_pct=0.12
        ))
        assert result["signal_score"] >= VALIDATED_THRESHOLD
        assert result["category_hint"] == "education"
        assert result["validation_level"] in ("goldmine", "validated")

    def test_high_rating_low_enrollment_returns_noise_or_weak(self):
        result = score_greatschools_school_stats(_stats_payload(
            school_rating=9, enrollment=200, zip_growth_pct=0.0
        ))
        assert result["validation_level"] in ("noise", "weak_signal")
        assert result["signal_score"] <= VALIDATED_THRESHOLD

    def test_stats_mode_source_specific(self):
        result = score_greatschools_school_stats(_stats_payload(
            school_rating=3, enrollment=850, zip_growth_pct=0.06
        ))
        assert result["source_specific"]["signal_mode"] == "school_stats"
        assert result["source_specific"]["school_rating"] == 3


class TestRatingTierBoosts:
    def test_low_school_rating_amplifies_score(self):
        text = "My child needs a tutor for math and reading."
        r_low = score_greatschools_review(_review_payload(text, school_rating=2))
        r_high = score_greatschools_review(_review_payload(text, school_rating=9))
        assert r_low["signal_score"] > r_high["signal_score"]


class TestEdgeCases:
    def test_short_review_returns_noise(self):
        result = score_greatschools_review(_review_payload("Bad.", school_rating=1))
        assert result["validation_level"] == "noise"

    def test_no_city_in_stats_returns_noise(self):
        payload = {
            "school": {
                "id": "gs-noloc",
                "rating": 2,
                "enrollment": 900,
                "zip_growth_pct": 0.10,
                "location": {},
            }
        }
        result = score_greatschools_school_stats(payload)
        assert result["validation_level"] == "noise"
