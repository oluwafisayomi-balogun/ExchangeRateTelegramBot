"""
services/subscribers.py
-----------------------
Stores the chat IDs of users who want the daily rates broadcast.

A Telegram bot can only message a user who has previously interacted with it,
and only if we've saved their chat_id. This module keeps that list in a small
JSON file so it survives bot restarts.

Note on Railway:
  Railway's filesystem is *ephemeral* — this JSON file is wiped on every redeploy.
  For a test/learning project that's fine (users just re-subscribe). For real
  persistence you'd attach a Railway Volume or use a database. We keep it simple here.
"""

from __future__ import annotations

import json
from pathlib import Path

# The file lives next to this module. Path(__file__).parent is the services/ folder.
_FILE = Path(__file__).parent / "subscribers.json"


def _load() -> set[int]:
    """Read the JSON file into a set of chat IDs. Returns empty set if missing/corrupt."""
    if not _FILE.exists():
        return set()
    try:
        return set(json.loads(_FILE.read_text()))
    except (json.JSONDecodeError, ValueError):
        # If the file got corrupted somehow, start fresh rather than crashing.
        return set()


def _save(chat_ids: set[int]) -> None:
    """Write the set back to the JSON file (as a list, since JSON has no set type)."""
    _FILE.write_text(json.dumps(sorted(chat_ids)))


def add(chat_id: int) -> bool:
    """
    Subscribe a chat. Returns True if newly added, False if already subscribed.
    The boolean lets the handler show the right message ("subscribed!" vs "already in").
    """
    chat_ids = _load()
    if chat_id in chat_ids:
        return False
    chat_ids.add(chat_id)
    _save(chat_ids)
    return True


def remove(chat_id: int) -> bool:
    """
    Unsubscribe a chat. Returns True if it was removed, False if it wasn't subscribed.
    """
    chat_ids = _load()
    if chat_id not in chat_ids:
        return False
    chat_ids.discard(chat_id)
    _save(chat_ids)
    return True


def all_subscribers() -> set[int]:
    """Return every subscribed chat ID — used by the scheduled broadcast."""
    return _load()
