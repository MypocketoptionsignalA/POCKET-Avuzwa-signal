import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
POCKET_SSID = os.getenv("POCKET_SSID")

DEFAULT_AMOUNT = 10
USE_DEMO = True                     # ← Change to False only when you're ready for REAL money

# Timeframe → Expiration in seconds
TIMEFRAMES = {
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "30s": 30,
    "60s": 60,
}
