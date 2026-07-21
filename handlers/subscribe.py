"""
handlers/subscribe.py
---------------------
Handles /subscribe and /unsubscribe — opting in and out of the daily rates broadcast.

Each command just saves or removes the user's chat_id via the subscribers service.
The scheduled job in bot.py later reads that list and messages everyone on it.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services import subscribers

router = Router()


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    """
    Add the user's chat to the daily broadcast list.

    message.chat.id is the ID we need to message them later. For a private chat
    with the bot, this is the same as the user's own ID.
    """
    added = await subscribers.add(message.chat.id)
    if added:
        await message.answer(
            "✅ Subscribed! You'll get USD rates every day at 7:00 AM (UTC).\n\n"
            "Send /unsubscribe any time to stop."
        )
    else:
        await message.answer("You're already subscribed. Send /unsubscribe to stop.")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message) -> None:
    """Remove the user's chat from the daily broadcast list."""
    removed = await subscribers.remove(message.chat.id)
    if removed:
        await message.answer("🛑 Unsubscribed. You won't get the daily broadcast anymore.")
    else:
        await message.answer("You weren't subscribed. Send /subscribe to opt in.")
