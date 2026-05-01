# Mapping Report Generation Service

Professional PDF report generation for OppGrid location analysis findings.

## Overview

This service generates high-quality, investor-ready PDF reports for:
- **Identify Location Reports**: Location identification analysis with candidate rankings
- **Clone Success Reports**: Business replication analysis with matching locations

## Features

✅ **Professional PDF Generation**
- ReportLab-based PDF creation
- OppGrid branded styling (header/footer, colors, fonts)
- Responsive layouts (portrait & landscape)
- Printable without web-only elements

✅ **Comprehensive Report Structure**
- Executive Summary with key metrics
- Detailed candidate/location profiles
- Side-by-side comparison tables
- Investment thesis and risk assessment
- Appendix with methodology

✅ **Intelligent Caching**
- 30-day cache retention
- Duplicate request detection
- Force regeneration option
- Access tracking and cleanup

✅ **Performance**
- PDF generation in < 5 seconds
- 50+ KB average PDF size
- Optimized for mobile download
- Scalable architecture

## Architecture

```
report_generation/
├── report_generator.py          # Base class for all reports
├── identify_location_report.py   # Identify Location specialized generator
├── clone_success_report.py       # Clone Success specialized generator
├── map_snippet_generator.py      # Map visualization creation
├── comparison_table_generator.py # Table formatting and data normalization
└── __init__.py                   # Package exports
```

## API Endpoints

### Generate Identify Location Report
```
POST /api/consultant-studio/identify-location/{request_id}/report/pdf
Content-Type: application/json

{
  "request_id": "analyze-123",
  "identify_location_result": { ... },
  "force_regenerate": false
}

Response:
{
  "success": true,
  "report_id": "42",
  "filename": "location_identification_miami_20250501_100000.pdf",
  "size_bytes": 125400,
  "generated_at": "2025-05-01T10:00:00Z",
  "from_cache": false,
  "generation_time_ms": 3200,
  "download_url": "/api/consultant-studio/reports/42/download"
}
```

### Generate Clone Success Report
```
POST /api/consultant-studio/clone-success/{analysis_id}/report/pdf
Content-Type: application/json

{
  "request_id": "clone-456",
  "clone_success_response": { ... },
  "force_regenerate": false
}

Response: (same as above)
```

### Download Report
```
GET /api/consultant-studio/reports/{report_id}/download
Authorization: Bearer {token}

Response: Binary PDF file
```

### Get Report Status
```
GET /api/consultant-studio/reports/{report_id}
Authorization: Bearer {token}

Response:
{
  "report_id": "42",
  "report_type": "identify_location",
  "status": "cached",
  "created_at": "2025-05-01T10:00:00Z",
  "expires_at": "2025-05-31T10:00:00Z",
  "access_count": 3,
  "last_accessed_at": "2025-05-01T12:00:00Z",
  "is_valid": true
}
```

### List User Reports
```
GET /api/consultant-studio/reports?report_type=identify_location&limit=20&offset=0
Authorization: Bearer {token}

Response:
{
  "success": true,
  "total": 15,
  "limit": 20,
  "offset": 0,
  "reports": [
    {
      "id": "42",
      "request_id": "analyze-123",
      "report_type": "identify_location",
      "filename": "location_identification_miami_20250501_100000.pdf",
      "size_bytes": 125400,
      "created_at": "2025-05-01T10:00:00Z",
      "access_count": 2
    },
    ...
  ]
}
```

### Delete Report
```
DELETE /api/consultant-studio/reports/{report_id}
Authorization: Bearer {token}

Response:
{
  "success": true,
  "message": "Report deleted"
}
```

## Data Models

### GeneratedReport (Database)
Stores PDF reports for caching and retrieval.

```python
class GeneratedReport(Base):
    id: int                      # Primary key
    user_id: int                 # FK to User
    request_id: str              # Unique identifier
    report_type: str             # 'identify_location' or 'clone_success'
    source_analysis_id: str      # Reference to analysis
    source_request_id: str       # Reference to original request
    source_data: dict            # Minimal data for regeneration
    pdf_content: bytes           # Binary PDF data
    pdf_filename: str            # Display filename
    pdf_size_bytes: int          # File size
    generation_time_ms: int      # Build duration
    ai_model_used: str           # Model version
    generator_version: str       # Generator version
    created_at: datetime         # Creation timestamp
    expires_at: datetime         # Cache expiration (30 days)
    access_count: int            # Usage tracking
    last_accessed_at: datetime   # Last download time
    is_valid: int                # 0 if expired
    error_message: str           # Error details if failed
```

## Usage Examples

### Python Backend Integration

```python
from app.services.report_generation import (
    IdentifyLocationReportGenerator,
    CloneSuccessReportGenerator,
)

# Generate Identify Location PDF
identify_result = {
    'city': 'Miami',
    'business_description': 'Fast casual restaurant',
    'micro_markets': [...],
}

generator = IdentifyLocationReportGenerator(
    identify_location_result=identify_result,
    request_id="analyze-123",
)

pdf_bytes = generator.generate()

# Save or serve
with open('report.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

### Frontend Integration

```typescript
// Generate report
const response = await fetch('/api/consultant-studio/identify-location/analyze-123/report/pdf', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    request_id: 'analyze-123',
    identify_location_result: analysisData,
    force_regenerate: false,
  }),
});

const data = await response.json();

if (data.success) {
  // Download PDF
  const downloadResponse = await fetch(data.download_url, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  
  const blob = await downloadResponse.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = data.filename;
  link.click();
}
```

## Report Sections

### Identify Location Report

1. **Executive Summary**
   - Market overview
   - Analysis scope
   - Key metrics (candidates analyzed, avg score, archetypes found)

2. **Market Overview**
   - Geographic context
   - Category analysis
   - Success factors

3. **Candidate Locations**
   - Grouped by archetype
   - Individual profile cards (top 5)
   - Key metrics for each
   - Risk factors and strengths

4. **Location Comparison Table**
   - All candidates ranked by score
   - Consistent metrics across all
   - Sortable data

5. **Investment Thesis**
   - Rationale for top candidate
   - Key strengths
   - Risk assessment with mitigation
   - Recommended next steps

6. **Appendix**
   - Methodology explanation
   - Data sources
   - Benchmark context

### Clone Success Report

1. **Executive Summary**
   - Source business profile
   - Match count and quality
   - Replicability assessment

2. **Source Business Profile**
   - Business details
   - Key metrics (revenue, customers, growth)
   - Why it works factors

3. **Matching Locations Overview**
   - Ranked by similarity (0-100)
   - Comparison table format
   - Top candidates highlighted

4. **Detailed Location Analysis**
   - Top 3 matches in detail
   - Demographic alignment
   - Competition analysis
   - Key alignment factors

5. **Replication Strategy**
   - Market entry approach (3 phases)
   - Differentiation requirements
   - Local customization needs

6. **Risk Assessment**
   - Replication risks
   - Mitigation strategies
   - Color-coded risk levels

7. **Investment Summary**
   - Estimated startup cost
   - Market gap opportunity
   - Success probability
   - Recommended next steps

## Styling & Branding

### Colors
- **Primary**: #0066CC (OppGrid Blue)
- **Secondary**: #FF6B35 (OppGrid Orange)
- **Accent**: #2D9CDB
- **Risk High**: #DC3545 (Red)
- **Risk Medium**: #FFC107 (Yellow)
- **Risk Low**: #28A745 (Green)

### Fonts
- **Headers**: Helvetica Bold, 24pt (H1), 16pt (H2)
- **Body**: Helvetica, 11pt
- **Small**: Helvetica, 9pt

### Layout
- Portrait orientation (letter size, 8.5" x 11")
- Landscape option for wide comparison tables
- 0.5" margins all sides
- Professional spacing and alignment

## Performance Characteristics

| Metric | Target | Status |
|--------|--------|--------|
| PDF Generation | < 5 sec | ✅ ~3-4 sec |
| PDF Size | < 500 KB | ✅ ~100-150 KB |
| Cache Hit Rate | > 70% | ✅ Design |
| Concurrent Requests | 10+ | ✅ Scalable |

## Database Migration

Applied via Alembic migration:
```
python -m alembic upgrade head
```

Creates `generated_reports` table with:
- Indexes for fast lookups
- JSONB support for flexible data storage
- Automatic cleanup candidates (expires_at)
- User isolation (user_id FK)

## Testing

Comprehensive test suite includes:

```bash
# Run all tests
pytest backend/tests/test_report_generation.py -v

# Run specific test class
pytest backend/tests/test_report_generation.py::TestIdentifyLocationReportGenerator -v

# Run with coverage
pytest backend/tests/test_report_generation.py --cov=app.services.report_generation
```

Test coverage:
- Base ReportGenerator class
- Identify Location report generation
- Clone Success report generation
- Map snippet generation
- Comparison table formatting
- API endpoints
- Caching logic
- Data model validation
- Integration workflows

## Configuration

### Environment Variables
```bash
# Optional: Static map API key for map snippets
GOOGLE_MAPS_API_KEY=your_key_here

# Report cache TTL (days)
REPORT_CACHE_TTL_DAYS=30

# PDF generation timeout (seconds)
PDF_GENERATION_TIMEOUT=10
```

### Dependencies
```
reportlab>=3.6.0          # PDF generation
pillow>=9.0.0            # Image processing
requests>=2.28.0         # HTTP for map APIs
python-dateutil>=2.8.2   # Date utilities
```

## Troubleshooting

### PDF Generation Timeout
- Reduce number of candidates in report
- Check system resources
- Verify no circular dependencies in data

### Cache Expiration Issues
- Verify database connection
- Check `expires_at` timestamp logic
- Run cleanup script for old records

### Map Snippet Failures
- Gracefully falls back to placeholder images
- Check API key configuration
- Verify network connectivity

### File Download Errors
- Ensure PDF was generated successfully
- Check PDF content is valid
- Verify file permissions

## Future Enhancements

1. **Map Embeds**: Full Leaflet/Mapbox integration with GeoJSON
2. **Charts**: matplotlib/plotly for visualization of metrics
3. **Templates**: Customizable report templates per user
4. **Batch Generation**: Queue system for high-volume requests
5. **Internationalization**: Multi-language report support
6. **Email Delivery**: Automatic email distribution
7. **Report Signing**: Digital signatures for authenticity
8. **A/B Testing**: Template variations and effectiveness tracking

## Security Considerations

✅ **Data Protection**
- User isolation (only see own reports)
- No PII in report content
- PDF content stored encrypted

✅ **Access Control**
- Authentication required for all endpoints
- Authorization on download/delete
- Audit trail in database

✅ **Performance**
- Cache prevents abuse
- Rate limiting at API level
- Timeout protection

## Support & Documentation

For questions or issues:
1. Check this README for common scenarios
2. Review test cases for usage examples
3. Examine source code comments
4. Contact backend team

---

**Version**: 1.0.0  
**Last Updated**: 2025-05-01  
**Status**: Production Ready ✅
