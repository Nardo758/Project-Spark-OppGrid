import logging
import os
from typing import Optional, List
from apify_client import ApifyClient

logger = logging.getLogger(__name__)

REDDIT_ACTOR_ID = "trudax/reddit-scraper-lite"

DEFAULT_REDDIT_SUBREDDITS: List[str] = [
    "entrepreneur",
    "smallbusiness",
    "startups",
    "sidehustle",
    "business",
    "mildlyinfuriating",
    "firstworldproblems",
    "Showerthoughts",
    "somebodymakethis",
    "doesanybodyelse",
]

REDDIT_ACTOR_DEFAULT_INPUT = {
    "startUrls": [
        {"url": f"https://www.reddit.com/r/{sub}/new/"} for sub in DEFAULT_REDDIT_SUBREDDITS
    ],
    "maxItems": 200,
    "proxy": {"useApifyProxy": True},
    "searchMode": "posts",
}


class ApifyService:
    def __init__(self):
        self.token = os.getenv("APIFY_API_TOKEN")
        self._client: Optional[ApifyClient] = None
    
    @property
    def client(self) -> ApifyClient:
        if not self._client:
            if not self.token:
                raise ValueError("APIFY_API_TOKEN not configured")
            self._client = ApifyClient(self.token)
        return self._client
    
    def is_configured(self) -> bool:
        return bool(self.token)
    
    def get_actors(self, limit: int = 100) -> list:
        try:
            actors = self.client.actors().list(limit=limit)
            return actors.items if actors else []
        except Exception as e:
            print(f"Error fetching actors: {e}")
            return []
    
    def get_actor(self, actor_id: str) -> dict:
        try:
            return self.client.actor(actor_id).get() or {}
        except Exception as e:
            print(f"Error fetching actor {actor_id}: {e}")
            return {}
    
    def get_schedules(self, limit: int = 100) -> list:
        try:
            schedules = self.client.schedules().list(limit=limit)
            return schedules.items if schedules else []
        except Exception as e:
            print(f"Error fetching schedules: {e}")
            return []
    
    def get_schedule(self, schedule_id: str) -> dict:
        try:
            return self.client.schedule(schedule_id).get() or {}
        except Exception as e:
            print(f"Error fetching schedule {schedule_id}: {e}")
            return {}
    
    def create_schedule(
        self,
        name: str,
        cron_expression: str,
        actor_id: str,
        input_data: dict = None,
        timezone: str = "UTC",
        is_enabled: bool = True
    ) -> dict:
        try:
            schedule = self.client.schedules().create(
                name=name,
                cronExpression=cron_expression,
                isEnabled=is_enabled,
                timezone=timezone,
                actions=[
                    {
                        "type": "RUN_ACTOR",
                        "actorId": actor_id,
                        "input": input_data or {}
                    }
                ]
            )
            return schedule or {}
        except Exception as e:
            print(f"Error creating schedule: {e}")
            raise
    
    def update_schedule(
        self,
        schedule_id: str,
        name: str = None,
        cron_expression: str = None,
        is_enabled: bool = None,
        timezone: str = None
    ) -> dict:
        try:
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if cron_expression is not None:
                update_data["cronExpression"] = cron_expression
            if is_enabled is not None:
                update_data["isEnabled"] = is_enabled
            if timezone is not None:
                update_data["timezone"] = timezone
            
            return self.client.schedule(schedule_id).update(**update_data) or {}
        except Exception as e:
            print(f"Error updating schedule {schedule_id}: {e}")
            raise
    
    def delete_schedule(self, schedule_id: str) -> bool:
        try:
            self.client.schedule(schedule_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting schedule {schedule_id}: {e}")
            return False
    
    def get_runs(self, actor_id: str = None, limit: int = 50) -> list:
        try:
            if actor_id:
                runs = self.client.actor(actor_id).runs().list(limit=limit)
            else:
                runs = self.client.runs().list(limit=limit)
            return runs.items if runs else []
        except Exception as e:
            print(f"Error fetching runs: {e}")
            return []
    
    def get_run(self, run_id: str) -> dict:
        try:
            return self.client.run(run_id).get() or {}
        except Exception as e:
            print(f"Error fetching run {run_id}: {e}")
            return {}
    
    def start_actor(self, actor_id: str, input_data: dict = None) -> dict:
        try:
            run_info = self.client.actor(actor_id).start(run_input=input_data or {})
            return run_info or {}
        except Exception as e:
            print(f"Error starting actor {actor_id}: {e}")
            raise
    
    def abort_run(self, run_id: str) -> bool:
        try:
            self.client.run(run_id).abort()
            return True
        except Exception as e:
            print(f"Error aborting run {run_id}: {e}")
            return False
    
    def get_dataset_items(self, dataset_id: str, limit: int = 100) -> list:
        try:
            items = self.client.dataset(dataset_id).list_items(limit=limit)
            return items.items if items else []
        except Exception as e:
            print(f"Error fetching dataset items: {e}")
            return []
    
    def run_google_maps_search(
        self,
        search_terms: list,
        location: str,
        max_results: int = 100,
        max_reviews: int = 20
    ) -> dict:
        """
        Run Google Maps search using compass/crawler-google-places actor
        
        Args:
            search_terms: List of business types to search (e.g., ["restaurant", "plumber"])
            location: Location to search in (e.g., "Austin, TX")
            max_results: Maximum places per search term
            max_reviews: Maximum reviews per place
        
        Returns:
            Run info dict with id, status, datasetId
        """
        actor_id = "compass/crawler-google-places"
        
        search_queries = [f"{term} in {location}" for term in search_terms]
        
        input_data = {
            "searchStringsArray": search_queries,
            "maxCrawledPlacesPerSearch": max_results,
            "language": "en",
            "maxReviews": max_reviews,
            "scrapeReviewerName": True,
            "scrapeReviewerId": False,
            "scrapeReviewerUrl": False,
            "scrapeReviewId": False,
            "scrapeReviewUrl": False,
            "scrapeResponseFromOwnerText": True,
            "includeHistogram": False,
            "includeOpeningHours": True,
            "includePeopleAlsoSearch": False,
            "additionalInfo": False,
        }
        
        return self.start_actor(actor_id, input_data)

    def run_reddit_scraper(
        self,
        subreddits: Optional[List[str]] = None,
        max_items: int = 200,
    ) -> dict:
        """
        Start a Reddit scraper run using the trudax/reddit-scraper-lite actor.

        Uses DEFAULT_REDDIT_SUBREDDITS when no subreddits are specified.
        Returns run info dict with id, status, defaultDatasetId.
        """
        target_subs = subreddits or DEFAULT_REDDIT_SUBREDDITS
        run_input = {
            "startUrls": [
                {"url": f"https://www.reddit.com/r/{sub}/new/"} for sub in target_subs
            ],
            "maxItems": max_items,
            "proxy": {"useApifyProxy": True},
            "searchMode": "posts",
        }
        logger.info(
            "Starting Reddit actor %s across %d subreddits (max_items=%d)",
            REDDIT_ACTOR_ID, len(target_subs), max_items,
        )
        run_info = self.start_actor(REDDIT_ACTOR_ID, run_input)
        run_id = (run_info or {}).get("id", "unknown")
        logger.info("Reddit actor run started: run_id=%s", run_id)
        return run_info or {}

    def get_run_results(self, run_id: str, limit: int = 1000) -> list:
        """Get results from an Apify run"""
        try:
            run_info = self.get_run(run_id)
            dataset_id = run_info.get("defaultDatasetId")
            if not dataset_id:
                return []
            return self.get_dataset_items(dataset_id, limit=limit)
        except Exception as e:
            print(f"Error fetching run results: {e}")
            return []
    
    def import_existing_run(self, run_id: str) -> dict:
        """Import results from an existing Apify run"""
        run_info = self.get_run(run_id)
        if not run_info:
            raise ValueError(f"Run {run_id} not found")
        
        status = run_info.get("status")
        dataset_id = run_info.get("defaultDatasetId")
        
        if status not in ["SUCCEEDED", "ABORTED"]:
            return {
                "status": status,
                "message": f"Run is {status}, cannot import yet",
                "results": []
            }
        
        results = self.get_dataset_items(dataset_id, limit=2000)
        
        return {
            "status": status,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "total_results": len(results),
            "results": results
        }


apify_service = ApifyService()
