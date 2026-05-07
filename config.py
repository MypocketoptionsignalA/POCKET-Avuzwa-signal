from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
POCKET_SSID = os.getenv("POCKET_SSID")
DEFAULT_AMOUNT = int(os.getenv("DEFAULT_AMOUNT", 10))
USE_DEMO = os.getenv("USE_DEMO", "True").lower() == "true"

TIMEFRAMES = {
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "30s": 30
}
