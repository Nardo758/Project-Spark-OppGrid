import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, case, text

from app.models.google_scraping import (
    LocationCatalog, KeywordGroup, GoogleScrapeJob, GoogleMapsBusiness, GoogleSearchCache
)
from app.services.serpapi_service import SerpAPIService

logger = logging.getLogger(__name__)


class GoogleScrapingService:
    def __init__(self, db: Session):
        self.db = db
        self.serpapi = SerpAPIService()
    
    def get_locations(
        self, 
        skip: int = 0, 
        limit: int = 50, 
        search: Optional[str] = None,
        location_type: Optional[str] = None,
        active_only: bool = True,
        exclude_zip_codes: bool = True
    ) -> List[LocationCatalog]:
        query = self.db.query(LocationCatalog)
        
        if active_only:
            query = query.filter(LocationCatalog.is_active == True)
        
        if exclude_zip_codes and not location_type:
            query = query.filter(LocationCatalog.location_type != 'zip_code')
        
        if search:
            query = query.filter(
                or_(
                    LocationCatalog.name.ilike(f"%{search}%"),
                    LocationCatalog.normalized_name.ilike(f"%{search}%")
                )
            )
        
        if location_type:
            query = query.filter(LocationCatalog.location_type == location_type)
        
        type_order = case(
            (LocationCatalog.location_type == 'city', 1),
            (LocationCatalog.location_type == 'metro', 2),
            (LocationCatalog.location_type == 'neighborhood', 3),
            else_=4
        )
        return query.order_by(type_order, LocationCatalog.name).offset(skip).limit(limit).all()
    
    def get_location(self, location_id: int) -> Optional[LocationCatalog]:
        return self.db.query(LocationCatalog).filter(LocationCatalog.id == location_id).first()
    
    def create_location(self, data: Dict[str, Any]) -> LocationCatalog:
        normalized = data.get("name", "").lower().strip()
        location = LocationCatalog(
            name=data.get("name"),
            normalized_name=normalized,
            place_id=data.get("place_id"),
            location_type=data.get("location_type", "city"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            radius_km=data.get("radius_km", 5.0),
            address=data.get("address"),
            google_maps_url=data.get("google_maps_url"),
            extra_data=data.get("extra_data", {}),
            is_active=True
        )
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location
    
    def update_location(self, location_id: int, data: Dict[str, Any]) -> Optional[LocationCatalog]:
        location = self.get_location(location_id)
        if not location:
            return None
        
        for key, value in data.items():
            if hasattr(location, key) and key not in ["id", "created_at"]:
                setattr(location, key, value)
        
        if "name" in data:
            location.normalized_name = data["name"].lower().strip()
        
        self.db.commit()
        self.db.refresh(location)
        return location
    
    def delete_location(self, location_id: int) -> bool:
        location = self.get_location(location_id)
        if not location:
            return False
        location.is_active = False
        self.db.commit()
        return True
    
    def get_location_children(self, parent_id: int) -> List[LocationCatalog]:
        """Get child locations (e.g., zip codes) for a parent location"""
        return self.db.query(LocationCatalog).filter(
            LocationCatalog.parent_location_id == parent_id,
            LocationCatalog.is_active == True
        ).order_by(LocationCatalog.name).all()
    
    def get_keyword_groups(
        self, 
        skip: int = 0, 
        limit: int = 50, 
        search: Optional[str] = None,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[KeywordGroup]:
        query = self.db.query(KeywordGroup)
        
        if active_only:
            query = query.filter(KeywordGroup.is_active == True)
        
        if search:
            query = query.filter(
                or_(
                    KeywordGroup.name.ilike(f"%{search}%"),
                    KeywordGroup.category.ilike(f"%{search}%")
                )
            )
        
        if category:
            query = query.filter(KeywordGroup.category == category)
        
        return query.order_by(KeywordGroup.name).offset(skip).limit(limit).all()
    
    def get_keyword_group(self, group_id: int) -> Optional[KeywordGroup]:
        return self.db.query(KeywordGroup).filter(KeywordGroup.id == group_id).first()
    
    def create_keyword_group(self, data: Dict[str, Any], user_id: Optional[int] = None) -> KeywordGroup:
        group = KeywordGroup(
            name=data.get("name"),
            category=data.get("category"),
            keywords=data.get("keywords", []),
            description=data.get("description"),
            match_type=data.get("match_type", "phrase"),
            negative_keywords=data.get("negative_keywords", []),
            required_patterns=data.get("required_patterns", []),
            language=data.get("language", "en"),
            created_by=user_id
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group
    
    def update_keyword_group(self, group_id: int, data: Dict[str, Any]) -> Optional[KeywordGroup]:
        group = self.get_keyword_group(group_id)
        if not group:
            return None
        
        for key, value in data.items():
            if hasattr(group, key) and key not in ["id", "created_at", "created_by"]:
                setattr(group, key, value)
        
        self.db.commit()
        self.db.refresh(group)
        return group
    
    def delete_keyword_group(self, group_id: int) -> bool:
        group = self.get_keyword_group(group_id)
        if not group:
            return False
        group.is_active = False
        self.db.commit()
        return True
    
    def get_jobs(
        self, 
        skip: int = 0, 
        limit: int = 50, 
        status: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> List[GoogleScrapeJob]:
        query = self.db.query(GoogleScrapeJob)
        
        if status:
            query = query.filter(GoogleScrapeJob.status == status)
        
        if source_type:
            query = query.filter(GoogleScrapeJob.source_type == source_type)
        
        return query.order_by(desc(GoogleScrapeJob.created_at)).offset(skip).limit(limit).all()
    
    def get_job(self, job_id: int) -> Optional[GoogleScrapeJob]:
        return self.db.query(GoogleScrapeJob).filter(GoogleScrapeJob.id == job_id).first()
    
    def create_job(self, data: Dict[str, Any], user_id: Optional[int] = None) -> GoogleScrapeJob:
        job = GoogleScrapeJob(
            location_id=data.get("location_id"),
            keyword_group_id=data.get("keyword_group_id"),
            name=data.get("name"),
            source_type=data.get("source_type", "google_maps_reviews"),
            depth=data.get("depth", 50),
            radius_km=data.get("radius_km", 5),
            language=data.get("language", "en-US"),
            sort_by=data.get("sort_by", "relevance"),
            min_rating=data.get("min_rating", 1),
            max_age_days=data.get("max_age_days"),
            schedule_type=data.get("schedule_type", "once"),
            scheduled_at=data.get("scheduled_at"),
            created_by=user_id
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def run_job(self, job_id: int) -> Dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        self.db.commit()
        
        try:
            location = self.get_location(job.location_id) if job.location_id else None
            keyword_group = self.get_keyword_group(job.keyword_group_id) if job.keyword_group_id else None
            
            location_query = location.name if location else "Austin, TX"
            keywords = keyword_group.keywords if keyword_group else []
            
            all_results = []
            
            if job.source_type == "google_maps_reviews":
                for keyword in keywords[:5]:
                    search_query = f"{keyword} {location_query}"
                    places_result = self.serpapi.google_maps_search(query=search_query, location=location_query)
                    
                    local_results = places_result.get("local_results", [])
                    if local_results:
                        for place in local_results[:3]:
                            if place.get("data_id"):
                                try:
                                    reviews_result = self.serpapi.google_maps_reviews(data_id=place["data_id"])
                                    all_results.append({
                                        "place": place,
                                        "reviews": reviews_result.get("reviews", []),
                                        "keyword": keyword
                                    })
                                    self._cache_business(place, location.id if location else None)
                                except Exception as e:
                                    print(f"Error fetching reviews: {e}")
            
            elif job.source_type == "google_search":
                for keyword in keywords[:10]:
                    search_query = f"{keyword} {location_query}"
                    search_result = self.serpapi.google_search(query=search_query, location=location_query, num=job.depth // len(keywords) if keywords else job.depth)
                    
                    organic_results = search_result.get("organic_results", [])
                    if organic_results:
                        all_results.append({
                            "keyword": keyword,
                            "results": organic_results
                        })
                        
                        self._cache_search_results(keyword, location_query, search_result)
            
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.total_found = len(all_results)
            job.total_processed = len(all_results)
            job.results = all_results
            job.last_result_at = datetime.utcnow()
            
            if location:
                location.last_scraped_at = datetime.utcnow()
                location.scraped_count = (location.scraped_count or 0) + 1
            
            if keyword_group:
                keyword_group.last_used_at = datetime.utcnow()
                keyword_group.total_searches = (keyword_group.total_searches or 0) + 1
            
            self.db.commit()

            signals_written = self._persist_results_to_scraped_data(
                job, all_results, location
            )
            logger.info(
                "Job %s complete: %d result(s), %d signal(s) written to scraped_data",
                job.id, len(all_results), signals_written
            )

            if signals_written > 0:
                self._trigger_s2o(limit=min(signals_written * 10, 500))

            return {
                "success": True,
                "job_id": job.id,
                "total_found": job.total_found,
                "signals_written": signals_written,
                "results": all_results,
            }
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.retry_count = (job.retry_count or 0) + 1
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def _cache_business(self, place_data: Dict, location_id: Optional[int]):
        place_id = place_data.get("place_id") or place_data.get("data_id")
        if not place_id:
            return
        
        existing = self.db.query(GoogleMapsBusiness).filter(GoogleMapsBusiness.place_id == place_id).first()
        
        if existing:
            existing.last_scraped_at = datetime.utcnow()
            existing.scraped_count = (existing.scraped_count or 0) + 1
        else:
            coords = place_data.get("gps_coordinates", {})
            business = GoogleMapsBusiness(
                place_id=place_id,
                name=place_data.get("title") or place_data.get("name", "Unknown"),
                address=place_data.get("address"),
                latitude=coords.get("latitude"),
                longitude=coords.get("longitude"),
                location_id=location_id,
                types=place_data.get("types", []),
                rating=place_data.get("rating"),
                user_ratings_total=place_data.get("reviews"),
                phone_number=place_data.get("phone"),
                website=place_data.get("website"),
                last_scraped_at=datetime.utcnow()
            )
            self.db.add(business)
    
    def _cache_search_results(self, keyword: str, location: str, results: Dict):
        query_string = f"{keyword}|{location}"
        query_hash = hashlib.sha256(query_string.encode()).hexdigest()
        
        existing = self.db.query(GoogleSearchCache).filter(GoogleSearchCache.query_hash == query_hash).first()
        
        if existing:
            existing.raw_results = results
            existing.created_at = datetime.utcnow()
            existing.expires_at = datetime.utcnow() + timedelta(hours=24)
        else:
            cache = GoogleSearchCache(
                query_hash=query_hash,
                location_query=location,
                keyword_query=keyword,
                search_type="organic",
                total_results=results.get("search_information", {}).get("total_results"),
                raw_results=results,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            self.db.add(cache)
    
    def _persist_results_to_scraped_data(
        self,
        job: GoogleScrapeJob,
        all_results: List[Dict],
        location: Optional[LocationCatalog],
    ) -> int:
        """Write scraped place and review data into the scraped_data table.

        Returns the number of new rows inserted.
        """
        location_name = location.name if location else None
        signals_written = 0

        for result_item in all_results:
            keyword: str = result_item.get("keyword", "")

            # Handle google_search organic results
            if "results" in result_item and "place" not in result_item:
                for organic in result_item.get("results", []):
                    link = organic.get("link") or ""
                    title = organic.get("title") or "Unknown"
                    snippet = (organic.get("snippet") or "").strip()
                    if not snippet:
                        continue
                    source_id = hashlib.md5(
                        (link or title + keyword).encode()
                    ).hexdigest()
                    meta = {"keyword": keyword, "job_id": job.id, "position": organic.get("position")}
                    self.db.execute(
                        text("""
                            INSERT INTO scraped_data
                                (source, source_id, content_type, title, content,
                                 url, author, location, metadata, scraped_at)
                            VALUES
                                (:source, :source_id, 'web_result', :title, :content,
                                 :url, NULL, :location, :metadata::jsonb, NOW())
                            ON CONFLICT (source, source_id) DO NOTHING
                        """),
                        {
                            "source": "serpapi_google_search",
                            "source_id": source_id,
                            "title": title,
                            "content": snippet,
                            "url": link,
                            "location": location_name,
                            "metadata": json.dumps(meta),
                        },
                    )
                    signals_written += 1
                continue

            place: Dict = result_item.get("place", {})
            reviews: List[Dict] = result_item.get("reviews", [])

            place_id = place.get("data_id") or place.get("place_id")
            if not place_id:
                continue

            coords = place.get("gps_coordinates") or {}
            lat = coords.get("latitude") if isinstance(coords, dict) else None
            lng = coords.get("longitude") if isinstance(coords, dict) else None

            business_meta = {
                "category": keyword,
                "rating": place.get("rating"),
                "reviews_count": place.get("reviews"),
                "phone": place.get("phone"),
                "website": place.get("website"),
                "keyword": keyword,
                "job_id": job.id,
            }

            place_stmt = text("""
                INSERT INTO scraped_data
                    (source, source_id, content_type, title, content,
                     url, author, location, latitude, longitude, metadata, scraped_at)
                VALUES
                    (:source, :source_id, :content_type, :title, :content,
                     :url, :author, :location, :latitude, :longitude, :metadata::jsonb, NOW())
                ON CONFLICT (source, source_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    scraped_at = NOW()
                RETURNING id
            """)
            self.db.execute(place_stmt, {
                "source": "serpapi_google_maps",
                "source_id": place_id,
                "content_type": "business",
                "title": place.get("title", "Unknown"),
                "content": (
                    f"Category: {keyword}\n"
                    f"Rating: {place.get('rating', 'N/A')}\n"
                    f"Reviews: {place.get('reviews', 0)}"
                ),
                "url": place.get("link"),
                "author": None,
                "location": location_name or place.get("address"),
                "latitude": lat,
                "longitude": lng,
                "metadata": json.dumps(business_meta),
            })
            signals_written += 1

            for review in reviews:
                review_text = (review.get("snippet") or review.get("text") or "").strip()
                if not review_text:
                    continue

                reviewer_id = review.get("user", {}).get("link", "") or review.get("user_id", "")
                review_source_id = f"{place_id}_{reviewer_id}"
                review_meta = {
                    "rating": review.get("rating"),
                    "business_name": place.get("title"),
                    "business_category": keyword,
                    "job_id": job.id,
                }

                review_stmt = text("""
                    INSERT INTO scraped_data
                        (source, source_id, content_type, title, content,
                         url, author, location, latitude, longitude, metadata, scraped_at)
                    VALUES
                        (:source, :source_id, :content_type, :title, :content,
                         :url, :author, :location, :latitude, :longitude, :metadata::jsonb, NOW())
                    ON CONFLICT (source, source_id) DO NOTHING
                """)
                self.db.execute(review_stmt, {
                    "source": "serpapi_google_maps_review",
                    "source_id": review_source_id,
                    "content_type": "review",
                    "title": f"Review of {place.get('title', 'Unknown')}",
                    "content": review_text,
                    "url": place.get("link"),
                    "author": (review.get("user") or {}).get("name"),
                    "location": location_name or place.get("address"),
                    "latitude": lat,
                    "longitude": lng,
                    "metadata": json.dumps(review_meta),
                })
                signals_written += 1

        try:
            self.db.commit()
        except Exception as exc:
            logger.warning("Failed to commit scraped_data rows: %s", exc)
            self.db.rollback()
            return 0

        return signals_written

    def _trigger_s2o(self, limit: int = 500) -> None:
        """Trigger the Signal-to-Opportunity processor on freshly written scraped data."""
        try:
            from app.services.signal_to_opportunity import get_signal_processor
            processor = get_signal_processor(self.db)
            stats = processor.process_scraped_data(limit=limit)
            logger.info(
                "S2O processing complete: %d opportunities created from %d signals",
                stats.get("opportunities_created", 0),
                stats.get("total_signals", 0),
            )
        except Exception as exc:
            logger.warning("S2O auto-trigger failed (non-fatal): %s", exc)

    def get_keyword_categories(self) -> List[str]:
        categories = self.db.query(KeywordGroup.category).distinct().filter(
            KeywordGroup.category.isnot(None),
            KeywordGroup.is_active == True
        ).all()
        return [c[0] for c in categories if c[0]]
    
    def get_location_types(self) -> List[str]:
        types = self.db.query(LocationCatalog.location_type).distinct().filter(
            LocationCatalog.location_type.isnot(None),
            LocationCatalog.is_active == True
        ).all()
        return [t[0] for t in types if t[0]]
    
    def get_stats(self) -> Dict[str, Any]:
        total_locations = self.db.query(LocationCatalog).filter(LocationCatalog.is_active == True).count()
        total_keywords = self.db.query(KeywordGroup).filter(KeywordGroup.is_active == True).count()
        total_jobs = self.db.query(GoogleScrapeJob).count()
        completed_jobs = self.db.query(GoogleScrapeJob).filter(GoogleScrapeJob.status == "completed").count()
        cached_businesses = self.db.query(GoogleMapsBusiness).count()
        
        return {
            "total_locations": total_locations,
            "total_keyword_groups": total_keywords,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "cached_businesses": cached_businesses
        }
