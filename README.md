# RateBot 

> **Live demo → [@RateFetchBot](https://t.me/RateFetchBot)**

A Telegram bot that fetches live currency exchange rates on demand.

Built with **aiogram 3.x** and the free [open.er-api.com](https://www.exchangerate-api.com).

---

## Features

| Command | What it does |
|---|---|
| `/start` | Welcome message with usage instructions |
| `/rates` | Live rates with USD as the base |
| `/rates EUR` | Rates from any supported base currency (in this case EUR)|
| `/subscribe` | Get USD rates automatically every day at 8:00 AM (WAT) |
| `/unsubscribe` | Stop the daily broadcast |
| Inline buttons | Tap USD / EUR / GBP / JPY / CAD / AUD to switch base |

Output always shows 5 major currencies + NGN regardless of the base.

Supported base currencies: `USD` `EUR` `GBP` `JPY` `CAD` `AUD` `CHF` `CNY` `INR` `BRL` `MXN` `ZAR` `SEK` `NOK` `DKK` `SGD` `NGN`

---

## Project structure

```
ratebot/
├── bot.py                 # Entry point — creates Bot, Dispatcher, starts polling
├── handlers/
│   ├── start.py           # /start command
│   ├── rates.py           # /rates command + inline keyboard callbacks
│   └── subscribe.py       # /subscribe + /unsubscribe commands
├── services/
│   ├── exchange.py        # Async HTTP fetch + message formatter
│   ├── subscribers.py     # Saves/loads subscriber chat IDs (JSON file)
│   └── scheduler.py       # APScheduler daily broadcast job
├── Procfile               # Tells Railway to run: worker: python bot.py
├── .env                  
├── requirements.txt
└── README.md
```

The three-layer split (bot → handlers → services) is intentional:
- **handlers** only deal with Telegram — receiving updates, building keyboards, sending replies
- **services** only deal with data — HTTP calls, parsing, formatting
- **bot.py** only deals with wiring — connecting the pieces together

---

## Daily broadcast

Users who send `/subscribe` are added to a list and receive USD rates automatically
every morning at **8:00 AM WAT** (West Africa Time).

**How it works:**

- A Telegram bot can only message a user who has interacted with it first, so
  `/subscribe` saves the user's `chat_id` to `services/subscribers.json`.
- [APScheduler](https://apscheduler.readthedocs.io/) runs *inside* the bot process
  (not as a separate Railway Cron job). Since the bot is already running 24/7 for
  polling, the scheduler shares that same process, bot instance, and subscriber list.
- At 8:00 AM WAT the scheduled job fetches rates **once** and sends them to every
  subscriber. One bad `chat_id` (e.g. a user who blocked the bot) is logged and
  skipped so it can't break the whole broadcast.

**Why not Railway Cron?** Railway Cron spins up a fresh, separate container per run.
That would mean two processes sharing one bot token and no shared subscriber list.
An in-process scheduler is the standard pattern for an always-on bot.

> ⚠️ **Persistence note:** Railway's filesystem is *ephemeral* — `subscribers.json`
> is wiped on every redeploy, so subscribers must re-subscribe after each deploy.
> For durable storage, attach a Railway Volume or use a database.

---