"""
OppGrid Scraper Diagnostic Script
Run this on Replit to check the health of all data pipelines.

Usage:
    cd backend
    python scraper_diagnostic.py

Output: Full report of scraper status, table counts, data freshness, and missing API keys.
"""
import os
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import get_db
from sqlalchemy import func, text
from sqlalchemy.orm import Session

def log(section: str, message: str, level: str = "info"):
    emoji = {"info": "ℹ️", "ok": "✅", "warn": "⚠️", "error": "❌", "header": "🔍"}
    print(f"{emoji.get(level, 'ℹ️')}  [{section}] {message}")

def check_env_vars():
    log("ENV", "Checking API keys and environment variables", "header")
    keys = {
        "SERPAPI_API_KEY": "SerpAPI Google scraper",
        "APIFY_API_KEY": "Apify Reddit scraper",
        "FRED_API_KEY": "FRED economic data",
        "BLS_API_KEY": "BLS labor data",
        "CENSUS_API_KEY": "Census demographic data",
        "STRIPE_SECRET_KEY": "Stripe payments",
        "OPENAI_API_KEY": "OpenAI AI generation",
        "ANTHROPIC_API_KEY": "Anthropic AI generation",
        "GOOGLE_MAPS_API_KEY": "Google Maps / Places",
        "DEEPSEEK_API_KEY": "DeepSeek AI",
        "RESEND_API_KEY": "Resend email",
    }
    for key, description in keys.items():
        value = os.getenv(key)
        if value and len(value) > 10:
            log("ENV", f"{key} ({description}): SET ({value[:4]}...{value[-4:]})", "ok")
        else:
            log("ENV", f"{key} ({description}): MISSING or INVALID", "error")

def check_table_counts(db: Session):
    log("DB", "Checking table row counts", "header")
    tables = [
        ("HubOpportunityEnriched", "app.models.data_hub", "HubOpportunityEnriched"),
        ("HubMarketByGeography", "app.models.data_hub", "HubMarketByGeography"),
        ("HubIndustryInsight", "app.models.data_hub", "HubIndustryInsight"),
        ("HubMarketSignal", "app.models.data_hub", "HubMarketSignal"),
        ("DetectedTrend", "app.models.detected_trend", "DetectedTrend"),
        ("ScrapeJob", "app.models.data_source", "ScrapeJob"),
        ("DataSource", "app.models.data_source", "DataSource"),
        ("Opportunity", "app.models.opportunity", "Opportunity"),
        ("GeneratedReport", "app.models.generated_report", "GeneratedReport"),
        ("UserAIUsage", "app.models.ai_usage", "UserAIUsage"),
        ("Dataset", "app.models.dataset", "Dataset"),
        ("DatasetPurchase", "app.models.dataset", "DatasetPurchase"),
    ]
    for name, module_path, class_name in tables:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            count = db.query(cls).count()
            status = "ok" if count > 0 else "warn"
            log("DB", f"{name}: {count} rows", status)
        except Exception as e:
            log("DB", f"{name}: ERROR — {e}", "error")

def check_data_freshness(db: Session):
    log("DB", "Checking data freshness (most recent records)", "header")
    checks = [
        ("HubOpportunityEnriched", "app.models.data_hub", "HubOpportunityEnriched", "created_at"),
        ("DetectedTrend", "app.models.detected_trend", "DetectedTrend", "detected_at"),
        ("ScrapeJob", "app.models.data_source", "ScrapeJob", "completed_at"),
        ("Opportunity", "app.models.opportunity", "Opportunity", "created_at"),
        ("GeneratedReport", "app.models.generated_report", "GeneratedReport", "created_at"),
    ]
    for name, module_path, class_name, date_col in checks:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            col = getattr(cls, date_col)
            latest = db.query(col).order_by(col.desc()).first()
            if latest and latest[0]:
                latest_dt = latest[0]
                age_hours = (datetime.utcnow() - latest_dt).total_seconds() / 3600
                if age_hours < 24:
                    status = "ok"
                elif age_hours < 168:
                    status = "warn"
                else:
                    status = "error"
                log("DB", f"{name} latest record: {latest_dt.isoformat()} ({age_hours:.1f}h ago)", status)
            else:
                log("DB", f"{name}: No records with date", "warn")
        except Exception as e:
            log("DB", f"{name}: ERROR — {e}", "error")

def check_scraper_jobs(db: Session):
    log("JOBS", "Checking scraper job history", "header")
    try:
        from app.models.data_source import ScrapeJob
        jobs = db.query(ScrapeJob).order_by(ScrapeJob.completed_at.desc()).limit(20).all()
        if not jobs:
            log("JOBS", "No ScrapeJob records found", "warn")
            return
        job_types = defaultdict(list)
        for job in jobs:
            job_types[job.job_type].append({
                "status": job.status,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "items_processed": job.items_processed,
                "items_accepted": job.items_accepted,
                "error_message": job.error_message,
            })
        for job_type, records in job_types.items():
            latest = records[0]
            latest_dt = latest["completed_at"] if latest["completed_at"] else "never"
            status = latest["status"]
            total_items = sum(r["items_processed"] or 0 for r in records)
            total_accepted = sum(r["items_accepted"] or 0 for r in records)
            error_count = sum(1 for r in records if r["error_message"])
            if status == "completed" and error_count == 0:
                level = "ok"
            elif status == "completed":
                level = "warn"
            else:
                level = "error"
            log("JOBS", f"{job_type}: latest={latest_dt}, status={status}, items={total_items}, accepted={total_accepted}, errors={error_count}", level)
    except Exception as e:
        log("JOBS", f"ERROR checking scraper jobs: {e}", "error")

def check_api_connectivity():
    log("API", "Testing external API connectivity (quick checks)", "header")
    tests = []
    # FRED
    if os.getenv("FRED_API_KEY"):
        try:
            import requests
            r = requests.get("https://api.stlouisfed.org/fred/series/observations", params={
                "series_id": "FEDFUNDS", "api_key": os.getenv("FRED_API_KEY"), "file_type": "json", "limit": 1
            }, timeout=10)
            if r.status_code == 200:
                log("API", "FRED API: CONNECTED", "ok")
            else:
                log("API", f"FRED API: HTTP {r.status_code}", "error")
        except Exception as e:
            log("API", f"FRED API: FAILED — {e}", "error")
    else:
        log("API", "FRED API: SKIPPED (no key)", "warn")
    # SerpAPI
    if os.getenv("SERPAPI_KEY"):
        try:
            import requests
            r = requests.get("https://serpapi.com/account", params={"api_key": os.getenv("SERPAPI_KEY")}, timeout=10)
            if r.status_code == 200:
                log("API", "SerpAPI: CONNECTED", "ok")
            else:
                log("API", f"SerpAPI: HTTP {r.status_code}", "error")
        except Exception as e:
            log("API", f"SerpAPI: FAILED — {e}", "error")
    else:
        log("API", "SerpAPI: SKIPPED (no key)", "warn")
    # Apify
    if os.getenv("APIFY_API_KEY"):
        try:
            import requests
            r = requests.get("https://api.apify.com/v2/actor-runs", headers={"Authorization": f"Bearer {os.getenv('APIFY_API_KEY')}"}, timeout=10)
            if r.status_code in (200, 401):
                log("API", "Apify API: CONNECTED", "ok")
            else:
                log("API", f"Apify API: HTTP {r.status_code}", "error")
        except Exception as e:
            log("API", f"Apify API: FAILED — {e}", "error")
    else:
        log("API", "Apify API: SKIPPED (no key)", "warn")

def check_dataset_definitions(db: Session):
    log("DATASETS", "Checking dataset marketplace definitions", "header")
    try:
        from app.models.dataset import Dataset
        datasets = db.query(Dataset).all()
        if not datasets:
            log("DATASETS", "No Dataset definitions found in marketplace", "warn")
            return
        for ds in datasets:
            status = "ok" if ds.is_active else "warn"
            log("DATASETS", f"{ds.name} ({ds.id}): type={ds.dataset_type}, active={ds.is_active}, records={ds.record_count or 0}, price=${ds.price_cents or 0}", status)
    except Exception as e:
        log("DATASETS", f"ERROR checking datasets: {e}", "error")

def generate_summary(db: Session):
    log("SUMMARY", "--- Diagnostic Summary ---", "header")
    try:
        from app.models.data_hub import HubOpportunityEnriched
        from app.models.detected_trend import DetectedTrend
        from app.models.data_source import ScrapeJob
        opp_count = db.query(HubOpportunityEnriched).count()
        trend_count = db.query(DetectedTrend).count()
        job_count = db.query(ScrapeJob).count()
        log("SUMMARY", f"HubOpportunityEnriched: {opp_count} rows", "ok" if opp_count > 100 else "warn")
        log("SUMMARY", f"DetectedTrend: {trend_count} rows", "ok" if trend_count > 100 else "warn")
        log("SUMMARY", f"ScrapeJob: {job_count} rows", "ok" if job_count > 10 else "warn")
        if opp_count > 100 and trend_count > 100 and job_count > 10:
            log("SUMMARY", "MARKETPLACE CAN BE RE-ENABLED — sufficient real data exists", "ok")
        else:
            log("SUMMARY", "MARKETPLACE MUST STAY DISABLED — need more real data before relaunch", "error")
    except Exception as e:
        log("SUMMARY", f"ERROR generating summary: {e}", "error")

def main():
    print("=" * 70)
    print("  OppGrid Scraper & Data Pipeline Diagnostic")
    print(f"  Run at: {datetime.utcnow().isoformat()} UTC")
    print("=" * 70)
    print()

    db = next(get_db())
    try:
        check_env_vars()
        print()
        check_table_counts(db)
        print()
        check_data_freshness(db)
        print()
        check_scraper_jobs(db)
        print()
        check_api_connectivity()
        print()
        check_dataset_definitions(db)
        print()
        generate_summary(db)
    finally:
        db.close()

    print()
    print("=" * 70)
    print("  Diagnostic complete. Review ❌ errors and ⚠️ warnings above.")
    print("=" * 70)

if __name__ == "__main__":
    main()
