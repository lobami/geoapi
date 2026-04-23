# Toroto — Architecture & Design Decisions

## Overview

Toroto is a geospatial intelligence platform for territorial interventions. It ingests operational records with spatial coordinates and exposes them through deterministic PostGIS queries, a REST API, and a natural-language interface backed by an LLM intent layer.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  User (Browser)                                             │
│                                                             │
│  ┌──────────────┐    ┌────────────────────────────────┐    │
│  │  Map + Filters│    │  Natural-Language Assistant     │    │
│  │  (MapLibre GL)│    │  (question → /geospatial/ask)  │    │
│  └──────┬───────┘    └───────────────┬────────────────┘    │
└─────────┼───────────────────────────-┼────────────────────-┘
          │ REST (HTTPS / Cloudflare)  │
          ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI (Python 3.12)                                      │
│                                                             │
│  ┌──────────────────┐    ┌────────────────────────────┐    │
│  │  Geospatial      │    │  NL Query Service           │    │
│  │  Query Service   │    │                             │    │
│  │                  │    │  1. LLM (Fyra / Claude)     │    │
│  │  ST_Distance     │    │     → structured GeoIntent  │    │
│  │  ST_DWithin      │    │  2. Pydantic validation      │    │
│  │  ST_Within       │    │  3. Heuristic fallback       │    │
│  └────────┬─────────┘    └──────────────┬─────────────┘    │
│           │                             │                   │
│           └──────────────┬──────────────┘                   │
│                          ▼                                   │
│                ┌─────────────────┐                          │
│                │  PostGIS 3.4    │                          │
│                │  PostgreSQL 16  │                          │
│                │                 │                          │
│                │  interventions  │ ← spatial index (GIST)  │
│                │  areas          │ ← polygon references    │
│                └─────────────────┘                          │
└─────────────────────────────────────────────────────────────┘

Deployment: VPS (Docker) + Cloudflare Pages (frontend) + Cloudflare edge proxy (TLS)
CI/CD: GitHub Actions → Docker build → VPS redeploy
```

---

## Database Schema

### `interventions`
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR (PK) | e.g. `iv_001` |
| type, subtype | VARCHAR | indexed — `gavion`, `reforestacion`, etc. |
| status | VARCHAR | indexed — `planned`, `in_progress`, `completed`, `validated` |
| project_id, region | VARCHAR | indexed for filter queries |
| lat, lon | NUMERIC | raw coordinates (stored for export) |
| geom | GEOMETRY(Point, 4326) | PostGIS spatial column, GIST-indexed |
| quality_score | FLOAT | 0–1 operational quality metric |
| date, timestamp | DATE / TIMESTAMP | for time-range filtering |
| metrics, metadata_json | JSONB | per-subtype measurements |

### `areas`
| Column | Type | Notes |
|--------|------|-------|
| area_id | VARCHAR (PK) | `zone_a`, `zone_b`, `zone_c` |
| name | VARCHAR | human-readable label |
| geom | GEOMETRY(Polygon, 4326) | GIST-indexed for ST_Within |
| geometry_json | JSONB | GeoJSON copy for frontend rendering |

Both tables use WGS84 (SRID 4326) and geography-cast operations for accurate metric distances.

---

## Geospatial Query Strategy

All spatial operations run inside PostGIS. The application layer never attempts to compute distances or containment in Python — it only constructs parameterized queries.

### 1. Nearest neighbor

```sql
ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
LIMIT 1
```

The `<->` operator uses the GIST spatial index for efficient nearest-neighbor search without a full table scan.

### 2. Within radius

```sql
WHERE ST_DWithin(geom::geography,
                 ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                 :radius_m)
```

`ST_DWithin` on geography columns uses meters directly, preserving accuracy across Mexico's full extent.

### 3. Within polygon

```sql
WHERE ST_Within(geom, (SELECT geom FROM areas WHERE area_id = :area_id))
```

Preloaded polygon areas allow containment checks without per-request geometry parsing.

---

## AI / Natural Language Layer

### Design decision: intent extraction, not SQL generation

The LLM is given a bounded task: classify the question into one of six allowed intents and extract structured parameters. It never produces SQL. Execution is fully deterministic — the same intent always runs the same parameterized PostGIS query.

**Why this matters:**
- No prompt injection path to arbitrary query execution
- Outputs are Pydantic-validated before reaching the database
- The model can be swapped (Fyra OSS → Claude → any OpenAI-compatible API) without changing query logic
- The heuristic fallback makes the system usable even without a live model key

### Intent flow

```
User question
     │
     ▼
LLM (gpt-oss-20b / configurable)
  → JSON: { intent, lat, lon, radius_km, area_id, place, filters, explanation }
     │
     ▼
Pydantic GeoIntent validation
     │  (if model unavailable or fails)
     ├──────────────────────────────→ Heuristic parser (regex + keyword matching)
     │
     ▼
Geospatial query service
     │
     ▼
PostGIS result → structured API response
```

### Allowed intents

| Intent | Query executed |
|--------|---------------|
| `nearest` | ST_Distance ordered ASC, LIMIT 1, from lat/lon |
| `nearest_to_place` | Same, from a pre-defined Mexican state centroid |
| `farthest_from_place` | ST_Distance ordered DESC, LIMIT 1 |
| `within_radius` | ST_DWithin with km → m conversion |
| `within_area` | ST_Within against a named polygon |
| `count_by_region` | GROUP BY region with optional subtype/status filters |

---

## Trade-offs

| Dimension | Decision | Consequence |
|-----------|----------|-------------|
| **Spatial DB** | PostGIS over a pure-Python spatial lib (Shapely) | Correct geodetic math, scales to millions of rows; adds operational complexity (PostGIS extension) |
| **AI approach** | Intent extraction vs. text-to-SQL | Safer and testable; limits query flexibility (only 6 intents) |
| **Model size** | gpt-oss-20b (Fyra) over frontier model | Lower cost and latency; slightly worse on ambiguous or multilingual edge cases |
| **Heuristic fallback** | Always compiled, used when model is unavailable | Resilient system; heuristic has lower recall on complex queries |
| **Monorepo** | Single repo (api + web + infra) | Easier coordination; would split into dedicated repos at team scale |
| **Cloudflare Pages** | Static frontend CDN | Zero-cost global distribution; no SSR |

---

## Scalability Path

### Horizontal query scaling
- Read replicas in PostgreSQL for query-heavy workloads
- Connection pooling via PgBouncer in front of PostGIS
- Spatial GIST indexes already in place; partitioning by `region` or `date` as the dataset grows

### AI layer
- The LLM call is stateless — horizontally scalable behind any load balancer
- Provider abstraction: the `_fyra_intent()` function is the only integration point; swap the URL and model name to move to Claude, OpenAI, or a local Ollama instance
- Caching: identical questions can be cached at the intent level (Redis + a deterministic cache key on the normalized question) to eliminate repeat model calls

### Data ingestion
- The current seed script is a one-shot loader; production path is a streaming ingestion pipeline (Kafka → consumer → PostGIS COPY) or a batch ETL via Airflow
- GeoJSON uploads through an admin API with ST_GeomFromGeoJSON for new polygon areas

### Observability
- Structured logging on every `/ask` request: intent, source (model vs heuristic), latency
- Metric: model_used (fyra | heuristic), intent type distribution, query latency p95
- Audit trail for AI-interpreted queries (stored intent JSON alongside the user question)

---

## Future evolution

1. **Multi-turn queries** — maintain session context so follow-up questions like "¿y las validadas?" refine the previous result
2. **Polygon uploads** — admin endpoint to POST GeoJSON and register new reference areas
3. **Richer intent set** — add `timeline` (interventions over time) and `compare_regions` (side-by-side aggregates)
4. **Provider abstraction** — wrap the LLM client behind a `ModelProvider` interface with pluggable backends (Fyra, Claude, local Ollama)
5. **Role-based access** — project-scoped API keys so operators only see interventions from their project
6. **Export** — GeoJSON / CSV export endpoints for GIS desktop integration
