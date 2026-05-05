"""
db/mongo.py
───────────
MongoDB client using Motor (async MongoDB driver).
Used as the RAW SIGNAL DATA LAKE – every signal is stored here.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_url)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    return get_mongo_client()[settings.mongo_db_name]


async def get_signals_collection():
    """FastAPI dependency – returns the raw_signals collection."""
    db = get_mongo_db()
    return db[settings.mongo_signals_collection]


async def close_mongo():
    global _client
    if _client:
        _client.close()
        _client = None


async def ensure_indexes():
    """Create indexes for fast queries on component_id and timestamp."""
    col = get_mongo_db()[settings.mongo_signals_collection]
    await col.create_index("component_id")
    await col.create_index("work_item_id")
    await col.create_index("received_at")
    await col.create_index([("component_id", 1), ("received_at", -1)])
