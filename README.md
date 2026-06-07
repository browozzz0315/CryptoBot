# CryptoBot

Phase 1 MVP for a cryptocurrency monitoring and Telegram push bot.

## Current scope

- `/start`, `/help`, `/price <symbol>` Telegram commands
- CoinGecko price lookup
- APScheduler periodic market summary push
- `.env` + `config.yaml` configuration loading
- `loguru` logging

## Quick start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN`.
3. Update `config.yaml` if needed.
4. Run `python -m bot.main`

## Notes

- `TELEGRAM_DEFAULT_CHAT_ID` or `push.chat_id` must be set for scheduled pushes.
- The scheduler starts with the bot process.
