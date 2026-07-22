"""
bot.py
------
The entry point for RateBot. Run this file to start the bot:
    python bot.py

What happens here-:
  1. Load the bot token from the .env file
  2. Create a Bot instance (the Telegram API client)
  3. Create a Dispatcher (routes incoming updates to the right handler)
  4. Register our handler routers with the Dispatcher
  5. Start polling — the bot repeatedly asks Telegram "any new messages?" and
     dispatches them. This runs forever until you Ctrl+C.
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from handlers import rates, start, subscribe
from services.scheduler import setup_scheduler
from services.subscribers import init_storage

# load_dotenv() reads the .env file and adds its variables to os.environ.
# This must be called before any os.getenv() calls.
load_dotenv()

# Configure Python's built-in logger. INFO level shows connection events and
# handler invocations without the noisy DEBUG output from aiogram internals.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set. Copy .env.example to .env and add your token.")

    # DefaultBotProperties sets defaults applied to every Bot API call.
    # Setting ParseMode.MARKDOWN here means all message.answer() calls will
    # use Markdown formatting unless a handler explicitly overrides it.
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # The Dispatcher is the heart of an aiogram bot. It receives every incoming
    # Telegram update (messages, callbacks, inline queries, etc.) and routes each
    # one to the matching handler function based on the registered filters.
    dp = Dispatcher()

    # Routers are like sub-dispatchers. Including them here wires their handlers
    # into the main Dispatcher. Order matters if two routers could match the same
    # update — the first one wins. start → rates is a logical reading order.
    dp.include_router(start.router)
    dp.include_router(rates.router)
    dp.include_router(subscribe.router)

    # Prepare the subscriber storage. If DATABASE_URL is set (Railway), this opens
    # a Postgres connection pool and creates the table; otherwise it's a no-op and
    # the JSON file is used. Must run before polling so subscriptions can be saved.
    await init_storage()

    # Start the background scheduler for the daily rates broadcast. It runs on the
    # same event loop as the bot, so it must be created after the bot exists but
    # before we begin polling. We keep a reference so it isn't garbage-collected.
    scheduler = setup_scheduler(bot)

    logger.info("RateBot is starting…")

    # start_polling tells Telegram to send us all unprocessed updates since the
    # bot last ran. It runs an infinite loop until the process is killed.
    # `bot` is passed as a keyword argument so handlers can access it if needed.
    await dp.start_polling(bot)


# Standard Python async entry point.
# asyncio.run() creates an event loop, runs main(), then closes the loop cleanly.
if __name__ == "__main__":
    asyncio.run(main())
