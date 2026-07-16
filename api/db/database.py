"""
db/database.py — Async MongoDB connection (motor) + JSON file fallback
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv

load_dotenv()

# ── In-memory store (used when MongoDB is unavailable) ─────────────────────────
_DEFAULTS: dict = {"users": [], "orders": [], "subscribers": [], "reviews": []}
_mem: Optional[dict] = None
_client = None
_db = None
_connected = False


async def connect() -> bool:
    global _client, _db, _connected, _mem
    if _connected:
        return True

    uri = os.getenv("MONGODB_URI", "")
    if not uri or "XXXX" in uri or len(uri) < 20:
        print("[mongo] MONGODB_URI not set — using in-memory JSON store")
        _mem = {k: list(v) for k, v in _DEFAULTS.items()}
        return False

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        # Ping to verify connection
        await _client.admin.command("ping")
        _db = _client["ecoplant"]
        _connected = True
        print("[mongo] ✅ Connected to MongoDB")
        return True
    except Exception as e:
        print(f"[mongo] ❌ Connection failed: {e}")
        _mem = {k: list(v) for k, v in _DEFAULTS.items()}
        return False


def is_connected() -> bool:
    return _connected


def get_db():
    """Return the Motor async db handle (raises if not connected)."""
    if not _connected or _db is None:
        raise RuntimeError("MongoDB not connected")
    return _db


# ── JSON / in-memory fallback helpers ─────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "./data/db.json")


def _load_file() -> dict:
    global _mem
    if _mem is not None:
        return _mem
    p = Path(DB_PATH)
    try:
        if p.exists():
            data = json.loads(p.read_text())
            return data
    except Exception:
        pass
    return {k: list(v) for k, v in _DEFAULTS.items()}


def _save_file(data: dict) -> None:
    global _mem
    if _mem is not None:
        _mem = data
        return
    try:
        p = Path(DB_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, default=str))
    except Exception:
        _mem = data


class JsonDB:
    """Synchronous JSON/in-memory fallback database."""

    def get(self, collection: str) -> list:
        return _load_file().get(collection, [])

    def set(self, collection: str, value: list) -> None:
        data = _load_file()
        data[collection] = value
        _save_file(data)

    def push(self, collection: str, item: dict) -> dict:
        data = _load_file()
        data.setdefault(collection, []).append(item)
        _save_file(data)
        return item

    def find_one(self, collection: str, predicate: Callable) -> Optional[dict]:
        for item in self.get(collection):
            if predicate(item):
                return item
        return None

    def update(self, collection: str, predicate: Callable, updater: Callable) -> None:
        data = _load_file()
        data[collection] = [
            {**item, **updater(item)} if predicate(item) else item
            for item in data.get(collection, [])
        ]
        _save_file(data)

    def remove(self, collection: str, predicate: Callable) -> None:
        data = _load_file()
        data[collection] = [
            item for item in data.get(collection, []) if not predicate(item)
        ]
        _save_file(data)


json_db = JsonDB()
