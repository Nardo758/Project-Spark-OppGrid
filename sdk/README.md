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

# Get a specific opportunity by integer ID
opp = client.opportunities.get(42)
print(opp.description)

# List market trends
trends = client.trends.list(region="north_america", days=14)
for t in trends["data"]:
    print(f"{t.trend_name} (strength: {t.trend_strength})")

# Market overview (grouped by category)
markets = client.markets.list()

# Market intelligence for a specific region
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

Returns opportunities ordered by AI opportunity score (highest first).

| Parameter    | Type  | Default | Description                              |
|-------------|-------|---------|------------------------------------------|
| `category`  | `str` | `None`  | Filter by category (partial match)       |
| `city`      | `str` | `None`  | Filter by city name (partial match)      |
| `region`    | `str` | `None`  | Filter by region / state (partial match) |
| `min_score` | `int` | `None`  | Minimum AI opportunity score (0–100)     |
| `page`      | `int` | `1`     | Page number (1-indexed)                  |
| `limit`     | `int` | `20`    | Results per page (max 100)               |

Returns a dict with `data` (list of `Opportunity` objects), `total`, `page`, `limit`, `has_next`.

#### `.get(opportunity_id)` → `Opportunity`

Fetch a single opportunity by its integer ID.

| Parameter        | Type  | Description              |
|-----------------|-------|--------------------------|
| `opportunity_id` | `int` | Integer ID of the record |

---

### `client.trends`

#### `.list(**kwargs)` → `dict`

Returns AI-detected market trends ordered by trend strength.

| Parameter      | Type  | Default | Description                      |
|----------------|-------|---------|----------------------------------|
| `category`     | `str` | `None`  | Filter by category (partial match) |
| `min_strength` | `int` | `None`  | Minimum trend strength (0–100)   |
| `page`         | `int` | `1`     | Page number (1-indexed)          |
| `limit`        | `int` | `20`    | Results per page (max 100)       |

Returns a dict with `data` (list of `Trend` objects), `total`, `page`, `limit`, `has_next`.

---

### `client.markets`

#### `.list()` → `dict`

Get aggregated market intelligence grouped by category.
Returns a dict with `data` (list of `Market` objects) and `total`.

#### `.get(region)` → `dict`

Get market intelligence for opportunities in a specific region.
`region` is matched as a partial, case-insensitive string
(e.g. `"north_america"`, `"europe"`, `"california"`).
Returns a dict with `data` (list of `Market` objects) and `total`.

---

## Data Classes

### `Opportunity`

| Field                    | Type              | Description                  |
|--------------------------|-------------------|------------------------------|
| `id`                     | `int`             | Opportunity ID               |
| `title`                  | `str`             | Opportunity title            |
| `description`            | `str \| None`     | Full description             |
| `category`               | `str \| None`     | Market category              |
| `city`                   | `str \| None`     | City                         |
| `region`                 | `str \| None`     | Region / state               |
| `ai_opportunity_score`   | `int \| None`     | AI score 0–100               |
| `ai_market_size_estimate`| `str \| None`     | Market size range            |
| `ai_target_audience`     | `str \| None`     | Target audience description  |
| `ai_competition_level`   | `str \| None`     | low / medium / high          |
| `growth_rate`            | `float \| None`   | Growth rate (%)              |
| `created_at`             | `str \| None`     | ISO 8601 creation timestamp  |

### `Trend`

| Field               | Type            | Description                    |
|---------------------|-----------------|--------------------------------|
| `id`                | `int`           | Trend ID                       |
| `trend_name`        | `str`           | Trend name                     |
| `trend_strength`    | `int`           | Strength score 0–100           |
| `category`          | `str \| None`   | Market category                |
| `opportunities_count` | `int`         | Related opportunities          |
| `growth_rate`       | `float \| None` | Growth rate (%)                |
| `detected_at`       | `str \| None`   | ISO 8601 detection timestamp   |

### `Market`

| Field                | Type            | Description                     |
|---------------------|-----------------|---------------------------------|
| `category`           | `str`           | Market category                 |
| `total_opportunities`| `int`           | Total opportunities in category |
| `avg_score`          | `float \| None` | Average AI opportunity score    |
| `top_regions`        | `list[str]`     | Top geographic regions          |

---

## Error Handling

```python
from oppgrid import OppGrid, AuthenticationError, RateLimitError, NotFoundError, OppGridError

client = OppGrid(api_key="og_live_...")

try:
    opp = client.opportunities.get(99999)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
except NotFoundError:
    print("Opportunity not found")
except OppGridError as e:
    print(f"API error {e.status_code}: {e.message}")
```

| Exception             | HTTP Status | Description                              |
|-----------------------|-------------|------------------------------------------|
| `AuthenticationError` | 401         | Missing, invalid, or expired API key     |
| `NotFoundError`       | 404         | Resource does not exist                  |
| `RateLimitError`      | 429         | Too many requests — check `retry_after`  |
| `OppGridError`        | 4xx / 5xx   | Any other API error (base exception)     |

## Requirements

- Python 3.8+
- `requests >= 2.28.0`

## License

MIT
