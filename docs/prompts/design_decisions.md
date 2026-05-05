# IMS – Design Prompts & Specifications

This file documents every design decision and prompt used to build this system.

---

## System Design Prompt

> Build a mission-critical Incident Management System (IMS) that:
> - Ingests signals at up to 10,000/sec without crashing
> - Debounces 100 signals per component within 10s into 1 Work Item
> - Manages Work Item lifecycle via State Pattern (OPEN→INVESTIGATING→RESOLVED→CLOSED)
> - Uses Strategy Pattern for P0/P1/P2 alerting
> - Blocks CLOSED transition without complete RCA
> - Auto-calculates MTTR from RCA timestamps
> - Uses MongoDB for raw signal audit log, PostgreSQL for Work Items+RCA, Redis for dashboard cache

---

## Architecture Decisions

### Why asyncio.Queue for the Ring Buffer?
Standard asyncio.Queue is thread-safe and event-loop native. Setting maxsize=100,000 gives us a bounded buffer. We override the "full" behavior to drop the oldest item (ring buffer semantics) instead of blocking – this ensures the HTTP handler is never blocked by a slow database.

### Why Token Bucket for Rate Limiting?
Token bucket allows burst tolerance (unlike fixed window rate limiting). If signals arrive at 500/sec on average but spike to 2000/sec briefly, the bucket absorbs the burst. We set capacity=5×rate to allow 5-second bursts.

### Why Motor for MongoDB?
Motor is the official async MongoDB driver. It integrates natively with asyncio and supports connection pooling. We use it for fire-and-forget raw signal storage.

### Why asyncpg for PostgreSQL?
asyncpg is 3-10× faster than psycopg2 for async workloads. It speaks the PostgreSQL binary protocol directly.

### Why TimescaleDB?
TimescaleDB is a PostgreSQL extension – same connection, same ORM, zero extra service. It adds time-series hypertables for MTTR aggregations and signal frequency queries.

### Debounce Window Algorithm
Each component_id gets a time-windowed bucket. The bucket stores all signals within the window and records the Work Item ID. The first signal triggers Work Item creation. Subsequent signals are linked by Work Item ID. After `debounce_window_seconds`, the bucket expires and a new one starts (new incident).

### State Machine (State Pattern)
Implemented as an immutable value object. `WorkItemStateMachine.transition()` returns a NEW instance rather than mutating state. This makes transitions explicit and testable without side effects.

### Alerting Strategy (Strategy Pattern)
`AlertStrategy` ABC defines the interface. Concrete implementations (`P0CriticalAlert`, `P1HighAlert`, `P2WarningAlert`) are registered in `COMPONENT_STRATEGY_MAP`. The `get_alert_strategy()` factory picks the right one by component type. Adding a new alert type requires only a new class + one line in the map.

### RCA Validation Gate
Validation happens in two places:
1. On `POST /incidents/{id}/rca` – validates the RCA payload before saving
2. On `PATCH /incidents/{id}/status` when target is CLOSED – validates the saved RCA exists and is complete

This double-gate prevents race conditions where a partial RCA could slip through.

---

## Frontend Architecture

### React Query for Server State
React Query handles caching, background refetching (every 5s), and loading/error states. This gives us a "live feed" without WebSockets.

### Zod + React Hook Form for RCA Form
Zod schemas define validation rules that are reused between frontend and can be kept in sync with the backend Pydantic schemas. React Hook Form is performant (uncontrolled inputs) and integrates cleanly with Zod via `@hookform/resolvers`.

### Why Dark Theme?
Incident dashboards are monitored 24/7 by on-call engineers. Dark theme reduces eye strain during night shifts.
