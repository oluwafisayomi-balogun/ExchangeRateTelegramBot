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
| `/subscribe` | Get USD rates automatically every day at 7:00 AM (UTC) |
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
every morning at **7:00 AM UTC**.

**How it works:**

- A Telegram bot can only message a user who has interacted with it first, so
  `/subscribe` saves the user's `chat_id` (see the storage section below).
- [APScheduler](https://apscheduler.readthedocs.io/) runs *inside* the bot process
  (not as a separate Railway Cron job). Since the bot is already running 24/7 for
  polling, the scheduler shares that same process, bot instance, and subscriber list.
- At 7:00 AM UTC the scheduled job fetches rates **once** and sends them to every
  subscriber. One bad `chat_id` (e.g. a user who blocked the bot) is logged and
  skipped so it can't break the whole broadcast.

**Why not Railway Cron?** Railway Cron spins up a fresh, separate container per run.
That would mean two processes sharing one bot token and no shared subscriber list.
An in-process scheduler is the standard pattern for an always-on bot.

### Where subscribers are stored

`services/subscribers.py` picks its storage backend automatically:

| Environment | Backend | Why |
|---|---|---|
| Railway (production) | **PostgreSQL** | Set a `DATABASE_URL` env var and the bot uses Postgres — data survives redeploys, restarts, and crashes. |
| Local (development) | **JSON file** | No `DATABASE_URL`, so it falls back to `subscribers.json` — zero setup, easy to inspect. |

The same three functions (`add` / `remove` / `all_subscribers`) serve both backends,
so the rest of the app never knows which one is active. That's the point of putting
storage behind its own module.

**Setting up Postgres on Railway:**

1. In your Railway project → **New** → **Database** → **Add PostgreSQL**
2. Railway automatically injects a `DATABASE_URL` variable into your bot service
3. Redeploy — on startup the bot connects and creates the `subscribers` table

> Without a `DATABASE_URL`, Railway would fall back to the JSON file, which its
> *ephemeral* filesystem wipes on every redeploy. Postgres is what makes
> subscriptions durable in production.

---