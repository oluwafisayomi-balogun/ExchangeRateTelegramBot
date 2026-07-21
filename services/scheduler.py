"""
services/scheduler.py
---------------------
Sets up the scheduled daily rates broadcast.

We use APScheduler (Advanced Python Scheduler) running *inside* the bot process.
This is simpler than Railway Cron because the bot is already running 24/7 for
polling — the scheduler just shares that same running process and bot instance,
so it can reuse the subscriber list and the same Telegram connection.

Timezone: WAT (West Africa Time, UTC+1). We use ZoneInfo("Africa/Lagos") so the
schedule is anchored to WAT regardless of what timezone Railway's server runs in.
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

# WAT has no daylight saving, but using a named zone is still the correct habit —
# it makes the intent explicit and works the same everywhere.
WAT = ZoneInfo("Africa/Lagos")


async def broadcast_rates(bot: Bot) -> None:
    """
    Fetch USD rates once, then send them to every subscriber.

    We fetch a single time (not per-user) to avoid hammering the API. If the fetch
    fails, we log it and skip this run rather than sending a broken message to everyone.
    """
    chat_ids = subscribers.all_subscribers()
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
    Create the scheduler and register the broadcast jobs.

    CronTrigger works like a Unix cron entry. hour=8, minute=0 → 08:00 WAT daily.
    We pass `bot` to the job via `args` so broadcast_rates has something to send with.
    """
    scheduler = AsyncIOScheduler(timezone=WAT)

    # 8:00 AM WAT — the real daily broadcast.
    scheduler.add_job(
        broadcast_rates,
        CronTrigger(hour=8, minute=0, timezone=WAT),
        args=[bot],
        name="daily_rates_8am",
    )

    # 9:35 PM WAT — a temporary test slot so you can confirm it works today.
    # Remove this second job once you've verified the broadcast works.
    scheduler.add_job(
        broadcast_rates,
        CronTrigger(hour=21, minute=35, timezone=WAT),
        args=[bot],
        name="test_rates_935pm",
    )

    scheduler.start()
    logger.info("Scheduler started — broadcasts at 08:00 and 21:35 WAT.")
    return scheduler
