"""
Tests for Report Generation Service
Tests for PDF generation, caching, and API endpoints
"""

import pytest
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.services.report_generation import (
    ReportGenerator,
    IdentifyLocationReportGenerator,
    CloneSuccessReportGenerator,
    MapSnippetGenerator,
    ComparisonTableGenerator,
)
from app.models.generated_report import GeneratedReport
from app.schemas.report_generation import (
    IdentifyLocationReportRequest,
    CloneSuccessReportRequest,
)


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_identify_location_result():
    """Sample Identify Location response"""
    return {
        'success': True,
        'city': 'Miami',
        'state': 'FL',
        'business_description': 'Fast casual restaurant',
        'inferred_category': 'Food & Beverage',
        'geo_analysis': {
            'description': 'Miami metro area, South Florida',
        },
        'market_report': {
            'summary': 'Growing market with strong demand signals',
        },
        'micro_markets': [
            {
                'name': 'Downtown Miami',
                'archetype': 'Urban Core',
                'fit_score': 85,
                'population': 450000,
                'median_income': 52000,
                'competitor_count': 15,
                'demand_pct': 75,
                'avg_rent': 3500,
                'risk_factors': [
                    {'title': 'High Competition', 'level': 'medium', 'description': 'Multiple competitors in area'},
                ],
                'strengths': ['High foot traffic', 'Strong demographics'],
                'lat': 25.7617,
                'lng': -80.1918,
            },
            {
                'name': 'Wynwood',
                'archetype': 'Emerging Neighborhood',
                'fit_score': 78,
                'population': 250000,
                'median_income': 48000,
                'competitor_count': 8,
                'demand_pct': 68,
                'avg_rent': 2800,
                'risk_factors': [],
                'strengths': ['Growing area', 'Younger demographic'],
                'lat': 25.8196,
                'lng': -80.1993,
            },
        ],
        'site_recommendations': [],
        'data_quality': {
            'completeness': '92%',
            'confidence_score': '85/100',
        },
    }


@pytest.fixture
def sample_clone_success_response():
    """Sample Clone Success response"""
    return {
        'success': True,
        'source_business': {
            'name': 'Panera Bread - Miami Flagship',
            'location': 'Downtown Miami, FL',
            'category': 'Fast Casual',
            'description': 'Market-leading fast casual restaurant',
            'metrics': {
                'revenue': 2500000,
                'customers': 150000,
                'market_share': 8.5,
                'growth_rate': 12.5,
            },
        },
        'matching_locations': [
            {
                'name': 'Location 1',
                'city': 'Tampa',
                'state': 'FL',
                'lat': 27.9506,
                'lng': -82.4572,
                'similarity_score': 92,
                'demographics_match': 88,
                'competition_match': 85,
                'population': 400000,
                'median_income': 51000,
                'competition_count': 12,
                'key_factors': ['Strong demographics', 'Good foot traffic'],
            },
            {
                'name': 'Location 2',
                'city': 'Orlando',
                'state': 'FL',
                'lat': 28.5421,
                'lng': -81.3723,
                'similarity_score': 87,
                'demographics_match': 84,
                'competition_match': 79,
                'population': 350000,
                'median_income': 49000,
                'competition_count': 10,
                'key_factors': ['Growing market', 'Competitive rent'],
            },
        ],
        'analysis_radius_miles': 3,
        'replicability_label': 'High',
        'why_it_works': [
            'Strong market demand in casual dining',
            'Proven operational model',
            'Multiple revenue streams',
        ],
        'differentiation_needed': 'Local menu customization',
        'est_startup_cost': '$750K - $1.2M',
        'market_gap_pct': 42,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Report Generator Base Class
# ─────────────────────────────────────────────────────────────────────────────

class TestReportGenerator:
    """Tests for base ReportGenerator class"""
    
    def test_report_generator_initialization(self):
        """Test ReportGenerator can be subclassed with proper initialization"""
        
        class TestGenerator(ReportGenerator):
            def build(self):
                self.elements.append(Mock())
        
        gen = TestGenerator("Test Report", "test-req-123")
        assert gen.title == "Test Report"
        assert gen.request_id == "test-req-123"
        assert gen.timestamp is not None
    
    def test_branding_colors_are_defined(self):
        """Test that branding colors are properly configured"""
        from app.services.report_generation.report_generator import BrandingConfig
        
        assert BrandingConfig.PRIMARY_COLOR is not None
        assert BrandingConfig.SECONDARY_COLOR is not None
        assert BrandingConfig.RISK_HIGH is not None
        assert BrandingConfig.RISK_MEDIUM is not None
        assert BrandingConfig.RISK_LOW is not None


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Identify Location Report Generator
# ─────────────────────────────────────────────────────────────────────────────

class TestIdentifyLocationReportGenerator:
    """Tests for IdentifyLocationReportGenerator"""
    
    def test_generator_initialization(self, sample_identify_location_result):
        """Test IdentifyLocationReportGenerator initialization"""
        gen = IdentifyLocationReportGenerator(
            identify_location_result=sample_identify_location_result,
            request_id="test-123",
        )
        
        assert gen.title == "Location Identification Report"
        assert gen.request_id == "test-123"
        assert gen.city == "Miami"
        assert gen.category == "Food & Beverage"
        assert len(gen.candidates) == 2
    
    def test_candidates_extraction(self, sample_identify_location_result):
        """Test candidates are properly extracted from result"""
        gen = IdentifyLocationReportGenerator(
            identify_location_result=sample_identify_location_result,
            request_id="test-123",
        )
        
        candidates = gen.candidates
        assert len(candidates) == 2
        assert candidates[0]['score'] == 85
        assert candidates[1]['score'] == 78
    
    def test_candidates_sorted_by_score(self, sample_identify_location_result):
        """Test candidates are sorted by score descending"""
        gen = IdentifyLocationReportGenerator(
            identify_location_result=sample_identify_location_result,
            request_id="test-123",
        )
        
        scores = [c['score'] for c in gen.candidates]
        assert scores == sorted(scores, reverse=True)
    
    def test_grouping_by_archetype(self, sample_identify_location_result):
        """Test candidates are grouped by archetype"""
        gen = IdentifyLocationReportGenerator(
            identify_location_result=sample_identify_location_result,
            request_id="test-123",
        )
        
        archetypes = gen.candidates_by_archetype
        assert 'Urban Core' in archetypes
        assert 'Emerging Neighborhood' in archetypes
        assert len(archetypes['Urban Core']) == 1
    
    @patch('app.services.report_generation.identify_location_report.MapSnippetGenerator')
    def test_pdf_generation(self, mock_map_gen, sample_identify_location_result):
        """Test PDF generation completes successfully"""
        gen = IdentifyLocationReportGenerator(
            identify_location_result=sample_identify_location_result,
            request_id="test-123",
        )
        
        pdf_bytes = gen.generate()
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'  # PDF magic bytes


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Clone Success Report Generator
# ─────────────────────────────────────────────────────────────────────────────

class TestCloneSuccessReportGenerator:
    """Tests for CloneSuccessReportGenerator"""
    
    def test_generator_initialization(self, sample_clone_success_response):
        """Test CloneSuccessReportGenerator initialization"""
        gen = CloneSuccessReportGenerator(
            clone_success_response=sample_clone_success_response,
            request_id="test-123",
        )
        
        assert gen.title == "Business Clone Success Report"
        assert gen.request_id == "test-123"
        assert gen.source_business['name'] == "Panera Bread - Miami Flagship"
    
    def test_matching_locations_extracted(self, sample_clone_success_response):
        """Test matching locations are extracted"""
        gen = CloneSuccessReportGenerator(
            clone_success_response=sample_clone_success_response,
            request_id="test-123",
        )
        
        assert len(gen.matching_locations) == 2
        assert gen.matching_locations[0]['similarity_score'] == 92
    
    def test_locations_sorted_by_similarity(self, sample_clone_success_response):
        """Test locations are sorted by similarity descending"""
        gen = CloneSuccessReportGenerator(
            clone_success_response=sample_clone_success_response,
            request_id="test-123",
        )
        
        scores = [l['similarity_score'] for l in gen.matching_locations]
        assert scores == sorted(scores, reverse=True)
    
    @patch('app.services.report_generation.clone_success_report.MapSnippetGenerator')
    def test_pdf_generation(self, mock_map_gen, sample_clone_success_response):
        """Test PDF generation completes successfully"""
        gen = CloneSuccessReportGenerator(
            clone_success_response=sample_clone_success_response,
            request_id="test-123",
        )
        
        pdf_bytes = gen.generate()
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Comparison Table Generator
# ─────────────────────────────────────────────────────────────────────────────

class TestComparisonTableGenerator:
    """Tests for ComparisonTableGenerator"""
    
    def test_value_formatting_score(self):
        """Test score value formatting"""
        result = ComparisonTableGenerator.format_value(85, 'score')
        assert result == "85/100"
    
    def test_value_formatting_currency(self):
        """Test currency value formatting"""
        result = ComparisonTableGenerator.format_value(50000, 'currency')
        assert result == "$50,000"
    
    def test_value_formatting_percent(self):
        """Test percent value formatting"""
        result = ComparisonTableGenerator.format_value(75.5, 'percent')
        assert "75.5" in result or "75" in result
    
    def test_value_formatting_number(self):
        """Test number value formatting"""
        result = ComparisonTableGenerator.format_value(1250000, 'number')
        assert "1,250,000" in result
    
    def test_value_formatting_none(self):
        """Test None value handling"""
        result = ComparisonTableGenerator.format_value(None, 'score')
        assert result == "—"
    
    def test_identify_location_table_creation(self):
        """Test Identify Location comparison table creation"""
        candidates = [
            {
                'name': 'Location A',
                'score': 85,
                'population': 450000,
                'median_income': 52000,
                'competition_count': 15,
                'demand_signal': 75,
                'avg_rent': 3500,
                'risk_level': 'medium',
            },
            {
                'name': 'Location B',
                'score': 78,
                'population': 250000,
                'median_income': 48000,
                'competition_count': 8,
                'demand_signal': 68,
                'avg_rent': 2800,
                'risk_level': 'low',
            },
        ]
        
        headers, rows = ComparisonTableGenerator.create_identify_location_table(candidates)
        
        assert len(headers) > 0
        assert len(rows) == 2
        assert rows[0][0] == "1"  # First rank
        assert rows[1][0] == "2"  # Second rank
    
    def test_clone_success_table_creation(self):
        """Test Clone Success comparison table creation"""
        locations = [
            {
                'city': 'Tampa',
                'state': 'FL',
                'similarity_score': 92,
                'demographics_match': 88,
                'competition_match': 85,
                'population': 400000,
                'median_income': 51000,
            },
            {
                'city': 'Orlando',
                'state': 'FL',
                'similarity_score': 87,
                'demographics_match': 84,
                'competition_match': 79,
                'population': 350000,
                'median_income': 49000,
            },
        ]
        
        headers, rows = ComparisonTableGenerator.create_clone_success_table(locations)
        
        assert len(headers) > 0
        assert len(rows) == 2
        assert "Tampa" in rows[0][1]


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Map Snippet Generator
# ─────────────────────────────────────────────────────────────────────────────

class TestMapSnippetGenerator:
    """Tests for MapSnippetGenerator"""
    
    def test_generator_initialization(self):
        """Test MapSnippetGenerator initialization"""
        gen = MapSnippetGenerator(api_key="test-key")
        assert gen.api_key == "test-key"
    
    def test_placeholder_map_creation(self):
        """Test placeholder map creation when real maps unavailable"""
        gen = MapSnippetGenerator()
        
        png_bytes = gen._create_placeholder_map("Test Location", 400, 300)
        
        assert len(png_bytes) > 0
        # PNG magic bytes
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'


# ─────────────────────────────────────────────────────────────────────────────
# Tests for API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestMappingReportAPI:
    """Tests for mapping report API endpoints"""
    
    @pytest.mark.asyncio
    async def test_identify_location_pdf_generation(
        self,
        client,
        authenticated_headers,
        db_session,
        sample_identify_location_result,
    ):
        """Test Identify Location PDF generation endpoint"""
        request = IdentifyLocationReportRequest(
            request_id="test-req-123",
            identify_location_result=sample_identify_location_result,
        )
        
        response = await client.post(
            "/api/consultant-studio/identify-location/test-req-123/report/pdf",
            json=request.dict(),
            headers=authenticated_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'filename' in data
        assert '.pdf' in data['filename']
    
    @pytest.mark.asyncio
    async def test_clone_success_pdf_generation(
        self,
        client,
        authenticated_headers,
        db_session,
        sample_clone_success_response,
    ):
        """Test Clone Success PDF generation endpoint"""
        request = CloneSuccessReportRequest(
            request_id="test-req-456",
            clone_success_response=sample_clone_success_response,
        )
        
        response = await client.post(
            "/api/consultant-studio/clone-success/test-req-456/report/pdf",
            json=request.dict(),
            headers=authenticated_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'filename' in data
        assert '.pdf' in data['filename']
    
    @pytest.mark.asyncio
    async def test_report_caching(
        self,
        client,
        authenticated_headers,
        db_session,
        sample_identify_location_result,
    ):
        """Test report caching prevents regeneration"""
        request = IdentifyLocationReportRequest(
            request_id="test-cache-123",
            identify_location_result=sample_identify_location_result,
            force_regenerate=False,
        )
        
        # First request
        response1 = await client.post(
            "/api/consultant-studio/identify-location/test-cache-123/report/pdf",
            json=request.dict(),
            headers=authenticated_headers,
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1['from_cache'] is False
        
        # Second request should be from cache
        response2 = await client.post(
            "/api/consultant-studio/identify-location/test-cache-123/report/pdf",
            json=request.dict(),
            headers=authenticated_headers,
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2['from_cache'] is True
    
    @pytest.mark.asyncio
    async def test_force_regenerate_flag(
        self,
        client,
        authenticated_headers,
        db_session,
        sample_identify_location_result,
    ):
        """Test force_regenerate bypasses cache"""
        request_cached = IdentifyLocationReportRequest(
            request_id="test-force-123",
            identify_location_result=sample_identify_location_result,
            force_regenerate=False,
        )
        
        # First request
        await client.post(
            "/api/consultant-studio/identify-location/test-force-123/report/pdf",
            json=request_cached.dict(),
            headers=authenticated_headers,
        )
        
        # Second request with force_regenerate
        request_force = IdentifyLocationReportRequest(
            request_id="test-force-123",
            identify_location_result=sample_identify_location_result,
            force_regenerate=True,
        )
        
        response = await client.post(
            "/api/consultant-studio/identify-location/test-force-123/report/pdf",
            json=request_force.dict(),
            headers=authenticated_headers,
        )
        
        data = response.json()
        assert data['from_cache'] is False


# ─────────────────────────────────────────────────────────────────────────────
# Tests for Generated Report Model
# ─────────────────────────────────────────────────────────────────────────────

class TestGeneratedReportModel:
    """Tests for GeneratedReport database model"""
    
    def test_report_expiration_check(self):
        """Test report expiration logic"""
        report = GeneratedReport(
            user_id=1,
            request_id="test-123",
            report_type="identify_location",
            pdf_filename="test.pdf",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        
        assert report.is_expired() is True
    
    def test_report_not_expired(self):
        """Test non-expired report"""
        report = GeneratedReport(
            user_id=1,
            request_id="test-123",
            report_type="identify_location",
            pdf_filename="test.pdf",
            expires_at=datetime.utcnow() + timedelta(days=10),
        )
        
        assert report.is_expired() is False
    
    def test_access_tracking(self):
        """Test access tracking"""
        report = GeneratedReport(
            user_id=1,
            request_id="test-123",
            report_type="identify_location",
            pdf_filename="test.pdf",
            access_count=0,
        )
        
        report.update_access()
        assert report.access_count == 1
        assert report.last_accessed_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestReportGenerationIntegration:
    """Integration tests for complete report generation workflow"""
    
    def test_identify_location_full_workflow(self, sample_identify_location_result):
        """Test complete Identify Location report generation workflow"""
        gen = IdentifyLocationReportGenerator(
            identify_location_result=sample_identify_location_result,
            request_id="integration-test-1",
        )
        
        pdf_bytes = gen.generate()
        
        # Verify PDF
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Should be reasonably sized
        assert pdf_bytes[:4] == b'%PDF'
        
        # Verify it contains expected text
        pdf_text = pdf_bytes.decode('latin1', errors='ignore')
        assert 'Miami' in pdf_text
        assert 'Location' in pdf_text
    
    def test_clone_success_full_workflow(self, sample_clone_success_response):
        """Test complete Clone Success report generation workflow"""
        gen = CloneSuccessReportGenerator(
            clone_success_response=sample_clone_success_response,
            request_id="integration-test-2",
        )
        
        pdf_bytes = gen.generate()
        
        # Verify PDF
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes[:4] == b'%PDF'
        
        # Verify it contains expected content
        pdf_text = pdf_bytes.decode('latin1', errors='ignore')
        assert 'Panera' in pdf_text or 'clone' in pdf_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
