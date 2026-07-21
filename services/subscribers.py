"""
services/subscribers.py
-----------------------
Stores the chat IDs of users who want the daily rates broadcast.

A Telegram bot can only message a user who has previously interacted with it,
and only if we've saved their chat_id. This module keeps that list persistent.

Two storage backends, chosen automatically:
  - Postgres  — used when a DATABASE_URL env var exists (i.e. on Railway).
                Survives redeploys, restarts, and crashes.
  - JSON file — used locally when there's no DATABASE_URL. Zero setup, easy to
                inspect while learning. (Not durable on Railway — the container
                filesystem is wiped on every deploy, which is why we use a DB there.)

Because every function goes through the same three names (add / remove /
all_subscribers), the rest of the app doesn't know or care which backend is active.
That's the payoff of putting storage behind its own module.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Holds the asyncpg connection pool once init_storage() sets it up.
# Stays None when we're running on the JSON-file backend.
_pool = None

# JSON fallback file — lives next to this module (services/ folder).
_FILE = Path(__file__).parent / "subscribers.json"


async def init_storage() -> None:
    """
    Decide which backend to use and prepare it. Called once at startup from bot.py.

    If DATABASE_URL is set, we open an asyncpg connection pool and make sure the
    `subscribers` table exists. Otherwise we do nothing here and the functions
    below fall back to the JSON file.

    Why a "pool"?
      Opening a fresh DB connection for every query is slow. A pool keeps a small
      set of connections open and hands one out per query, then takes it back.
    """
    global _pool
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return  # no DB configured — the JSON fallback will be used

    import asyncpg  # imported lazily so local runs don't need it installed

    _pool = await asyncpg.create_pool(db_url)
    async with _pool.acquire() as conn:
        # BIGINT because Telegram chat IDs can exceed a 32-bit int.
        # PRIMARY KEY means the same chat_id can't be inserted twice.
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS subscribers (chat_id BIGINT PRIMARY KEY)"
        )


# ---------------------------------------------------------------------------
# JSON-file helpers (used only when there's no database configured)
# ---------------------------------------------------------------------------
def _json_load() -> set[int]:
    if not _FILE.exists():
        return set()
    try:
        return set(json.loads(_FILE.read_text()))
    except (json.JSONDecodeError, ValueError):
        return set()


def _json_save(chat_ids: set[int]) -> None:
    _FILE.write_text(json.dumps(sorted(chat_ids)))


# ---------------------------------------------------------------------------
# Public API — async so the same functions can hit either the DB or the file
# ---------------------------------------------------------------------------
async def add(chat_id: int) -> bool:
    """
    Subscribe a chat. Returns True if newly added, False if already subscribed.
    The boolean lets the handler show the right message.
    """
    if _pool:
        async with _pool.acquire() as conn:
            # ON CONFLICT DO NOTHING skips the insert if the chat_id already exists.
            # The command tag is "INSERT 0 1" when a row was added, "INSERT 0 0" if not.
            result = await conn.execute(
                "INSERT INTO subscribers (chat_id) VALUES ($1) ON CONFLICT DO NOTHING",
                chat_id,
            )
            return result.endswith("1")

    chat_ids = _json_load()
    if chat_id in chat_ids:
        return False
    chat_ids.add(chat_id)
    _json_save(chat_ids)
    return True


async def remove(chat_id: int) -> bool:
    """Unsubscribe a chat. Returns True if it was removed, False if it wasn't subscribed."""
    if _pool:
        async with _pool.acquire() as conn:
            # "DELETE 1" if a row was removed, "DELETE 0" if the id wasn't there.
            result = await conn.execute(
                "DELETE FROM subscribers WHERE chat_id = $1", chat_id
            )
            return result.endswith("1")

    chat_ids = _json_load()
    if chat_id not in chat_ids:
        return False
    chat_ids.discard(chat_id)
    _json_save(chat_ids)
    return True


async def all_subscribers() -> set[int]:
    """Return every subscribed chat ID — used by the scheduled broadcast."""
    if _pool:
        async with _pool.acquire() as conn:
            rows = await conn.fetch("SELECT chat_id FROM subscribers")
            return {row["chat_id"] for row in rows}

    return _json_load()
