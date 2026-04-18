# Pocket Option Telegram Signal & Auto-Trading Bot

This bot provides real-time trading signals for Pocket Option and can automatically execute trades on your real or demo account using your SSID.

## Features
- **Real-time Signals**: Uses RSI and Bollinger Bands strategy.
- **Auto-Trading**: Automatically places trades on Pocket Option based on signals.
- **Telegram Control**: Start and stop the bot directly from Telegram.
- **Customizable**: Set your own trade amount, duration, and assets.

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Your Pocket Option SSID (found in browser cookies after logging in)

### 2. Installation
```bash
pip install aiogram pocketoptionapi-async pandas pandas_ta
```

### 3. Configuration
Set the following environment variables:
- `TELEGRAM_TOKEN`: Your Telegram bot token.
- `POCKET_OPTION_SSID`: Your Pocket Option SSID.
- `IS_DEMO`: `True` for demo account, `False` for real account.
- `TRADE_AMOUNT`: Amount to invest per trade (e.g., `1.0`).
- `TRADE_DURATION`: Duration of the trade in seconds (e.g., `60`).
- `ASSETS`: Comma-separated list of assets (e.g., `EURUSD_otc,GBPUSD_otc`).

### 4. Running the Bot
```bash
python pocket_option_bot.py
```

### 5. Telegram Commands
- `/start`: Initialize the bot.
- `/run`: Start monitoring and trading.
- `/stop`: Stop the bot.

## Disclaimer
Trading involves risk. Use this bot at your own risk. The developers are not responsible for any financial losses.
