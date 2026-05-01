import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))

# Pocket Option Settings
POCKET_SSID = os.getenv("POCKET_SSID")

# Trading Settings
DEFAULT_AMOUNT = 10
USE_DEMO = True                    # ← This was missing! Change to False only when ready for real money

# Timeframe = Expiration time in seconds
TIMEFRAMES = {
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "30s": 30,
    "60s": 60,
}
