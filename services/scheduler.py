"""
services/scheduler.py
---------------------
Sets up the scheduled daily rates broadcast.

We use APScheduler (Advanced Python Scheduler) running *inside* the bot process.
This is simpler than Railway Cron because the bot is already running 24/7 for
polling — the scheduler just shares that same running process and bot instance,
so it can reuse the subscriber list and the same Telegram connection.

Timezone: UTC. We use ZoneInfo("UTC") so the schedule is anchored to UTC
regardless of what timezone Railway's server happens to run in.
"""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services import subscribers
from services.exchange import fetch_rates, format_rates_message

logger = logging.getLogger(__name__)

# Anchoring to a named zone makes the schedule's intent explicit and keeps it
# stable no matter which timezone the host server is configured with.
UTC = ZoneInfo("UTC")


async def broadcast_rates(bot: Bot) -> None:
    """
    Fetch USD rates once, then send them to every subscriber.

    We fetch a single time (not per-user) to avoid hammering the API. If the fetch
    fails, we log it and skip this run rather than sending a broken message to everyone.
    """
    chat_ids = await subscribers.all_subscribers()
    if not chat_ids:
        logger.info("Broadcast tick: no subscribers, nothing to send.")
        return

    data = await fetch_rates("USD")
    if data is None:
        logger.warning("Broadcast tick: rate fetch failed, skipping this run.")
        return

    text = f"☀️ *Daily Rates*\n\n{format_rates_message(data)}"

    sent = 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text)
            sent += 1
        except Exception as e:
            # A user may have blocked the bot or deleted their chat. Don't let one
            # bad chat_id kill the whole broadcast — log and move on.
            logger.warning("Broadcast: failed to message %s (%s)", chat_id, e)

    logger.info("Broadcast tick: sent to %d/%d subscribers.", sent, len(chat_ids))


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Create the scheduler and register the broadcast job.

    CronTrigger works like a Unix cron entry. hour=7, minute=0 → 07:00 UTC daily.
    We pass `bot` to the job via `args` so broadcast_rates has something to send with.
    """
    scheduler = AsyncIOScheduler(timezone=UTC)

    # 7:00 AM UTC — the daily broadcast.
    scheduler.add_job(
        broadcast_rates,
        CronTrigger(hour=7, minute=0, timezone=UTC),
        args=[bot],
        name="daily_rates_7am_utc",
    )

    scheduler.start()
    logger.info("Scheduler started — broadcast at 07:00 UTC.")
    return scheduler
