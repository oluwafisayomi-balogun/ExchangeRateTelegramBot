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
│   └── rates.py           # /rates command + inline keyboard callbacks
├── services/
│   └── exchange.py        # Async HTTP fetch + message formatter
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