# CryptoBot

Phase 1 MVP for a cryptocurrency monitoring and Telegram push bot.

## Current scope

- `/start`, `/help`, `/price <symbol>`, `/fear` Telegram commands
- CoinGecko keyless price lookup with richer market snapshot
- Alternative.me Fear & Greed integration
- Startup notification + immediate market summary push
- APScheduler periodic market summary push
- `.env` + `config.yaml` configuration loading
- `loguru` logging

## Quick start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN`.
3. Update `config.yaml` if needed.
4. Run `python -m bot.main`
5. In Telegram, test `/price BTC`, `/price btcusdt`, and `/fear`

## `/price` behavior

- Accepts symbols like `BTC`, `btc`, `BTCUSDT`, `ETHUSD`
- Returns price, 24h change, 24h range, market cap, volume, and data timestamp
- Unsupported symbols return a supported-symbol hint instead of a generic traceback

## Notes

- `TELEGRAM_DEFAULT_CHAT_ID` or `push.chat_id` must be set for scheduled pushes.
- The scheduler starts with the bot process.
- On startup, the bot sends an online notification and an immediate market summary before the regular interval schedule.
