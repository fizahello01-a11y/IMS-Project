"""
main.py
────────
FastAPI application factory.

Lifespan:
  - Creates DB tables on startup
  - Starts ring buffer drain worker
  - Starts metrics printer
  - Cleans up on shutdown
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.buffer import RingBuffer
from app.core.debounce import DebounceEngine
from app.core.metrics import MetricsCollector
from app.core.rate_limiter import TokenBucketLimiter
from app.core.worker import drain_worker
from app.db.postgres import create_tables
from app.db.mongo import ensure_indexes, close_mongo
from app.db.redis import close_redis
from app.api.routes import signals, incidents, rca, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup → run code before `yield`
    Shutdown → run code after `yield`
    """
    logger.info("=== IMS Starting up ===")

    # ── Initialise shared state ──────────────────────────────────────
    app.state.ring_buffer  = RingBuffer(maxsize=settings.buffer_size)
    app.state.debounce     = DebounceEngine()
    app.state.metrics      = MetricsCollector()
    app.state.rate_limiter = TokenBucketLimiter(
        rate=settings.rate_limit_per_sec,
        capacity=settings.rate_limit_per_sec * 5,
    )

    # ── Database setup ───────────────────────────────────────────────
    await create_tables()
    await ensure_indexes()
    logger.info("Databases ready")

    # ── Background tasks ─────────────────────────────────────────────
    drain_task   = asyncio.create_task(drain_worker(
        app.state.ring_buffer,
        app.state.debounce,
        app.state.metrics,
    ))
    metrics_task = asyncio.create_task(app.state.metrics.print_loop())
    debounce_cleanup = asyncio.create_task(_debounce_cleanup_loop(app.state.debounce))

    logger.info("Background workers started. IMS is ready ✓")

    yield   # ← application runs here

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("=== IMS Shutting down ===")
    drain_task.cancel()
    metrics_task.cancel()
    debounce_cleanup.cancel()
    await close_mongo()
    await close_redis()
    logger.info("Shutdown complete")


async def _debounce_cleanup_loop(debounce: DebounceEngine):
    """Runs every 60 seconds to free expired debounce buckets."""
    while True:
        await asyncio.sleep(60)
        await debounce.cleanup_expired()


# ── Create the app ────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Mission-Critical Incident Management System",
    lifespan=lifespan,
)

# ── CORS (allow the React frontend) ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routes ───────────────────────────────────────────────────────────
app.include_router(signals.router)
app.include_router(incidents.router)
app.include_router(rca.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {"message": "IMS API is running", "docs": "/docs"}
