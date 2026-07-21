# RateBot 💱

> **Live demo → [@RateFetchBot](https://t.me/RateFetchBot)**

A Telegram bot that fetches live currency exchange rates on demand.

Built with **aiogram 3.x** and the free [Frankfurter API](https://www.frankfurter.app) — no API key needed.

---

## Features

| Command | What it does |
|---|---|
| `/start` | Welcome message with usage instructions |
| `/rates` | Live rates with USD as the base |
| `/rates EUR` | Rates from any supported base currency |
| Inline buttons | Tap USD / EUR / GBP / JPY / CAD / AUD to switch base instantly |

---

## Project structure

```
ratebot/
├── bot.py                 # Entry point — creates Bot, Dispatcher, starts polling
├── handlers/
│   ├── start.py           # /start command
│   └── rates.py           # /rates command + inline keyboard callbacks
├── services/
│   └── exchange.py        # Async HTTP fetch from Frankfurter + message formatter
├── .env.example           # Copy this to .env and add your bot token
├── requirements.txt
└── README.md
```

The three-layer split (bot → handlers → services) is intentional:
- **handlers** only deal with Telegram — receiving updates, building keyboards, sending replies
- **services** only deal with data — HTTP calls, parsing, formatting
- **bot.py** only deals with wiring — connecting the pieces together

---

## How it works

### The Telegram bot model

Telegram bots work by **polling** or **webhooks**. This bot uses polling:
the bot repeatedly asks Telegram "do you have any new messages for me?" and
processes whatever comes back. Webhooks are more efficient for production but
require a public HTTPS URL — polling is simpler for development and small bots.

### Why aiogram 3.x?

aiogram is the most popular async Python library for Telegram bots. Version 3
was a full rewrite that introduced `Router` objects (so you can split handlers
across files), a filter/middleware system, and proper type hints throughout.
Version 2 is still common in old tutorials but is no longer maintained — always
use 3.x for new projects.

### Why async / aiohttp?

A bot can receive many messages at once. If you used `requests` (synchronous HTTP),
the bot would freeze while waiting for the exchange rate API to respond, blocking
all other users during that time. With `async`/`await` and `aiohttp`, Python can
handle other incoming messages while one user's rate request is in flight.

### How callback queries work

When a user taps an inline keyboard button, Telegram sends a **CallbackQuery**
(not a Message) to the bot. The `callback_data` field contains whatever string
you set when building the button — in this bot, that's `"rates:EUR"` etc.
The handler splits that string to get the currency code, then fetches and
displays new rates by editing the original message in place.

---

## Running locally

**1. Clone and install dependencies**

```bash
git clone https://github.com/yourusername/ratebot.git
cd ratebot
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Create a bot with BotFather**

- Open Telegram and search for `@BotFather`
- Send `/newbot` and follow the prompts
- Copy the token it gives you (looks like `123456789:AAF...`)

**3. Set your token**

```bash
cp .env.example .env
# Open .env in any editor and replace the placeholder:
# BOT_TOKEN=123456789:AAF...
```

**4. Run**

```bash
python bot.py
```

Open Telegram, find your bot, and send `/rates`.

---

## Deploying (Railway)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Add `BOT_TOKEN` as an environment variable under your project's Variables tab
4. Railway auto-detects Python and runs `python bot.py`

The bot will run 24/7. You can then share your live `@yourbotname` handle as a demo.

---

## Tech stack

| Library | Why |
|---|---|
| [aiogram 3.x](https://docs.aiogram.dev/en/latest/) | Async Telegram bot framework — current standard |
| [aiohttp](https://docs.aiohttp.org/) | Async HTTP client (used to call Frankfurter) |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Loads `.env` into environment variables |
| [Frankfurter API](https://www.frankfurter.app) | Free ECB-backed exchange rate data, no key needed |
