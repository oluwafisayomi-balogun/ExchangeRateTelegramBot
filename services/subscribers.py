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
from datetime import datetime, timezone
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
        # ADD COLUMN IF NOT EXISTS migrates an already-deployed table in place
        # instead of requiring a drop/recreate (which would lose subscribers).
        await conn.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS username TEXT")
        await conn.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS first_name TEXT")
        await conn.execute("ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_name TEXT")
        await conn.execute(
            "ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS subscribed_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()"
        )


# ---------------------------------------------------------------------------
# JSON-file helpers (used only when there's no database configured)
# ---------------------------------------------------------------------------
def _json_load() -> dict[int, dict]:
    """
    Returns {chat_id: {username, first_name, last_name, subscribed_at}}.

    Older versions of this file stored a plain list of chat_ids — if we find
    that shape, treat each id as a subscriber with no extra info yet.
    """
    if not _FILE.exists():
        return {}
    try:
        raw = json.loads(_FILE.read_text())
    except (json.JSONDecodeError, ValueError):
        return {}

    if isinstance(raw, list):  # legacy format
        return {chat_id: {} for chat_id in raw}
    return {int(chat_id): info for chat_id, info in raw.items()}


def _json_save(subscribers_by_id: dict[int, dict]) -> None:
    _FILE.write_text(json.dumps({str(k): v for k, v in subscribers_by_id.items()}))


# ---------------------------------------------------------------------------
# Public API — async so the same functions can hit either the DB or the file
# ---------------------------------------------------------------------------
async def add(
    chat_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> bool:
    """
    Subscribe a chat. Returns True if newly added, False if already subscribed.
    The boolean lets the handler show the right message.

    username/first_name/last_name come from Telegram's User object and are
    stored alongside the chat_id purely for admin visibility (e.g. browsing
    the table) — the broadcast itself only needs chat_id.
    """
    if _pool:
        async with _pool.acquire() as conn:
            # DO UPDATE keeps name/username fresh even for chats that never
            # unsubscribe. xmax = 0 distinguishes a true insert from a row that
            # already existed and only got its info refreshed via the conflict path.
            row = await conn.fetchrow(
                "INSERT INTO subscribers (chat_id, username, first_name, last_name) "
                "VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (chat_id) DO UPDATE "
                "SET username = $2, first_name = $3, last_name = $4 "
                "RETURNING (xmax = 0) AS inserted",
                chat_id, username, first_name, last_name,
            )
            return row["inserted"]

    subs = _json_load()
    is_new = chat_id not in subs
    existing = subs.get(chat_id, {})
    subs[chat_id] = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "subscribed_at": existing.get("subscribed_at", datetime.now(timezone.utc).isoformat()),
    }
    _json_save(subs)
    return is_new


async def remove(chat_id: int) -> bool:
    """Unsubscribe a chat. Returns True if it was removed, False if it wasn't subscribed."""
    if _pool:
        async with _pool.acquire() as conn:
            # "DELETE 1" if a row was removed, "DELETE 0" if the id wasn't there.
            result = await conn.execute(
                "DELETE FROM subscribers WHERE chat_id = $1", chat_id
            )
            return result.endswith("1")

    subs = _json_load()
    if chat_id not in subs:
        return False
    del subs[chat_id]
    _json_save(subs)
    return True


async def all_subscribers() -> set[int]:
    """Return every subscribed chat ID — used by the scheduled broadcast."""
    if _pool:
        async with _pool.acquire() as conn:
            rows = await conn.fetch("SELECT chat_id FROM subscribers")
            return {row["chat_id"] for row in rows}

    return set(_json_load().keys())
