# Phase 4 Part 2: Dataset Marketplace - Quick Reference

## Component Usage

### Marketplace Page
```typescript
// URL: /marketplace
import Marketplace from '@/pages/Marketplace'

// Features:
- Browse all datasets
- Filter by: category, vertical, city
- Sort by: price, newest, popular
- Search by name
- Responsive grid layout
```

### DatasetCard Component
```typescript
// URL: /components/DatasetCard.tsx
import DatasetCard from '@/components/DatasetCard'

interface Dataset {
  id: string
  name: string
  description: string
  dataset_type: 'opportunities' | 'markets' | 'trends' | 'raw_data'
  vertical?: string | null
  city?: string | null
  price_cents: number      // 9900 = $99.00
  record_count: number     // 2500 = "2.5K records"
  data_freshness: string   // ISO date string
  created_at: string       // ISO date string
  is_active: boolean
}

// Usage:
<DatasetCard dataset={dataset} />

// Events:
- Preview button: Opens DatasetPreview modal
- Purchase button: Routes to /datasets/{id}/checkout
- Auto-redirects to signin if not authenticated
```

### DatasetPreview Modal
```typescript
// Component: /components/DatasetPreview.tsx
import DatasetPreview from '@/components/DatasetPreview'

interface DatasetPreviewProps {
  datasetId: string
  datasetName: string
  onClose: () => void
  onCheckout: () => void
}

// Usage:
<DatasetPreview 
  datasetId="dataset-123"
  datasetName="Coffee Shops NYC"
  onClose={() => setShowPreview(false)}
  onCheckout={() => navigate('/datasets/dataset-123/checkout')}
/>

// Expected API Response (GET /api/v1/datasets/{id}/preview):
{
  metadata: {
    record_count: 2500,
    data_freshness: "2026-04-30T10:00:00Z",
    vertical: "Coffee",
    city: "New York"
  },
  rows: [
    { name: "Brew & Bean", address: "123 Main St", rating: 4.5 },
    // ... 4 more rows
  ],
  columns: ["name", "address", "rating", "phone", "hours", ...]
}
```

### DatasetCheckout Page
```typescript
// URL: /datasets/:datasetId/checkout
import DatasetCheckout from '@/pages/DatasetCheckout'

// Features:
- Display dataset info and price
- Terms of use acceptance
- Payment method (Stripe placeholder)
- Purchase completion with download link
- Handles auth redirects

// Expected API Responses:

// GET /api/v1/datasets/{id}
{
  id: "uuid",
  name: "Coffee Shops NYC",
  description: "2500 active coffee shops...",
  dataset_type: "opportunities",
  vertical: "Coffee",
  city: "New York",
  price_cents: 9900,
  record_count: 2500,
  data_freshness: "2026-04-30T10:00:00Z",
  created_at: "2026-04-20T00:00:00Z",
  is_active: true
}

// POST /api/v1/datasets/{id}/purchase
// Request:
{
  payment_method: "stripe"
}

// Response:
{
  purchase_id: "uuid",
  dataset_id: "uuid",
  download_url: "https://s3.amazonaws.com/...",
  expires_at: "2026-05-30T10:00:00Z",
  status: "completed"
}
```

## API Endpoints

### GET /api/v1/datasets
Fetch all datasets with optional filtering

**Query Parameters:**
```
- search: string (search dataset names)
- dataset_type: string (opportunities|markets|trends|raw_data)
- vertical: string (Coffee, Coworking, Gyms, etc.)
- city: string (San Francisco, New York, Los Angeles, etc.)
- sort_by: string (price_asc|price_desc|newest|popular)
- limit: number (default: 100)
- offset: number (default: 0)
```

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Dataset Name",
    "description": "Description",
    "dataset_type": "opportunities",
    "vertical": "Coffee",
    "city": "San Francisco",
    "price_cents": 9900,
    "record_count": 2500,
    "data_freshness": "2026-04-30T10:00:00Z",
    "created_at": "2026-04-20T00:00:00Z",
    "is_active": true
  }
]
```

### GET /api/v1/datasets/{id}
Get dataset details

**Response:**
Same as above for single dataset

### GET /api/v1/datasets/{id}/preview
Get preview data (first 5 rows)

**Auth:** Required (Bearer token)

**Response:**
```json
{
  "metadata": {
    "record_count": 2500,
    "data_freshness": "2026-04-30T10:00:00Z",
    "vertical": "Coffee",
    "city": "New York"
  },
  "rows": [
    { "col1": "value1", "col2": "value2" },
    // ... up to 5 rows
  ],
  "columns": ["col1", "col2", "col3", ...]
}
```

### POST /api/v1/datasets/{id}/purchase
Process dataset purchase

**Auth:** Required (Bearer token)

**Request:**
```json
{
  "payment_method": "stripe"
}
```

**Response:**
```json
{
  "purchase_id": "uuid",
  "dataset_id": "uuid",
  "download_url": "https://...",
  "expires_at": "2026-05-30T10:00:00Z",
  "status": "completed"
}
```

## Testing Scenarios

### 1. Browse Marketplace
```bash
# Navigate to /marketplace
# Expected: Loads dataset grid with filter sidebar
# Test filters individually and in combination
# Test search by typing dataset name
# Verify sorting changes dataset order
```

### 2. Preview Dataset
```bash
# Click "Preview" on any dataset card
# Not authenticated: Should redirect to /signin
# Authenticated: Should open modal with first 5 rows
# Close button: Closes modal
# "Download Full Dataset" button: Routes to checkout
```

### 3. Complete Purchase
```bash
# Navigate to /datasets/{id}/checkout
# Not authenticated: Should redirect to /signin
# Authenticated: Display dataset info and price
# Uncheck terms: Purchase button disabled
# Check terms: Purchase button enabled
# Click purchase: Shows loading state, then success
# Success page: Shows download link and expiration date
```

### 4. Responsive Design
```bash
# Mobile (375px): Single column, collapsible filters
# Tablet (768px): 2 columns, sidebar togglable
# Desktop (1024px): 3+ columns, fixed sidebar
# Test on actual devices or DevTools
```

## Category Styling Reference

```typescript
const CATEGORY_COLORS = {
  opportunities: { 
    bg: 'bg-purple-900/30', 
    text: 'text-purple-300',
    icon: '💡'
  },
  markets: { 
    bg: 'bg-blue-900/30', 
    text: 'text-blue-300',
    icon: '📊'
  },
  trends: { 
    bg: 'bg-green-900/30', 
    text: 'text-green-300',
    icon: '📈'
  },
  raw_data: { 
    bg: 'bg-orange-900/30', 
    text: 'text-orange-300',
    icon: '📦'
  },
}
```

## Price Formatting

```typescript
// Cents to dollar format:
9900 → $99.00
10050 → $100.50
500 → $5.00
99 → $0.99

// Record count formatting:
1000000 → 1.0M records
500000 → 500.0K records
2500 → 2.5K records
500 → 500 records
```

## Time Formatting

```typescript
// Data freshness display:
< 1 hour → "Just now"
1-24 hours → "2h ago", "12h ago"
1-30 days → "5d ago", "15d ago"
1-12 months → "3mo ago", "6mo ago"
> 12 months → "1y ago", "2y ago"
```

## Tailwind Classes Used

**Dark Background:**
```
bg-gray-900    # Darkest
bg-gray-800    # Dark
bg-gray-700    # Medium
bg-gray-600    # Light
```

**Borders:**
```
border-gray-700   # Darker borders
border-gray-600   # Light borders
```

**Text:**
```
text-white         # Primary text
text-gray-300      # Secondary text
text-gray-400      # Tertiary text
```

**Interactive:**
```
hover:bg-gray-700    # Hover background
hover:border-gray-600 # Hover border
transition-colors    # Smooth transitions
focus:outline-none   # Remove focus outline
```

## Common Issues & Solutions

**Issue:** Purchase button always disabled
- **Solution:** Check that checkbox for terms is properly connected to state

**Issue:** Preview modal doesn't show data
- **Solution:** Check GET /api/v1/datasets/{id}/preview endpoint returns correct format

**Issue:** Unauthenticated users can't see anything
- **Solution:** Marketplace is public, only preview/checkout require auth. Check routes.

**Issue:** Responsive layout broken on mobile
- **Solution:** Check Tailwind breakpoints in CSS, verify mobile classes applied

**Issue:** Filters not updating results
- **Solution:** Check query parameters sent to GET /api/v1/datasets API

## Git Commit Reference

```
Commit: e155a7f
Message: Add Phase 4 Part 2: Dataset marketplace UI

Changes:
- frontend/src/pages/Marketplace.tsx (NEW)
- frontend/src/components/DatasetCard.tsx (NEW)
- frontend/src/components/DatasetPreview.tsx (NEW)
- frontend/src/pages/DatasetCheckout.tsx (NEW)
- frontend/src/App.tsx (MODIFIED - added routes)
- frontend/src/components/Navbar.tsx (MODIFIED - added link)

Total additions: 1,208 lines
```

## Related Files

**Backend Models:**
- `/backend/app/models/dataset.py` - Dataset and DatasetPurchase models

**Backend Routes (To be created):**
- `/backend/app/routers/datasets.py` - Dataset endpoints

**Frontend Configuration:**
- `/frontend/package.json` - Dependencies already included
- `/frontend/tailwind.config.js` - Styling configuration

---

**For detailed implementation info, see:** `PHASE4_PART2_MARKETPLACE_FRONTEND.md`
