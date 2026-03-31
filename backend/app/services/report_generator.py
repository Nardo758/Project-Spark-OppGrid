"""
Report Generator Service

Generates tiered opportunity reports:
- Layer 1: Problem Overview ($15/Pro+) 
- Layer 2: Deep Dive Analysis (Business+)
- Layer 3: Execution Package (Business 5/mo or Enterprise)
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

import logging
from app.models.opportunity import Opportunity
from app.models.generated_report import GeneratedReport, ReportType, ReportStatus
from app.models.user import User
from app.services.ai_report_generator import ai_report_generator
from app.services.branding_service import get_user_team_branding, inject_branding_into_report

logger = logging.getLogger(__name__)


MAPBOX_STYLE_SATELLITE = "mapbox/satellite-streets-v11"
MAPBOX_STYLE_DARK = "mapbox/dark-v11"
MAPBOX_STYLE_LIGHT = "mapbox/light-v11"

# Miles to meters conversion
MILES_TO_METERS = 1609.34


def generate_circle_geojson(center_lng: float, center_lat: float, radius_miles: float, color: str = "3b82f6") -> str:
    """Generate a GeoJSON circle for Mapbox static API overlay.
    
    Args:
        center_lng: Center longitude
        center_lat: Center latitude  
        radius_miles: Radius in miles
        color: Hex color (without #)
    
    Returns:
        URL-encoded GeoJSON path string for Mapbox
    """
    import math
    import urllib.parse
    
    # Generate circle points (36 points for smooth circle)
    points = []
    radius_km = radius_miles * 1.60934
    
    for i in range(37):  # 37 to close the circle
        angle = (i * 10) * math.pi / 180
        # Approximate lat/lng offset
        dlat = (radius_km / 111.32) * math.cos(angle)
        dlng = (radius_km / (111.32 * math.cos(math.radians(center_lat)))) * math.sin(angle)
        points.append([round(center_lng + dlng, 6), round(center_lat + dlat, 6)])
    
    geojson = {
        "type": "Feature",
        "properties": {
            "stroke": f"#{color}",
            "stroke-width": 2,
            "stroke-opacity": 0.8,
            "fill": f"#{color}",
            "fill-opacity": 0.15
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [points]
        }
    }
    
    return urllib.parse.quote(str(geojson).replace("'", '"'), safe='')


def build_static_map_with_radius(
    center_lng: float,
    center_lat: float,
    radii: List[float] = [3, 5],  # Miles
    zoom: int = 11,
    width: int = 800,
    height: int = 500,
    markers: Optional[List[Dict]] = None,
    style: str = MAPBOX_STYLE_LIGHT,
    recommended_sites: Optional[List[Dict]] = None
) -> Optional[str]:
    """Build a static map with radius circles for location reports.
    
    Args:
        center_lng: Center longitude
        center_lat: Center latitude
        radii: List of radius values in miles (default [3, 5])
        zoom: Zoom level
        width: Image width
        height: Image height
        markers: Additional markers
        style: Mapbox style
        recommended_sites: List of {lat, lng, name} for recommended locations
    
    Returns:
        Static map URL with radius circles
    """
    token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    if not token:
        return None
    
    overlays = []
    
    # Add radius circles (outer first so inner is on top)
    radius_colors = {
        5: "94a3b8",  # Gray for 5 mile
        3: "3b82f6",  # Blue for 3 mile
    }
    
    for radius in sorted(radii, reverse=True):
        color = radius_colors.get(radius, "3b82f6")
        circle_geojson = generate_circle_geojson(center_lng, center_lat, radius, color)
        overlays.append(f"geojson({circle_geojson})")
    
    # Add center marker
    overlays.append(f"pin-l-star+ef4444({center_lng},{center_lat})")
    
    # Add recommended site markers
    if recommended_sites:
        for i, site in enumerate(recommended_sites[:5]):
            lng = site.get("lng") or site.get("longitude")
            lat = site.get("lat") or site.get("latitude")
            if lng and lat:
                label = chr(97 + i)  # a, b, c, d, e
                overlays.append(f"pin-s-{label}+22c55e({lng},{lat})")
    
    # Add custom markers
    if markers:
        for m in markers[:10]:
            color = m.get("color", "ff5544")
            lng = m.get("lng", m.get("longitude"))
            lat = m.get("lat", m.get("latitude"))
            if lng and lat:
                overlays.append(f"pin-s+{color}({lng},{lat})")
    
    overlay_str = ",".join(overlays) + "/" if overlays else ""
    
    url = f"https://api.mapbox.com/styles/v1/{style}/static/{overlay_str}{center_lng},{center_lat},{zoom}/{width}x{height}@2x?access_token={token}"
    return url


def build_static_map_url(
    center_lng: float,
    center_lat: float,
    zoom: int = 4,
    width: int = 600,
    height: int = 300,
    markers: Optional[List[Dict]] = None,
    style: str = MAPBOX_STYLE_SATELLITE,
    use_satellite: bool = True
) -> Optional[str]:
    """Build a Mapbox Static Images API URL for embedding in reports.
    
    Args:
        center_lng: Center longitude
        center_lat: Center latitude
        zoom: Zoom level (1-22)
        width: Image width in pixels (max 1280)
        height: Image height in pixels (max 1280)
        markers: List of marker dicts with lat, lng, color keys
        style: Mapbox style ID (defaults to satellite-streets-v11)
        use_satellite: If True, uses satellite imagery with labels
    
    Returns:
        Static map URL or None if MAPBOX_ACCESS_TOKEN not set
    """
    token = os.environ.get("MAPBOX_ACCESS_TOKEN")
    if not token:
        return None
    
    if use_satellite:
        style = MAPBOX_STYLE_SATELLITE
    
    overlay = ""
    if markers:
        marker_parts = []
        for m in markers[:20]:
            color = m.get("color", "ff5544")
            lng = m.get("lng", m.get("longitude"))
            lat = m.get("lat", m.get("latitude"))
            label = m.get("label", "")
            if lng is not None and lat is not None:
                if label:
                    marker_parts.append(f"pin-s-{label}+{color}({lng},{lat})")
                else:
                    marker_parts.append(f"pin-s+{color}({lng},{lat})")
        if marker_parts:
            overlay = ",".join(marker_parts) + "/"
    
    url = f"https://api.mapbox.com/styles/v1/{style}/static/{overlay}{center_lng},{center_lat},{zoom}/{width}x{height}@2x?access_token={token}"
    return url


class ReportGenerator:
    """Base class for generating opportunity reports."""
    
    TIER_REQUIREMENTS = {
        ReportType.LAYER_1_OVERVIEW: ["pro", "business", "enterprise"],
        ReportType.LAYER_2_DEEP_DIVE: ["business", "enterprise"],
        ReportType.LAYER_3_EXECUTION: ["business", "enterprise"],
    }
    
    TIER_PRICES = {
        ReportType.LAYER_1_OVERVIEW: 1500,
        ReportType.LAYER_2_DEEP_DIVE: None,
        ReportType.LAYER_3_EXECUTION: None,
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_city_fallback_coords(self, city: Optional[str], state: Optional[str]) -> Dict[str, float]:
        """Get fallback coordinates for a city/state when opportunity lacks lat/lng."""
        from .location_utils import get_location_coords
        
        return get_location_coords(
            city=city,
            state=state,
            context="report_generator._get_city_fallback_coords"
        )
    
    def _validate_opportunity_coords(self, opp: Opportunity) -> Dict[str, Any]:
        """
        Validate opportunity coordinates against expected state.
        Returns validated coordinates or corrected fallback.
        """
        from .location_utils import validate_coordinates_in_state, get_location_coords
        import logging
        logger = logging.getLogger(__name__)
        
        result = {
            "lat": None,
            "lng": None,
            "valid": False,
            "source": "none",
            "warning": None
        }
        
        if opp.latitude and opp.longitude:
            if opp.region:
                is_valid, warning = validate_coordinates_in_state(
                    float(opp.latitude), float(opp.longitude), opp.region,
                    context=f"Report generation for opportunity {opp.id}"
                )
                if not is_valid:
                    logger.warning(f"Opportunity {opp.id} has invalid coordinates for state {opp.region}: {warning}")
                    fallback = get_location_coords(opp.city, opp.region, context=f"Report fallback for opp {opp.id}")
                    result["lat"] = fallback["lat"]
                    result["lng"] = fallback["lng"]
                    result["valid"] = True
                    result["source"] = "fallback_corrected"
                    result["warning"] = warning
                    return result
            
            result["lat"] = float(opp.latitude)
            result["lng"] = float(opp.longitude)
            result["valid"] = True
            result["source"] = "opportunity"
            return result
        
        fallback = self._get_city_fallback_coords(opp.city, opp.region)
        result["lat"] = fallback["lat"]
        result["lng"] = fallback["lng"]
        result["valid"] = True
        result["source"] = "city_fallback"
        return result
    
    def check_entitlement(self, user: User, report_type: ReportType) -> Dict[str, Any]:
        """Check if user has access to generate this report type."""
        user_tier = 'free'
        if user.subscription and user.subscription.tier:
            tier_val = user.subscription.tier
            user_tier = tier_val.value.lower() if hasattr(tier_val, 'value') else str(tier_val).lower()
        
        allowed_tiers = self.TIER_REQUIREMENTS.get(report_type, [])
        
        if user.is_admin:
            return {"allowed": True, "reason": "admin_access"}
        
        if user_tier in allowed_tiers:
            return {"allowed": True, "reason": "tier_access"}
        
        return {
            "allowed": False, 
            "reason": "tier_required",
            "required_tiers": allowed_tiers,
            "user_tier": user_tier,
            "price": self.TIER_PRICES.get(report_type)
        }
    
    def generate_layer1_report(self, opportunity: Opportunity, user: User, demographics: Optional[Dict] = None) -> GeneratedReport:
        """Generate Layer 1: Problem Overview report."""
        start_time = datetime.utcnow()
        
        report = GeneratedReport(
            user_id=user.id,
            opportunity_id=opportunity.id,
            report_type=ReportType.LAYER_1_OVERVIEW,
            status=ReportStatus.GENERATING,
            title=f"Problem Overview: {opportunity.title}",
        )
        self.db.add(report)
        self.db.commit()
        
        try:
            content = self._build_layer1_content(opportunity, demographics)
            summary = self._build_layer1_summary(opportunity)
            
            branding = get_user_team_branding(user, self.db)
            if branding:
                content = inject_branding_into_report(content, branding)
            
            report.content = content
            report.summary = summary
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            report.generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            report.confidence_score = opportunity.ai_opportunity_score or 75
            
            self.db.commit()
            self.db.refresh(report)
            
            return report
        except Exception as e:
            logger.error(f"Failed to generate Layer 1 report for opportunity {opportunity.id}: {e}")
            report.status = ReportStatus.FAILED
            report.error_type = "generation_error"
            report.error_message = str(e)[:500]
            report.generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.db.commit()
            self.db.refresh(report)
            return report
    
    def _build_layer1_content(self, opp: Opportunity, demographics: Optional[Dict] = None) -> str:
        """Build Layer 1 report content in HTML format with AI-generated insights."""
        market_size = opp.ai_market_size_estimate or opp.market_size or "Under Analysis"
        target_audience = opp.ai_target_audience or "General consumers"
        competition = opp.ai_competition_level or "Medium"
        urgency = opp.ai_urgency_level or "Medium"
        score = opp.ai_opportunity_score or opp.severity * 20
        
        problem_statement = opp.ai_problem_statement or opp.description
        pain_points = opp.ai_competitive_advantages or ["Market gap exists", "User pain point validated"]
        risks = opp.ai_key_risks or ["Market timing", "Competition"]
        
        opp_dict = {
            'title': opp.title,
            'category': opp.category,
            'city': opp.city,
            'region': opp.region,
            'description': opp.description or '',
            'market_size': market_size,
            'score': score,
            'target_audience': target_audience,
            'competition_level': competition,
            'signals': str(pain_points),
        }
        
        try:
            ai_executive_summary = ai_report_generator.generate_executive_summary(opp_dict)
        except Exception as e:
            logger.warning(f"Failed to generate AI executive summary: {e}")
            ai_executive_summary = opp.ai_summary or (opp.description[:500] if opp.description else 'Analysis in progress...')
        
        try:
            ai_problem_analysis = ai_report_generator.generate_problem_analysis(opp_dict)
            ai_problem_analysis_html = ai_problem_analysis.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '')
        except Exception as e:
            logger.warning(f"Failed to generate AI problem analysis: {e}")
            ai_problem_analysis_html = f"<p>{problem_statement}</p>"
        
        satellite_map_section = self._build_satellite_map_section(opp)
        target_customer_section = self._build_target_customer_section(opp, demographics)
        geographic_heat_section = self._build_geographic_heat_section(opp)
        signal_quality_section = self._build_signal_quality_section(opp)
        
        html_content = f"""
<div class="report-layer1">
    <header class="report-header">
        <h1>Problem Overview Report</h1>
        <div class="report-meta">
            <span class="category">{opp.category}</span>
            <span class="date">Generated: {datetime.utcnow().strftime('%B %d, %Y')}</span>
        </div>
    </header>
    
    {satellite_map_section}
    
    <section class="executive-summary">
        <h2>Executive Summary</h2>
        <div class="opportunity-title">{opp.title}</div>
        <div class="ai-content">
            <p>{ai_executive_summary}</p>
        </div>
        <div class="score-badge">
            <span class="score">{score}</span>
            <span class="label">Opportunity Score</span>
        </div>
    </section>
    
    <section class="lean-canvas-analysis">
        <h2>Lean Canvas Problem Analysis</h2>
        <div class="ai-content">
            {ai_problem_analysis_html}
        </div>
    </section>
    
    <section class="pain-metrics-section">
        <h2>Pain Metrics</h2>
        <div class="pain-metrics">
            <div class="metric">
                <span class="value">{opp.ai_pain_intensity or opp.severity}/10</span>
                <span class="label">Pain Intensity</span>
            </div>
            <div class="metric">
                <span class="value capitalize">{urgency}</span>
                <span class="label">Urgency Level</span>
            </div>
            <div class="metric">
                <span class="value">{opp.validation_count}</span>
                <span class="label">Validations</span>
            </div>
        </div>
    </section>
    
    <section class="market-snapshot">
        <h2>Market Snapshot</h2>
        <div class="market-grid">
            <div class="market-card">
                <span class="label">Market Size</span>
                <span class="value">{market_size}</span>
            </div>
            <div class="market-card">
                <span class="label">Target Audience</span>
                <span class="value">{target_audience}</span>
            </div>
            <div class="market-card">
                <span class="label">Competition</span>
                <span class="value capitalize">{competition}</span>
            </div>
            <div class="market-card">
                <span class="label">Geographic Focus</span>
                <span class="value">{opp.city or opp.region or opp.country or 'National'}</span>
            </div>
        </div>
    </section>
    
    {target_customer_section}
    
    {geographic_heat_section}
    
    {signal_quality_section}
    
    <section class="validation-signals">
        <h2>Validation Signals</h2>
        <ul class="signal-list">
            {''.join(f'<li class="signal-item positive">{point}</li>' for point in pain_points[:5])}
        </ul>
    </section>
    
    <section class="key-risks">
        <h2>Key Risks</h2>
        <ul class="risk-list">
            {''.join(f'<li class="risk-item">{risk}</li>' for risk in risks[:5])}
        </ul>
    </section>
    
    <section class="next-steps">
        <h2>Recommended Next Steps</h2>
        <ol class="steps-list">
            <li>Conduct deeper market validation through customer interviews</li>
            <li>Analyze competitive landscape for positioning opportunities</li>
            <li>Define minimum viable product (MVP) scope</li>
            <li>Upgrade to Layer 2 Deep Dive for comprehensive analysis</li>
        </ol>
    </section>
    
    <footer class="report-footer">
        <p>This report was generated by OppGrid's AI-powered analysis engine using Claude.</p>
        <p>For comprehensive market analysis with trade area insights, upgrade to Layer 2 Deep Dive.</p>
    </footer>
</div>
"""
        return html_content
    
    def _build_satellite_map_section(self, opp: Opportunity) -> str:
        """Build satellite map section for the opportunity location."""
        coords = self._validate_opportunity_coords(opp)
        lat = coords["lat"]
        lng = coords["lng"]
        
        if not lat or not lng:
            return """
    <section class="map-section">
        <h2>Geographic Context</h2>
        <div class="map-placeholder">
            <p>Location data pending geographic analysis.</p>
        </div>
    </section>
"""
        
        map_url = build_static_map_url(
            center_lng=lng,
            center_lat=lat,
            zoom=12,
            width=800,
            height=400,
            markers=[{"lat": lat, "lng": lng, "color": "ff5544", "label": "o"}],
            use_satellite=True
        )
        
        if not map_url:
            return """
    <section class="map-section">
        <h2>Geographic Context</h2>
        <div class="map-placeholder">
            <p>Map visualization requires Mapbox configuration.</p>
        </div>
    </section>
"""
        
        location_name = f"{opp.city}, {opp.region}" if opp.city and opp.region else opp.city or opp.region or "Location"
        
        return f"""
    <section class="map-section">
        <h2>Geographic Context: {location_name}</h2>
        <div class="satellite-map">
            <img src="{map_url}" alt="Satellite map of {location_name}" style="width: 100%; max-width: 800px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
        </div>
        <div class="map-legend">
            <span class="legend-item"><span class="marker-dot"></span> Opportunity Location</span>
            <span class="coordinates">Coordinates: {lat:.4f}, {lng:.4f}</span>
        </div>
    </section>
"""
    
    def _build_layer1_summary(self, opp: Opportunity) -> str:
        """Build Layer 1 report summary."""
        return f"Problem Overview for '{opp.title}' - Score: {opp.ai_opportunity_score or opp.severity * 20}/100. {opp.ai_summary[:200] if opp.ai_summary else opp.description[:200] if opp.description else 'Analysis pending'}..."
    
    def _build_target_customer_section(self, opp: Opportunity, demographics: Optional[Dict] = None) -> str:
        """Build Target Customer Profile section using Census data."""
        if not demographics:
            return """
    <section class="target-customer">
        <h2>Target Customer Profile</h2>
        <p class="placeholder-note">Demographic insights will be available after geographic analysis is complete.</p>
        <div class="customer-grid">
            <div class="customer-card">
                <span class="label">Primary Demographic</span>
                <span class="value">--</span>
            </div>
            <div class="customer-card">
                <span class="label">Income Level</span>
                <span class="value">--</span>
            </div>
            <div class="customer-card">
                <span class="label">Purchasing Power</span>
                <span class="value">--</span>
            </div>
        </div>
    </section>
"""
        
        pop = demographics.get('population', 0)
        pop_display = f"{pop/1000000:.1f}M" if pop >= 1000000 else f"{pop/1000:.0f}K" if pop >= 1000 else str(pop)
        
        income = demographics.get('median_income', 0)
        income_display = f"${income/1000:.0f}K" if income else "--"
        
        income_level = "High Income" if income > 100000 else "Upper-Middle" if income > 75000 else "Middle Income" if income > 50000 else "Working Class"
        
        purchasing_power = demographics.get('purchasing_power', 0)
        pp_display = f"${purchasing_power/1000000000:.1f}B" if purchasing_power >= 1000000000 else f"${purchasing_power/1000000:.0f}M" if purchasing_power >= 1000000 else "--"
        
        age_data = demographics.get('age_distribution', {})
        primary_demo = self._get_primary_demographic(age_data)
        
        households = demographics.get('households') or demographics.get('total_households') or demographics.get('internet_access', {}).get('total_households', 0)
        hh_display = f"{households/1000:.0f}K" if households >= 1000 else str(households) if households else "--"
        
        homeowner_pct = demographics.get('housing_tenure', {}).get('owner_pct', 0)
        housing_status = "Homeowner Majority" if homeowner_pct > 60 else "Renter Majority" if homeowner_pct < 40 else "Mixed Housing"
        
        broadband_pct = demographics.get('internet_access', {}).get('broadband_pct', 0)
        digital_ready = "High" if broadband_pct > 90 else "Moderate" if broadband_pct > 70 else "Developing"
        
        income_segments = ""
        income_under_50k = demographics.get('income_under_50k', 0)
        income_50k_100k = demographics.get('income_50k_100k', 0)
        income_100k_plus = demographics.get('income_100k_plus', 0)
        total_income_hh = income_under_50k + income_50k_100k + income_100k_plus
        
        if total_income_hh > 0:
            pct_under_50k = round((income_under_50k / total_income_hh) * 100)
            pct_50k_100k = round((income_50k_100k / total_income_hh) * 100)
            pct_100k_plus = round((income_100k_plus / total_income_hh) * 100)
            income_segments = f"""
            <div class="income-segments">
                <div class="segment"><span class="bar" style="width: {pct_under_50k}%"></span><span>Under $50K: {pct_under_50k}%</span></div>
                <div class="segment"><span class="bar" style="width: {pct_50k_100k}%"></span><span>$50K-$100K: {pct_50k_100k}%</span></div>
                <div class="segment"><span class="bar" style="width: {pct_100k_plus}%"></span><span>$100K+: {pct_100k_plus}%</span></div>
            </div>
"""
        
        return f"""
    <section class="target-customer">
        <h2>Target Customer Profile</h2>
        <p class="section-intro">Census-validated demographic insights for {opp.city or opp.region or 'the target market'}.</p>
        <div class="customer-grid">
            <div class="customer-card">
                <span class="label">Population</span>
                <span class="value">{pop_display}</span>
            </div>
            <div class="customer-card">
                <span class="label">Primary Age Group</span>
                <span class="value">{primary_demo}</span>
            </div>
            <div class="customer-card">
                <span class="label">Median Income</span>
                <span class="value">{income_display}</span>
            </div>
            <div class="customer-card">
                <span class="label">Income Level</span>
                <span class="value">{income_level}</span>
            </div>
            <div class="customer-card">
                <span class="label">Households</span>
                <span class="value">{hh_display}</span>
            </div>
            <div class="customer-card">
                <span class="label">Purchasing Power</span>
                <span class="value">{pp_display}</span>
            </div>
            <div class="customer-card">
                <span class="label">Housing</span>
                <span class="value">{housing_status}</span>
            </div>
            <div class="customer-card">
                <span class="label">Digital Readiness</span>
                <span class="value">{digital_ready}</span>
            </div>
        </div>
        {income_segments}
    </section>
"""
    
    def _get_primary_demographic(self, age_data: Dict) -> str:
        """Determine the primary age demographic from Census age distribution."""
        if not age_data:
            return "Adults 25-54"
        
        age_groups = [
            ("under_18", "Youth (Under 18)"),
            ("18_24", "Young Adults (18-24)"),
            ("25_44", "Prime Working Age (25-44)"),
            ("45_64", "Established Adults (45-64)"),
            ("65_plus", "Seniors (65+)"),
        ]
        
        max_group = None
        max_count = 0
        for key, label in age_groups:
            count = age_data.get(key, 0) or 0
            if count > max_count:
                max_count = count
                max_group = label
        
        return max_group or "Adults 25-54"
    
    def _get_top_cities_by_category(self, category: str, limit: int = 5) -> List[Dict]:
        """Get top cities by problem density for a given category with coordinates."""
        from sqlalchemy import func
        
        results = self.db.query(
            Opportunity.city,
            Opportunity.region,
            func.count(Opportunity.id).label('problem_count'),
            func.avg(Opportunity.severity).label('avg_severity'),
            func.avg(Opportunity.ai_opportunity_score).label('avg_score'),
            func.avg(Opportunity.latitude).label('avg_latitude'),
            func.avg(Opportunity.longitude).label('avg_longitude')
        ).filter(
            Opportunity.category == category,
            Opportunity.city.isnot(None),
            Opportunity.city != ''
        ).group_by(
            Opportunity.city,
            Opportunity.region
        ).order_by(
            func.count(Opportunity.id).desc()
        ).limit(limit).all()
        
        cities = []
        for r in results:
            cities.append({
                "city": r.city,
                "region": r.region,
                "problem_count": r.problem_count,
                "avg_severity": round(float(r.avg_severity or 0), 1),
                "avg_score": round(float(r.avg_score or 70), 0),
                "latitude": float(r.avg_latitude) if r.avg_latitude else None,
                "longitude": float(r.avg_longitude) if r.avg_longitude else None,
            })
        return cities
    
    def _build_signal_quality_section(self, opp: Opportunity) -> str:
        """Build Signal Quality Breakdown section showing data quality metrics."""
        validation_count = opp.validation_count or 0
        severity = opp.severity or 5
        score = opp.ai_opportunity_score or (severity * 20)
        
        signal_strength = "Strong" if validation_count >= 10 else "Moderate" if validation_count >= 5 else "Emerging"
        strength_class = "strong" if validation_count >= 10 else "moderate" if validation_count >= 5 else "emerging"
        
        freshness = "Fresh" if hasattr(opp, 'created_at') and opp.created_at else "Recent"
        freshness_class = "fresh"
        
        confidence_level = "High" if score >= 80 else "Medium" if score >= 60 else "Low"
        confidence_class = "high" if score >= 80 else "medium" if score >= 60 else "low"
        
        source_types = []
        if opp.source_type:
            source_types.append(opp.source_type)
        else:
            source_types = ["Market Analysis", "Consumer Feedback"]
        
        sources_html = "".join(f'<span class="source-tag">{s}</span>' for s in source_types[:3])
        
        return f"""
    <section class="signal-quality">
        <h2>Signal Quality Breakdown</h2>
        <div class="quality-grid">
            <div class="quality-card {strength_class}">
                <span class="label">Signal Strength</span>
                <span class="value">{signal_strength}</span>
                <span class="detail">{validation_count} validations</span>
            </div>
            <div class="quality-card {freshness_class}">
                <span class="label">Data Freshness</span>
                <span class="value">{freshness}</span>
                <span class="detail">Regularly updated</span>
            </div>
            <div class="quality-card {confidence_class}">
                <span class="label">Confidence Level</span>
                <span class="value">{confidence_level}</span>
                <span class="detail">Score: {int(score)}/100</span>
            </div>
        </div>
        <div class="source-breakdown">
            <span class="label">Data Sources:</span>
            {sources_html}
        </div>
    </section>
"""
    
    def _build_geographic_heat_section(self, opp: Opportunity) -> str:
        """Build Geographic Heat section showing top cities by problem density with static map."""
        top_cities = self._get_top_cities_by_category(opp.category)
        
        if not top_cities:
            return """
    <section class="geographic-heat">
        <h2>Geographic Hotspots</h2>
        <p class="placeholder-note">Geographic data is being analyzed. Check back soon for insights on where this problem is most prevalent.</p>
    </section>
"""
        
        markers = []
        for city in top_cities:
            if city.get('latitude') and city.get('longitude'):
                severity = city.get('avg_severity', 5)
                color = "ff4444" if severity >= 7 else "ffaa44" if severity >= 5 else "44aaff"
                markers.append({
                    "lat": city['latitude'],
                    "lng": city['longitude'],
                    "color": color
                })
        
        center_lng = -98.5795
        center_lat = 39.8283
        if markers:
            center_lng = sum(m['lng'] for m in markers) / len(markers)
            center_lat = sum(m['lat'] for m in markers) / len(markers)
        
        map_url = build_static_map_url(
            center_lng=center_lng,
            center_lat=center_lat,
            zoom=3,
            width=600,
            height=280,
            markers=markers,
            style="mapbox/dark-v11"
        )
        
        map_html = ""
        if map_url:
            map_html = f"""
        <div class="geographic-map">
            <img src="{map_url}" alt="Geographic hotspots map" class="static-map" style="width:100%;max-width:600px;border-radius:8px;margin-bottom:16px;" />
        </div>"""
        
        city_rows = ""
        for i, city in enumerate(top_cities, 1):
            city_name = f"{city['city']}, {city['region']}" if city['region'] else city['city']
            heat_class = "hot" if city['avg_severity'] >= 7 else "warm" if city['avg_severity'] >= 5 else "cool"
            city_rows += f"""
            <tr class="{heat_class}">
                <td class="rank">#{i}</td>
                <td class="city">{city_name}</td>
                <td class="count">{city['problem_count']} signals</td>
                <td class="severity">{city['avg_severity']}/10</td>
                <td class="score">{int(city['avg_score'])}</td>
            </tr>"""
        
        return f"""
    <section class="geographic-heat">
        <h2>Geographic Hotspots</h2>
        <p class="section-intro">Top 5 cities where this problem category is most prevalent.</p>
        {map_html}
        <table class="heat-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Location</th>
                    <th>Problem Signals</th>
                    <th>Avg Severity</th>
                    <th>Opp Score</th>
                </tr>
            </thead>
            <tbody>
                {city_rows}
            </tbody>
        </table>
    </section>
"""
    
    def generate_layer2_report(self, opportunity: Opportunity, user: User, demographics: Optional[Dict] = None) -> GeneratedReport:
        """Generate Layer 2: Deep Dive Analysis report with trade area analysis."""
        from app.services.trade_area_analyzer import trade_area_analyzer
        
        start_time = datetime.utcnow()
        
        report = GeneratedReport(
            user_id=user.id,
            opportunity_id=opportunity.id,
            report_type=ReportType.LAYER_2_DEEP_DIVE,
            status=ReportStatus.GENERATING,
            title=f"Deep Dive Analysis: {opportunity.title}",
        )
        self.db.add(report)
        self.db.commit()
        
        try:
            opp_dict = {
                'title': opportunity.title,
                'category': opportunity.category,
                'city': opportunity.city,
                'region': opportunity.region,
                'country': opportunity.country,
                'description': opportunity.description,
                'latitude': opportunity.latitude,
                'longitude': opportunity.longitude,
                'severity': opportunity.severity,
                'market_size': opportunity.ai_market_size_estimate or opportunity.market_size,
                'target_audience': opportunity.ai_target_audience,
            }
            
            try:
                trade_area = trade_area_analyzer.analyze(
                    opp_dict,
                    include_competitors=True,
                    include_demographics=demographics is None,
                    include_ai_synthesis=True
                )
                
                if demographics is None and trade_area.demographics:
                    demographics = trade_area.demographics
            except Exception as e:
                logger.warning(f"Trade area analysis failed: {e}")
                trade_area = None
            
            content = self._build_layer2_content(opportunity, demographics, trade_area)
            summary = f"Deep Dive Analysis for '{opportunity.title}' including trade area analysis, TAM/SAM/SOM, competitive landscape, and AI-powered market insights."
            
            report.content = content
            report.summary = summary
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            report.generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            report.confidence_score = opportunity.ai_opportunity_score or 80
            
            self.db.commit()
            self.db.refresh(report)
            
            return report
        except Exception as e:
            logger.error(f"Failed to generate Layer 2 report for opportunity {opportunity.id}: {e}")
            report.status = ReportStatus.FAILED
            report.error_type = "generation_error"
            report.error_message = str(e)[:500]
            report.generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.db.commit()
            self.db.refresh(report)
            return report
    
    def _calculate_tam_sam_som(self, opp: Opportunity, demographics: Optional[Dict] = None) -> Dict[str, Any]:
        """Calculate TAM/SAM/SOM using Census data and opportunity characteristics."""
        category_spend_per_capita = {
            "Home Services": 3500,
            "Healthcare": 4200,
            "Transportation": 2800,
            "Food & Beverage": 2400,
            "Professional Services": 1800,
            "Technology": 1500,
            "Retail": 3200,
            "Education": 2100,
            "Entertainment": 1200,
            "Financial Services": 1600,
        }
        
        base_spend = category_spend_per_capita.get(opp.category, 2000)
        
        us_population = 330_000_000
        tam_value = us_population * base_spend * 0.15
        tam_methodology = f"US population ({us_population/1_000_000:.0f}M) × Category annual spend (${base_spend:,}) × Problem addressable rate (15%)"
        
        if demographics and demographics.get('population'):
            regional_pop = demographics['population']
            income = demographics.get('median_income', 65000)
            income_multiplier = min(1.5, max(0.7, income / 65000))
            sam_value = regional_pop * base_spend * 0.20 * income_multiplier
            sam_methodology = f"Regional population ({regional_pop:,}) × Category spend (${base_spend:,}) × Addressable rate (20%) × Income multiplier ({income_multiplier:.2f}x)"
            
            households = demographics.get('total_households') or demographics.get('households') or (regional_pop // 2.5)
            broadband_rate = 0.85
            if demographics.get('internet_access'):
                broadband_rate = demographics['internet_access'].get('broadband_pct', 85) / 100
            
            som_value = households * base_spend * 0.05 * broadband_rate
            som_methodology = f"Households ({households:,}) × Category spend (${base_spend:,}) × Capture rate (5%) × Digital accessibility ({broadband_rate*100:.0f}%)"
        else:
            sam_value = tam_value * 0.10
            sam_methodology = "TAM × Geographic filter (10%)"
            som_value = sam_value * 0.10
            som_methodology = "SAM × Realistic capture rate (10%)"
        
        def format_market_size(value: float) -> str:
            if value >= 1_000_000_000:
                return f"${value/1_000_000_000:.1f}B"
            elif value >= 1_000_000:
                return f"${value/1_000_000:.0f}M"
            else:
                return f"${value/1_000:.0f}K"
        
        return {
            "tam": {"value": tam_value, "display": format_market_size(tam_value), "methodology": tam_methodology},
            "sam": {"value": sam_value, "display": format_market_size(sam_value), "methodology": sam_methodology},
            "som": {"value": som_value, "display": format_market_size(som_value), "methodology": som_methodology},
            "data_source": "US Census Bureau ACS 5-Year Estimates" if demographics else "Industry benchmarks",
            "confidence": "High" if demographics else "Medium"
        }
    
    def _build_income_distribution_section(self, demographics: Optional[Dict]) -> str:
        """Build Income Distribution table section for Layer 2."""
        if not demographics or not demographics.get('income_segments'):
            return """
    <section class="income-distribution">
        <h2>Income Distribution</h2>
        <p class="no-data">Income distribution data not available for this region.</p>
    </section>
"""
        income_data = demographics['income_segments']
        
        rows_html = ""
        income_brackets = [
            ("Under $25K", "under_25k_pct", "Entry-level, budget-conscious"),
            ("$25K - $50K", "25k_50k_pct", "Price-sensitive middle"),
            ("$50K - $100K", "50k_100k_pct", "Core purchasing power"),
            ("$100K - $150K", "100k_150k_pct", "Premium segment"),
            ("$150K+", "over_150k_pct", "Affluent market"),
        ]
        
        for label, key, insight in income_brackets:
            pct = income_data.get(key, 0)
            bar_width = min(100, max(5, pct * 3))
            rows_html += f"""
            <tr>
                <td>{label}</td>
                <td class="pct">{pct:.1f}%</td>
                <td class="bar-cell"><div class="bar" style="width: {bar_width}%;"></div></td>
                <td class="insight">{insight}</td>
            </tr>"""
        
        return f"""
    <section class="income-distribution">
        <h2>Income Distribution</h2>
        <p class="source-note">Data source: US Census Bureau ACS 5-Year Estimates (B19001)</p>
        <table class="income-table">
            <thead>
                <tr>
                    <th>Income Bracket</th>
                    <th>% of Households</th>
                    <th>Distribution</th>
                    <th>Market Insight</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </section>
"""
    
    def _build_top_markets_section(self, opp: Opportunity) -> str:
        """Build Top 10 Markets by Opportunity Score section for Layer 2."""
        from sqlalchemy import func
        
        top_markets = self.db.query(
            Opportunity.city,
            Opportunity.region,
            func.count(Opportunity.id).label('signal_count'),
            func.avg(Opportunity.ai_opportunity_score).label('avg_score'),
            func.avg(Opportunity.severity).label('avg_severity'),
            func.sum(Opportunity.validation_count).label('total_validations')
        ).filter(
            Opportunity.category == opp.category,
            Opportunity.city.isnot(None)
        ).group_by(
            Opportunity.city,
            Opportunity.region
        ).order_by(
            func.avg(Opportunity.ai_opportunity_score).desc().nullslast()
        ).limit(10).all()
        
        if not top_markets:
            return """
    <section class="top-markets">
        <h2>Top Markets by Opportunity Score</h2>
        <p class="no-data">Insufficient market data available for ranking.</p>
    </section>
"""
        
        rows_html = ""
        for idx, market in enumerate(top_markets, 1):
            city = market.city or "Unknown"
            region = market.region or ""
            location = f"{city}, {region}" if region else city
            signal_count = market.signal_count or 0
            avg_score = float(market.avg_score or 70)
            severity = float(market.avg_severity or 5)
            validations = market.total_validations or 0
            
            score_class = "high" if avg_score >= 80 else "medium" if avg_score >= 60 else "low"
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else str(idx)
            
            rows_html += f"""
            <tr>
                <td class="rank">{medal}</td>
                <td class="location">{location}</td>
                <td class="signals">{signal_count}</td>
                <td class="score {score_class}">{avg_score:.0f}</td>
                <td class="severity">{severity:.1f}</td>
                <td class="validations">{validations}</td>
            </tr>"""
        
        return f"""
    <section class="top-markets">
        <h2>Top 10 Markets by Opportunity Score</h2>
        <p class="source-note">Category: {opp.category} | Scoring: Signal density × Severity × Validation strength</p>
        <table class="markets-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Market</th>
                    <th>Signals</th>
                    <th>Score</th>
                    <th>Severity</th>
                    <th>Validations</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <div class="methodology">
            <h4>Scoring Methodology</h4>
            <ul>
                <li><strong>Signals:</strong> Count of validated market signals in this geography</li>
                <li><strong>Score:</strong> AI-computed opportunity score (0-100) based on market fit, timing, and growth potential</li>
                <li><strong>Severity:</strong> Average pain intensity (1-10) reported across signals</li>
                <li><strong>Validations:</strong> Total user/expert confirmations supporting these signals</li>
            </ul>
        </div>
    </section>
"""
    
    def _build_layer2_map_section(self, opp: Opportunity) -> str:
        """Build static map image for Layer 2 geographic analysis."""
        coords = self._validate_opportunity_coords(opp)
        center_lat = coords["lat"]
        center_lng = coords["lng"]
        
        markers = []
        if center_lat and center_lng:
            markers.append({
                "lat": center_lat,
                "lng": center_lng,
                "color": "8b5cf6"
            })
        
        zoom = 6 if opp.city else 4
        
        map_url = build_static_map_url(
            center_lng=center_lng,
            center_lat=center_lat,
            zoom=zoom,
            width=640,
            height=320,
            markers=markers,
            style="mapbox/dark-v11"
        )
        
        if not map_url:
            return ""
        
        return f"""
        <div class="geographic-map">
            <img src="{map_url}" alt="Geographic analysis map" class="static-map" style="width:100%;max-width:640px;border-radius:8px;margin-bottom:20px;" />
        </div>"""
    
    def _build_housing_lifestyle_section(self, demographics: Optional[Dict]) -> str:
        """Build Housing & Lifestyle section for Layer 2."""
        if not demographics:
            return """
    <section class="housing-lifestyle">
        <h2>Housing & Lifestyle</h2>
        <p class="no-data">Housing data not available for this region.</p>
    </section>
"""
        
        housing_tenure = demographics.get('housing_tenure', {})
        internet = demographics.get('internet_access', {})
        commute = demographics.get('commute_patterns', {})
        
        homeowner_pct = housing_tenure.get('owner_pct', 0)
        renter_pct = housing_tenure.get('renter_pct', 0)
        broadband_pct = internet.get('broadband_pct', 0)
        no_internet_pct = internet.get('no_internet_pct', 0)
        avg_commute = commute.get('avg_commute_minutes', 0)
        work_from_home_pct = commute.get('work_from_home_pct', 0)
        
        return f"""
    <section class="housing-lifestyle">
        <h2>Housing & Lifestyle</h2>
        <p class="source-note">Data source: US Census Bureau ACS 5-Year Estimates</p>
        <div class="lifestyle-grid">
            <div class="lifestyle-block">
                <h3>Housing Tenure</h3>
                <div class="tenure-bar">
                    <div class="owner" style="width: {homeowner_pct}%;">{homeowner_pct:.0f}% Own</div>
                    <div class="renter" style="width: {renter_pct}%;">{renter_pct:.0f}% Rent</div>
                </div>
                <p class="insight">{"Homeowner-dominant market - stable, higher LTV" if homeowner_pct > 50 else "Renter-dominant market - higher churn, subscription-friendly"}</p>
            </div>
            <div class="lifestyle-block">
                <h3>Digital Access</h3>
                <div class="stat-row">
                    <span class="stat-value">{broadband_pct:.1f}%</span>
                    <span class="stat-label">Broadband Access</span>
                </div>
                <div class="stat-row">
                    <span class="stat-value">{no_internet_pct:.1f}%</span>
                    <span class="stat-label">No Internet</span>
                </div>
                <p class="insight">{"High digital readiness - strong e-commerce potential" if broadband_pct > 80 else "Mixed digital access - consider offline channels"}</p>
            </div>
            <div class="lifestyle-block">
                <h3>Commute Patterns</h3>
                <div class="stat-row">
                    <span class="stat-value">{avg_commute:.0f} min</span>
                    <span class="stat-label">Avg Commute Time</span>
                </div>
                <div class="stat-row">
                    <span class="stat-value">{work_from_home_pct:.1f}%</span>
                    <span class="stat-label">Work From Home</span>
                </div>
                <p class="insight">{"Remote-work friendly - daytime residential traffic" if work_from_home_pct > 15 else "Traditional commuter market - peak hour patterns"}</p>
            </div>
        </div>
    </section>
"""
    
    def _build_layer2_content(self, opp: Opportunity, demographics: Optional[Dict] = None, trade_area=None) -> str:
        """Build Layer 2 report content with trade area analysis and demographics."""
        market_sizing = self._calculate_tam_sam_som(opp, demographics)
        income_section = self._build_income_distribution_section(demographics)
        housing_section = self._build_housing_lifestyle_section(demographics)
        top_markets_section = self._build_top_markets_section(opp)
        trade_area_section = self._build_trade_area_section(opp, trade_area)
        competitive_section = self._build_competitive_analysis_section(opp, trade_area)
        ai_insights_section = self._build_ai_insights_section(opp, demographics, trade_area)
        
        pop_display = "--"
        income_display = "--"
        education_display = "--"
        households_display = "--"
        
        if demographics:
            if demographics.get('population'):
                pop = demographics['population']
                pop_display = f"{pop/1000000:.1f}M" if pop >= 1000000 else f"{pop/1000:.0f}K"
            if demographics.get('median_income'):
                income_display = f"${demographics['median_income']/1000:.0f}K"
            if demographics.get('bachelors_degree_holders') and demographics.get('population'):
                education_display = f"{(demographics['bachelors_degree_holders'] / demographics['population'] * 100):.0f}%"
            if demographics.get('total_households') or demographics.get('households'):
                hh = demographics.get('total_households') or demographics.get('households')
                households_display = f"{hh/1000:.0f}K" if hh >= 1000 else str(hh)
        
        html_content = f"""
<div class="report-layer2">
    <header class="report-header">
        <h1>Deep Dive Analysis Report</h1>
        <div class="report-meta">
            <span class="tier-badge">BUSINESS</span>
            <span class="category">{opp.category}</span>
            <span class="date">Generated: {datetime.utcnow().strftime('%B %d, %Y')}</span>
        </div>
    </header>
    
    {trade_area_section}
    
    {ai_insights_section}
    
    <section class="tam-sam-som">
        <h2>Market Size Analysis (TAM/SAM/SOM)</h2>
        <p class="source-note">Data source: {market_sizing['data_source']} | Confidence: {market_sizing['confidence']}</p>
        <div class="market-funnel">
            <div class="funnel-level tam">
                <span class="label">Total Addressable Market (TAM)</span>
                <span class="value">{market_sizing['tam']['display']}</span>
                <p class="methodology">{market_sizing['tam']['methodology']}</p>
            </div>
            <div class="funnel-level sam">
                <span class="label">Serviceable Available Market (SAM)</span>
                <span class="value">{market_sizing['sam']['display']}</span>
                <p class="methodology">{market_sizing['sam']['methodology']}</p>
            </div>
            <div class="funnel-level som">
                <span class="label">Serviceable Obtainable Market (SOM)</span>
                <span class="value">{market_sizing['som']['display']}</span>
                <p class="methodology">{market_sizing['som']['methodology']}</p>
            </div>
        </div>
    </section>
    
    {competitive_section}
    
    <section class="demographic-deep-dive">
        <h2>Demographic Deep Dive</h2>
        <p class="source-note">Data source: US Census Bureau ACS 5-Year Estimates</p>
        <div class="demo-grid">
            <div class="demo-card">
                <span class="value">{pop_display}</span>
                <span class="label">Population</span>
            </div>
            <div class="demo-card">
                <span class="value">{income_display}</span>
                <span class="label">Median Income</span>
            </div>
            <div class="demo-card">
                <span class="value">{education_display}</span>
                <span class="label">College Educated</span>
            </div>
            <div class="demo-card">
                <span class="value">{households_display}</span>
                <span class="label">Households</span>
            </div>
        </div>
    </section>
    
    {income_section}
    
    {housing_section}
    
    {top_markets_section}
    
    <section class="business-models">
        <h2>Recommended Business Models</h2>
        <div class="model-cards">
            {''.join(f'<div class="model-card"><h4>{model}</h4><p>Viable approach based on market analysis</p></div>' for model in (opp.ai_business_model_suggestions or ["SaaS Platform", "Marketplace", "Subscription Service"])[:4])}
        </div>
    </section>
    
    <footer class="report-footer">
        <p>This comprehensive analysis was generated by OppGrid's AI engine using Claude with Census data integration.</p>
        <p>For full execution package with business plan, upgrade to Layer 3.</p>
    </footer>
</div>
"""
        return html_content
    
    def _build_trade_area_section(self, opp: Opportunity, trade_area) -> str:
        """Build the trade area visualization section with satellite map."""
        if not trade_area:
            lat = opp.latitude
            lng = opp.longitude
            
            if lat and lng:
                map_url = build_static_map_url(
                    center_lng=lng,
                    center_lat=lat,
                    zoom=12,
                    width=1000,
                    height=500,
                    markers=[{"lat": lat, "lng": lng, "color": "22c55e", "label": "c"}],
                    use_satellite=True
                )
                if map_url:
                    return f"""
    <section class="trade-area-analysis">
        <h2>Trade Area Analysis</h2>
        <div class="satellite-map">
            <img src="{map_url}" alt="Satellite trade area map" style="width: 100%; max-width: 1000px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
        </div>
        <div class="trade-area-summary">
            <p>Detailed competitor mapping requires SerpAPI configuration.</p>
        </div>
    </section>
"""
            return """
    <section class="trade-area-analysis">
        <h2>Trade Area Analysis</h2>
        <div class="placeholder">
            <p>Geographic data pending - trade area analysis requires location coordinates.</p>
        </div>
    </section>
"""
        
        competitors_count = len(trade_area.competitors) if trade_area.competitors else 0
        white_space = trade_area.white_space_score
        
        competitor_rows = ""
        if trade_area.competitors:
            for i, comp in enumerate(trade_area.competitors[:10], 1):
                rating_stars = "★" * int(comp.get('rating', 0)) + "☆" * (5 - int(comp.get('rating', 0)))
                competitor_rows += f"""
                <tr>
                    <td>{i}</td>
                    <td>{comp.get('name', 'Unknown')}</td>
                    <td>{rating_stars} ({comp.get('rating', 'N/A')})</td>
                    <td>{comp.get('reviews', 0)} reviews</td>
                    <td>{comp.get('address', '')[:50]}...</td>
                </tr>"""
        
        competitor_table = ""
        if competitor_rows:
            competitor_table = f"""
        <div class="competitor-table-wrapper">
            <h3>Nearby Competitors</h3>
            <table class="competitor-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Business Name</th>
                        <th>Rating</th>
                        <th>Reviews</th>
                        <th>Address</th>
                    </tr>
                </thead>
                <tbody>
                    {competitor_rows}
                </tbody>
            </table>
        </div>"""
        
        map_html = ""
        if trade_area.map_url:
            map_html = f"""
        <div class="satellite-map">
            <img src="{trade_area.map_url}" alt="Trade area satellite map with competitors" style="width: 100%; max-width: 1000px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
            <div class="map-legend">
                <span class="legend-item"><span class="dot green"></span> Opportunity Center</span>
                <span class="legend-item"><span class="dot red"></span> Competitors</span>
                <span class="legend-item"><span class="dot blue"></span> Demand Signals</span>
            </div>
        </div>"""
        
        return f"""
    <section class="trade-area-analysis">
        <h2>Trade Area Analysis</h2>
        {map_html}
        <div class="trade-area-metrics">
            <div class="metric-card">
                <span class="value">{trade_area.radius_km:.1f} km</span>
                <span class="label">Service Radius</span>
            </div>
            <div class="metric-card">
                <span class="value">{competitors_count}</span>
                <span class="label">Competitors Found</span>
            </div>
            <div class="metric-card">
                <span class="value">{white_space:.0f}%</span>
                <span class="label">White Space Score</span>
            </div>
            <div class="metric-card">
                <span class="value">{len(trade_area.signal_clusters)}</span>
                <span class="label">Demand Signals</span>
            </div>
        </div>
        {competitor_table}
    </section>
"""
    
    def _build_competitive_analysis_section(self, opp: Opportunity, trade_area) -> str:
        """Build Porter's Five Forces competitive analysis section."""
        try:
            opp_dict = {
                'title': opp.title,
                'category': opp.category,
                'city': opp.city,
                'region': opp.region,
                'description': opp.description or '',
            }
            competitors = trade_area.competitors if trade_area else []
            
            ai_analysis = ai_report_generator.generate_competitive_analysis(opp_dict, competitors)
            ai_analysis_html = ai_analysis.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '') if ai_analysis else ""
        except Exception as e:
            logger.warning(f"Failed to generate competitive analysis: {e}")
            ai_analysis_html = ""
        
        if ai_analysis_html:
            return f"""
    <section class="competitive-analysis">
        <h2>Competitive Analysis (Porter's Five Forces)</h2>
        <div class="ai-content">
            {ai_analysis_html}
        </div>
    </section>
"""
        
        return f"""
    <section class="competitive-landscape">
        <h2>Competitive Landscape</h2>
        <div class="competition-level">
            <span class="level capitalize">{opp.ai_competition_level or 'Medium'}</span>
            <span class="description">Overall competition intensity</span>
        </div>
        <div class="advantages">
            <h3>Key Competitive Advantages</h3>
            <ul>
                {''.join(f'<li>{adv}</li>' for adv in (opp.ai_competitive_advantages or ["Market gap identified", "First-mover potential", "Underserved segment"])[:5])}
            </ul>
        </div>
    </section>
"""
    
    def _build_ai_insights_section(self, opp: Opportunity, demographics: Optional[Dict], trade_area) -> str:
        """Build AI-generated market insights section."""
        if trade_area and trade_area.ai_synthesis:
            ai_content = trade_area.ai_synthesis.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '')
            return f"""
    <section class="ai-market-insights">
        <h2>AI Market Intelligence</h2>
        <div class="ai-badge">Powered by Claude</div>
        <div class="ai-content">
            {ai_content}
        </div>
    </section>
"""
        
        try:
            opp_dict = {
                'title': opp.title,
                'category': opp.category,
                'city': opp.city,
                'region': opp.region,
                'description': opp.description or '',
                'market_size': opp.ai_market_size_estimate or opp.market_size or '',
                'target_audience': opp.ai_target_audience or '',
            }
            
            competitors = trade_area.competitors if trade_area else []
            ai_insights = ai_report_generator.generate_market_insights(opp_dict, demographics, competitors)
            ai_content = ai_insights.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '') if ai_insights else ""
            
            if ai_content:
                return f"""
    <section class="ai-market-insights">
        <h2>AI Market Intelligence</h2>
        <div class="ai-badge">Powered by Claude</div>
        <div class="ai-content">
            {ai_content}
        </div>
    </section>
"""
        except Exception as e:
            logger.warning(f"Failed to generate AI insights: {e}")
        
        return ""
    
    def generate_layer3_report(self, opportunity: Opportunity, user: User, demographics: Optional[Dict] = None) -> GeneratedReport:
        """Generate Layer 3: Execution Package report."""
        start_time = datetime.utcnow()
        
        report = GeneratedReport(
            user_id=user.id,
            opportunity_id=opportunity.id,
            report_type=ReportType.LAYER_3_EXECUTION,
            status=ReportStatus.GENERATING,
            title=f"Execution Package: {opportunity.title}",
        )
        self.db.add(report)
        self.db.commit()
        
        try:
            content = self._build_layer3_content(opportunity, demographics)
            summary = f"Complete Execution Package for '{opportunity.title}' including business plan, go-to-market strategy, and 90-day roadmap."
            
            report.content = content
            report.summary = summary
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            report.generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            report.confidence_score = opportunity.ai_opportunity_score or 85
            
            self.db.commit()
            self.db.refresh(report)
            
            return report
        except Exception as e:
            logger.error(f"Failed to generate Layer 3 report for opportunity {opportunity.id}: {e}")
            report.status = ReportStatus.FAILED
            report.error_type = "generation_error"
            report.error_message = str(e)[:500]
            report.generation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.db.commit()
            self.db.refresh(report)
            return report
    
    def _build_layer3_content(self, opp: Opportunity, demographics: Optional[Dict] = None) -> str:
        """Build Layer 3 Execution Package content with AI-generated business plan and strategy."""
        opp_dict = {
            'title': opp.title,
            'category': opp.category,
            'city': opp.city,
            'region': opp.region,
            'description': opp.description or '',
            'market_size': opp.ai_market_size_estimate or opp.market_size or '',
            'target_audience': opp.ai_target_audience or '',
            'business_models': ', '.join(opp.ai_business_model_suggestions or []) if opp.ai_business_model_suggestions else '',
        }
        
        try:
            ai_business_plan = ai_report_generator.generate_business_plan(opp_dict)
            ai_business_plan_html = ai_business_plan.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '') if ai_business_plan else ""
        except Exception as e:
            logger.warning(f"Failed to generate AI business plan: {e}")
            ai_business_plan_html = ""
        
        try:
            ai_financial = ai_report_generator.generate_financial_projections(opp_dict)
            ai_financial_html = ai_financial.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '') if ai_financial else ""
        except Exception as e:
            logger.warning(f"Failed to generate AI financial projections: {e}")
            ai_financial_html = ""
        
        try:
            ai_strategy = ai_report_generator.generate_strategic_recommendations(opp_dict, demographics)
            ai_strategy_html = ai_strategy.replace('\n', '<br>').replace('**', '<strong>').replace('</strong><strong>', '') if ai_strategy else ""
        except Exception as e:
            logger.warning(f"Failed to generate AI strategic recommendations: {e}")
            ai_strategy_html = ""
        
        expansion_map_section = self._build_expansion_map_section(opp)
        
        business_plan_section = ""
        if ai_business_plan_html:
            business_plan_section = f"""
    <section class="ai-business-plan">
        <h2>AI-Generated Business Plan</h2>
        <div class="ai-badge">Powered by Claude (Business Model Canvas)</div>
        <div class="ai-content">
            {ai_business_plan_html}
        </div>
    </section>
"""
        else:
            business_plan_section = f"""
    <section class="business-plan-summary">
        <h2>Business Plan Summary</h2>
        <div class="plan-overview">
            <h3>Vision Statement</h3>
            <p>To become the leading solution for {opp.ai_target_audience or 'target customers'} by addressing {opp.title.lower()}.</p>
            
            <h3>Value Proposition</h3>
            <p>{opp.ai_problem_statement or opp.description}</p>
            
            <h3>Revenue Model</h3>
            <ul>
                {''.join(f'<li>{model}</li>' for model in (opp.ai_business_model_suggestions or ["Subscription", "Transaction fees", "Premium features"])[:3])}
            </ul>
        </div>
    </section>
"""
        
        strategy_section = ""
        if ai_strategy_html:
            strategy_section = f"""
    <section class="ai-strategy">
        <h2>Strategic Recommendations & Go-to-Market</h2>
        <div class="ai-badge">Powered by Claude</div>
        <div class="ai-content">
            {ai_strategy_html}
        </div>
    </section>
"""
        else:
            strategy_section = """
    <section class="go-to-market">
        <h2>Go-to-Market Strategy</h2>
        <div class="gtm-phases">
            <div class="phase">
                <h4>Phase 1: Foundation (Days 1-30)</h4>
                <ul>
                    <li>Finalize MVP feature set</li>
                    <li>Establish brand identity</li>
                    <li>Set up initial marketing channels</li>
                    <li>Begin beta user recruitment</li>
                </ul>
            </div>
            <div class="phase">
                <h4>Phase 2: Launch (Days 31-60)</h4>
                <ul>
                    <li>Soft launch with beta users</li>
                    <li>Gather feedback and iterate</li>
                    <li>Begin content marketing</li>
                    <li>Establish partnerships</li>
                </ul>
            </div>
            <div class="phase">
                <h4>Phase 3: Growth (Days 61-90)</h4>
                <ul>
                    <li>Public launch</li>
                    <li>Scale marketing efforts</li>
                    <li>Optimize conversion funnels</li>
                    <li>Expand to adjacent markets</li>
                </ul>
            </div>
        </div>
    </section>
"""
        
        financial_section = ""
        if ai_financial_html:
            financial_section = f"""
    <section class="ai-financials">
        <h2>Financial Projections (3-Year)</h2>
        <div class="ai-badge">Powered by Claude</div>
        <div class="ai-content">
            {ai_financial_html}
        </div>
    </section>
"""
        else:
            financial_section = """
    <section class="financial-projections">
        <h2>Financial Projections (3-Year)</h2>
        <table class="financials-table">
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Year 1</th>
                    <th>Year 2</th>
                    <th>Year 3</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Revenue</td>
                    <td>$250K</td>
                    <td>$1.2M</td>
                    <td>$3.5M</td>
                </tr>
                <tr>
                    <td>Customers</td>
                    <td>500</td>
                    <td>2,500</td>
                    <td>8,000</td>
                </tr>
                <tr>
                    <td>Gross Margin</td>
                    <td>60%</td>
                    <td>70%</td>
                    <td>75%</td>
                </tr>
                <tr>
                    <td>EBITDA</td>
                    <td>-$150K</td>
                    <td>$100K</td>
                    <td>$700K</td>
                </tr>
            </tbody>
        </table>
    </section>
"""
        
        html_content = f"""
<div class="report-layer3">
    <header class="report-header">
        <h1>Execution Package</h1>
        <div class="report-meta">
            <span class="tier-badge">ENTERPRISE</span>
            <span class="category">{opp.category}</span>
            <span class="date">Generated: {datetime.utcnow().strftime('%B %d, %Y')}</span>
        </div>
    </header>
    
    {expansion_map_section}
    
    {business_plan_section}
    
    {strategy_section}
    
    {financial_section}
    
    <section class="roadmap-90day">
        <h2>90-Day Action Roadmap</h2>
        <div class="roadmap-timeline">
            <div class="week week-1-4">
                <h4>Weeks 1-4: Research & Validate</h4>
                <ul>
                    <li>Conduct 20+ customer interviews</li>
                    <li>Analyze competitive landscape</li>
                    <li>Define MVP requirements</li>
                    <li>Select technology stack</li>
                </ul>
            </div>
            <div class="week week-5-8">
                <h4>Weeks 5-8: Build & Test</h4>
                <ul>
                    <li>Develop core MVP features</li>
                    <li>Create landing page</li>
                    <li>Begin beta testing</li>
                    <li>Iterate based on feedback</li>
                </ul>
            </div>
            <div class="week week-9-12">
                <h4>Weeks 9-12: Launch & Learn</h4>
                <ul>
                    <li>Soft launch to early adopters</li>
                    <li>Implement analytics</li>
                    <li>Optimize onboarding</li>
                    <li>Plan scaling strategy</li>
                </ul>
            </div>
        </div>
    </section>
    
    <section class="risk-mitigation">
        <h2>Risk Mitigation Plan</h2>
        <ul class="risk-items">
            {''.join(f'<li><strong>{risk}</strong><br/>Mitigation: Monitor market trends and adapt strategy accordingly.</li>' for risk in (opp.ai_key_risks or ["Market timing", "Competition", "Funding"])[:5])}
        </ul>
    </section>
    
    <footer class="report-footer">
        <p>This comprehensive execution package was generated by OppGrid's AI-powered business intelligence engine using Claude.</p>
        <p>For personalized strategy sessions, connect with our expert network.</p>
    </footer>
</div>
"""
        return html_content
    
    def _build_expansion_map_section(self, opp: Opportunity) -> str:
        """Build expansion map section showing regional opportunity."""
        lat = opp.latitude
        lng = opp.longitude
        
        if not lat or not lng:
            return ""
        
        map_url = build_static_map_url(
            center_lng=lng,
            center_lat=lat,
            zoom=8,
            width=1000,
            height=400,
            markers=[
                {"lat": lat, "lng": lng, "color": "22c55e", "label": "c"},
            ],
            use_satellite=True
        )
        
        if not map_url:
            return ""
        
        location_name = f"{opp.city}, {opp.region}" if opp.city and opp.region else opp.city or opp.region or "Target Market"
        
        return f"""
    <section class="expansion-map">
        <h2>Market Expansion Opportunity: {location_name}</h2>
        <div class="satellite-map">
            <img src="{map_url}" alt="Satellite expansion map of {location_name}" style="width: 100%; max-width: 1000px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
        </div>
        <div class="map-legend">
            <span class="legend-item"><span class="dot green"></span> Primary Launch Market</span>
        </div>
        <div class="expansion-notes">
            <p>This satellite view shows your primary launch market. The execution plan includes phased expansion to adjacent markets based on initial traction.</p>
        </div>
    </section>
"""


report_generator = ReportGenerator
