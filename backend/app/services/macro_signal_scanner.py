"""
MacroSignalScanner — promotes FRED, BLS, SEC-API, Census, and Google Trends
from enrichment-only services to active discovery sources.

Each scan method detects anomalies in macro data and emits ScrapedSource rows
with source_platform='macro_anomaly' so SignalToOpportunityProcessor can cluster
them with micro-signals and generate opportunities.

Severity scoring
----------------
  mild     → base score 0.55
  moderate → base score 0.72
  severe   → base score 0.85

Corroboration boost: +0.02 per matching micro-signal in scraped_sources (same
geo + category, last 60 days), capped at +0.15.  6+ micro-signals elevates the
confidence_tier to 'goldmine'.

Dry-run mode
------------
Set MACRO_SCAN_DRY_RUN=true to log anomalies without writing to the database.

Entry point
-----------
  await run_macro_scan(db)   ← called by job_runner every 6 hours
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DRY_RUN: bool = os.getenv("MACRO_SCAN_DRY_RUN", "").lower() in ("true", "1", "yes")

_DATA_DIR = Path(__file__).parent.parent / "data"

SEVERITY_SCORES: Dict[str, float] = {
    "mild":     0.55,
    "moderate": 0.72,
    "severe":   0.85,
}

CORR_BOOST_PER_SIGNAL: float = 0.02
CORR_BOOST_CAP:        float = 0.15
GOLDMINE_THRESHOLD:    int   = 6


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

FRED_RULES: List[Dict[str, Any]] = [
    {
        "series_id":   "UNRATE",
        "name":        "Unemployment Rate Spike",
        "category":    "labor_market",
        "threshold":   0.5,   # percentage-point delta triggers mild
        "moderate_at": 1.0,
        "severe_at":   2.0,
        "direction":   "up",
        "description": "UNRATE rose {delta:.2f} pp — labour market softening may signal unmet service demand",
    },
    {
        "series_id":   "CPIAUCSL",
        "name":        "CPI Inflation Spike",
        "category":    "inflation",
        "threshold":   0.3,
        "moderate_at": 0.7,
        "severe_at":   1.5,
        "direction":   "up",
        "description": "CPI index rose {delta:.2f} pts — inflationary pressure may expand affordable-alternative demand",
    },
    {
        "series_id":   "MORTGAGE30US",
        "name":        "Mortgage Rate Surge",
        "category":    "housing",
        "threshold":   0.25,
        "moderate_at": 0.5,
        "severe_at":   1.0,
        "direction":   "up",
        "description": "30-yr mortgage rate up {delta:.2f} pp — housing affordability crunch driving rental-service demand",
    },
    {
        "series_id":   "UMCSENT",
        "name":        "Consumer Sentiment Drop",
        "category":    "consumer_confidence",
        "threshold":   3.0,
        "moderate_at": 7.0,
        "severe_at":   12.0,
        "direction":   "down",
        "description": "Consumer sentiment fell {delta:.2f} pts — recession-resilient & value service categories may surge",
    },
]

BLS_RULES: List[Dict[str, Any]] = [
    {
        "naics":       "722511",
        "name":        "Restaurant Employment Surge",
        "category":    "food_beverage",
        "threshold":   0.03,
        "moderate_at": 0.06,
        "severe_at":   0.10,
        "direction":   "up",
        "description": "Restaurant employment grew {delta:.1%} — market-entry demand rising",
    },
    {
        "naics":       "713940",
        "name":        "Fitness Employment Contraction",
        "category":    "fitness",
        "threshold":   0.03,
        "moderate_at": 0.06,
        "severe_at":   0.10,
        "direction":   "down",
        "description": "Fitness sector employment fell {delta:.1%} — facility closures creating supply gap",
    },
    {
        "naics":       "624410",
        "name":        "Childcare Employment Drop",
        "category":    "childcare",
        "threshold":   0.02,
        "moderate_at": 0.05,
        "severe_at":   0.08,
        "direction":   "down",
        "description": "Childcare employment contracted {delta:.1%} — childcare supply crunch opportunity",
    },
    {
        "naics":       "531130",
        "name":        "Self-Storage Employment Growth",
        "category":    "self_storage",
        "threshold":   0.04,
        "moderate_at": 0.08,
        "severe_at":   0.12,
        "direction":   "up",
        "description": "Self-storage employment grew {delta:.1%} — migration-driven storage demand",
    },
]

CENSUS_RULES: List[Dict[str, Any]] = [
    {
        "metric":      "population_growth_rate",
        "name":        "Population Surge",
        "category":    "demographics",
        "threshold":   0.015,
        "moderate_at": 0.03,
        "severe_at":   0.05,
        "direction":   "up",
        "description": "Population grew {delta:.1%} — underserved service capacity likely",
    },
    {
        "metric":      "migration_net",
        "name":        "Domestic In-Migration Wave",
        "category":    "demographics",
        "threshold":   2000,
        "moderate_at": 5000,
        "severe_at":   10000,
        "direction":   "up",
        "description": "Net domestic in-migration of {delta:,.0f} — new-resident service gaps forming",
    },
    {
        "metric":      "median_income_drop",
        "name":        "Median Income Decline",
        "category":    "affordability",
        "threshold":   0.02,
        "moderate_at": 0.04,
        "severe_at":   0.07,
        "direction":   "up",
        "description": "Median income fell {delta:.1%} — affordable-alternative business demand rising",
    },
]

SEC_SUPPLY_KEYWORDS: List[str] = [
    "supply shortage", "supply constraint", "supply chain disruption",
    "capacity constraints", "unmet demand", "supply deficit",
    "limited supply", "insufficient capacity", "supply gap",
    "product shortage", "shortage of", "unable to meet demand",
]

SEC_EXIT_KEYWORDS: List[str] = [
    "market exit", "exiting the market", "store closures", "closure of",
    "divesting", "discontinuing operations", "wind down", "ceased operations",
    "reduced footprint", "geographic exit", "pulling out", "strategic exit",
    "closing locations", "business closure",
]

SEC_RULES: List[Dict[str, Any]] = [
    {
        "name":        "Supply Shortage Signal",
        "category":    "supply_shortage",
        "keywords":    SEC_SUPPLY_KEYWORDS,
        "threshold":   2,
        "moderate_at": 5,
        "severe_at":   10,
        "description": "SEC filings mention supply constraints {delta} times — product/service scarcity opportunity",
    },
    {
        "name":        "Competitive Exit Signal",
        "category":    "competitive_exit",
        "keywords":    SEC_EXIT_KEYWORDS,
        "threshold":   1,
        "moderate_at": 3,
        "severe_at":   7,
        "description": "SEC filings signal competitor exit ({delta} mentions) — market-share capture opportunity",
    },
]

TRENDS_RULES: List[Dict[str, Any]] = [
    {
        "keyword":     "home daycare near me",
        "category":    "childcare",
        "threshold":   20,
        "moderate_at": 40,
        "severe_at":   65,
        "name":        "Childcare Search Surge",
        "description": "Google Trends interest for '{keyword}' at {delta} — latent demand spike",
    },
    {
        "keyword":     "affordable gym membership",
        "category":    "fitness",
        "threshold":   20,
        "moderate_at": 45,
        "severe_at":   70,
        "name":        "Budget Fitness Search Surge",
        "description": "Google Trends interest for '{keyword}' at {delta} — value-fitness demand spike",
    },
    {
        "keyword":     "food delivery alternatives",
        "category":    "food_beverage",
        "threshold":   25,
        "moderate_at": 50,
        "severe_at":   75,
        "name":        "Food Delivery Alt Search Surge",
        "description": "Google Trends interest for '{keyword}' at {delta} — delivery-cost backlash",
    },
    {
        "keyword":     "small business for sale",
        "category":    "acquisition",
        "threshold":   30,
        "moderate_at": 55,
        "severe_at":   80,
        "name":        "Business Acquisition Search Surge",
        "description": "Google Trends interest for '{keyword}' at {delta} — distressed acquisition demand",
    },
    {
        "keyword":     "storage unit prices",
        "category":    "self_storage",
        "threshold":   20,
        "moderate_at": 40,
        "severe_at":   60,
        "name":        "Self-Storage Demand Search Surge",
        "description": "Google Trends interest for '{keyword}' at {delta} — migration-driven storage demand",
    },
]


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class MacroAnomaly:
    source:      str              # fred | bls | census | sec | trends
    rule_name:   str
    category:    str
    severity:    str              # mild | moderate | severe
    base_score:  float
    geo:         Optional[str]    # state abbr, CBSA code, or None for national
    delta:       float
    description: str
    metadata:    Dict[str, Any] = field(default_factory=dict)

    # Populated by corroboration step
    corr_count:  int   = 0
    final_score: float = 0.0
    conf_tier:   str   = "weak_signal"

    def to_signal_dict(self) -> Dict[str, Any]:
        return {
            "signal_score":      self.final_score,
            "validation_level":  self.conf_tier,
            "matched_patterns":  [self.rule_name],
            "category_hint":     self.category,
            "location_hint":     self.geo,
            "raw_excerpt":       self.description,
        }


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class MacroSignalScanner:

    def __init__(self) -> None:
        self._metros: Optional[List[Dict]] = None
        self._zips:   Optional[List[Dict]] = None

    # ------------------------------------------------------------------
    # Target data loaders
    # ------------------------------------------------------------------

    def _target_metros(self) -> List[Dict]:
        if self._metros is None:
            path = _DATA_DIR / "target_metros.json"
            try:
                self._metros = json.loads(path.read_text())
            except Exception as exc:
                logger.warning("[MacroScan] Could not load target_metros.json: %s", exc)
                self._metros = []
        return self._metros

    def _target_zips(self) -> List[Dict]:
        if self._zips is None:
            path = _DATA_DIR / "target_zips.json"
            try:
                self._zips = json.loads(path.read_text())
            except Exception as exc:
                logger.warning("[MacroScan] Could not load target_zips.json: %s", exc)
                self._zips = []
        return self._zips

    # ------------------------------------------------------------------
    # Severity + score helpers
    # ------------------------------------------------------------------

    def _classify_severity(self, value: float, rule: Dict) -> Optional[str]:
        """Return severity tier if value clears the base threshold, else None."""
        if abs(value) >= rule["severe_at"]:
            return "severe"
        if abs(value) >= rule["moderate_at"]:
            return "moderate"
        if abs(value) >= rule["threshold"]:
            return "mild"
        return None

    def _compute_macro_signal_score(self, anomaly: MacroAnomaly, corr_count: int) -> None:
        """Mutate anomaly with final_score and conf_tier after corroboration lookup."""
        boost = min(corr_count * CORR_BOOST_PER_SIGNAL, CORR_BOOST_CAP)
        anomaly.corr_count  = corr_count
        anomaly.final_score = min(anomaly.base_score + boost, 1.0)

        if corr_count >= GOLDMINE_THRESHOLD or anomaly.final_score >= 0.85:
            anomaly.conf_tier = "goldmine"
        elif anomaly.final_score >= 0.70:
            anomaly.conf_tier = "validated"
        elif anomaly.final_score >= 0.50:
            anomaly.conf_tier = "weak_signal"
        else:
            anomaly.conf_tier = "noise"

    # ------------------------------------------------------------------
    # Corroboration query
    # ------------------------------------------------------------------

    def _find_corroborating_signals(
        self,
        db: Session,
        geo: Optional[str],
        category: str,
        days: int = 60,
    ) -> int:
        """
        Count matching micro-signals in scraped_sources for the same geo+category
        within the last `days` days.  Returns an int count.
        """
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            q = text("""
                SELECT COUNT(*) FROM scraped_sources
                WHERE received_at >= :since
                  AND source_type != 'macro_anomaly'
                  AND (
                    raw_data->>'category_hint' ILIKE :category
                    OR raw_data->>'category' ILIKE :category
                  )
                  AND (
                    :geo IS NULL
                    OR raw_data->>'geo' ILIKE :geo_like
                    OR raw_data->>'state' ILIKE :geo_like
                    OR raw_data->>'location_hint' ILIKE :geo_like
                  )
            """)
            params = {
                "since":    since,
                "category": f"%{category}%",
                "geo":      geo,
                "geo_like": f"%{geo}%" if geo else "%",
            }
            result = db.execute(q, params).scalar()
            return int(result or 0)
        except Exception as exc:
            logger.warning("[MacroScan] Corroboration query failed: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # DB emit
    # ------------------------------------------------------------------

    def _emit_signal(self, db: Session, anomaly: MacroAnomaly) -> Optional[Any]:
        """Write one ScrapedSource row. Skipped (logged only) in dry-run mode."""
        from app.models.scraped_source import ScrapedSource

        external_id = (
            f"macro_{anomaly.source}_{anomaly.rule_name.lower().replace(' ', '_')}"
            f"_{anomaly.geo or 'national'}_{datetime.utcnow().strftime('%Y%m%d')}"
        )

        payload: Dict[str, Any] = {
            "source":        anomaly.source,
            "rule_name":     anomaly.rule_name,
            "category":      anomaly.category,
            "category_hint": anomaly.category,
            "severity":      anomaly.severity,
            "geo":           anomaly.geo,
            "delta":         anomaly.delta,
            "description":   anomaly.description,
            "corr_count":    anomaly.corr_count,
            "conf_tier":     anomaly.conf_tier,
            "_oppgrid_signal": anomaly.to_signal_dict(),
            **anomaly.metadata,
        }

        if DRY_RUN:
            logger.info(
                "[MacroScan DRY-RUN] Would emit: %s | score=%.2f tier=%s geo=%s",
                anomaly.rule_name, anomaly.final_score, anomaly.conf_tier, anomaly.geo,
            )
            return None

        try:
            row = ScrapedSource(
                external_id=external_id,
                source_type="macro_anomaly",
                scrape_id=f"macro_scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                raw_data=payload,
                processed=0,
            )
            db.add(row)
            db.flush()
            logger.info(
                "[MacroScan] Emitted id=%s rule=%s score=%.2f tier=%s geo=%s",
                row.id, anomaly.rule_name, anomaly.final_score, anomaly.conf_tier, anomaly.geo,
            )
            return row
        except Exception as exc:
            logger.error("[MacroScan] Failed to emit signal %s: %s", anomaly.rule_name, exc)
            db.rollback()
            return None

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    async def scan_all(self, db: Session) -> Dict[str, Any]:
        """Run all five scanners. Returns stats dict."""
        stats: Dict[str, Any] = {
            "started_at":    datetime.utcnow().isoformat(),
            "dry_run":       DRY_RUN,
            "anomalies":     [],
            "emitted":       0,
            "skipped":       0,
            "by_source":     {},
            "by_severity":   {"mild": 0, "moderate": 0, "severe": 0},
            "by_tier":       {"goldmine": 0, "validated": 0, "weak_signal": 0, "noise": 0},
        }

        scanners = [
            ("fred",   self._scan_fred),
            ("bls",    self._scan_bls),
            ("census", self._scan_census),
            ("sec",    self._scan_sec),
            ("trends", self._scan_trends),
        ]

        for source_name, scanner_fn in scanners:
            try:
                anomalies: List[MacroAnomaly] = await scanner_fn(db)
            except Exception as exc:
                logger.error("[MacroScan] Scanner %s failed: %s", source_name, exc)
                anomalies = []

            emitted_count = 0
            for anomaly in anomalies:
                corr = self._find_corroborating_signals(db, anomaly.geo, anomaly.category)
                self._compute_macro_signal_score(anomaly, corr)

                row = self._emit_signal(db, anomaly)
                if row is not None or DRY_RUN:
                    emitted_count += 1
                    stats["emitted"] += 1
                    stats["by_severity"][anomaly.severity] = stats["by_severity"].get(anomaly.severity, 0) + 1
                    stats["by_tier"][anomaly.conf_tier]    = stats["by_tier"].get(anomaly.conf_tier, 0) + 1
                    stats["anomalies"].append({
                        "rule":     anomaly.rule_name,
                        "source":   anomaly.source,
                        "geo":      anomaly.geo,
                        "severity": anomaly.severity,
                        "score":    anomaly.final_score,
                        "tier":     anomaly.conf_tier,
                    })
                else:
                    stats["skipped"] += 1

            stats["by_source"][source_name] = emitted_count

        if not DRY_RUN:
            try:
                db.commit()
            except Exception as exc:
                logger.error("[MacroScan] Final commit failed: %s", exc)
                db.rollback()

        stats["finished_at"] = datetime.utcnow().isoformat()
        logger.info(
            "[MacroScan] Complete — emitted=%d skipped=%d dry_run=%s",
            stats["emitted"], stats["skipped"], DRY_RUN,
        )
        return stats

    # ------------------------------------------------------------------
    # FRED scanner
    # ------------------------------------------------------------------

    async def _scan_fred(self, db: Session) -> List[MacroAnomaly]:
        from app.services.fred_service import FREDService
        service = FREDService()
        if not service.is_configured:
            logger.debug("[MacroScan/FRED] Not configured — skipping")
            return []

        anomalies: List[MacroAnomaly] = []

        for rule in FRED_RULES:
            try:
                data = await service.get_series(rule["series_id"])
                if not data:
                    continue
                observations = data.get("observations", [])
                if len(observations) < 2:
                    continue

                latest_val = _safe_float(observations[0].get("value"))
                prior_val  = _safe_float(observations[1].get("value"))
                if latest_val is None or prior_val is None:
                    continue

                delta = latest_val - prior_val
                if rule["direction"] == "down":
                    delta = -delta  # we test magnitude of drop

                severity = self._classify_severity(delta, rule)
                if severity is None:
                    continue

                description = rule["description"].format(delta=abs(delta))
                anomalies.append(MacroAnomaly(
                    source=     "fred",
                    rule_name=  rule["name"],
                    category=   rule["category"],
                    severity=   severity,
                    base_score= SEVERITY_SCORES[severity],
                    geo=        None,  # FRED series are national
                    delta=      abs(delta),
                    description=description,
                    metadata={
                        "series_id":     rule["series_id"],
                        "latest_value":  latest_val,
                        "prior_value":   prior_val,
                        "latest_date":   observations[0].get("date"),
                        "prior_date":    observations[1].get("date"),
                    },
                ))
            except Exception as exc:
                logger.warning("[MacroScan/FRED] Rule %s failed: %s", rule["name"], exc)

        return anomalies

    # ------------------------------------------------------------------
    # BLS scanner
    # ------------------------------------------------------------------

    async def _scan_bls(self, db: Session) -> List[MacroAnomaly]:
        from app.services.bls_service import BLSService
        service = BLSService()

        anomalies: List[MacroAnomaly] = []

        for rule in BLS_RULES:
            try:
                # BLS service get_industry_data is synchronous; wrap inline
                data = await _run_sync(service.get_industry_data, rule["naics"])
                if not data:
                    continue

                # get_industry_data returns IndustryLaborData; grab employment
                emp = getattr(data, "total_employment", None)
                emp_growth = getattr(data, "employment_growth_rate", None)
                if emp_growth is None:
                    continue

                # Convert from the "3.5 %" style string if needed
                if isinstance(emp_growth, str):
                    emp_growth = _safe_float(emp_growth.replace("%", "").strip())
                if emp_growth is None:
                    continue

                # Normalise to fraction
                if abs(emp_growth) > 1.0:
                    emp_growth = emp_growth / 100.0

                delta = emp_growth
                if rule["direction"] == "down":
                    delta = -emp_growth

                severity = self._classify_severity(delta, rule)
                if severity is None:
                    continue

                description = rule["description"].format(delta=abs(emp_growth))
                anomalies.append(MacroAnomaly(
                    source=     "bls",
                    rule_name=  rule["name"],
                    category=   rule["category"],
                    severity=   severity,
                    base_score= SEVERITY_SCORES[severity],
                    geo=        None,
                    delta=      abs(emp_growth),
                    description=description,
                    metadata={
                        "naics":            rule["naics"],
                        "total_employment": emp,
                        "growth_rate":      emp_growth,
                    },
                ))
            except Exception as exc:
                logger.warning("[MacroScan/BLS] Rule %s failed: %s", rule["name"], exc)

        return anomalies

    # ------------------------------------------------------------------
    # Census scanner
    # ------------------------------------------------------------------

    async def _scan_census(self, db: Session) -> List[MacroAnomaly]:
        from app.services.census_service import CensusDataService
        service = CensusDataService()
        if not service.is_configured:
            logger.debug("[MacroScan/Census] Not configured — skipping")
            return []

        anomalies: List[MacroAnomaly] = []
        metros = self._target_metros()

        # Sample first 10 metros to avoid hammering the API in a single run
        for metro in metros[:10]:
            state_fips  = metro.get("state_fips", "")
            county_fips = metro.get("county_fips", "")
            label       = metro.get("label", metro.get("cbsa_code", "unknown"))

            if not state_fips or not county_fips:
                continue

            try:
                data = await service.fetch_by_county(state_fips, county_fips)
                if not data:
                    continue

                for rule in CENSUS_RULES:
                    metric = rule["metric"]
                    value  = data.get(metric)
                    if value is None:
                        continue

                    severity = self._classify_severity(abs(value), rule)
                    if severity is None:
                        continue

                    description = rule["description"].format(delta=abs(value))
                    anomalies.append(MacroAnomaly(
                        source=     "census",
                        rule_name=  rule["name"],
                        category=   rule["category"],
                        severity=   severity,
                        base_score= SEVERITY_SCORES[severity],
                        geo=        label,
                        delta=      abs(value),
                        description=description,
                        metadata={
                            "cbsa_label":   label,
                            "state_fips":   state_fips,
                            "county_fips":  county_fips,
                            "metric":       metric,
                            "metric_value": value,
                        },
                    ))
            except Exception as exc:
                logger.warning("[MacroScan/Census] Metro %s failed: %s", label, exc)

        return anomalies

    # ------------------------------------------------------------------
    # SEC scanner
    # ------------------------------------------------------------------

    async def _scan_sec(self, db: Session) -> List[MacroAnomaly]:
        from app.services.sec_api_service import SECAPIService
        service = SECAPIService()
        if not getattr(service, "is_configured", False):
            logger.debug("[MacroScan/SEC] Not configured — skipping")
            return []

        anomalies: List[MacroAnomaly] = []

        # Fetch recent filings (10-K / 10-Q / 8-K) and keyword-scan their text
        filing_types = ["10-K", "10-Q", "8-K"]

        for rule in SEC_RULES:
            total_hits = 0
            filing_matches: List[Dict] = []

            try:
                for filing_type in filing_types:
                    filings = await _run_sync(
                        service.search_filings,
                        form_type=filing_type,
                        limit=20,
                    )
                    if not filings:
                        continue
                    if isinstance(filings, dict):
                        filings = filings.get("filings", []) or filings.get("hits", []) or []

                    for filing in filings:
                        text_body = _extract_filing_text(filing)
                        if not text_body:
                            continue
                        hit_count = sum(
                            1 for kw in rule["keywords"]
                            if re.search(re.escape(kw), text_body, re.IGNORECASE)
                        )
                        if hit_count:
                            total_hits += hit_count
                            filing_matches.append({
                                "form":     filing_type,
                                "hits":     hit_count,
                                "company":  _extract_company(filing),
                            })

                if total_hits == 0:
                    continue

                severity = self._classify_severity(total_hits, rule)
                if severity is None:
                    continue

                description = rule["description"].format(delta=total_hits)
                anomalies.append(MacroAnomaly(
                    source=     "sec",
                    rule_name=  rule["name"],
                    category=   rule["category"],
                    severity=   severity,
                    base_score= SEVERITY_SCORES[severity],
                    geo=        None,
                    delta=      float(total_hits),
                    description=description,
                    metadata={
                        "total_keyword_hits": total_hits,
                        "filing_matches":     filing_matches[:10],
                        "filing_types_scanned": filing_types,
                    },
                ))
            except Exception as exc:
                logger.warning("[MacroScan/SEC] Rule %s failed: %s", rule["name"], exc)

        return anomalies

    # ------------------------------------------------------------------
    # Google Trends scanner
    # ------------------------------------------------------------------

    async def _scan_trends(self, db: Session) -> List[MacroAnomaly]:
        from app.services.google_trends_service import GoogleTrendsService
        service = GoogleTrendsService()
        if not service.is_configured:
            logger.debug("[MacroScan/Trends] Not configured — skipping")
            return []

        anomalies: List[MacroAnomaly] = []

        for rule in TRENDS_RULES:
            try:
                trend = await _run_sync(
                    service.fetch_interest_over_time,
                    rule["keyword"],
                    "US",
                    "today 3-m",
                )
                if not trend:
                    continue

                interest = trend.get("current_interest") or trend.get("average_interest") or 0
                if not interest:
                    continue

                severity = self._classify_severity(interest, rule)
                if severity is None:
                    continue

                description = rule["description"].format(
                    keyword=rule["keyword"],
                    delta=interest,
                )
                anomalies.append(MacroAnomaly(
                    source=     "trends",
                    rule_name=  rule["name"],
                    category=   rule["category"],
                    severity=   severity,
                    base_score= SEVERITY_SCORES[severity],
                    geo=        None,
                    delta=      float(interest),
                    description=description,
                    metadata={
                        "keyword":          rule["keyword"],
                        "current_interest": interest,
                        "average_interest": trend.get("average_interest"),
                        "peak_interest":    trend.get("peak_interest"),
                        "trend_direction":  trend.get("trend_direction"),
                    },
                ))
            except Exception as exc:
                logger.warning("[MacroScan/Trends] Rule %s failed: %s", rule["name"], exc)

        return anomalies


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _extract_filing_text(filing: Dict) -> str:
    """Extract readable text from a sec-api filing object."""
    parts = []
    for key in ("periodOfReport", "description", "formType", "entityName",
                "linkToTxt", "linkToHtml"):
        v = filing.get(key)
        if v and isinstance(v, str):
            parts.append(v)
    # _source or nested entity
    src = filing.get("_source") or {}
    if isinstance(src, dict):
        for k in ("description", "periodOfReport", "entityName"):
            v = src.get(k)
            if v and isinstance(v, str):
                parts.append(v)
    return " ".join(parts)


def _extract_company(filing: Dict) -> str:
    src = filing.get("_source") or {}
    return (
        filing.get("entityName")
        or src.get("entityName")
        or filing.get("companyName")
        or "Unknown"
    )


async def _run_sync(fn, *args, **kwargs):
    """Call a synchronous function from an async context without blocking."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_macro_scan(db: Session) -> Dict[str, Any]:
    """Public entry point called by job_runner every 6 hours."""
    scanner = MacroSignalScanner()
    return await scanner.scan_all(db)
