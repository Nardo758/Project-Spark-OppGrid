# OppGrid Python SDK

Official Python client for the [OppGrid Public API v1](https://oppgrid.com/developer).

## Installation

```bash
pip install -e sdk/
```

Or from the repo root:

```bash
pip install -e .
```

## Quick Start

```python
from oppgrid import OppGrid

client = OppGrid(api_key="og_live_...")

# List opportunities (with filters)
result = client.opportunities.list(min_score=70, page=1)
for opp in result["data"]:
    print(f"{opp.title} — Score: {opp.ai_opportunity_score}")

# Get a specific opportunity
opp = client.opportunities.get("123")
print(opp.description)

# List market trends
trends = client.trends.list(region="north_america", days=14)

# Market overview
markets = client.markets.list()

# Regional breakdown
market = client.markets.get("north_america")
```

## Configuration

| Parameter  | Type  | Default                         | Description                              |
|------------|-------|---------------------------------|------------------------------------------|
| `api_key`  | `str` | **required**                    | Your API key (`og_live_…` or `og_test_…`) |
| `base_url` | `str` | `https://api.oppgrid.com/v1`    | Override for local/staging environments  |
| `timeout`  | `int` | `30`                            | Request timeout in seconds               |

### Local development

```python
client = OppGrid(
    api_key="og_live_...",
    base_url="http://localhost:8000/v1",
)
```

## Resources

### `client.opportunities`

#### `.list(**kwargs)` → `dict`

| Parameter    | Type    | Default                  | Description                              |
|-------------|---------|--------------------------|------------------------------------------|
| `category`   | `str`   | `None`                   | Filter by category (e.g. `"fintech"`)    |
| `city`       | `str`   | `None`                   | Filter by city                           |
| `state`      | `str`   | `None`                   | Filter by US state abbreviation          |
| `min_score`  | `int`   | `None`                   | Minimum signal quality score (0–100)     |
| `page`       | `int`   | `1`                      | Page number                              |
| `per_page`   | `int`   | `20`                     | Results per page (max 100)               |
| `sort_by`    | `str`   | `"signal_quality_score"` | Field to sort by                         |
| `sort_order` | `str`   | `"desc"`                 | Sort direction: `"asc"` or `"desc"`      |

Returns a dict with `data` (list of `Opportunity` objects), `pagination`, and `meta`.

#### `.get(opportunity_id, include_sources=False)` → `Opportunity`

Fetch a single opportunity by UUID. Set `include_sources=True` to include raw source
data (Professional+ tier required).

---

### `client.trends`

#### `.list(**kwargs)` → `dict`

| Parameter      | Type    | Default | Description                         |
|----------------|---------|---------|-------------------------------------|
| `category`     | `str`   | `None`  | Filter by category                  |
| `region`       | `str`   | `None`  | Filter by region                    |
| `min_velocity` | `float` | `None`  | Minimum trend velocity              |
| `days`         | `int`   | `30`    | Look-back period in days            |
| `page`         | `int`   | `1`     | Page number                         |
| `per_page`     | `int`   | `20`    | Results per page                    |

---

### `client.markets`

#### `.list()` → `dict`

Get an overview of all tracked geographic markets.

#### `.get(region, category=None, include_heatmap=False)` → `dict`

Get detailed market intelligence for a region (e.g. `"north_america"`, `"europe"`).
`include_heatmap=True` requires Enterprise tier.

---

## Error Handling

```python
from oppgrid import OppGrid, AuthenticationError, RateLimitError, NotFoundError, OppGridError

client = OppGrid(api_key="og_live_...")

try:
    opp = client.opportunities.get("non-existent-id")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
except NotFoundError:
    print("Opportunity not found")
except OppGridError as e:
    print(f"API error {e.status_code}: {e.message}")
```

| Exception           | HTTP Status | Description                              |
|---------------------|-------------|------------------------------------------|
| `AuthenticationError` | 401       | Missing, invalid, or expired API key     |
| `NotFoundError`     | 404         | Resource does not exist                  |
| `RateLimitError`    | 429         | Too many requests — check `retry_after`  |
| `OppGridError`      | 4xx / 5xx   | Any other API error (base exception)     |

## Requirements

- Python 3.8+
- `requests >= 2.28.0`

## License

MIT
