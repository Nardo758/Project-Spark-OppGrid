"""
Integration tests for MacroSignalScanner.

Covers:
1. Dry-run mode — no DB rows written when MACRO_SCAN_DRY_RUN=true
2. scan_all returns a valid stats dict with expected keys
3. Corroboration scoring math — +0.02 per signal, cap at +0.15, goldmine at 6+
4. _classify_severity returns correct tiers
5. target_metros.json and target_zips.json load correctly and have ≥100 / ≥500 entries
6. _emit_signal skips write in dry-run, returns None

All DB tests require DATABASE_URL env var (skipped automatically if absent).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.macro_signal_scanner import (
    CORR_BOOST_CAP,
    CORR_BOOST_PER_SIGNAL,
    GOLDMINE_THRESHOLD,
    SEVERITY_SCORES,
    MacroAnomaly,
    MacroSignalScanner,
    _safe_float,
    run_macro_scan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_anomaly(severity: str = "mild", category: str = "labor_market", geo: str = None) -> MacroAnomaly:
    return MacroAnomaly(
        source="fred",
        rule_name="Test Rule",
        category=category,
        severity=severity,
        base_score=SEVERITY_SCORES[severity],
        geo=geo,
        delta=1.0,
        description="Test description",
    )


def _run(coro):
    """Run an async coroutine synchronously for non-async test cases."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Unit — no DB required
# ---------------------------------------------------------------------------

class TestSeverityClassification:
    scanner = MacroSignalScanner()

    rule = {
        "threshold":   1.0,
        "moderate_at": 2.0,
        "severe_at":   4.0,
    }

    def test_none_below_threshold(self):
        assert self.scanner._classify_severity(0.5, self.rule) is None

    def test_mild(self):
        assert self.scanner._classify_severity(1.5, self.rule) == "mild"

    def test_moderate(self):
        assert self.scanner._classify_severity(3.0, self.rule) == "moderate"

    def test_severe(self):
        assert self.scanner._classify_severity(5.0, self.rule) == "severe"

    def test_exact_boundary_mild(self):
        assert self.scanner._classify_severity(1.0, self.rule) == "mild"

    def test_exact_boundary_severe(self):
        assert self.scanner._classify_severity(4.0, self.rule) == "severe"


class TestCorroborationScoring:
    scanner = MacroSignalScanner()

    def test_zero_corr_preserves_base(self):
        anomaly = _make_anomaly("mild")
        self.scanner._compute_macro_signal_score(anomaly, 0)
        assert anomaly.final_score == pytest.approx(SEVERITY_SCORES["mild"])
        assert anomaly.conf_tier == "weak_signal"

    def test_boost_per_signal(self):
        anomaly = _make_anomaly("moderate")
        self.scanner._compute_macro_signal_score(anomaly, 3)
        expected = SEVERITY_SCORES["moderate"] + 3 * CORR_BOOST_PER_SIGNAL
        assert anomaly.final_score == pytest.approx(expected, abs=1e-6)

    def test_boost_cap(self):
        anomaly = _make_anomaly("mild")
        self.scanner._compute_macro_signal_score(anomaly, 100)
        assert anomaly.final_score == pytest.approx(SEVERITY_SCORES["mild"] + CORR_BOOST_CAP, abs=1e-6)

    def test_goldmine_at_threshold(self):
        anomaly = _make_anomaly("moderate")
        self.scanner._compute_macro_signal_score(anomaly, GOLDMINE_THRESHOLD)
        assert anomaly.conf_tier == "goldmine"

    def test_severe_lone_is_weak_signal(self):
        """Per spec: a lone macro anomaly (no corroboration) is always weak_signal."""
        anomaly = _make_anomaly("severe")
        self.scanner._compute_macro_signal_score(anomaly, 0)
        assert anomaly.conf_tier == "weak_signal"
        assert anomaly.final_score == pytest.approx(SEVERITY_SCORES["severe"])

    def test_validated_tier(self):
        """Moderate score + 2+ corroboration signals → validated."""
        anomaly = _make_anomaly("moderate")
        self.scanner._compute_macro_signal_score(anomaly, 2)
        assert anomaly.conf_tier == "validated"

    def test_moderate_lone_is_weak_signal(self):
        """Per spec: lone macro anomaly — even moderate — is weak_signal."""
        anomaly = _make_anomaly("moderate")
        self.scanner._compute_macro_signal_score(anomaly, 0)
        assert anomaly.conf_tier == "weak_signal"

    def test_weak_signal_tier(self):
        anomaly = _make_anomaly("mild")
        self.scanner._compute_macro_signal_score(anomaly, 0)
        assert anomaly.conf_tier == "weak_signal"

    def test_corr_count_stored(self):
        anomaly = _make_anomaly("mild")
        self.scanner._compute_macro_signal_score(anomaly, 4)
        assert anomaly.corr_count == 4


class TestSignalDict:
    def test_to_signal_dict_keys(self):
        anomaly = _make_anomaly("moderate")
        anomaly.final_score = 0.75
        anomaly.conf_tier = "validated"
        d = anomaly.to_signal_dict()
        assert "signal_score" in d
        assert "validation_level" in d
        assert "matched_patterns" in d
        assert "category_hint" in d
        assert d["signal_score"] == 0.75
        assert d["validation_level"] == "validated"


class TestSafeFloat:
    def test_valid_number(self):
        assert _safe_float("3.14") == pytest.approx(3.14)

    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_invalid_string_returns_none(self):
        assert _safe_float("N/A") is None

    def test_int(self):
        assert _safe_float(5) == pytest.approx(5.0)


class TestDataFiles:
    scanner = MacroSignalScanner()

    def test_metros_loads(self):
        metros = self.scanner._target_metros()
        assert len(metros) >= 100, f"Expected ≥100 metros, got {len(metros)}"

    def test_metros_have_required_keys(self):
        metros = self.scanner._target_metros()
        for m in metros:
            assert "cbsa_code" in m, f"Missing cbsa_code in {m}"
            assert "label" in m,     f"Missing label in {m}"

    def test_zips_loads(self):
        zips = self.scanner._target_zips()
        assert len(zips) >= 500, f"Expected ≥500 ZIPs, got {len(zips)}"

    def test_zips_have_required_keys(self):
        zips = self.scanner._target_zips()
        for z in zips:
            assert "zip"   in z, f"Missing zip in {z}"
            assert "state" in z, f"Missing state in {z}"


# ---------------------------------------------------------------------------
# Dry-run — no DB required
# ---------------------------------------------------------------------------

class TestDryRun:

    def _make_db_mock(self) -> MagicMock:
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 0
        return db

    def test_emit_returns_none_in_dry_run(self):
        scanner = MacroSignalScanner()
        anomaly = _make_anomaly("moderate")
        anomaly.final_score = 0.72
        anomaly.conf_tier = "validated"
        db = self._make_db_mock()

        with patch.dict(os.environ, {"MACRO_SCAN_DRY_RUN": "true"}):
            import importlib
            import app.services.macro_signal_scanner as mod
            original = mod.DRY_RUN
            mod.DRY_RUN = True
            try:
                result = scanner._emit_signal(db, anomaly)
                assert result is None
                db.add.assert_not_called()
                db.flush.assert_not_called()
            finally:
                mod.DRY_RUN = original

    def test_scan_all_dry_run_no_db_writes(self):
        """scan_all() in dry-run must not call db.add / db.flush / db.commit."""
        scanner = MacroSignalScanner()
        db = self._make_db_mock()

        # Mock all five individual scanners to return one anomaly each
        mild_anomaly = _make_anomaly("mild")

        async def _fake_scan(db_):
            return [mild_anomaly]

        import app.services.macro_signal_scanner as mod
        original_dry = mod.DRY_RUN
        mod.DRY_RUN = True
        try:
            with (
                patch.object(scanner, "_scan_fred",   side_effect=_fake_scan),
                patch.object(scanner, "_scan_bls",    side_effect=_fake_scan),
                patch.object(scanner, "_scan_census", side_effect=_fake_scan),
                patch.object(scanner, "_scan_sec",    side_effect=_fake_scan),
                patch.object(scanner, "_scan_trends", side_effect=_fake_scan),
                patch.object(scanner, "_find_corroborating_signals", return_value=0),
            ):
                stats = _run(scanner.scan_all(db))

            db.add.assert_not_called()
            db.flush.assert_not_called()
            db.commit.assert_not_called()

            # But stats should still record the anomalies as "emitted" (dry-run counts them)
            assert stats["dry_run"] is True
            assert stats["emitted"] == 5  # one per scanner
        finally:
            mod.DRY_RUN = original_dry


# ---------------------------------------------------------------------------
# stats dict shape
# ---------------------------------------------------------------------------

class TestScanAllStatsShape:

    def test_stats_has_all_expected_keys(self):
        scanner = MacroSignalScanner()
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 0

        async def _no_anomalies(db_):
            return []

        import app.services.macro_signal_scanner as mod
        original_dry = mod.DRY_RUN
        mod.DRY_RUN = True
        try:
            with (
                patch.object(scanner, "_scan_fred",   side_effect=_no_anomalies),
                patch.object(scanner, "_scan_bls",    side_effect=_no_anomalies),
                patch.object(scanner, "_scan_census", side_effect=_no_anomalies),
                patch.object(scanner, "_scan_sec",    side_effect=_no_anomalies),
                patch.object(scanner, "_scan_trends", side_effect=_no_anomalies),
            ):
                stats = _run(scanner.scan_all(db))
        finally:
            mod.DRY_RUN = original_dry

        required_keys = [
            "started_at", "finished_at", "dry_run",
            "anomalies", "emitted", "skipped",
            "by_source", "by_severity", "by_tier",
        ]
        for key in required_keys:
            assert key in stats, f"Missing key '{key}' in stats"

    def test_by_source_has_all_five_scanners(self):
        scanner = MacroSignalScanner()
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 0

        async def _no_anomalies(db_):
            return []

        import app.services.macro_signal_scanner as mod
        original_dry = mod.DRY_RUN
        mod.DRY_RUN = True
        try:
            with (
                patch.object(scanner, "_scan_fred",   side_effect=_no_anomalies),
                patch.object(scanner, "_scan_bls",    side_effect=_no_anomalies),
                patch.object(scanner, "_scan_census", side_effect=_no_anomalies),
                patch.object(scanner, "_scan_sec",    side_effect=_no_anomalies),
                patch.object(scanner, "_scan_trends", side_effect=_no_anomalies),
            ):
                stats = _run(scanner.scan_all(db))
        finally:
            mod.DRY_RUN = original_dry

        for source in ("fred", "bls", "census", "sec", "trends"):
            assert source in stats["by_source"], f"Missing source '{source}' in by_source"

    def test_severity_score_constants(self):
        assert SEVERITY_SCORES["mild"]     == pytest.approx(0.55)
        assert SEVERITY_SCORES["moderate"] == pytest.approx(0.72)
        assert SEVERITY_SCORES["severe"]   == pytest.approx(0.85)

    def test_corroboration_constants(self):
        assert CORR_BOOST_PER_SIGNAL == pytest.approx(0.02)
        assert CORR_BOOST_CAP        == pytest.approx(0.15)
        assert GOLDMINE_THRESHOLD    == 6


# ---------------------------------------------------------------------------
# external_id dedup key
# ---------------------------------------------------------------------------

class TestExternalId:

    def test_external_id_contains_source_and_rule(self):
        anomaly = _make_anomaly("mild", geo="Austin, TX")
        eid = anomaly.external_id()
        assert "fred" in eid
        assert "test_rule" in eid

    def test_external_id_contains_date(self):
        from datetime import datetime
        anomaly = _make_anomaly("mild")
        eid = anomaly.external_id()
        today = datetime.utcnow().strftime("%Y%m%d")
        assert today in eid

    def test_external_id_national_when_no_geo(self):
        anomaly = _make_anomaly("mild", geo=None)
        eid = anomaly.external_id()
        assert "national" in eid

    def test_external_id_stable_within_same_day(self):
        """Same anomaly called twice should produce the same external_id."""
        anomaly = _make_anomaly("moderate", geo="Houston")
        assert anomaly.external_id() == anomaly.external_id()


# ---------------------------------------------------------------------------
# _apply_census_rules helper
# ---------------------------------------------------------------------------

class TestApplyCensusRules:
    scanner = MacroSignalScanner()

    def test_high_unemployment_triggers_anomaly(self):
        anomalies: list = []
        data = {"unemployment_rate": 10.5, "poverty_rate": 5.0, "median_rent": 900.0}
        self.scanner._apply_census_rules(
            anomalies, data, geo="Detroit, MI", geo_meta={"zip": "48201"}
        )
        cats = [a.category for a in anomalies]
        assert "labor_market" in cats

    def test_high_rent_triggers_anomaly(self):
        anomalies: list = []
        data = {"unemployment_rate": 3.0, "poverty_rate": 5.0, "median_rent": 2500.0}
        self.scanner._apply_census_rules(
            anomalies, data, geo="San Francisco, CA", geo_meta={}
        )
        cats = [a.category for a in anomalies]
        assert "housing" in cats

    def test_below_threshold_no_anomaly(self):
        anomalies: list = []
        data = {"unemployment_rate": 2.0, "poverty_rate": 4.0, "median_rent": 800.0}
        self.scanner._apply_census_rules(anomalies, data, geo="Suburbia", geo_meta={})
        assert anomalies == []

    def test_geo_propagated_to_anomaly(self):
        anomalies: list = []
        data = {"unemployment_rate": 12.0}
        self.scanner._apply_census_rules(
            anomalies, data, geo="Memphis, TN", geo_meta={}
        )
        assert any(a.geo == "Memphis, TN" for a in anomalies)


# ---------------------------------------------------------------------------
# _sample_zips — spread sampling
# ---------------------------------------------------------------------------

class TestSampleZips:
    scanner = MacroSignalScanner()

    def test_sample_count_bounded(self):
        from app.services.macro_signal_scanner import _CENSUS_MAX_ZIPS
        sample = self.scanner._sample_zips()
        assert len(sample) <= _CENSUS_MAX_ZIPS

    def test_sample_is_non_empty(self):
        sample = self.scanner._sample_zips()
        assert len(sample) > 0

    def test_sample_zips_have_zip_key(self):
        for z in self.scanner._sample_zips():
            assert "zip" in z


# ---------------------------------------------------------------------------
# Idempotency — _already_emitted_today
# ---------------------------------------------------------------------------

class TestIdempotency:

    def test_already_emitted_returns_false_when_not_found(self):
        scanner = MacroSignalScanner()
        db = MagicMock()
        db.execute.return_value.scalar.return_value = None
        assert scanner._already_emitted_today(db, "macro_fred_test_national_20260513") is False

    def test_already_emitted_returns_true_when_found(self):
        scanner = MacroSignalScanner()
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 1
        assert scanner._already_emitted_today(db, "macro_fred_test_national_20260513") is True

    def test_already_emitted_returns_false_on_db_error(self):
        scanner = MacroSignalScanner()
        db = MagicMock()
        db.execute.side_effect = Exception("DB error")
        assert scanner._already_emitted_today(db, "any_ext_id") is False


# ---------------------------------------------------------------------------
# DB integration — skipped when DATABASE_URL absent
# ---------------------------------------------------------------------------

class TestDBIntegration:

    @pytest.fixture()
    def db(self):
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            pytest.skip("DATABASE_URL not configured")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            yield session
        finally:
            session.rollback()
            session.close()

    def test_corroboration_query_returns_int(self, db):
        scanner = MacroSignalScanner()
        count = scanner._find_corroborating_signals(db, geo="TX", category="childcare", days=60)
        assert isinstance(count, int)
        assert count >= 0

    def test_no_db_writes_dry_run_with_real_db(self, db):
        """With a real DB connection and dry-run enabled, no rows are inserted."""
        from sqlalchemy import text as sa_text

        scanner = MacroSignalScanner()
        anomaly = _make_anomaly("moderate")
        anomaly.final_score = 0.72
        anomaly.conf_tier = "validated"

        before = db.execute(
            sa_text("SELECT COUNT(*) FROM scraped_sources WHERE source_type='macro_anomaly'")
        ).scalar()

        import app.services.macro_signal_scanner as mod
        original_dry = mod.DRY_RUN
        mod.DRY_RUN = True
        try:
            result = scanner._emit_signal(db, anomaly)
        finally:
            mod.DRY_RUN = original_dry

        after = db.execute(
            sa_text("SELECT COUNT(*) FROM scraped_sources WHERE source_type='macro_anomaly'")
        ).scalar()

        assert result is None
        assert before == after, "Dry-run must not insert rows into scraped_sources"

    # ------------------------------------------------------------------
    # Corroboration query correctness against real-shaped micro-signal rows
    # ------------------------------------------------------------------

    @pytest.fixture()
    def seeded_micro_signals(self, db):
        """
        Seed representative scraped_sources rows that match the two storage
        layouts used by real micro-signal sources, then clean up after the test.
        """
        from sqlalchemy import text as sa_text
        import json

        # Layout 1 — simple/top-level: raw_data has category_hint at top level
        payload_top_level = json.dumps({
            "category_hint": "childcare",
            "location_hint": "TX",
            "text": "Looking for childcare in Austin TX",
        })

        # Layout 2 — webhook_gateway enriched: raw_data has _oppgrid_signal nested
        payload_nested = json.dumps({
            "text": "No childcare available near me Austin",
            "state": "TX",
            "_oppgrid_signal": {
                "signal_score": 0.80,
                "validation_level": "validated",
                "matched_patterns": ["childcare"],
                "category_hint": "childcare",
                "location_hint": "Austin, TX",
                "raw_excerpt": "No childcare available",
            },
        })

        # Layout 3 — unrelated (should NOT be counted for childcare+TX)
        payload_unrelated = json.dumps({
            "category_hint": "food_beverage",
            "location_hint": "CA",
            "_oppgrid_signal": {
                "category_hint": "food_beverage",
                "location_hint": "Los Angeles, CA",
            },
        })

        inserted_ids = []
        for payload, src_type in [
            (payload_top_level, "yelp"),
            (payload_nested,    "nextdoor"),
            (payload_unrelated, "yelp"),
        ]:
            row = db.execute(
                sa_text("""
                    INSERT INTO scraped_sources
                        (source_type, scrape_id, raw_data, processed, received_at)
                    VALUES
                        (:st, 'test_corr_seed', CAST(:rd AS jsonb), 0, NOW())
                    RETURNING id
                """),
                {"st": src_type, "rd": payload},
            ).scalar()
            inserted_ids.append(row)
        db.flush()

        yield inserted_ids

        # Cleanup — remove seeded rows so they don't affect other tests
        db.execute(
            sa_text("DELETE FROM scraped_sources WHERE id = ANY(:ids)"),
            {"ids": inserted_ids},
        )
        db.flush()

    def test_corroboration_finds_nested_oppgrid_signal(self, db, seeded_micro_signals):
        """
        Corroboration query must count micro-signals whose category/geo lives in
        the nested _oppgrid_signal dict (the primary webhook_gateway layout).
        """
        scanner = MacroSignalScanner()
        count = scanner._find_corroborating_signals(
            db, geo="TX", category="childcare", days=1
        )
        # We seeded 2 matching rows (top-level + nested) and 1 unrelated
        assert count >= 2, (
            f"Expected >= 2 corroborating signals for childcare+TX, got {count}. "
            "The query may not be checking raw_data->'_oppgrid_signal'->>'category_hint'."
        )

    def test_corroboration_excludes_unrelated_rows(self, db, seeded_micro_signals):
        """Corroboration count for food_beverage+TX should be 0 (unrelated row is CA)."""
        scanner = MacroSignalScanner()
        count = scanner._find_corroborating_signals(
            db, geo="TX", category="food_beverage", days=1
        )
        # The unrelated row is food_beverage but geo=CA, so TX search should not match it
        assert count == 0, (
            f"Expected 0 for food_beverage+TX, got {count}. "
            "Geo filter may be too broad."
        )

    def test_corroboration_triggers_goldmine_tier(self, db, seeded_micro_signals):
        """
        When corr_count >= GOLDMINE_THRESHOLD, tier must be 'goldmine'.
        Tested here with a mocked corroboration count against real tier logic.
        """
        scanner = MacroSignalScanner()
        anomaly = _make_anomaly("moderate")
        # Simulate 6+ matching micro-signals
        scanner._compute_macro_signal_score(anomaly, GOLDMINE_THRESHOLD)
        assert anomaly.conf_tier == "goldmine", (
            f"Expected goldmine with corr={GOLDMINE_THRESHOLD}, got {anomaly.conf_tier}"
        )
