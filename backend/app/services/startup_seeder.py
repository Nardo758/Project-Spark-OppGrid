"""
Idempotent first-run seeder for the Google opportunity pipeline.

Called once at application startup; all operations are guarded by
"do nothing if rows already exist" checks so they are safe to run
on every deployment.
"""
import json
import logging
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


TOP_20_US_METROS = [
    {"name": "New York, NY",       "normalized": "new york ny",      "lat": 40.7128,  "lng": -74.0060,  "address": "New York, NY, USA"},
    {"name": "Los Angeles, CA",    "normalized": "los angeles ca",   "lat": 34.0522,  "lng": -118.2437, "address": "Los Angeles, CA, USA"},
    {"name": "Chicago, IL",        "normalized": "chicago il",       "lat": 41.8781,  "lng": -87.6298,  "address": "Chicago, IL, USA"},
    {"name": "Houston, TX",        "normalized": "houston tx",       "lat": 29.7604,  "lng": -95.3698,  "address": "Houston, TX, USA"},
    {"name": "Phoenix, AZ",        "normalized": "phoenix az",       "lat": 33.4484,  "lng": -112.0740, "address": "Phoenix, AZ, USA"},
    {"name": "Philadelphia, PA",   "normalized": "philadelphia pa",  "lat": 39.9526,  "lng": -75.1652,  "address": "Philadelphia, PA, USA"},
    {"name": "San Antonio, TX",    "normalized": "san antonio tx",   "lat": 29.4241,  "lng": -98.4936,  "address": "San Antonio, TX, USA"},
    {"name": "San Diego, CA",      "normalized": "san diego ca",     "lat": 32.7157,  "lng": -117.1611, "address": "San Diego, CA, USA"},
    {"name": "Dallas, TX",         "normalized": "dallas tx",        "lat": 32.7767,  "lng": -96.7970,  "address": "Dallas, TX, USA"},
    {"name": "Jacksonville, FL",   "normalized": "jacksonville fl",  "lat": 30.3322,  "lng": -81.6557,  "address": "Jacksonville, FL, USA"},
    {"name": "Austin, TX",         "normalized": "austin tx",        "lat": 30.2672,  "lng": -97.7431,  "address": "Austin, TX, USA"},
    {"name": "Fort Worth, TX",     "normalized": "fort worth tx",    "lat": 32.7555,  "lng": -97.3308,  "address": "Fort Worth, TX, USA"},
    {"name": "Columbus, OH",       "normalized": "columbus oh",      "lat": 39.9612,  "lng": -82.9988,  "address": "Columbus, OH, USA"},
    {"name": "Charlotte, NC",      "normalized": "charlotte nc",     "lat": 35.2271,  "lng": -80.8431,  "address": "Charlotte, NC, USA"},
    {"name": "San Francisco, CA",  "normalized": "san francisco ca", "lat": 37.7749,  "lng": -122.4194, "address": "San Francisco, CA, USA"},
    {"name": "Indianapolis, IN",   "normalized": "indianapolis in",  "lat": 39.7684,  "lng": -86.1581,  "address": "Indianapolis, IN, USA"},
    {"name": "Seattle, WA",        "normalized": "seattle wa",       "lat": 47.6062,  "lng": -122.3321, "address": "Seattle, WA, USA"},
    {"name": "Denver, CO",         "normalized": "denver co",        "lat": 39.7392,  "lng": -104.9903, "address": "Denver, CO, USA"},
    {"name": "Nashville, TN",      "normalized": "nashville tn",     "lat": 36.1627,  "lng": -86.7816,  "address": "Nashville, TN, USA"},
    {"name": "Oklahoma City, OK",  "normalized": "oklahoma city ok", "lat": 35.4676,  "lng": -97.5164,  "address": "Oklahoma City, OK, USA"},
]


DEFAULT_KEYWORD_GROUPS = [
    {
        "name": "Restaurant & Dining Problems",
        "category": "restaurant",
        "description": "Pain-point searches targeting restaurants with service or quality gaps",
        "keywords": [
            "restaurant slow service", "restaurant long wait", "restaurant overpriced",
            "bad food quality restaurant", "restaurant rude staff", "restaurant dirty",
            "restaurant understaffed", "restaurant wrong order",
        ],
    },
    {
        "name": "Childcare & Daycare Gaps",
        "category": "childcare",
        "description": "Pain-point searches targeting childcare centers with quality or availability issues",
        "keywords": [
            "daycare no availability", "childcare waitlist", "preschool problems",
            "daycare expensive", "childcare understaffed", "preschool poor communication",
        ],
    },
    {
        "name": "Home Services Pain Points",
        "category": "home_services",
        "description": "Pain-point searches for home service providers with reliability issues",
        "keywords": [
            "plumber unreliable", "electrician slow response", "contractor no-show",
            "HVAC repair expensive", "cleaning service problems", "landscaping complaints",
            "home repair delays", "contractor overpriced",
        ],
    },
    {
        "name": "Healthcare Access Problems",
        "category": "healthcare",
        "description": "Pain-point searches for healthcare providers with access or quality gaps",
        "keywords": [
            "doctor long wait time", "clinic appointment unavailable", "dentist expensive",
            "medical office poor service", "pharmacy stock issues", "therapy waitlist",
        ],
    },
    {
        "name": "Apartment & Housing Complaints",
        "category": "apartment",
        "description": "Pain-point searches targeting property management with unresolved tenant issues",
        "keywords": [
            "apartment maintenance slow", "property management unresponsive",
            "apartment hidden fees", "landlord problems", "apartment noisy",
            "property management bad reviews", "apartment parking issues",
        ],
    },
    {
        "name": "Retail & Shopping Gaps",
        "category": "retail",
        "description": "Pain-point searches for retail stores with service or inventory issues",
        "keywords": [
            "store out of stock", "retail poor customer service", "shop long checkout",
            "grocery store problems", "retail return policy problems", "store rude employees",
        ],
    },
    {
        "name": "Fitness & Wellness Issues",
        "category": "fitness",
        "description": "Pain-point searches for gyms and wellness centers with problems",
        "keywords": [
            "gym overcrowded", "fitness center equipment broken", "yoga studio waitlist",
            "gym expensive membership", "fitness class cancelled", "gym dirty locker room",
        ],
    },
    {
        "name": "Automotive Service Complaints",
        "category": "automotive",
        "description": "Pain-point searches for auto shops with service quality issues",
        "keywords": [
            "mechanic overpriced", "auto repair delays", "car dealership problems",
            "tire shop long wait", "oil change expensive", "auto body shop poor quality",
        ],
    },
    {
        "name": "Beauty & Personal Care Gaps",
        "category": "beauty",
        "description": "Pain-point searches for salons and spas with service problems",
        "keywords": [
            "hair salon long wait", "salon appointment unavailable", "nail salon problems",
            "spa overpriced", "barber shop rude", "salon poor quality",
        ],
    },
    {
        "name": "Pet Services Problems",
        "category": "pet_services",
        "description": "Pain-point searches for pet service providers with quality issues",
        "keywords": [
            "vet expensive", "pet groomer problems", "veterinary long wait",
            "dog grooming complaints", "kennel poor reviews", "pet sitter unreliable",
        ],
    },
]


def seed_locations(db: Session) -> int:
    """Seed top-20 US metro locations if the location_catalog table is empty."""
    count = db.execute(text("SELECT COUNT(*) FROM location_catalog")).scalar()
    if count and count > 0:
        logger.info("location_catalog already has %d rows — skipping seed", count)
        return 0

    added = 0
    for loc in TOP_20_US_METROS:
        db.execute(
            text("""
                INSERT INTO location_catalog
                    (name, normalized_name, location_type, latitude, longitude,
                     address, radius_km, scraped_count, is_active)
                VALUES
                    (:name, :normalized, 'city', :lat, :lng,
                     :address, 50, 0, TRUE)
            """),
            loc,
        )
        added += 1

    db.commit()
    logger.info("Seeded %d locations into location_catalog", added)
    return added


def seed_keyword_groups(db: Session) -> int:
    """Seed default pain-point keyword groups if the keyword_groups table is empty."""
    count = db.execute(text("SELECT COUNT(*) FROM keyword_groups")).scalar()
    if count and count > 0:
        logger.info("keyword_groups already has %d rows — skipping seed", count)
        return 0

    added = 0
    for group in DEFAULT_KEYWORD_GROUPS:
        kws = "{" + ",".join(f'"{k}"' for k in group["keywords"]) + "}"
        db.execute(
            text("""
                INSERT INTO keyword_groups
                    (name, category, keywords, description, match_type,
                     negative_keywords, required_patterns, language, is_active, total_searches)
                VALUES
                    (:name, :category, :keywords::text[], :description, 'phrase',
                     ARRAY[]::text[], ARRAY[]::text[], 'en', TRUE, 0)
            """),
            {
                "name": group["name"],
                "category": group["category"],
                "keywords": kws,
                "description": group["description"],
            },
        )
        added += 1

    db.commit()
    logger.info("Seeded %d keyword groups into keyword_groups", added)
    return added


def check_serpapi_key() -> bool:
    """Log whether the SERPAPI_KEY secret is present at startup."""
    key = os.getenv("SERPAPI_KEY")
    if key:
        logger.info("SERPAPI_KEY is configured — Google opportunity pipeline is active")
        return True
    logger.warning(
        "SERPAPI_KEY is NOT set. "
        "Google Maps scraping jobs will fail until this Replit Secret is added."
    )
    return False


def check_apify_secrets() -> bool:
    """Log whether the Apify secrets are present at startup."""
    token = os.getenv("APIFY_API_TOKEN")
    secret = os.getenv("APIFY_WEBHOOK_SECRET")
    if token and secret:
        logger.info("APIFY_API_TOKEN + APIFY_WEBHOOK_SECRET configured — Reddit pipeline active")
        return True
    if token and not secret:
        logger.warning(
            "APIFY_API_TOKEN is set but APIFY_WEBHOOK_SECRET is missing. "
            "Reddit actor runs will succeed but webhooks cannot be verified. "
            "Add APIFY_WEBHOOK_SECRET to Replit Secrets and configure it in the "
            "trudax/reddit-scraper-lite actor webhook settings in Apify."
        )
        return False
    logger.warning(
        "APIFY_API_TOKEN is NOT set. "
        "Reddit scraper jobs will fail until this Replit Secret is added."
    )
    return False


def check_mapbox_config() -> bool:
    """Log whether the Mapbox Access Token is present at startup."""
    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if token:
        logger.info(
            "MAPBOX_ACCESS_TOKEN configured — static map images and competitor "
            "density maps are active for Business Plan reports."
        )
        return True
    logger.warning(
        "MAPBOX_ACCESS_TOKEN is NOT set. "
        "Static map images will be omitted from Business Plan reports. "
        "Add MAPBOX_ACCESS_TOKEN to Replit Secrets to enable map generation."
    )
    return False


def check_census_config() -> bool:
    """Log whether the Census API key is present at startup."""
    key = os.getenv("CENSUS_API_KEY")
    if key:
        logger.info(
            "CENSUS_API_KEY configured — demographic data enrichment "
            "(population, income, housing) is active for opportunity scoring."
        )
        return True
    logger.warning(
        "CENSUS_API_KEY is NOT set. "
        "Demographic enrichment will be skipped; opportunity scores will not "
        "be adjusted for local population or income context. "
        "Add CENSUS_API_KEY to Replit Secrets (free key at api.census.gov/data/key_signup.html)."
    )
    return False


def check_deepseek_config() -> bool:
    """Log whether the DeepSeek API key is present at startup."""
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        logger.info(
            "DEEPSEEK_API_KEY configured — DeepSeek (deepseek-chat) is active "
            "for data-side intelligence: signal extraction, clustering, and "
            "market analysis before Claude's creative pass."
        )
        return True
    logger.warning(
        "DEEPSEEK_API_KEY is NOT set. "
        "The DeepSeek coordinator will be skipped; signal extraction and "
        "clustering will fall back to Claude-only processing (higher cost). "
        "Add DEEPSEEK_API_KEY to Replit Secrets to enable the dual-AI pipeline."
    )
    return False


def run_pipeline_seed(db: Session) -> None:
    """Run all pipeline seed operations idempotently. Safe to call on every startup."""
    try:
        check_serpapi_key()
        check_apify_secrets()
        check_mapbox_config()
        check_census_config()
        check_deepseek_config()
        seed_locations(db)
        seed_keyword_groups(db)
    except Exception as exc:
        logger.error("Pipeline seeder encountered an error (non-fatal): %s", exc)
