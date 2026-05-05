#  IMS — Incident Management System

A resilient incident management platform that ingests monitoring signals, normalizes them into work items, enforces incident lifecycle rules, and requires Root Cause Analysis before closing incidents.

## Overview

IMS is built to show a modern observability-driven workflow with:
- async signal ingestion via FastAPI
- rate limiting and in-memory buffering for traffic safety
- raw audit logging in MongoDB
- normalized incident state in PostgreSQL/TimescaleDB
- hot-path dashboard caching in Redis
- React frontend for live incident monitoring and RCA submission

## Project structure

```text
ims/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/            # FastAPI route handlers
│   │   ├── core/                  # buffering, rate limiting, worker, metrics
│   │   ├── db/                    # PostgreSQL, MongoDB, Redis adapters
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── workflow/              # state machine and RCA validation
│   │   ├── config.py              # environment-driven settings
│   │   └── main.py                # app factory and lifecycle management
│   ├── tests/                     # backend tests
│   ├── Dockerfile                # backend image build
│   ├── pyproject.toml            # Python package and dependency config
│   └── alembic/                  # PostgreSQL migrations
├── frontend/
│   ├── src/
│   │   ├── api/                   # Axios client and endpoints
│   │   ├── components/            # UI components
│   │   ├── pages/                 # React pages
│   │   ├── types/                 # TypeScript domain definitions
│   │   └── main.tsx               # React bootstrap
│   ├── Dockerfile                # frontend image build
│   ├── package.json
│   └── vite.config.ts            # dev server and proxy config
├── docker-compose.yml            # service composition
├── scripts/                      # helper scripts for seed/load testing
├── Demonstration.pdf             # demonstration of the project with output screenshots
└── README.md                     # project documentation
```

## Architecture


The system is divided into ingestion, processing, storage, cache, and UI layers.

- Ingestion: front-door API receives signals via `POST /signals`
- Rate limiting: protects backend from traffic bursts
- Buffer: in-memory ring buffer decouples HTTP requests from DB writes
- Worker: background drain worker processes signals asynchronously
- Storage: PostgreSQL stores normalized work items and RCA records, MongoDB stores raw   signal audit logs
- Cache: Redis serves fast dashboard reads
- UI: React dashboard consumes backend APIs to display incidents and RCA workflows

## Why this design

- `FastAPI` for fast async HTTP handling and auto-generated docs
- `PostgreSQL` for transactional incident state and relational integrity
- `TimescaleDB` as the PostgreSQL extension for time-series readiness
- `MongoDB` for flexible, append-only raw signal storage
- `Redis` for caching hot dashboard queries
- `React + Vite` for quick frontend development and instant feedback
- `Docker Compose` for local environment reproducibility

## Quick start

### Prerequisites
- Docker Desktop installed

### Start the entire stack

```bash
cd ims
docker compose up --build
```

### Access the app

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Stop the stack

```bash
docker compose down
```
#### Seed failure events

To populate the system with sample incidents, run the seed script:

```bash
python scripts/seed_failure_event.py
```

This sends simulated failure signals to the backend, creating work items and raw audit logs. Watch the frontend dashboard update live.

#### Load testing

To stress-test the ingestion pipeline:

```bash
python scripts/load_test.py
```

This floods the API with 1,000 concurrent signals, testing rate limiting, buffering, and processing. Monitor logs and metrics for performance.

#### Run backend tests

```bash
pytest tests/ -v
```

## Useful commands

```bash

docker compose logs --tail=50 backend
docker compose restart backend
```

## Configuration

The backend configuration is managed in `backend/app/config.py` and uses environment variables via Pydantic settings.

Important variables:

- `DATABASE_URL` — PostgreSQL connection string
- `MONGO_URL` — MongoDB connection string
- `REDIS_URL` — Redis connection string
- `RATE_LIMIT_PER_SEC` — maximum signals per second
- `BUFFER_SIZE` — ring buffer capacity
- `ENVIRONMENT` — runtime environment

The frontend reads `VITE_API_URL` to call the backend API.

## API reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/signals` | Ingest a monitoring signal |
| `GET` | `/incidents` | List all incidents |
| `GET` | `/incidents/{id}` | Get incident details |
| `PATCH` | `/incidents/{id}/status` | Transition incident status |
| `POST` | `/incidents/{id}/rca` | Submit an RCA |
| `GET` | `/incidents/{id}/rca` | Retrieve RCA for an incident |
| `GET` | `/signals/raw/{work_item_id}` | Get raw signals from MongoDB |
| `GET` | `/health` | Liveness/health check |
| `GET` | `/metrics` | App metrics and throughput |

## Example payload

```bash
curl -X POST http://localhost:8000/signals \
  -H "Content-Type: application/json" \
  -d '{
    "component_id": "POSTGRES_PRIMARY",
    "component_type": "RDBMS",
    "error_code": "CONNECTION_TIMEOUT",
    "message": "Primary DB unreachable",
    "severity": "P0"
  }'
```

## How the backend works

### `backend/app/main.py`
- Creates the FastAPI app
- Initializes shared runtime state: ring buffer, debounce engine, metrics, rate limiter
- Starts background workers
- Registers routers and CORS

### `backend/app/core/`
- `buffer.py`: ring buffer implementation for non-blocking ingestion
- `rate_limiter.py`: token bucket rate limiter
- `debounce.py`: deduplicates and groups raw signals
- `worker.py`: drains the buffer and persists events

### `backend/app/db/`
- `postgres.py`: async SQLAlchemy engine and table lifecycle
- `mongo.py`: MongoDB client and raw signal collection
- `redis.py`: Redis cache adapter

### `backend/app/db/models/`
- Work item and RCA ORM models
- PostgreSQL enum status type for incident lifecycle

### `backend/app/workflow/`
- Business rules for status transitions and RCA validation

### `backend/app/api/routes/`
- REST endpoints for signals, incidents, RCA, and health

## Frontend structure

- `frontend/src/api/` — Axios client and typed API wrappers
- `frontend/src/components/` — reusable UI components
- `frontend/src/pages/` — dashboard and incident detail pages
- `frontend/src/types/` — TypeScript models
- `frontend/vite.config.ts` — development proxy and host config


## Troubleshooting

- If the frontend cannot reach the API, confirm the backend is running on `localhost:8000`
- If startup fails, inspect logs:
  ```bash
docker compose logs --tail=50 backend
```
- If DB schema errors appear, ensure migrations are applied before startup

## Design and intent

This repository is intentionally built to demonstrate:
- separation of ingestion and persistence
- asynchronous processing for high-throughput signals
- audit logging separate from normalized state
- enforced RCA before incident closure
- modern full-stack deployment with Docker Compose
