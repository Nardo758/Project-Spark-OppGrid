import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.scraped_source import ScrapedSource, SourceType
from app.models.rate_limit import RateLimitCounter

logger = logging.getLogger(__name__)


class WebhookValidationError(Exception):
    """Raised when webhook validation fails"""
    pass


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded - should return HTTP 429"""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class WebhookGateway:
    """
    Webhook Gateway with HMAC authentication for 6 data sources.
    Implements 4-stage validation pipeline:
    1. HMAC signature verification
    2. Schema validation
    3. Deduplication check
    4. Rate limiting
    """

    SUPPORTED_SOURCES = {
        "google_maps": SourceType.google_maps,
        "yelp": SourceType.yelp,
        "reddit": SourceType.reddit,
        "twitter": SourceType.twitter,
        "nextdoor": SourceType.nextdoor,
        "craigslist": SourceType.craigslist,
        "custom": SourceType.custom,
    }

    REQUIRED_FIELDS = {
        "google_maps": ["place_id", "name", "location"],
        "yelp": ["business_id", "name", "coordinates"],
        "reddit": ["title"],  # post_id/id and subreddit/communityName handled via FIELD_ALIASES
        "twitter": ["text"],  # tweet_id or tweetId accepted, text required
        "nextdoor": ["post_id", "neighborhood"],
        "craigslist": ["title"],  # Craigslist listings always have a title
        "custom": ["id", "data"],
    }

    # Alternative field names accepted per source.  Each entry is a list of
    # (canonical_name, [aliases...]) tuples.  At least one name in the group
    # must be present for validation to pass.
    FIELD_ALIASES: dict = {
        "reddit": [
            # reddit-scraper-lite uses "id"; older/custom feeds may use "post_id"
            ("post_id", ["id", "parsedId"]),
            # reddit-scraper-lite uses "communityName"/"parsedCommunityName"
            ("subreddit", ["communityName", "parsedCommunityName"]),
        ],
        "craigslist": [
            # ivanvs actor may use "id", "listingId", or "postingId"
            ("id", ["listingId", "postingId", "pid"]),
        ],
    }

    def __init__(self, db: Session, skip_hmac_validation: bool = False):
        self.db = db
        self.is_dev_mode = os.getenv("WEBHOOK_DEV_MODE", "0") == "1"
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")

        if not self.webhook_secret:
            if self.is_dev_mode or skip_hmac_validation:
                # skip_hmac_validation is used by the Apify webhook path which
                # authenticates independently via X-Apify-Webhook-Secret.
                self.webhook_secret = "unused-apify-path"
                if not self.is_dev_mode:
                    logger.debug(
                        "WebhookGateway initialised without WEBHOOK_SECRET "
                        "(HMAC validation skipped — Apify webhook path)"
                    )
            else:
                raise ValueError(
                    "WEBHOOK_SECRET environment variable is required for production. "
                    "Set WEBHOOK_DEV_MODE=1 for development testing without signatures."
                )

    def verify_hmac_signature(
        self, 
        payload: bytes, 
        signature: str, 
        source: str
    ) -> bool:
        """Stage 1: Verify HMAC-SHA256 signature"""
        if not signature:
            return False
        
        source_secret = os.getenv(f"WEBHOOK_SECRET_{source.upper()}", self.webhook_secret)
        expected_signature = hmac.new(
            source_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        provided_sig = signature.replace("sha256=", "")
        return hmac.compare_digest(expected_signature, provided_sig)

    def validate_schema(self, source: str, data: Dict[str, Any]) -> bool:
        """Stage 2: Validate required fields exist (honours FIELD_ALIASES)."""
        required = self.REQUIRED_FIELDS.get(source, [])
        if not all(field in data for field in required):
            return False
        # For each alias group, at least one name must be present
        for _canonical, aliases in self.FIELD_ALIASES.get(source, []):
            group = [_canonical] + aliases
            if not any(field in data for field in group):
                return False
        return True

    def check_duplicate(self, source: str, external_id: str) -> bool:
        """Stage 3: Check for duplicate entries"""
        existing = self.db.query(ScrapedSource).filter(
            ScrapedSource.source_type == source,
            ScrapedSource.external_id == external_id
        ).first()
        return existing is not None

    def extract_external_id(self, source: str, data: Dict[str, Any]) -> Optional[str]:
        """Extract the external ID from the payload based on source type"""
        if source == "twitter":
            # Support both Apify format (tweetId) and standard format (tweet_id)
            tweet_id = data.get("tweetId") or data.get("tweet_id") or data.get("id")
            return str(tweet_id) if tweet_id else None
        
        if source == "reddit":
            # reddit-scraper-lite: "id" (e.g. "t3_abc123") or "parsedId"
            # older/custom feeds: "post_id"
            reddit_id = (
                data.get("post_id")
                or data.get("id")
                or data.get("parsedId")
            )
            return str(reddit_id) if reddit_id else None

        if source == "craigslist":
            # ivanvs actor may expose: "id", "listingId", "postingId", or "pid"
            cl_id = (
                data.get("id")
                or data.get("listingId")
                or data.get("postingId")
                or data.get("pid")
            )
            return str(cl_id) if cl_id else None

        id_fields = {
            "google_maps": "place_id",
            "yelp": "business_id",
            "nextdoor": "post_id",
            "custom": "id",
        }
        field = id_fields.get(source, "id")
        return str(data.get(field, "")) if data.get(field) else None

    async def process_webhook(
        self,
        source: str,
        payload: bytes,
        data: Dict[str, Any],
        signature: Optional[str] = None,
        scrape_id: Optional[str] = None,
        skip_hmac: bool = False,
    ) -> Dict[str, Any]:
        """
        Process incoming webhook with 4-stage validation.
        1. HMAC signature verification
        2. Schema validation
        3. Deduplication check (before rate limiting to avoid quota drain)
        4. Rate limiting (only for new, valid items)
        Returns processed result or raises WebhookValidationError.
        """
        if source not in self.SUPPORTED_SOURCES:
            raise WebhookValidationError(f"Unsupported source: {source}")

        if not skip_hmac and not self.verify_hmac_signature(payload, signature or "", source):
            logger.warning(f"HMAC verification failed for source: {source}")
            raise WebhookValidationError("Invalid signature")

        if not self.validate_schema(source, data):
            required = self.REQUIRED_FIELDS.get(source, [])
            raise WebhookValidationError(f"Missing required fields: {required}")

        from sqlalchemy import text
        import json
        
        external_id = self.extract_external_id(source, data)
        
        if external_id and self.check_duplicate(source, external_id):
            logger.info(f"Duplicate entry skipped (pre-rate-limit check): {source}/{external_id}")
            return {"status": "duplicate", "external_id": external_id}
        
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        max_requests = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))

        ensure_counter_sql = text("""
            INSERT INTO rate_limit_counters (source, window_start, count, max_requests, created_at)
            VALUES (:source, :window_start, 0, :max_requests, :now)
            ON CONFLICT (source, window_start) DO NOTHING
        """)
        
        lock_and_reserve_sql = text("""
            UPDATE rate_limit_counters
            SET count = count + 1, updated_at = :now
            WHERE source = :source AND window_start = :window_start
              AND count < max_requests
            RETURNING id, count
        """)
        
        insert_sql = text("""
            INSERT INTO scraped_sources (external_id, source_type, scrape_id, raw_data, processed, received_at)
            VALUES (:external_id, :source_type, :scrape_id, CAST(:raw_data AS JSONB), 0, :received_at)
            ON CONFLICT (source_type, external_id) WHERE external_id IS NOT NULL
            DO NOTHING
            RETURNING id
        """)
        
        release_slot_sql = text("""
            UPDATE rate_limit_counters
            SET count = GREATEST(count - 1, 0), updated_at = :now
            WHERE source = :source AND window_start = :window_start
        """)
        
        try:
            self.db.execute(ensure_counter_sql, {
                "source": source,
                "window_start": window_start,
                "max_requests": max_requests,
                "now": now,
            })
            
            result = self.db.execute(lock_and_reserve_sql, {
                "source": source,
                "window_start": window_start,
                "now": now,
            })
            row = result.fetchone()
            
            if row is None:
                self.db.rollback()
                logger.warning(f"Rate limit exceeded for source: {source}")
                raise RateLimitExceededError(
                    f"Rate limit exceeded for source {source}",
                    retry_after=60
                )
            
            # Enrich Craigslist items with demand signal score before storage so
            # OpportunityProcessor has the full keyword analysis immediately.
            if source == "craigslist":
                try:
                    from app.services.craigslist_keyword_matrix import score_craigslist_post
                    post_text = " ".join(filter(None, [
                        data.get("title", ""),
                        data.get("body", data.get("description", data.get("text", ""))),
                    ]))
                    cl_section = (
                        data.get("category")
                        or data.get("section")
                        or data.get("subcategory", "")
                    )
                    cl_score = score_craigslist_post(
                        text=post_text,
                        category=cl_section or None,
                    )
                    data = {**data, "_oppgrid_signal": cl_score}
                except Exception as _score_exc:
                    logger.warning("Craigslist scoring failed for item: %s", _score_exc)

            result = self.db.execute(insert_sql, {
                "external_id": external_id,
                "source_type": source,
                "scrape_id": scrape_id,
                "raw_data": json.dumps(data),
                "received_at": now,
            })
            row = result.fetchone()
            
            if row is None:
                self.db.execute(release_slot_sql, {
                    "source": source,
                    "window_start": window_start,
                    "now": now,
                })
                self.db.commit()
                logger.info(f"Duplicate entry detected via ON CONFLICT: {source}/{external_id}")
                return {"status": "duplicate", "external_id": external_id}
            
            source_id = row[0]
            self.db.commit()
            
        except RateLimitExceededError:
            raise
        except Exception as e:
            self.db.rollback()
            raise

        logger.info(f"Webhook processed: source={source}, id={source_id}")

        return {
            "status": "accepted",
            "source_id": source_id,
            "external_id": external_id,
            "source": source,
        }

    async def process_batch(
        self,
        source: str,
        items: List[Dict[str, Any]],
        scrape_id: Optional[str] = None,
        pre_authenticated: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a batch of items from a single source.
        
        Two-phase processing:
        1. Validation phase: Check schema and duplicates for all items (no quota consumed)
        2. Insertion phase: Reserve quota and insert only valid, non-duplicate items
        
        Args:
            source: The source type (google_maps, yelp, etc.)
            items: List of items to process
            scrape_id: Optional scrape job ID for tracking
            pre_authenticated: If True, HMAC was already verified at router level.
                              If False in production mode, raises error.
        """
        if not pre_authenticated and not self.is_dev_mode:
            raise WebhookValidationError(
                "Batch processing requires pre_authenticated=True in production mode. "
                "HMAC must be verified at the router level before calling process_batch."
            )
        
        results = {
            "accepted": 0,
            "duplicates": 0,
            "errors": 0,
            "rate_limited": 0,
            "items": [],
        }

        from sqlalchemy import text
        import json
        
        valid_items = []
        for item in items:
            if source not in self.SUPPORTED_SOURCES:
                results["errors"] += 1
                results["items"].append({"status": "error", "message": f"Unsupported source: {source}"})
                continue
                
            if not self.validate_schema(source, item):
                required = self.REQUIRED_FIELDS.get(source, [])
                results["errors"] += 1
                results["items"].append({"status": "error", "message": f"Missing required fields: {required}"})
                continue
            
            external_id = self.extract_external_id(source, item)
            
            if external_id and self.check_duplicate(source, external_id):
                results["duplicates"] += 1
                results["items"].append({"status": "duplicate", "external_id": external_id})
                continue
            
            valid_items.append((item, external_id))
        
        if not valid_items:
            return results
        
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        max_requests = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        
        ensure_counter_sql = text("""
            INSERT INTO rate_limit_counters (source, window_start, count, max_requests, created_at)
            VALUES (:source, :window_start, 0, :max_requests, :now)
            ON CONFLICT (source, window_start) DO NOTHING
        """)
        
        lock_and_reserve_sql = text("""
            UPDATE rate_limit_counters
            SET count = count + 1, updated_at = :now
            WHERE source = :source AND window_start = :window_start
              AND count < max_requests
            RETURNING id, count
        """)
        
        insert_sql = text("""
            INSERT INTO scraped_sources (external_id, source_type, scrape_id, raw_data, processed, received_at)
            VALUES (:external_id, :source_type, :scrape_id, CAST(:raw_data AS JSONB), 0, :received_at)
            ON CONFLICT (source_type, external_id) WHERE external_id IS NOT NULL
            DO NOTHING
            RETURNING id
        """)
        
        release_slot_sql = text("""
            UPDATE rate_limit_counters
            SET count = GREATEST(count - 1, 0), updated_at = :now
            WHERE source = :source AND window_start = :window_start
        """)
        
        self.db.execute(ensure_counter_sql, {
            "source": source,
            "window_start": window_start,
            "max_requests": max_requests,
            "now": now,
        })
        self.db.commit()
        
        for item, external_id in valid_items:
            try:
                result = self.db.execute(lock_and_reserve_sql, {
                    "source": source,
                    "window_start": window_start,
                    "now": now,
                })
                row = result.fetchone()
                
                if row is None:
                    self.db.rollback()
                    results["rate_limited"] += 1
                    results["items"].append({
                        "status": "rate_limited",
                        "external_id": external_id,
                        "message": "Rate limit exceeded"
                    })
                    continue
                
                result = self.db.execute(insert_sql, {
                    "external_id": external_id,
                    "source_type": source,
                    "scrape_id": scrape_id,
                    "raw_data": json.dumps(item),
                    "received_at": now,
                })
                row = result.fetchone()
                
                if row is None:
                    self.db.execute(release_slot_sql, {
                        "source": source,
                        "window_start": window_start,
                        "now": now,
                    })
                    self.db.commit()
                    results["duplicates"] += 1
                    results["items"].append({"status": "duplicate", "external_id": external_id})
                else:
                    self.db.commit()
                    results["accepted"] += 1
                    results["items"].append({
                        "status": "accepted",
                        "source_id": row[0],
                        "external_id": external_id,
                    })
            except Exception as e:
                self.db.rollback()
                results["errors"] += 1
                results["items"].append({"status": "error", "message": str(e)})

        return results
    
    async def _process_batch_item(
        self,
        source: str,
        data: Dict[str, Any],
        scrape_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a single item in a batch (HMAC already verified at batch level)"""
        if source not in self.SUPPORTED_SOURCES:
            raise WebhookValidationError(f"Unsupported source: {source}")

        if not self.validate_schema(source, data):
            required = self.REQUIRED_FIELDS.get(source, [])
            raise WebhookValidationError(f"Missing required fields: {required}")

        external_id = self.extract_external_id(source, data)
        if external_id and self.check_duplicate(source, external_id):
            return {"status": "duplicate", "external_id": external_id}

        scraped_source = ScrapedSource(
            external_id=external_id,
            source_type=source,
            scrape_id=scrape_id,
            raw_data=data,
            processed=0,
            received_at=datetime.utcnow(),
        )
        self.db.add(scraped_source)
        self.db.commit()
        self.db.refresh(scraped_source)

        return {
            "status": "accepted",
            "source_id": scraped_source.id,
            "external_id": external_id,
        }
    
    def _check_rate_limit_soft(self, source: str) -> Dict[str, Any]:
        """
        Soft rate limit check - only checks if limit is reached, doesn't reserve.
        
        Used before attempting insert. The actual counter increment happens
        after successful insert to ensure duplicates don't consume quota.
        """
        from sqlalchemy import text
        
        max_requests = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        
        check_sql = text("""
            SELECT count FROM rate_limit_counters 
            WHERE source = :source AND window_start = :window_start
        """)
        
        result = self.db.execute(check_sql, {
            "source": source,
            "window_start": window_start,
        })
        row = result.fetchone()
        
        if row is None:
            return {"exceeded": False, "remaining": max_requests}
        
        current_count = row[0]
        if current_count >= max_requests:
            return {"exceeded": True, "retry_after": 60}
        
        return {"exceeded": False, "remaining": max_requests - current_count}

    def _increment_rate_limit_counter(self, source: str, slots: int = 1) -> None:
        """
        Increment rate limit counter AFTER successful insert.
        
        Uses ON CONFLICT to atomically create or increment the counter.
        Only called after insert succeeds, so duplicates never consume quota.
        """
        from sqlalchemy import text
        
        max_requests = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        
        upsert_sql = text("""
            INSERT INTO rate_limit_counters (source, window_start, count, max_requests, created_at)
            VALUES (:source, :window_start, :slots, :max_requests, :now)
            ON CONFLICT (source, window_start) DO UPDATE SET
                count = rate_limit_counters.count + :slots,
                updated_at = :now
        """)
        
        self.db.execute(upsert_sql, {
            "source": source,
            "window_start": window_start,
            "slots": slots,
            "max_requests": max_requests,
            "now": now,
        })

    def _atomic_rate_limit_reserve(self, source: str, slots: int = 1) -> Dict[str, Any]:
        """
        Atomically reserve rate limit slot(s) using ON CONFLICT for concurrency safety.
        
        Uses the rate_limit_counters table with INSERT...ON CONFLICT DO UPDATE
        to atomically increment the counter and check against the limit.
        
        Returns: {"success": True/False, "retry_after": seconds if failed}
        """
        from sqlalchemy import text
        
        max_requests = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        
        reserve_sql = text("""
            INSERT INTO rate_limit_counters (source, window_start, count, max_requests, created_at)
            VALUES (:source, :window_start, :slots, :max_requests, :now)
            ON CONFLICT (source, window_start) DO UPDATE SET
                count = CASE 
                    WHEN rate_limit_counters.count + :slots <= rate_limit_counters.max_requests 
                    THEN rate_limit_counters.count + :slots 
                    ELSE rate_limit_counters.count 
                END,
                updated_at = :now
            RETURNING count, max_requests, 
                (rate_limit_counters.count + :slots <= rate_limit_counters.max_requests) AS reserved
        """)
        
        try:
            result = self.db.execute(reserve_sql, {
                "source": source,
                "window_start": window_start,
                "slots": slots,
                "max_requests": max_requests,
                "now": now,
            })
            row = result.fetchone()
            self.db.commit()
            
            if row is None:
                return {"success": False, "retry_after": 60}
            
            count, max_req, reserved = row
            if not reserved:
                return {"success": False, "retry_after": 60, "current": count, "max": max_req}
            
            return {"success": True, "remaining": max_req - count}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Rate limit reservation failed: {e}")
            return {"success": True}

    def _check_rate_limit_simple(self, source: str) -> Dict[str, Any]:
        """
        Stage 4: Simple rate limiting based on recent accepted entries.
        
        Counts entries in scraped_sources within the last 60 seconds.
        Quota is naturally consumed when items are successfully inserted.
        Duplicates don't consume quota because they hit the unique constraint.
        
        Configure via WEBHOOK_RATE_LIMIT environment variable (default: 100/minute).
        """
        max_requests_per_window = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        window_start = datetime.utcnow() - timedelta(seconds=60)
        
        recent_count = self.db.query(ScrapedSource).filter(
            ScrapedSource.source_type == source,
            ScrapedSource.received_at >= window_start
        ).count()
        
        if recent_count >= max_requests_per_window:
            return {"exceeded": True, "retry_after": 60}
        
        return {"exceeded": False, "remaining": max_requests_per_window - recent_count}

    def _reserve_rate_limit_slot(self, source: str, slots: int = 1) -> Dict[str, Any]:
        """
        Stage 4: Atomically reserve rate limit slot(s) within current transaction.
        
        This method does NOT commit - the caller must commit or rollback.
        If the insert succeeds, the slot is reserved as part of the same transaction.
        If the insert fails and rolls back, the slot reservation is also rolled back.
        
        Uses flush() instead of execute() to ensure the operation participates
        in the current SQLAlchemy session transaction.
        
        Args:
            source: The source type to check
            slots: Number of slots to reserve
            
        Returns:
            {"success": True} if slot reserved
            {"success": False, "retry_after": 60} if rate limit exceeded
        """
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        
        max_requests_per_window = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        
        counter = self.db.query(RateLimitCounter).filter(
            RateLimitCounter.source == source,
            RateLimitCounter.window_start == window_start
        ).with_for_update().first()
        
        if counter is None:
            counter = RateLimitCounter(
                source=source,
                window_start=window_start,
                count=slots,
                max_requests=max_requests_per_window
            )
            self.db.add(counter)
            try:
                self.db.flush()
            except IntegrityError:
                self.db.rollback()
                return self._reserve_rate_limit_slot(source, slots)
        else:
            if counter.count + slots > counter.max_requests:
                return {"success": False, "retry_after": 60}
            counter.count += slots
            counter.updated_at = now
            self.db.flush()
        
        return {"success": True}

    def _check_rate_limit_available(self, source: str, slots_needed: int = 1) -> Dict[str, Any]:
        """
        Stage 4: Atomic rate limiting with dedicated counter table.
        
        Uses INSERT ON CONFLICT UPDATE with row-level locking to provide
        atomic rate limiting. Each source/minute window has a counter row
        that is atomically incremented.
        
        Configure via WEBHOOK_RATE_LIMIT environment variable (default: 100/minute).
        
        Args:
            source: The source type to check
            slots_needed: Number of slots needed (for batch processing)
        """
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
        
        max_requests_per_window = int(os.getenv("WEBHOOK_RATE_LIMIT", "100"))
        
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO rate_limit_counters (source, window_start, count, max_requests, created_at, updated_at)
                    VALUES (:source, :window_start, :slots, :max_requests, NOW(), NOW())
                    ON CONFLICT (source, window_start) 
                    DO UPDATE SET 
                        count = rate_limit_counters.count + :slots,
                        updated_at = NOW()
                    WHERE rate_limit_counters.count + :slots <= rate_limit_counters.max_requests
                    RETURNING count, max_requests
                """),
                {
                    "source": source, 
                    "window_start": window_start, 
                    "slots": slots_needed,
                    "max_requests": max_requests_per_window
                }
            )
            row = result.fetchone()
            
            if row is None:
                current = self.db.execute(
                    text("""
                        SELECT count, max_requests FROM rate_limit_counters 
                        WHERE source = :source AND window_start = :window_start
                    """),
                    {"source": source, "window_start": window_start}
                ).fetchone()
                remaining = (current[1] - current[0]) if current else 0
                return {"exceeded": True, "retry_after": 60, "remaining": max(0, remaining)}
            
            current_count, max_reqs = row
            remaining = max_reqs - current_count
            
            return {"exceeded": False, "remaining": remaining, "acquired": slots_needed}
            
        except IntegrityError:
            self.db.rollback()
            return {"exceeded": True, "retry_after": 60, "remaining": 0}

    def get_unprocessed_sources(self, limit: int = 100) -> List[ScrapedSource]:
        """Get unprocessed scraped sources for the worker queue"""
        return self.db.query(ScrapedSource).filter(
            ScrapedSource.processed == 0
        ).limit(limit).all()

    def mark_processed(self, source_id: int, error: Optional[str] = None):
        """Mark a source as processed"""
        source = self.db.query(ScrapedSource).filter(
            ScrapedSource.id == source_id
        ).first()
        if source:
            source.processed = 1 if not error else -1
            source.error_message = error
            source.processed_at = datetime.utcnow()
            self.db.commit()
