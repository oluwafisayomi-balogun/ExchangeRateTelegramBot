"""
services/exchange.py
--------------------
Responsible for everything related to fetching and formatting exchange rate data.
Keeping this in a separate module means the handlers never touch HTTP logic directly —
if you ever swap APIs, you only change this file.
"""

# Enables the `X | Y` union type syntax on Python 3.7–3.9.
# Without this, `dict | None` only works on Python 3.10+.
from __future__ import annotations

import aiohttp
from datetime import datetime

# open.er-api.com is a free exchange rate API that includes NGN.
# No API key required. Rates update roughly every hour.
# We switched from Frankfurter because Frankfurter's ECB dataset excludes NGN.
BASE_URL = "https://open.er-api.com/v6/latest"

# Maps ISO 4217 currency codes to their country/region flag emoji.
CURRENCY_FLAGS = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "NGN": "🇳🇬",
    "JPY": "🇯🇵", "CAD": "🇨🇦", "AUD": "🇦🇺", "CHF": "🇨🇭",
    "CNY": "🇨🇳", "INR": "🇮🇳", "BRL": "🇧🇷", "MXN": "🇲🇽",
    "ZAR": "🇿🇦", "KES": "🇰🇪", "GHS": "🇬🇭", "EGP": "🇪🇬",
    "SEK": "🇸🇪", "NOK": "🇳🇴", "DKK": "🇩🇰", "SGD": "🇸🇬",
}

# Currencies users can set as the base (the "from" currency).
# NGN is included here because open.er-api.com supports it as a base.
SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF",
    "CNY", "INR", "BRL", "MXN", "ZAR", "SEK", "NOK",
    "DKK", "SGD", "NGN",
]

# The 6 currencies shown as quick-switch buttons on the inline keyboard.
# When displaying rates, we show whichever 5 of these aren't the base, plus NGN.
QUICK_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]


async def fetch_rates(base: str = "USD") -> dict | None:
    """
    Fetch live exchange rates from open.er-api.com for the given base currency.

    Returns a dict like:
        {"base": "USD", "date": "2024-01-15", "rates": {"EUR": 0.9203, "NGN": 1580.0, ...}}

    Returns None if the request fails for any reason (network error, bad status, etc.).
    The caller decides how to handle a None result — we just signal failure cleanly.

    Why async?
    ----------
    This function is `async` because it does I/O (a network request). In a normal
    (synchronous) function, the entire program would freeze while waiting for the API
    to respond. With `async`, Python can handle other incoming Telegram messages while
    it waits for the HTTP response. `aiohttp` is the async equivalent of `requests`.
    """
    base = base.upper()
    if base not in SUPPORTED_CURRENCIES:
        return None

    url = f"{BASE_URL}/{base}"
    try:
        # `async with` is the async version of `with`. It awaits the setup and
        # teardown of the resource (the HTTP session) without blocking the event loop.
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                # `await` pauses this function here until the response body arrives,
                # but lets other async tasks run in the meantime.
                data = await resp.json()
                if data.get("result") != "success":
                    return None
                # open.er-api.com includes the base itself (e.g. USD: 1.0) in rates.
                # We pop it out so it doesn't appear in the output.
                rates = data["rates"]
                rates.pop(base, None)
                # Parse the full UTC string e.g. "Tue, 21 Jul 2026 00:00:01 +0000"
                # into a clean "21 Jul 2026" label for the message.
                raw_date = data["time_last_update_utc"]
                date = datetime.strptime(raw_date, "%a, %d %b %Y %H:%M:%S %z").strftime("%d %B %Y")
                return {
                    "base": data["base_code"],
                    "date": date,
                    "rates": rates,
                }
    except Exception:
        # Broad catch is intentional: network timeouts, JSON parse errors, etc.
        # all mean the same thing to the caller — "the data isn't available right now."
        return None


def format_rates_message(data: dict) -> str:
    """
    Turn the raw rates dict into a Telegram-ready Markdown string.

    Only shows the top 5 currencies (the QUICK_CURRENCIES that aren't the base)
    plus NGN — keeping the message short and focused.

    Telegram uses a subset of Markdown:
      - *text*  → bold
      - `text`  → monospace / code
      - _text_  → italic
    We use monospace for numbers so they align neatly in the message.
    """
    base = data["base"]
    date = data["date"]
    rates = data["rates"]
    flag = CURRENCY_FLAGS.get(base, "💱")

    lines = [
        f"{flag} {base} Exchange Rates. {date}",
        "",  # blank line before the rate rows
    ]

    # 5 quick currencies (excluding whichever is the current base) + NGN.
    display = [c for c in QUICK_CURRENCIES if c != base]
    if "NGN" not in display and base != "NGN":
        display.append("NGN")

    for code in display:
        rate = rates.get(code)
        if rate is None:
            continue
        currency_flag = CURRENCY_FLAGS.get(code, "  ")
        # Large rates (JPY, NGN) look fine at 2 decimal places.
        # Rates close to 1 (EUR, GBP, CAD) need 4 to show meaningful differences.
        formatted = f"{rate:,.4f}" if rate < 100 else f"{rate:,.2f}"
        lines.append(f"{currency_flag} {code} - {formatted}")

    return "\n".join(lines)
