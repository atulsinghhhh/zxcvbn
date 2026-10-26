# WindSight

A day-ahead wind-generation forecast analytics dashboard for electricity trading teams. WindSight shows the best forecast that was legally available at a configurable decision cutoff and measures how accurate that forecast turned out to be against national actuals — covering the January 2026 trading period.

All data comes directly from the Elexon Balancing Mechanism Reporting Service (BMRS) API. No observations are invented or cached from static files.

> **AI assistance disclosure:** The backend business logic and frontend application logic were written by the Mine. AI assistance (Claude Sonnet 4.6 via Claude Code) was used for UI generation and in a small number of specific places during development. All API behaviour claims are based on live endpoint probing.

---

## Contents

- [Business problem](#business-problem)
- [Features](#features)
- [Architecture](#architecture)
- [Directory structure](#directory-structure)
- [Data sources](#data-sources)
- [Forecast cutoff and vintage selection](#forecast-cutoff-and-vintage-selection)
- [Accuracy metrics](#accuracy-metrics)
- [Local setup](#local-setup)
- [Docker Compose](#docker-compose)
- [Environment variables](#environment-variables)
- [API reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Limitations](#limitations)

---

## Business problem

A day-ahead electricity trader must decide how much wind generation to bank on for tomorrow before the N2EX/EPEX gate closure (approximately 11:00 UK local time). The decision is anchored to the latest WINDFOR vintage published at or before that cutoff. Selecting a forecast published after the cutoff would introduce look-ahead bias and invalidate the trading decision simulation.

WindSight answers two questions:

1. **What was the best forecast I could have used** for a given delivery date, given the decision cutoff?
2. **How accurate have those forecasts been** over the January 2026 analysis period?

---

## Features

- **Anti-look-ahead vintage selection** — only forecasts published at or before the configurable cutoff are eligible
- **Live Elexon data** — WINDFOR (hourly forecast) and FUELHH (half-hourly actuals) fetched on demand
- **Correct DST handling** — 23-hour spring-forward days and 25-hour fall-back days handled via `zoneinfo`
- **Honest missing-data treatment** — missing half-hours produce `null`, never zero; excluded from all metrics
- **MAE, RMSE, bias, percentiles** — over a common evaluation sample; formulas documented and unit-tested
- **Paginated interval table** — sortable per-hour forecast vs actual with signed and absolute errors
- **Historical accuracy view** — January 2026 day-by-day and aggregate metrics
- **Structured error handling** — 404 for no vintage, 502/503 for upstream failures; no stack traces exposed
- **Docker Compose** — single command to run the full stack locally

---

## Architecture

```
┌─────────────────────────────────┐
│  React 19 + Vite + Tailwind     │  frontend (port 8080 via nginx)
│  Recharts · shadcn/ui           │
└──────────────┬──────────────────┘
               │  /api/* proxied to backend
┌──────────────▼──────────────────┐
│  FastAPI + Uvicorn              │  backend (port 8000)
│                                 │
│  app/clients/     ← HTTP layer (httpx, retry, timeout)
│  app/domain/      ← Pure domain logic (no I/O)
│    timestamps.py  ← UTC/UK/DST utilities
│    vintage.py     ← Anti-look-ahead vintage selection
│    matcher.py     ← WINDFOR→FUELHH half-hour aggregation
│    evaluator.py   ← Top-level orchestrator
│  app/analytics/   ← Metric calculation (pure functions)
│  app/api/         ← Routes, schemas, service layer
└──────────────┬──────────────────┘
               │  HTTPS
┌──────────────▼──────────────────┐
│  Elexon BMRS API                │
│  /datasets/WINDFOR/stream       │
│  /datasets/FUELHH/stream        │
└─────────────────────────────────┘
```

**Key design choices:**

- Domain logic is pure (no I/O) so it is fully unit-testable without mocking
- Analytics runs after matching, over a typed list of `DeliveryHour` records; no raw API objects reach the metric layer
- The service layer wraps synchronous `httpx` calls in `run_in_threadpool` so they do not block FastAPI's async event loop
- All timestamps are UTC-aware internally; UK local conversion happens only at display boundaries

---

## Directory structure

```
wind-sight/
├── backend/
│   ├── app/
│   │   ├── analytics/         # Metric formulas (calculator.py, models.py)
│   │   ├── api/
│   │   │   ├── routes/        # One file per endpoint
│   │   │   ├── deps.py        # FastAPI dependency injection
│   │   │   ├── schemas.py     # Pydantic response models
│   │   │   └── service.py     # fetch + evaluate + calculate orchestration
│   │   ├── clients/           # Elexon HTTP clients (windfor, fuelhh, base)
│   │   ├── domain/            # Pure business logic
│   │   ├── models/            # Pydantic wire-format models (WINDFOR, FUELHH)
│   │   ├── config.py          # pydantic-settings configuration
│   │   ├── exceptions.py      # Domain exception hierarchy
│   │   └── main.py            # FastAPI app factory + exception handlers
│   ├── tests/                 # 203 pytest tests
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               # Fetch client and TypeScript types
│   │   ├── components/        # React components
│   │   ├── hooks/             # useWindSight, useOverview, useAccuracy
│   │   ├── lib/               # Formatters
│   │   └── test/              # 17 Vitest component tests
│   ├── nginx.conf             # Reverse-proxy for /api/*
│   ├── Dockerfile
│   └── package.json
├── docs/
│   ├── assumptions.md         # Documented assumptions and limitations
│   └── data_dictionary.md     # Field descriptions for WINDFOR and FUELHH
├── docker-compose.yml
├── .env.example               # Environment variable template
├── .gitignore
└── README.md
```

---

## Data sources

| Dataset | Endpoint | Description |
|---|---|---|
| **WINDFOR** | `/datasets/WINDFOR/stream` | National wind-power forecast, published roughly every 2–4 hours. Each vintage covers ~73 hourly delivery intervals (~3 days ahead). Unit: MW. |
| **FUELHH** | `/datasets/FUELHH/stream` | Half-hourly fuel-mix actuals filtered to `fuelType=WIND`. Each settlement period is 30 minutes. Unit: MW. |

Both endpoints are at `https://data.elexon.co.uk/bmrs/api/v1`. No authentication required. See `docs/data_dictionary.md` for field descriptions.

**National (metered) wind only.** Embedded generation is excluded from both datasets; the forecast and actual comparison is like-for-like.

---

## Forecast cutoff and vintage selection

The decision cutoff is `cutoff_hour:00` UK local time on the calendar day immediately preceding the delivery date. Default: **11:00 UK local** (approximating the N2EX/EPEX Spot day-ahead gate closure — this is a convention, not a claimed market rule).

```
delivery_date = 2026-01-15   →   cutoff = 2026-01-14T11:00:00Z  (GMT)
delivery_date = 2026-07-15   →   cutoff = 2026-07-14T10:00:00Z  (BST → UTC)
```

**Vintage selection rule:**

1. Fetch all WINDFOR records published in the 48-hour window ending at the cutoff.
2. Remove duplicate `(publishTime, startTime)` pairs — last occurrence wins.
3. Filter to records with `publishTime ≤ cutoff` (inclusive — a forecast published exactly at the cutoff was available).
4. Select the single latest `publishTime` among eligible records.
5. Return all records from that `publishTime` as the selected vintage.

A `404` is returned if no vintage is found at or before the cutoff.

**Half-hourly to hourly aggregation:** WINDFOR is hourly; FUELHH is half-hourly. Each delivery hour's actual is the arithmetic mean of the two FUELHH half-hours starting within that hour. If either half-hour is absent the actual for that hour is `null` and the hour is excluded from all error metrics.

---

## Accuracy metrics

All metrics are computed over the **common evaluation sample (CES)**: hours where both `forecast_mw` and `actual_mw` are non-`null` and finite.

**Sign convention:** `signed_error = forecast_mw − actual_mw`
- Positive → over-forecast (predicted more wind than was generated)
- Negative → under-forecast

| Metric | Formula | Notes |
|---|---|---|
| MAE | `(1/n) × Σ \|signed_error\|` | Always ≥ 0 |
| RMSE | `√((1/n) × Σ signed_error²)` | Penalises large errors more than MAE |
| Bias | `(1/n) × Σ signed_error` | Positive = systematic over-forecast |
| P90 abs error | Linear interpolation at 90th percentile | Same method as `numpy.percentile` default |

**Missing data is never imputed as zero.** Hours with missing forecast or actual are counted in `missing_forecast_hours` / `missing_actual_hours` and excluded from the CES. Non-finite values (NaN, ±∞) are counted in `invalid_hours` and also excluded.

---

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose (for the containerised path)

### Backend (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs at `http://localhost:8000/api/docs`.

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev
```

The dev server is at `http://localhost:5173`. Vite proxies `/api/*` to `http://localhost:8000`.

---

## Docker Compose

```bash
# From the repo root:
docker compose up --build
```

| Service | Port | URL |
|---|---|---|
| Frontend (nginx) | 8080 | `http://localhost:8080` |
| Backend (uvicorn) | 8000 | `http://localhost:8000/api/health` |

The frontend nginx container reverse-proxies `/api/*` to the backend. The backend waits until the healthcheck passes before the frontend starts (`depends_on: condition: service_healthy`).

To stop:

```bash
docker compose down
```

---

## Environment variables

Copy `.env.example` to `.env` (backend) and `frontend/.env` (frontend) and adjust as needed. **Never commit `.env` files with real credentials.**

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `WINDSIGHT_ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Elexon BMRS API base URL |
| `WINDSIGHT_HTTP_TIMEOUT_SECONDS` | `30.0` | Wall-clock timeout per HTTP request (seconds) |
| `WINDSIGHT_HTTP_MAX_RETRIES` | `3` | Max retry attempts for transient 5xx/429 errors |
| `WINDSIGHT_HTTP_RETRY_WAIT_SECONDS` | `1.0` | Initial backoff (doubles each attempt) |
| `WINDSIGHT_CACHE_TTL_SECONDS` | `900.0` | TTL for the in-memory Elexon response cache; `0` disables caching |
| `WINDSIGHT_CACHE_MAX_ENTRIES` | `512` | Max cached responses before LRU eviction |
| `WINDSIGHT_CORS_ORIGINS` | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins. Accepts a JSON array, a comma-separated string, or a single origin. **Must include the production frontend URL before deployment.** |
| `WINDSIGHT_CORS_ORIGIN_REGEX` | `https://zxcvbn-.*\.vercel\.app` | Regex for origins that vary per deploy (e.g. Vercel preview URLs) |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | *(empty)* | Backend base URL. Leave empty to use relative URLs (works with both Vite proxy and nginx proxy). Set to the full backend URL only when the frontend is deployed separately from the API. |

---

## API reference

All endpoints return JSON. Error responses follow `{"error": "<code>", "detail": "<message>"}`.

### `GET /api/health`

Liveness check. Used by the Docker healthcheck.

```bash
curl http://localhost:8000/api/health
```

```json
{"status": "ok", "version": "0.1.0"}
```

---

### `GET /api/forecast`

Returns the selected forecast vintage and per-hour forecast/actual pairs for a single delivery date.

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `delivery_date` | `YYYY-MM-DD` | Yes | — | UK delivery date |
| `cutoff_hour` | integer 0–23 | No | `11` | Decision cutoff hour in UK local time |

**Example:**

```bash
curl "http://localhost:8000/api/forecast?delivery_date=2026-01-15&cutoff_hour=11"
```

```json
{
  "delivery_date": "2026-01-15",
  "decision_cutoff_utc": "2026-01-14T11:00:00Z",
  "selected_vintage_utc": "2026-01-14T09:30:00Z",
  "metrics": {
    "total_hours": 24,
    "evaluation_hours": 22,
    "missing_forecast_hours": 0,
    "missing_actual_hours": 2,
    "invalid_hours": 0,
    "mae_mw": 312.4,
    "rmse_mw": 401.7,
    "bias_mw": -85.2,
    "max_abs_error_mw": 950.0,
    "min_abs_error_mw": 12.0,
    "p90_abs_error_mw": 720.0,
    "max_signed_error_mw": 400.0,
    "min_signed_error_mw": -950.0
  },
  "hours": [
    {
      "start_utc": "2026-01-15T00:00:00Z",
      "start_uk": "2026-01-15T00:00:00Z",
      "forecast_mw": 5200.0,
      "actual_mw": 4850.0,
      "signed_error_mw": 350.0,
      "abs_error_mw": 350.0
    }
  ]
}
```

**Status codes:** `200` OK · `404` no vintage at or before cutoff · `502` upstream error · `503` upstream unreachable

---

### `GET /api/accuracy`

Forecast accuracy metrics for each day in a date range (maximum 31 days).

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `from_date` | `YYYY-MM-DD` | Yes | — | Start of range, inclusive |
| `to_date` | `YYYY-MM-DD` | Yes | — | End of range, inclusive |
| `cutoff_hour` | integer 0–23 | No | `11` | Decision cutoff hour in UK local time |

**Example:**

```bash
curl "http://localhost:8000/api/accuracy?from_date=2026-01-01&to_date=2026-01-07"
```

```json
{
  "from_date": "2026-01-01",
  "to_date": "2026-01-07",
  "cutoff_hour": 11,
  "total_days": 7,
  "days_with_data": 6,
  "failed_dates": ["2026-01-01"],
  "days": [...]
}
```

Days where no vintage was available at or before the cutoff are listed in `failed_dates` and omitted from `days`. **Status codes:** `200` OK · `422` invalid range · `502/503` upstream error

---

### `GET /api/overview`

Aggregate accuracy over a date range, plus per-day breakdown. Defaults to January 2026.

**Query parameters:** same as `/api/accuracy` plus defaults `from_date=2026-01-01`, `to_date=2026-01-31`.

**Example:**

```bash
curl "http://localhost:8000/api/overview"
```

```json
{
  "from_date": "2026-01-01",
  "to_date": "2026-01-31",
  "cutoff_hour": 11,
  "total_days": 31,
  "days_with_data": 30,
  "failed_dates": ["2026-01-01"],
  "aggregate_metrics": {
    "evaluation_hours": 690,
    "mae_mw": 385.2,
    ...
  },
  "days": [...]
}
```

`aggregate_metrics` is computed over all evaluated hours pooled across the range (not an average of daily MAEs). `null` when no days have data.

---

### `GET /api/intervals`

Paginated per-hour forecast/actual pairs for a single delivery date.

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `delivery_date` | `YYYY-MM-DD` | Yes | — | UK delivery date |
| `cutoff_hour` | integer 0–23 | No | `11` | Decision cutoff hour |
| `offset` | integer ≥ 0 | No | `0` | Hours to skip |
| `limit` | integer 1–50 | No | `25` | Hours to return |

**Example:**

```bash
curl "http://localhost:8000/api/intervals?delivery_date=2026-01-15&offset=0&limit=10"
```

```json
{
  "delivery_date": "2026-01-15",
  "decision_cutoff_utc": "2026-01-14T11:00:00Z",
  "selected_vintage_utc": "2026-01-14T09:30:00Z",
  "total": 24,
  "offset": 0,
  "limit": 10,
  "hours": [...]
}
```

---

### `GET /api/health`

Already documented above. Used by Docker healthcheck and monitoring.

---

## Testing

### Backend

```bash
cd backend

# All tests (203)
.venv/bin/pytest tests/ -v

# Individual modules
.venv/bin/pytest tests/test_domain_vintage.py tests/test_domain_timestamps.py -v
.venv/bin/pytest tests/test_analytics_calculator.py -v

# Lint
.venv/bin/ruff check app/ tests/

# Type checking (strict)
.venv/bin/mypy app/
```

**Test coverage by module:**

| Module | Tests | Description |
|---|---|---|
| `test_analytics_calculator.py` | 72 | MAE/RMSE/bias formulas, percentile, CES, edge cases — all with hand-calculated golden values |
| `test_domain_timestamps.py` | 16 | UTC/UK conversion, DST boundaries, delivery window |
| `test_domain_vintage.py` | 9 | Cutoff boundary (inclusive at equality), deduplication, no-vintage error |
| `test_domain_matcher.py` | 17 | Half-hour aggregation, DST window sizes, WIND-only guard, missing data |
| `test_domain_evaluator.py` | — | Integration of the above |
| `test_fuelhh_client.py` | 10 | HTTP retry, validation, WIND filter param |
| `test_windfor_client.py` | 11 | HTTP retry, validation, vintage selection |
| `test_api_*.py` | 5 files | FastAPI TestClient for all five routes |

### Frontend

```bash
cd frontend

# All tests (17)
npm test

# Watch mode
npm run test:watch

# Lint
npm run lint

# Type-check + production build
npm run build
```

Frontend tests use Vitest + React Testing Library. They cover loading states, error banners, null-value display (em-dash guard), stale-response rejection, date-change refetch, and section navigation.

### CI

There is no automated CI pipeline in the current repository. The tests listed above must be run manually. Adding a GitHub Actions workflow is the recommended next step.

---

## Deployment

### Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

Or connect the repository in the Vercel dashboard. Set the build command to `npm run build` and the output directory to `dist`. Set the environment variable `VITE_API_BASE_URL` to the full backend URL if the frontend is deployed separately from the API.

### Backend (any Python host — Fly.io, Railway, Render)

The backend requires a Python 3.11+ runtime. The `Dockerfile` in `backend/` is production-ready (non-root user, minimal base image, health check built in).

Before going live, set the following environment variable on the backend host:

```bash
WINDSIGHT_CORS_ORIGINS=["https://zxcvbn-sable.vercel.app"]
```

Confirm the backend is running:

```bash
curl https://your-backend-url/api/health
# {"status":"ok","version":"0.1.0"}
```

### Public URLs

| Resource | URL |
|---|---|
| GitHub repository | https://github.com/atulsinghhhh/zxcvbn |
| Frontend | https://zxcvbn-sable.vercel.app |
| Backend health | https://zxcvbn-s7pl.onrender.com/api/health |
| Demo video | *add after recording* |

---

## Limitations

| # | Limitation |
|---|---|
| L1 | **Multi-day endpoints are slow.** `/api/overview` and `/api/accuracy` issue two sequential Elexon HTTP calls per day. A 31-day request makes up to 62 sequential calls. Parallelising with `asyncio.gather` (with a concurrency cap to respect Elexon rate limits) is the recommended next step. |
| L2 | **No caching.** Every request re-fetches from Elexon. A Redis or in-process TTL cache keyed by `(delivery_date, cutoff_hour)` would reduce latency and API load significantly. |
| L3 | **No CI pipeline.** Tests must be run manually before each merge. |
| L4 | **WINDFOR granularity assumption.** The Elexon data dictionary does not confirm whether WINDFOR values represent the average or instantaneous generation over the hour. The application assumes average, consistent with FUELHH. The comparison is directionally valid either way. |
| L5 | **Elexon API availability.** Elexon BMRS has no SLA for third-party access. Persistent outages surface as 502/503 responses after three retry attempts. |
| L6 | **Historical data completeness.** Very old WINDFOR vintages (pre-2024) have not been verified for completeness. January 2026 data is the primary validated range. |
| L7 | **Backend port exposed in Docker Compose.** Port 8000 is published directly. For a public deployment, remove the backend `ports:` mapping and route all traffic through the nginx proxy on port 8080. |
