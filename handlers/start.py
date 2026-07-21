"""
handlers/start.py
-----------------
Handles the /start command — the first thing a user sees when they open the bot.

In aiogram 3.x, each file creates its own `Router`. A Router is like a mini
dispatcher that owns a group of related handlers. The main bot.py then registers
all routers together. This keeps large bots organised instead of putting every
handler in one giant file.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

# Create a router for this module. bot.py will call dp.include_router(start.router).
router = Router()


# @router.message(...) registers this function as a message handler.
# CommandStart() is a built-in aiogram filter that matches the /start command
# (including deep links like /start ref123). You could also write Command("start")
# but CommandStart is the idiomatic choice for the entry-point command.
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Greet the user and explain what the bot does.

    `message` is the incoming Telegram Message object. It carries everything:
    the text, the user info, the chat info, and methods to reply.

    `message.from_user` is the User who sent the message.
    We fall back to "there" in case the user has no first name set.
    """
    name = message.from_user.first_name or "there"

    # message.answer() sends a reply to the same chat.
    # parse_mode="Markdown" lets us use *bold*, _italic_, and `code` formatting.
    # (We set a global default in bot.py, but being explicit here is fine too.)
    await message.answer(
        f"👋 Hey {name}! I'm *RateBot*.\n\n"
        "I fetch live currency exchange rates so you always know what your money is worth.\n\n"
        "*Commands*\n"
        "• /rates — rates from USD\n"
        "• /rates EUR — rates from any base currency\n\n"
        "Try /rates to get started! 💱",
        parse_mode="Markdown",
    )
