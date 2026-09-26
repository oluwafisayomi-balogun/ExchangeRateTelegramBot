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
├── bot.py                 # Entry point - creates Bot, Dispatcher, starts polling
├── handlers/
│   ├── start.py           # /start command
│   ├── rates.py           # /rates command + inline keyboard callbacks
│   └── subscribe.py       # /subscribe + /unsubscribe commands
├── services/
│   ├── exchange.py        # Async HTTP fetch + message formatter
│   ├── subscribers.py     # Saves/loads subscriber info (Postgres or JSON file)
│   └── scheduler.py       # APScheduler daily broadcast job
├── Dockerfile             # Container image Fly builds: runs python bot.py
├── fly.toml               # Fly.io app config (1 always-on machine, London)
├── .env                  
├── requirements.txt
└── README.md
```

Three-layer split:
- **handlers** only deal with Telegram - receiving updates, building keyboards, sending replies
- **services** only deal with data - HTTP calls, parsing, formatting
- **bot.py** only deals with wiring - connecting the pieces together

---

## Daily broadcast

Users who send `/subscribe` are added to a list and receive USD rates automatically every morning at **7:00 AM UTC**.

---

## Deployment

Runs on [Fly.io](https://fly.io) as a single always-on machine, with subscribers stored in a free [Neon](https://neon.tech) Postgres database.

```bash
fly secrets set BOT_TOKEN=... DATABASE_URL=...   # one-time
fly deploy --ha=false                             # deploy (keep exactly 1 machine)
fly logs -a ratebot                               # view logs
```
