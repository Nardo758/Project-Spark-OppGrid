"""
Location validation utilities to prevent data mismatches.
Provides coordinate validation, state verification, and location normalization.
"""
import logging
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)

STATE_ABBREVIATIONS = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}

STATE_BOUNDING_BOXES = {
    "AL": {"min_lat": 30.22, "max_lat": 35.01, "min_lng": -88.47, "max_lng": -84.89},
    "AK": {"min_lat": 51.21, "max_lat": 71.40, "min_lng": -179.15, "max_lng": -129.98},
    "AZ": {"min_lat": 31.33, "max_lat": 37.00, "min_lng": -114.81, "max_lng": -109.05},
    "AR": {"min_lat": 33.00, "max_lat": 36.50, "min_lng": -94.62, "max_lng": -89.64},
    "CA": {"min_lat": 32.53, "max_lat": 42.01, "min_lng": -124.41, "max_lng": -114.13},
    "CO": {"min_lat": 36.99, "max_lat": 41.00, "min_lng": -109.05, "max_lng": -102.04},
    "CT": {"min_lat": 40.95, "max_lat": 42.05, "min_lng": -73.73, "max_lng": -71.79},
    "DE": {"min_lat": 38.45, "max_lat": 39.84, "min_lng": -75.79, "max_lng": -75.05},
    "FL": {"min_lat": 24.52, "max_lat": 31.00, "min_lng": -87.63, "max_lng": -80.03},
    "GA": {"min_lat": 30.36, "max_lat": 35.00, "min_lng": -85.61, "max_lng": -80.84},
    "HI": {"min_lat": 18.91, "max_lat": 22.24, "min_lng": -160.25, "max_lng": -154.81},
    "ID": {"min_lat": 41.99, "max_lat": 49.00, "min_lng": -117.24, "max_lng": -111.04},
    "IL": {"min_lat": 36.97, "max_lat": 42.51, "min_lng": -91.51, "max_lng": -87.02},
    "IN": {"min_lat": 37.77, "max_lat": 41.76, "min_lng": -88.10, "max_lng": -84.78},
    "IA": {"min_lat": 40.38, "max_lat": 43.50, "min_lng": -96.64, "max_lng": -90.14},
    "KS": {"min_lat": 36.99, "max_lat": 40.00, "min_lng": -102.05, "max_lng": -94.59},
    "KY": {"min_lat": 36.50, "max_lat": 39.15, "min_lng": -89.57, "max_lng": -81.96},
    "LA": {"min_lat": 28.93, "max_lat": 33.02, "min_lng": -94.04, "max_lng": -88.82},
    "ME": {"min_lat": 43.06, "max_lat": 47.46, "min_lng": -71.08, "max_lng": -66.95},
    "MD": {"min_lat": 37.91, "max_lat": 39.72, "min_lng": -79.49, "max_lng": -75.05},
    "MA": {"min_lat": 41.24, "max_lat": 42.89, "min_lng": -73.51, "max_lng": -69.93},
    "MI": {"min_lat": 41.70, "max_lat": 48.19, "min_lng": -90.42, "max_lng": -82.42},
    "MN": {"min_lat": 43.50, "max_lat": 49.38, "min_lng": -97.24, "max_lng": -89.49},
    "MS": {"min_lat": 30.17, "max_lat": 35.00, "min_lng": -91.66, "max_lng": -88.10},
    "MO": {"min_lat": 35.99, "max_lat": 40.61, "min_lng": -95.77, "max_lng": -89.10},
    "MT": {"min_lat": 44.36, "max_lat": 49.00, "min_lng": -116.05, "max_lng": -104.04},
    "NE": {"min_lat": 39.99, "max_lat": 43.00, "min_lng": -104.05, "max_lng": -95.31},
    "NV": {"min_lat": 35.00, "max_lat": 42.00, "min_lng": -120.00, "max_lng": -114.04},
    "NH": {"min_lat": 42.70, "max_lat": 45.31, "min_lng": -72.56, "max_lng": -70.70},
    "NJ": {"min_lat": 38.93, "max_lat": 41.36, "min_lng": -75.56, "max_lng": -73.89},
    "NM": {"min_lat": 31.33, "max_lat": 37.00, "min_lng": -109.05, "max_lng": -103.00},
    "NY": {"min_lat": 40.50, "max_lat": 45.02, "min_lng": -79.76, "max_lng": -71.86},
    "NC": {"min_lat": 33.84, "max_lat": 36.59, "min_lng": -84.32, "max_lng": -75.46},
    "ND": {"min_lat": 45.94, "max_lat": 49.00, "min_lng": -104.05, "max_lng": -96.55},
    "OH": {"min_lat": 38.40, "max_lat": 42.32, "min_lng": -84.82, "max_lng": -80.52},
    "OK": {"min_lat": 33.62, "max_lat": 37.00, "min_lng": -103.00, "max_lng": -94.43},
    "OR": {"min_lat": 41.99, "max_lat": 46.29, "min_lng": -124.57, "max_lng": -116.46},
    "PA": {"min_lat": 39.72, "max_lat": 42.27, "min_lng": -80.52, "max_lng": -74.69},
    "RI": {"min_lat": 41.15, "max_lat": 42.02, "min_lng": -71.86, "max_lng": -71.12},
    "SC": {"min_lat": 32.03, "max_lat": 35.22, "min_lng": -83.35, "max_lng": -78.54},
    "SD": {"min_lat": 42.48, "max_lat": 45.95, "min_lng": -104.06, "max_lng": -96.44},
    "TN": {"min_lat": 34.98, "max_lat": 36.68, "min_lng": -90.31, "max_lng": -81.65},
    "TX": {"min_lat": 25.84, "max_lat": 36.50, "min_lng": -106.65, "max_lng": -93.51},
    "UT": {"min_lat": 36.99, "max_lat": 42.00, "min_lng": -114.05, "max_lng": -109.04},
    "VT": {"min_lat": 42.73, "max_lat": 45.02, "min_lng": -73.44, "max_lng": -71.46},
    "VA": {"min_lat": 36.54, "max_lat": 39.47, "min_lng": -83.68, "max_lng": -75.24},
    "WA": {"min_lat": 45.54, "max_lat": 49.00, "min_lng": -124.85, "max_lng": -116.92},
    "WV": {"min_lat": 37.20, "max_lat": 40.64, "min_lng": -82.64, "max_lng": -77.72},
    "WI": {"min_lat": 42.49, "max_lat": 47.08, "min_lng": -92.89, "max_lng": -86.25},
    "WY": {"min_lat": 40.99, "max_lat": 45.01, "min_lng": -111.06, "max_lng": -104.05},
    "DC": {"min_lat": 38.79, "max_lat": 38.99, "min_lng": -77.12, "max_lng": -76.91},
}

STATE_CENTER_COORDS = {
    "AL": {"lat": 32.3182, "lng": -86.9023},
    "AK": {"lat": 64.2008, "lng": -152.4937},
    "AZ": {"lat": 34.0489, "lng": -111.0937},
    "AR": {"lat": 34.7465, "lng": -92.2896},
    "CA": {"lat": 36.7783, "lng": -119.4179},
    "CO": {"lat": 39.5501, "lng": -105.7821},
    "CT": {"lat": 41.6032, "lng": -73.0877},
    "DE": {"lat": 38.9108, "lng": -75.5277},
    "FL": {"lat": 27.6648, "lng": -81.5158},
    "GA": {"lat": 32.1656, "lng": -82.9001},
    "HI": {"lat": 19.8968, "lng": -155.5828},
    "ID": {"lat": 44.0682, "lng": -114.7420},
    "IL": {"lat": 40.6331, "lng": -89.3985},
    "IN": {"lat": 40.2672, "lng": -86.1349},
    "IA": {"lat": 41.8780, "lng": -93.0977},
    "KS": {"lat": 39.0119, "lng": -98.4842},
    "KY": {"lat": 37.8393, "lng": -84.2700},
    "LA": {"lat": 30.9843, "lng": -91.9623},
    "ME": {"lat": 45.2538, "lng": -69.4455},
    "MD": {"lat": 39.0458, "lng": -76.6413},
    "MA": {"lat": 42.4072, "lng": -71.3824},
    "MI": {"lat": 44.3148, "lng": -85.6024},
    "MN": {"lat": 46.7296, "lng": -94.6859},
    "MS": {"lat": 32.3547, "lng": -89.3985},
    "MO": {"lat": 37.9643, "lng": -91.8318},
    "MT": {"lat": 46.8797, "lng": -110.3626},
    "NE": {"lat": 41.4925, "lng": -99.9018},
    "NV": {"lat": 38.8026, "lng": -116.4194},
    "NH": {"lat": 43.1939, "lng": -71.5724},
    "NJ": {"lat": 40.0583, "lng": -74.4057},
    "NM": {"lat": 34.5199, "lng": -105.8701},
    "NY": {"lat": 40.7128, "lng": -74.0060},
    "NC": {"lat": 35.7596, "lng": -79.0193},
    "ND": {"lat": 47.5515, "lng": -101.0020},
    "OH": {"lat": 40.4173, "lng": -82.9071},
    "OK": {"lat": 35.4676, "lng": -97.5164},
    "OR": {"lat": 43.8041, "lng": -120.5542},
    "PA": {"lat": 41.2033, "lng": -77.1945},
    "RI": {"lat": 41.5801, "lng": -71.4774},
    "SC": {"lat": 33.8361, "lng": -81.1637},
    "SD": {"lat": 43.9695, "lng": -99.9018},
    "TN": {"lat": 35.5175, "lng": -86.5804},
    "TX": {"lat": 31.9686, "lng": -99.9018},
    "UT": {"lat": 39.3210, "lng": -111.0937},
    "VT": {"lat": 44.5588, "lng": -72.5778},
    "VA": {"lat": 37.4316, "lng": -78.6569},
    "WA": {"lat": 47.7511, "lng": -120.7401},
    "WV": {"lat": 38.5976, "lng": -80.4549},
    "WI": {"lat": 43.7844, "lng": -88.7879},
    "WY": {"lat": 43.0760, "lng": -107.2903},
    "DC": {"lat": 38.9072, "lng": -77.0369},
}

CITY_COORDS = {
    ("miami", "FL"): {"lat": 25.7617, "lng": -80.1918},
    ("orlando", "FL"): {"lat": 28.5383, "lng": -81.3792},
    ("tampa", "FL"): {"lat": 27.9506, "lng": -82.4572},
    ("jacksonville", "FL"): {"lat": 30.3322, "lng": -81.6557},
    ("fort walton beach", "FL"): {"lat": 30.4057, "lng": -86.6189},
    ("west palm beach", "FL"): {"lat": 26.7153, "lng": -80.0534},
    ("fort lauderdale", "FL"): {"lat": 26.1224, "lng": -80.1373},
    ("pensacola", "FL"): {"lat": 30.4213, "lng": -87.2169},
    ("tallahassee", "FL"): {"lat": 30.4383, "lng": -84.2807},
    ("houston", "TX"): {"lat": 29.7604, "lng": -95.3698},
    ("dallas", "TX"): {"lat": 32.7767, "lng": -96.7970},
    ("austin", "TX"): {"lat": 30.2672, "lng": -97.7431},
    ("san antonio", "TX"): {"lat": 29.4241, "lng": -98.4936},
    ("fort worth", "TX"): {"lat": 32.7555, "lng": -97.3308},
    ("el paso", "TX"): {"lat": 31.7619, "lng": -106.4850},
    ("phoenix", "AZ"): {"lat": 33.4484, "lng": -112.0740},
    ("tucson", "AZ"): {"lat": 32.2226, "lng": -110.9747},
    ("los angeles", "CA"): {"lat": 34.0522, "lng": -118.2437},
    ("san francisco", "CA"): {"lat": 37.7749, "lng": -122.4194},
    ("san diego", "CA"): {"lat": 32.7157, "lng": -117.1611},
    ("san jose", "CA"): {"lat": 37.3382, "lng": -121.8863},
    ("sacramento", "CA"): {"lat": 38.5816, "lng": -121.4944},
    ("new york", "NY"): {"lat": 40.7128, "lng": -74.0060},
    ("buffalo", "NY"): {"lat": 42.8864, "lng": -78.8784},
    ("albany", "NY"): {"lat": 42.6526, "lng": -73.7562},
    ("chicago", "IL"): {"lat": 41.8781, "lng": -87.6298},
    ("seattle", "WA"): {"lat": 47.6062, "lng": -122.3321},
    ("portland", "OR"): {"lat": 45.5152, "lng": -122.6784},
    ("denver", "CO"): {"lat": 39.7392, "lng": -104.9903},
    ("atlanta", "GA"): {"lat": 33.7490, "lng": -84.3880},
    ("boston", "MA"): {"lat": 42.3601, "lng": -71.0589},
    ("nashville", "TN"): {"lat": 36.1627, "lng": -86.7816},
    ("memphis", "TN"): {"lat": 35.1495, "lng": -90.0490},
    ("charlotte", "NC"): {"lat": 35.2271, "lng": -80.8431},
    ("raleigh", "NC"): {"lat": 35.7796, "lng": -78.6382},
    ("las vegas", "NV"): {"lat": 36.1699, "lng": -115.1398},
    ("philadelphia", "PA"): {"lat": 39.9526, "lng": -75.1652},
    ("pittsburgh", "PA"): {"lat": 40.4406, "lng": -79.9959},
    ("minneapolis", "MN"): {"lat": 44.9778, "lng": -93.2650},
    ("detroit", "MI"): {"lat": 42.3314, "lng": -83.0458},
    ("indianapolis", "IN"): {"lat": 39.7684, "lng": -86.1581},
    ("columbus", "OH"): {"lat": 39.9612, "lng": -82.9988},
    ("cleveland", "OH"): {"lat": 41.4993, "lng": -81.6944},
    ("kansas city", "MO"): {"lat": 39.0997, "lng": -94.5786},
    ("st louis", "MO"): {"lat": 38.6270, "lng": -90.1994},
    ("new orleans", "LA"): {"lat": 29.9511, "lng": -90.0715},
    ("baltimore", "MD"): {"lat": 39.2904, "lng": -76.6122},
    ("washington", "DC"): {"lat": 38.9072, "lng": -77.0369},
}

US_CENTER = {"lat": 39.8283, "lng": -98.5795}


def normalize_state(state: Optional[str]) -> Optional[str]:
    """Convert state name or abbreviation to standard 2-letter code."""
    if not state:
        return None
    
    state_clean = state.strip()
    
    if len(state_clean) == 2:
        return state_clean.upper()
    
    abbrev = STATE_ABBREVIATIONS.get(state_clean.lower())
    if abbrev:
        return abbrev
    
    logger.warning(f"[LOCATION] Unknown state format: '{state}' - could not normalize")
    return state_clean.upper()[:2] if len(state_clean) >= 2 else None


def validate_coordinates_in_state(
    lat: float, 
    lng: float, 
    expected_state: str,
    context: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Validate that coordinates fall within the expected state's bounding box.
    Returns (is_valid, warning_message).
    """
    state_abbrev = normalize_state(expected_state)
    if not state_abbrev:
        return True, None
    
    bounds = STATE_BOUNDING_BOXES.get(state_abbrev)
    if not bounds:
        return True, None
    
    in_bounds = (
        bounds["min_lat"] <= lat <= bounds["max_lat"] and
        bounds["min_lng"] <= lng <= bounds["max_lng"]
    )
    
    if not in_bounds:
        actual_state = find_state_for_coordinates(lat, lng)
        warning = (
            f"[LOCATION MISMATCH] Coordinates ({lat}, {lng}) are outside {state_abbrev} bounds. "
            f"Expected state: {state_abbrev}, Actual state: {actual_state or 'unknown'}. "
            f"Context: {context}"
        )
        logger.warning(warning)
        return False, warning
    
    return True, None


def find_state_for_coordinates(lat: float, lng: float) -> Optional[str]:
    """Find which US state contains the given coordinates."""
    for state, bounds in STATE_BOUNDING_BOXES.items():
        if (bounds["min_lat"] <= lat <= bounds["max_lat"] and
            bounds["min_lng"] <= lng <= bounds["max_lng"]):
            return state
    return None


def get_location_coords(
    city: Optional[str] = None,
    state: Optional[str] = None,
    context: str = ""
) -> Dict[str, float]:
    """
    Get coordinates for a location with fallback hierarchy.
    Logs warnings when using fallbacks.
    """
    state_abbrev = normalize_state(state) if state else None
    
    if city and state_abbrev:
        city_key = (city.lower().strip(), state_abbrev)
        if city_key in CITY_COORDS:
            return CITY_COORDS[city_key]
        logger.info(f"[LOCATION FALLBACK] City '{city}, {state_abbrev}' not in known cities, falling back to state center. Context: {context}")
    
    if city and not state_abbrev:
        city_lower = city.lower().strip()
        for (c, s), coords in CITY_COORDS.items():
            if c == city_lower:
                logger.info(f"[LOCATION RESOLVED] City-only '{city}' matched to '{c}, {s}'. Context: {context}")
                return coords

    if state_abbrev and state_abbrev in STATE_CENTER_COORDS:
        if city:
            logger.info(f"[LOCATION FALLBACK] Using state center for '{state_abbrev}' (city '{city}' unknown). Context: {context}")
        return STATE_CENTER_COORDS[state_abbrev]
    
    logger.warning(f"[LOCATION FALLBACK] No location data available, using US center. City: '{city}', State: '{state}'. Context: {context}")
    return US_CENTER


def validate_geocoding_result(
    geocoded_lat: float,
    geocoded_lng: float,
    expected_city: Optional[str],
    expected_state: Optional[str],
    context: str = ""
) -> Dict[str, Any]:
    """
    Validate geocoding results match expected location.
    Returns validation result with warnings if mismatch detected.
    """
    result = {
        "valid": True,
        "warnings": [],
        "actual_state": None,
        "expected_state": normalize_state(expected_state),
    }
    
    if expected_state:
        is_valid, warning = validate_coordinates_in_state(
            geocoded_lat, geocoded_lng, expected_state, context
        )
        if not is_valid:
            result["valid"] = False
            result["warnings"].append(warning)
            result["actual_state"] = find_state_for_coordinates(geocoded_lat, geocoded_lng)
    
    return result


def parse_address_location(address: str) -> Dict[str, Optional[str]]:
    """
    Parse city and state from a full address string.
    Handles formats like:
    - "7550 Okeechobee Blvd, West Palm Beach, FL 33411"
    - "Fort Walton Beach, FL"
    - "Miami, Florida"
    """
    result = {"city": None, "state": None, "zip_code": None}
    
    if not address:
        return result
    
    parts = [p.strip() for p in address.split(",")]
    
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        tokens = last_part.split()
        
        if tokens:
            if len(tokens[-1]) == 5 and tokens[-1].isdigit():
                result["zip_code"] = tokens[-1]
                tokens = tokens[:-1]
            elif len(tokens[-1]) == 10 and "-" in tokens[-1]:
                result["zip_code"] = tokens[-1]
                tokens = tokens[:-1]
        
        if tokens:
            potential_state = tokens[0] if len(tokens) == 1 else " ".join(tokens)
            normalized = normalize_state(potential_state)
            if normalized:
                result["state"] = normalized
        
        if len(parts) >= 2:
            city_part = parts[-2].strip() if result["state"] else parts[-1].strip()
            if city_part and not city_part[0].isdigit():
                result["city"] = city_part
    
    return result


def log_location_resolution(
    input_location: str,
    resolved_lat: float,
    resolved_lng: float,
    resolution_method: str,
    context: str = ""
) -> None:
    """Log how a location was resolved for debugging and auditing."""
    logger.info(
        f"[LOCATION RESOLVED] Input: '{input_location}' -> "
        f"({resolved_lat:.4f}, {resolved_lng:.4f}) via {resolution_method}. "
        f"Context: {context}"
    )
