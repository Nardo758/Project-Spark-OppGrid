import os
from typing import Optional, List, Dict, Any

try:
    from serpapi import GoogleSearch
except ImportError:
    # serpapi v1.x+ uses a different API; provide a compatibility wrapper
    import serpapi as _serpapi

    class GoogleSearch:
        def __init__(self, params: dict):
            self._params = params

        def get_dict(self) -> dict:
            return _serpapi.search(**self._params)


class SerpAPIService:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def google_search(
        self,
        query: str,
        location: str = None,
        num: int = 10,
        start: int = 0,
        gl: str = "us",
        hl: str = "en"
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise ValueError("SERPAPI_KEY not configured")
        
        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "num": num,
            "start": start,
            "gl": gl,
            "hl": hl
        }
        
        if location:
            params["location"] = location
        
        search = GoogleSearch(params)
        return search.get_dict()
    
    def google_maps_search(
        self,
        query: str,
        ll: str = None,
        location: str = None,
        hl: str = "en",
        type: str = "search"
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise ValueError("SERPAPI_KEY not configured")
        
        params = {
            "api_key": self.api_key,
            "engine": "google_maps",
            "q": query,
            "type": type,
            "hl": hl
        }
        
        if ll:
            params["ll"] = ll
        if location:
            params["location"] = location
        
        search = GoogleSearch(params)
        return search.get_dict()
    
    def google_maps_reviews(
        self,
        data_id: str,
        sort_by: str = "qualityScore",
        hl: str = "en",
        topic_id: str = None,
        next_page_token: str = None
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise ValueError("SERPAPI_KEY not configured")
        
        params = {
            "api_key": self.api_key,
            "engine": "google_maps_reviews",
            "data_id": data_id,
            "sort_by": sort_by,
            "hl": hl
        }
        
        if topic_id:
            params["topic_id"] = topic_id
        if next_page_token:
            params["next_page_token"] = next_page_token
        
        search = GoogleSearch(params)
        return search.get_dict()
    
    def search_places_with_reviews(
        self,
        query: str,
        location: str = None,
        ll: str = None,
        max_places: int = 5,
        reviews_per_place: int = 10
    ) -> List[Dict[str, Any]]:
        if not self.is_configured:
            raise ValueError("SERPAPI_KEY not configured")
        
        places_result = self.google_maps_search(
            query=query,
            location=location,
            ll=ll
        )
        
        local_results = places_result.get("local_results", [])[:max_places]
        
        results = []
        for place in local_results:
            data_id = place.get("data_id")
            if not data_id:
                continue
            
            place_data = {
                "title": place.get("title"),
                "address": place.get("address"),
                "rating": place.get("rating"),
                "reviews_count": place.get("reviews"),
                "data_id": data_id,
                "gps_coordinates": place.get("gps_coordinates"),
                "phone": place.get("phone"),
                "website": place.get("website"),
                "type": place.get("type"),
                "reviews": []
            }
            
            try:
                reviews_result = self.google_maps_reviews(
                    data_id=data_id,
                    sort_by="newestFirst"
                )
                place_data["reviews"] = reviews_result.get("reviews", [])[:reviews_per_place]
            except Exception as e:
                print(f"Error fetching reviews for {place.get('title')}: {e}")
            
            results.append(place_data)
        
        return results
    
    def get_account_info(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {"configured": False, "error": "SERPAPI_KEY not set"}
        
        try:
            params = {
                "api_key": self.api_key
            }
            import requests
            response = requests.get("https://serpapi.com/account", params=params)
            if response.ok:
                data = response.json()
                return {
                    "configured": True,
                    "plan": data.get("plan_name"),
                    "searches_per_month": data.get("searches_per_month"),
                    "this_month_usage": data.get("this_month_usage"),
                    "remaining": data.get("searches_per_month", 0) - data.get("this_month_usage", 0)
                }
            return {"configured": True, "error": "Could not fetch account info"}
        except Exception as e:
            return {"configured": True, "error": str(e)}


serpapi_service = SerpAPIService()
