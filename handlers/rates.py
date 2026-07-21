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
    Core logic: fetch rates for `base` and send/update the message.

    `target` can be either a Message (from the /rates command) or a
    CallbackQuery (from a button tap). We use isinstance() to handle
    the small differences between the two:
      - A Message needs a new reply sent, then edited with the result.
      - A CallbackQuery needs its existing message edited in place.

    Why edit instead of send a new message?
    Editing keeps the chat clean — tapping USD → EUR → GBP doesn't flood
    the chat with three separate messages.
    """
    base = base.upper()

    if base not in SUPPORTED_CURRENCIES:
        text = (
            f"❌ *{base}* isn't a supported base currency.\n\n"
            f"Supported: `{'`, `'.join(SUPPORTED_CURRENCIES)}`"
        )
        if isinstance(target, Message):
            await target.answer(text, parse_mode="Markdown")
        else:
            # For a CallbackQuery, show_alert=True pops up a small alert
            # dialog instead of silently doing nothing.
            await target.answer(f"{base} is not supported.", show_alert=True)
        return

    if isinstance(target, Message):
        # Send a placeholder first so the user knows something is happening.
        # We keep a reference to it so we can edit it once the data arrives.
        loading = await target.answer("⏳ Fetching rates…")
    else:
        # Calling target.answer() with no arguments acknowledges the callback
        # to Telegram. Without this, Telegram shows a loading spinner on the
        # button indefinitely.
        await target.answer()

    data = await fetch_rates(base)

    if data is None:
        error_text = "⚠️ Couldn't reach the exchange rate API. Try again in a moment."
        if isinstance(target, Message):
            await loading.edit_text(error_text)
        else:
            await target.message.edit_text(error_text)
        return

    text = format_rates_message(data)
    keyboard = build_keyboard(base)

    if isinstance(target, Message):
        # Edit the "⏳ Fetching rates…" placeholder with the real content.
        await loading.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True,  # stops Telegram auto-expanding the Frankfurter link
        )
    else:
        # Edit the message that contains the keyboard the user just tapped.
        await target.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


@router.message(Command("rates"))
async def cmd_rates(message: Message) -> None:
    """
    Handles: /rates  or  /rates EUR

    message.text is the full string the user sent, e.g. "/rates EUR".
    Splitting on whitespace with maxsplit=1 gives ["rates", "EUR"].
    If there's no second part, we default to USD.
    """
    parts = message.text.split(maxsplit=1)
    base = parts[1].strip() if len(parts) > 1 else "USD"
    await send_rates(base, message)


# F.data is an aiogram "magic filter" — it lets you filter CallbackQuery objects
# by their callback_data field. F.data.startswith("rates:") matches any callback
# that was triggered by our keyboard buttons (e.g. "rates:EUR", "rates:GBP").
@router.callback_query(F.data.startswith("rates:"))
async def cb_rates(callback: CallbackQuery) -> None:
    """
    Handles inline keyboard button taps.

    callback.data is the string we set in callback_data when building the keyboard.
    Splitting on ":" gives us ["rates", "EUR"], so index [1] is the currency.
    """
    base = callback.data.split(":")[1]
    await send_rates(base, callback)
