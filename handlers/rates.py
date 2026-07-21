"""
handlers/rates.py
-----------------
Handles the /rates command and the inline keyboard button presses.

Two types of updates are handled here:
  1. A Message — the user typed /rates or /rates EUR
  2. A CallbackQuery — the user tapped one of the inline keyboard buttons

Both need the same data (rates for a given base currency) so the core logic
lives in a shared helper `send_rates()` that both handlers call.
"""

# Enables the `X | Y` union type syntax on Python 3.7–3.9.
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from services.exchange import (
    QUICK_CURRENCIES,
    SUPPORTED_CURRENCIES,
    fetch_rates,
    format_rates_message,
)

router = Router()

# Tracks user IDs that currently have a fetch in progress.
# If the same user taps a button while one request is already running,
# we ignore the second tap instead of firing two API calls at once.
# This is an in-memory set — it resets when the bot restarts, which is fine.
_pending: set[int] = set()


def build_keyboard(current_base: str) -> InlineKeyboardMarkup:
    """
    Build the inline keyboard shown below the rates message.

    An InlineKeyboardButton has:
      - `text`          — what the user sees on the button
      - `callback_data` — a short string sent back to the bot when tapped

    We prefix the active currency with ✅ so the user can see which base is selected.

    `InlineKeyboardMarkup` takes a list of rows, where each row is a list of buttons.
    We split 6 buttons into two rows of 3 so it fits on a phone screen.
    """
    buttons = [
        InlineKeyboardButton(
            text=f"{'✅ ' if c == current_base else ''}{c}",
            # callback_data must be ≤64 bytes. "rates:USD" is well within that.
            callback_data=f"rates:{c}",
        )
        for c in QUICK_CURRENCIES
    ]
    rows = [buttons[:3], buttons[3:]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_rates(base: str, target: Message | CallbackQuery) -> None:
    """
    Core logic: fetch rates for `base` and send the result.

    Message flow:
      - /rates command  → send a loading placeholder, then edit it with the result.
      - Button tap      → acknowledge the callback, strip the keyboard off the old
                          message, then send a fresh message with the new rates.
                          This keeps the chat readable without flooding it with edits.

    Throttle:
      Each user gets one in-flight request at a time. If they tap again before the
      first fetch completes, the second tap is silently dropped (callbacks) or ignored
      (messages). The `_pending` set is cleared in a `finally` block so it always
      releases even if the fetch raises an exception.
    """
    user_id = target.from_user.id

    if user_id in _pending:
        if isinstance(target, CallbackQuery):
            # Show a brief toast — doesn't interrupt the chat.
            await target.answer("Already fetching, please wait…")
        return

    _pending.add(user_id)
    try:
        base = base.upper()

        if base not in SUPPORTED_CURRENCIES:
            text = (
                f"❌ {base} isn't a supported base currency.\n\n"
                f"Supported: {', '.join(SUPPORTED_CURRENCIES)}"
            )
            if isinstance(target, Message):
                await target.answer(text)
            else:
                await target.answer(f"{base} is not supported.", show_alert=True)
            return

        if isinstance(target, Message):
            # Send a placeholder so the user knows the bot is working.
            loading = await target.answer("⏳ Fetching rates…")
        else:
            # Acknowledge the callback immediately — Telegram removes the loading
            # spinner on the button as soon as we call this.
            await target.answer()
            # Strip the keyboard off the old message so it's clear the old rates
            # are stale and the new ones are coming in a fresh message below.
            await target.message.edit_reply_markup(reply_markup=None)

        data = await fetch_rates(base)

        if data is None:
            error_text = "⚠️ Couldn't reach the exchange rate API. Try again in a moment."
            if isinstance(target, Message):
                await loading.edit_text(error_text)
            else:
                await target.message.answer(error_text)
            return

        text = format_rates_message(data)
        keyboard = build_keyboard(base)

        if isinstance(target, Message):
            # Replace the "⏳ Fetching rates…" placeholder with the real content.
            await loading.edit_text(text, reply_markup=keyboard)
        else:
            # Send a brand-new message so the conversation scrolls to the latest rates.
            await target.message.answer(text, reply_markup=keyboard)

    finally:
        # Always release the lock, even if an unexpected exception occurred above.
        _pending.discard(user_id)


@router.message(Command("rates"))
async def cmd_rates(message: Message) -> None:
    """
    Handles: /rates  or  /rates EUR

    message.text is the full string the user sent, e.g. "/rates EUR".
    Splitting on whitespace with maxsplit=1 gives ["/rates", "EUR"].
    If there's no second part, we default to USD.
    """
    parts = message.text.split(maxsplit=1)
    base = parts[1].strip() if len(parts) > 1 else "USD"
    await send_rates(base, message)


# F.data is an aiogram "magic filter" — it lets you filter CallbackQuery objects
# by their callback_data field. F.data.startswith("rates:") matches any callback
# triggered by our keyboard buttons (e.g. "rates:EUR", "rates:GBP").
@router.callback_query(F.data.startswith("rates:"))
async def cb_rates(callback: CallbackQuery) -> None:
    """
    Handles inline keyboard button taps.

    callback.data is the string we set in callback_data when building the keyboard.
    Splitting on ":" gives ["rates", "EUR"], so index [1] is the currency.
    """
    base = callback.data.split(":")[1]
    await send_rates(base, callback)
