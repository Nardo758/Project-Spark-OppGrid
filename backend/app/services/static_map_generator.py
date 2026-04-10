"""
StaticMapGenerator — server-side static map images for embedded report HTML.

Generates PNG images via the Mapbox Static Images API and returns them as
base64-encoded data URIs ready for <img src="data:image/png;base64,..."> embedding.

Two map types are produced for Business Plan reports:
  1. competitor_density_map — pins for all competitors within 5-mile radius
  2. location_overview_map  — clean context map of the target city/area

Both degrade gracefully: if the API call fails or the token is absent, the
method returns "" and the caller omits the <figure> block.
"""

import base64
import logging
import os
from datetime import date
from typing import List, Optional, Tuple

import requests

from app.services.location_utils import get_location_coords

logger = logging.getLogger(__name__)

MAPBOX_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")

# Brand colours (CSS hex without the #)
EMERALD = "10B981"
NAVY = "0F172A"


def _fetch_image_as_base64(url: str, timeout: int = 12) -> str:
    """Download a URL and return its content as a base64 string. Returns '' on error."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode("utf-8")
    except Exception as exc:
        logger.warning(f"[StaticMap] Image fetch failed: {exc}")
        return ""


def _mapbox_static_url(
    style: str,
    overlay: str,
    center: str,
    width: int,
    height: int,
) -> str:
    """Build a Mapbox Static Images API URL.

    center: "{lon},{lat},{zoom}" or "auto"
    overlay: comma-separated pin descriptors, e.g. "pin-l+0F172A(-97.74,30.26)"
    """
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/{style}/static"
        f"/{overlay}/{center}/{width}x{height}"
        f"?access_token={MAPBOX_TOKEN}"
    )


def _build_pin_overlay(
    competitors: List[Tuple[float, float, str]],
    center_lat: float,
    center_lng: float,
    max_pins: int = 14,
) -> str:
    """
    Build a Mapbox overlay string with competitor pins + one center pin.

    Mapbox limits the overlay string length; we cap competitor pins at max_pins
    so the URL stays within the ~8 KB limit.

    Args:
        competitors: list of (lat, lng, name) tuples
        center_lat/center_lng: the target business location
        max_pins: max competitor markers to include

    Returns:
        Comma-separated overlay segment for the Mapbox Static API URL.
    """
    parts: List[str] = []

    # Center marker (navy, large pin)
    parts.append(f"pin-l+{NAVY}({center_lng:.5f},{center_lat:.5f})")

    # Competitor markers (emerald, small pin)
    for lat, lng, _name in competitors[:max_pins]:
        parts.append(f"pin-s+{EMERALD}({lng:.5f},{lat:.5f})")

    return ",".join(parts)


class StaticMapGenerator:
    """
    Generates embedded static map images for Business Plan reports.

    Methods are async to allow direct use inside async FastAPI endpoints
    and the async ReportOrchestrator pipeline.

    Usage:
        gen = StaticMapGenerator()
        html = await gen.competitor_density_map_html(
            business_type="Coffee Shop",
            city="Austin",
            state="TX",
        )
    """

    def __init__(self):
        self._token_available = bool(MAPBOX_TOKEN)

    async def _fetch_competitors(
        self,
        business_type: str,
        lat: float,
        lng: float,
        radius_miles: float = 5.0,
    ) -> List[Tuple[float, float, str]]:
        """
        Async fetch of competitor coordinates via SerpAPI.

        Returns list of (lat, lng, name) tuples.  Returns [] on any error.
        """
        try:
            from app.services.serpapi_service import serpapi_service

            radius_meters = int(radius_miles * 1609.34)
            query = f"{business_type} near {lat:.4f},{lng:.4f}"

            results = await serpapi_service.search_local_businesses(
                query=query,
                lat=lat,
                lng=lng,
                radius_meters=radius_meters,
            )

            competitors: List[Tuple[float, float, str]] = []
            for biz in results.get("local_results", []):
                gps = biz.get("gps_coordinates", {})
                c_lat = gps.get("latitude")
                c_lng = gps.get("longitude")
                name = biz.get("title", "Competitor")
                if c_lat and c_lng:
                    competitors.append((float(c_lat), float(c_lng), name))

            logger.info(
                f"[StaticMap] {len(competitors)} competitors for '{business_type}' "
                f"near {lat:.3f},{lng:.3f}"
            )
            return competitors

        except Exception as exc:
            logger.warning(f"[StaticMap] SerpAPI fetch failed: {exc}")
            return []

    async def competitor_density_map_html(
        self,
        business_type: str,
        city: str,
        state: str,
        radius_miles: float = 5.0,
    ) -> str:
        """
        Generate HTML for a competitor density map (5-mile radius pins).

        Injects into the Market Analysis section of a Business Plan.
        Returns a <figure> block, or "" if generation fails.
        """
        if not self._token_available:
            logger.warning("[StaticMap] MAPBOX_ACCESS_TOKEN not set — skipping competitor map")
            return ""

        coords = get_location_coords(
            city=city,
            state=state,
            context="StaticMapGenerator.competitor_density_map",
        )
        center_lat, center_lng = coords["lat"], coords["lng"]

        competitors = await self._fetch_competitors(
            business_type=business_type,
            lat=center_lat,
            lng=center_lng,
            radius_miles=radius_miles,
        )

        overlay = _build_pin_overlay(competitors, center_lat, center_lng)

        # Use "auto" to fit all markers, fallback to fixed zoom if no competitors
        if competitors:
            center_segment = "auto"
        else:
            center_segment = f"{center_lng:.5f},{center_lat:.5f},12"

        url = _mapbox_static_url(
            style="light-v11",
            overlay=overlay,
            center=center_segment,
            width=800,
            height=450,
        )

        logger.info(f"[StaticMap] Fetching competitor density map for {city}, {state}")
        b64 = _fetch_image_as_base64(url)
        if not b64:
            return ""

        count = len(competitors)
        caption_count = (
            f"{count} direct competitor{'s' if count != 1 else ''}"
            if count
            else "local businesses"
        )
        today = date.today().strftime("%B %Y")

        return (
            f'<figure style="margin:2rem 0;text-align:center;">'
            f'<img src="data:image/png;base64,{b64}" '
            f'alt="Competitive density map — {business_type} within {radius_miles:.0f} miles of {city}, {state}" '
            f'style="max-width:100%;border-radius:6px;border:1px solid #e2e8f0;" />'
            f'<figcaption style="font-size:0.78rem;color:#64748b;margin-top:0.5rem;">'
            f'<strong>Figure: Competitive Density Map</strong> — '
            f'{caption_count} identified within {radius_miles:.0f}-mile radius of {city}, {state}. '
            f'<span style="color:#10B981;">&#9679;</span>&thinsp;competitor&ensp;'
            f'<span style="color:#0F172A;">&#9679;</span>&thinsp;target location. '
            f'Source: Google Maps via OppGrid, {today}.'
            f'</figcaption>'
            f'</figure>'
        )

    async def location_overview_map_html(
        self,
        city: str,
        state: str,
        zoom: int = 11,
    ) -> str:
        """
        Generate HTML for a location overview map for the Executive Summary.

        Returns a <figure> block, or "" if generation fails.
        """
        if not self._token_available:
            return ""

        coords = get_location_coords(
            city=city,
            state=state,
            context="StaticMapGenerator.location_overview_map",
        )
        center_lat, center_lng = coords["lat"], coords["lng"]

        overlay = f"pin-l+{NAVY}({center_lng:.5f},{center_lat:.5f})"
        center_segment = f"{center_lng:.5f},{center_lat:.5f},{zoom}"

        url = _mapbox_static_url(
            style="light-v11",
            overlay=overlay,
            center=center_segment,
            width=800,
            height=300,
        )

        logger.info(f"[StaticMap] Fetching overview map for {city}, {state}")
        b64 = _fetch_image_as_base64(url)
        if not b64:
            return ""

        today = date.today().strftime("%B %Y")

        return (
            f'<figure style="margin:1.5rem 0;text-align:center;">'
            f'<img src="data:image/png;base64,{b64}" '
            f'alt="Location overview map — {city}, {state}" '
            f'style="max-width:100%;border-radius:6px;border:1px solid #e2e8f0;" />'
            f'<figcaption style="font-size:0.78rem;color:#64748b;margin-top:0.5rem;">'
            f'<strong>Figure: Target Market Location</strong> — {city}, {state}. '
            f'Source: Mapbox, {today}.'
            f'</figcaption>'
            f'</figure>'
        )
