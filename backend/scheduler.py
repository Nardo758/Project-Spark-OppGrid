#!/usr/bin/env python3
"""
Daily scheduler for Katalyst - runs Apify scraper and AI analysis
Can be triggered via cron, Replit scheduled deployments, or manual API call
"""

import os
import sys
import asyncio
import httpx
from datetime import datetime, timedelta

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = "trudax/reddit-scraper-lite"

def get_backend_url():
    """Get the backend URL, auto-detecting from Replit environment if not set"""
    backend_url = os.getenv("BACKEND_URL")
    if backend_url:
        return backend_url
    
    replit_domains = os.getenv("REPLIT_DOMAINS")
    if replit_domains:
        return f"https://{replit_domains.split(',')[0]}"
    
    return "http://localhost:8000"

BACKEND_URL = get_backend_url()

async def trigger_apify_scraper():
    """Trigger the Apify Reddit scraper to run"""
    if not APIFY_API_TOKEN:
        print("ERROR: APIFY_API_TOKEN not configured")
        return None
    
    run_url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs?token={APIFY_API_TOKEN}"
    
    run_input = {
        "debugMode": False,
        "maxItems": 200,
        "maxPostCount": 200,
        "maxComments": 0,
        "proxy": {
            "useApifyProxy": True
        },
        "scrollTimeout": 40,
        "searchComments": False,
        "searchCommunities": False,
        "searchPosts": True,
        "searchUsers": False,
        "searches": [
            "frustrated with",
            "wish there was",
            "why is it so hard to",
            "anyone else annoyed by",
            "there should be an app for",
            "I hate how",
            "biggest pain point",
            "looking for solution to"
        ],
        "skipComments": True,
        "sort": "relevance",
        "time": "week"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"[{datetime.now()}] Triggering Apify scraper...")
        response = await client.post(run_url, json=run_input)
        
        if response.status_code != 201:
            print(f"ERROR: Failed to trigger scraper: {response.status_code} - {response.text}")
            return None
        
        run_data = response.json().get("data", {})
        run_id = run_data.get("id")
        print(f"[{datetime.now()}] Scraper started with run ID: {run_id}")
        return run_id

async def wait_for_run_completion(run_id: str, max_wait_minutes: int = 30):
    """Wait for Apify run to complete"""
    if not run_id:
        return None
    
    run_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
    
    start_time = datetime.now()
    max_wait = timedelta(minutes=max_wait_minutes)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while datetime.now() - start_time < max_wait:
            response = await client.get(run_url)
            if response.status_code != 200:
                print(f"ERROR: Failed to check run status: {response.text}")
                await asyncio.sleep(30)
                continue
            
            run_data = response.json().get("data", {})
            status = run_data.get("status")
            
            print(f"[{datetime.now()}] Scraper status: {status}")
            
            if status == "SUCCEEDED":
                return run_data.get("defaultDatasetId")
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                print(f"ERROR: Scraper run failed with status: {status}")
                return None
            
            await asyncio.sleep(30)
    
    print("ERROR: Timed out waiting for scraper to complete")
    return None

async def fetch_and_import_data():
    """Fetch latest data from Apify and import to database"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"[{datetime.now()}] Fetching latest Apify data...")
        response = await client.post(
            f"{BACKEND_URL}/api/v1/webhook/apify/fetch-latest",
            params={"actor_id": APIFY_ACTOR_ID}
        )
        
        if response.status_code != 200:
            print(f"ERROR: Failed to fetch data: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        print(f"[{datetime.now()}] Import complete: {result.get('created', 0)} new, {result.get('skipped', 0)} duplicates")
        return result

async def run_ai_analysis(batch_size: int = 10):
    """Run AI analysis on unanalyzed opportunities"""
    async with httpx.AsyncClient(timeout=600.0) as client:
        print(f"[{datetime.now()}] Running AI analysis on new opportunities...")
        response = await client.post(
            f"{BACKEND_URL}/api/v1/ai-analysis/analyze-batch",
            json={"limit": batch_size}
        )
        
        if response.status_code != 200:
            print(f"ERROR: AI analysis failed: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        print(f"[{datetime.now()}] AI analysis complete: {result.get('processed', 0)} analyzed, {result.get('failed', 0)} failed")
        return result

async def run_deepseek_coordinator(batch_size: int = 20):
    """Run DeepSeek coordinator on unprocessed scraped data (Stage 0 of dual-AI pipeline)"""
    async with httpx.AsyncClient(timeout=600.0) as client:
        print(f"[{datetime.now()}] Running DeepSeek data coordination...")
        response = await client.post(
            f"{BACKEND_URL}/api/v1/ai-analysis/coordinate",
            json={"limit": batch_size}
        )

        if response.status_code != 200:
            print(f"WARNING: DeepSeek coordination returned {response.status_code} - {response.text}")
            print("Falling back to direct Claude analysis...")
            return None

        result = response.json()
        print(
            f"[{datetime.now()}] DeepSeek coordination complete: "
            f"{result.get('valid_signals', 0)} signals, "
            f"{result.get('clusters_formed', 0)} clusters"
        )
        return result


async def daily_sync(skip_scraper: bool = False, ai_batch_size: int = 20):
    """
    Full daily sync process (Dual-AI Pipeline):
    1. Trigger Apify scraper (optional)
    2. Wait for completion
    3. Fetch and import new data
    4. [DeepSeek] Signal extraction, clustering, market analysis
    5. [Claude] Creative narrative generation & validation
    """
    print(f"\n{'='*60}")
    print(f"OPPGRID DAILY SYNC (Dual-AI) - {datetime.now()}")
    print(f"{'='*60}\n")

    if not skip_scraper:
        run_id = await trigger_apify_scraper()
        if run_id:
            dataset_id = await wait_for_run_completion(run_id)
            if not dataset_id:
                print("WARNING: Scraper did not complete successfully, fetching latest available data...")

    import_result = await fetch_and_import_data()

    if import_result and import_result.get("created", 0) > 0:
        # Stage 1: DeepSeek data coordination (signal extraction + clustering + market analysis)
        coordinator_result = await run_deepseek_coordinator(batch_size=ai_batch_size)

        # Stage 2: Claude creative analysis (narratives + validation)
        await run_ai_analysis(batch_size=ai_batch_size)
    else:
        print("No new opportunities to analyze")

    print(f"\n{'='*60}")
    print(f"DAILY SYNC COMPLETE - {datetime.now()}")
    print(f"{'='*60}\n")

async def quick_sync():
    """Quick sync - just fetch latest data and analyze without triggering new scrape"""
    await daily_sync(skip_scraper=True, ai_batch_size=10)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Katalyst Daily Scheduler")
    parser.add_argument("--quick", action="store_true", help="Quick sync without triggering scraper")
    parser.add_argument("--batch-size", type=int, default=20, help="AI analysis batch size")
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(quick_sync())
    else:
        asyncio.run(daily_sync(ai_batch_size=args.batch_size))
