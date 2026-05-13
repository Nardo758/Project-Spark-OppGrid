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

    def test_goldmine_via_severe_score(self):
        anomaly = _make_anomaly("severe")
        self.scanner._compute_macro_signal_score(anomaly, 0)
        assert anomaly.conf_tier == "goldmine"
        assert anomaly.final_score == pytest.approx(SEVERITY_SCORES["severe"])

    def test_validated_tier(self):
        anomaly = _make_anomaly("moderate")
        self.scanner._compute_macro_signal_score(anomaly, 0)
        assert anomaly.conf_tier == "validated"

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
