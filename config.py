import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

ASSETS = {
    "EURUSD_otc": "🇪🇺/🇺🇸 EUR/USD OTC",
    "GBPUSD_otc": "🇬🇧/🇺🇸 GBP/USD OTC",
    "USDJPY_otc": "🇺🇸/🇯🇵 USD/JPY OTC",
    "AUDUSD_otc": "🇦🇺/🇺🇸 AUD/USD OTC",
    "GBPJPY_otc": "🇬🇧/🇯🇵 GBP/JPY OTC",
}

active_assets = {"EURUSD_otc", "GBPUSD_otc", "USDJPY_otc"}
TIMEFRAME = 60
