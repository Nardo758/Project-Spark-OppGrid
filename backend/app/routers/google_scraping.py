from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.db.database import get_db
from app.services.google_scraping_service import GoogleScrapingService
from app.core.dependencies import get_current_admin_user
from app.models.user import User


router = APIRouter(prefix="/google-scraping", tags=["google-scraping"])


class LocationCreate(BaseModel):
    name: str
    place_id: Optional[str] = None
    location_type: str = "city"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 5.0
    address: Optional[str] = None
    google_maps_url: Optional[str] = None
    extra_data: dict = {}


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    place_id: Optional[str] = None
    location_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class KeywordGroupCreate(BaseModel):
    name: str
    category: Optional[str] = None
    keywords: List[str]
    description: Optional[str] = None
    match_type: str = "phrase"
    negative_keywords: List[str] = []
    required_patterns: List[str] = []
    language: str = "en"


class KeywordGroupUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    match_type: Optional[str] = None
    negative_keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None


class JobCreate(BaseModel):
    name: str
    location_id: Optional[int] = None
    keyword_group_id: Optional[int] = None
    source_type: str = "google_maps_reviews"
    depth: int = 50
    radius_km: int = 5
    language: str = "en-US"
    sort_by: str = "relevance"
    min_rating: int = 1
    max_age_days: Optional[int] = None
    schedule_type: str = "once"


@router.get("/stats")
async def get_stats(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    return service.get_stats()


@router.get("/locations")
async def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    location_type: Optional[str] = None,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    locations = service.get_locations(skip, limit, search, location_type)
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "place_id": loc.place_id,
            "location_type": loc.location_type,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "radius_km": loc.radius_km,
            "address": loc.address,
            "last_scraped_at": loc.last_scraped_at.isoformat() if loc.last_scraped_at else None,
            "scraped_count": loc.scraped_count,
            "is_active": loc.is_active
        }
        for loc in locations
    ]


@router.post("/locations")
async def create_location(
    data: LocationCreate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    location = service.create_location(data.dict())
    return {"success": True, "location_id": location.id}


@router.put("/locations/{location_id}")
async def update_location(
    location_id: int,
    data: LocationUpdate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    location = service.update_location(location_id, data.dict(exclude_unset=True))
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"success": True}


@router.delete("/locations/{location_id}")
async def delete_location(
    location_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    if not service.delete_location(location_id):
        raise HTTPException(status_code=404, detail="Location not found")
    return {"success": True}


@router.post("/locations/seed")
async def seed_locations(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Seed locations from the keyword matrix - all major US cities and neighborhoods"""
    service = GoogleScrapingService(db)
    
    SEED_LOCATIONS = [
        {"name": "San Francisco, CA", "location_type": "city", "latitude": 37.7749, "longitude": -122.4194, "radius_km": 15},
        {"name": "New York, NY", "location_type": "city", "latitude": 40.7128, "longitude": -74.0060, "radius_km": 20},
        {"name": "Los Angeles, CA", "location_type": "city", "latitude": 34.0522, "longitude": -118.2437, "radius_km": 25},
        {"name": "Chicago, IL", "location_type": "city", "latitude": 41.8781, "longitude": -87.6298, "radius_km": 20},
        {"name": "Boston, MA", "location_type": "city", "latitude": 42.3601, "longitude": -71.0589, "radius_km": 15},
        {"name": "Seattle, WA", "location_type": "city", "latitude": 47.6062, "longitude": -122.3321, "radius_km": 15},
        {"name": "Denver, CO", "location_type": "city", "latitude": 39.7392, "longitude": -104.9903, "radius_km": 15},
        {"name": "Austin, TX", "location_type": "city", "latitude": 30.2672, "longitude": -97.7431, "radius_km": 15},
        {"name": "Portland, OR", "location_type": "city", "latitude": 45.5152, "longitude": -122.6784, "radius_km": 15},
        {"name": "Miami, FL", "location_type": "city", "latitude": 25.7617, "longitude": -80.1918, "radius_km": 15},
        {"name": "Mission District, SF", "location_type": "neighborhood", "latitude": 37.7599, "longitude": -122.4148, "radius_km": 3},
        {"name": "SOMA, SF", "location_type": "neighborhood", "latitude": 37.7785, "longitude": -122.3950, "radius_km": 3},
        {"name": "Castro, SF", "location_type": "neighborhood", "latitude": 37.7609, "longitude": -122.4350, "radius_km": 2},
        {"name": "Marina, SF", "location_type": "neighborhood", "latitude": 37.8030, "longitude": -122.4367, "radius_km": 2},
        {"name": "Williamsburg, Brooklyn", "location_type": "neighborhood", "latitude": 40.7081, "longitude": -73.9571, "radius_km": 3},
        {"name": "Park Slope, Brooklyn", "location_type": "neighborhood", "latitude": 40.6710, "longitude": -73.9777, "radius_km": 2},
        {"name": "Upper East Side, NYC", "location_type": "neighborhood", "latitude": 40.7736, "longitude": -73.9566, "radius_km": 3},
        {"name": "Hollywood, LA", "location_type": "neighborhood", "latitude": 34.0928, "longitude": -118.3287, "radius_km": 5},
        {"name": "Santa Monica, LA", "location_type": "neighborhood", "latitude": 34.0195, "longitude": -118.4912, "radius_km": 5},
        {"name": "Beverly Hills, LA", "location_type": "neighborhood", "latitude": 34.0736, "longitude": -118.4004, "radius_km": 3},
        {"name": "Bay Area", "location_type": "region", "latitude": 37.5585, "longitude": -122.2711, "radius_km": 50},
        {"name": "Silicon Valley", "location_type": "region", "latitude": 37.3875, "longitude": -122.0575, "radius_km": 30},
    ]
    
    added = 0
    skipped = 0
    
    for loc_data in SEED_LOCATIONS:
        existing = service.get_locations(0, 1, loc_data["name"], None)
        if existing:
            skipped += 1
            continue
        
        service.create_location(loc_data)
        added += 1
    
    return {"success": True, "added": added, "skipped": skipped, "total": len(SEED_LOCATIONS)}


@router.get("/locations/{location_id}/children")
async def get_location_children(
    location_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get child locations (e.g., zip codes) for a parent city"""
    service = GoogleScrapingService(db)
    children = service.get_location_children(location_id)
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "location_type": loc.location_type,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "radius_km": loc.radius_km,
            "last_scraped_at": loc.last_scraped_at.isoformat() if loc.last_scraped_at else None,
            "scraped_count": loc.scraped_count,
            "extra_data": loc.extra_data
        }
        for loc in children
    ]


@router.get("/keyword-groups")
async def get_keyword_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    groups = service.get_keyword_groups(skip, limit, search, category)
    return [
        {
            "id": g.id,
            "name": g.name,
            "category": g.category,
            "keywords": g.keywords,
            "description": g.description,
            "match_type": g.match_type,
            "negative_keywords": g.negative_keywords,
            "total_searches": g.total_searches,
            "hit_rate": g.hit_rate,
            "last_used_at": g.last_used_at.isoformat() if g.last_used_at else None,
            "is_active": g.is_active
        }
        for g in groups
    ]


@router.post("/keyword-groups/seed")
async def seed_keyword_groups(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Seed default pain-point keyword groups if none exist."""
    from app.services.startup_seeder import DEFAULT_KEYWORD_GROUPS

    service = GoogleScrapingService(db)
    added = 0
    skipped = 0

    for group_data in DEFAULT_KEYWORD_GROUPS:
        existing = service.get_keyword_groups(0, 1, group_data["name"], None)
        if existing:
            skipped += 1
            continue
        service.create_keyword_group(group_data, admin.id)
        added += 1

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "total": len(DEFAULT_KEYWORD_GROUPS),
    }


@router.get("/keyword-groups/categories")
async def get_keyword_categories(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    return service.get_keyword_categories()


@router.post("/keyword-groups")
async def create_keyword_group(
    data: KeywordGroupCreate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    group = service.create_keyword_group(data.dict(), admin.id)
    return {"success": True, "group_id": group.id}


@router.put("/keyword-groups/{group_id}")
async def update_keyword_group(
    group_id: int,
    data: KeywordGroupUpdate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    group = service.update_keyword_group(group_id, data.dict(exclude_unset=True))
    if not group:
        raise HTTPException(status_code=404, detail="Keyword group not found")
    return {"success": True}


@router.delete("/keyword-groups/{group_id}")
async def delete_keyword_group(
    group_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    if not service.delete_keyword_group(group_id):
        raise HTTPException(status_code=404, detail="Keyword group not found")
    return {"success": True}


@router.get("/jobs")
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    jobs = service.get_jobs(skip, limit, status, source_type)
    return [
        {
            "id": j.id,
            "name": j.name,
            "source_type": j.source_type,
            "location_name": j.location.name if j.location else None,
            "keyword_group_name": j.keyword_group.name if j.keyword_group else None,
            "status": j.status,
            "depth": j.depth,
            "total_found": j.total_found,
            "opportunities_found": j.opportunities_found,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat() if j.created_at else None
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "name": job.name,
        "source_type": job.source_type,
        "location": {"id": job.location.id, "name": job.location.name} if job.location else None,
        "keyword_group": {"id": job.keyword_group.id, "name": job.keyword_group.name, "keywords": job.keyword_group.keywords} if job.keyword_group else None,
        "status": job.status,
        "depth": job.depth,
        "radius_km": job.radius_km,
        "total_found": job.total_found,
        "total_processed": job.total_processed,
        "opportunities_found": job.opportunities_found,
        "results": job.results,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None
    }


@router.post("/jobs")
async def create_job(
    data: JobCreate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    job = service.create_job(data.dict(), admin.id)
    return {"success": True, "job_id": job.id}


@router.post("/jobs/{job_id}/run")
async def run_job(
    job_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    service = GoogleScrapingService(db)
    result = service.run_job(job_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Job execution failed"))
    return result
